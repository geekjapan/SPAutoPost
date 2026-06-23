"""二方言 baseline スキーマの構造的等価性テスト (DB 不要)。

正本: openspec/.../specs/storage-migration「二重ファイルドリフトのスキーマ等価
ガード」。PostgreSQL (db/migrations/postgres/0001_baseline.sql) と SQLite
(db/migrations/sqlite/0001_baseline.sql) の baseline を解析し、以下の集合が
等価であることを構造的に検証する:

- テーブル集合
- テーブルごとの列集合 (列名)
- CHECK enum 集合 (列ごとに許容される文字列リテラル値の集合)
- FK 集合 ((子テーブル, 子列, 親テーブル, 親列))
- UNIQUE index 集合 ((index 名, テーブル, 列))

方言型の差異 (JSONB/timestamptz/numeric/boolean <-> TEXT/REAL/INTEGER) は
許容する。型名は比較対象に含めない。DB は不要でローカル CI 双方で実行可能。
"""

from __future__ import annotations

import re
from pathlib import Path

# プロジェクトルート (tests/storage/ から 2 つ上)。
_ROOT = Path(__file__).resolve().parents[2]
_POSTGRES_SQL = _ROOT / "db" / "migrations" / "postgres" / "0001_baseline.sql"
_SQLITE_SQL = _ROOT / "db" / "migrations" / "sqlite" / "0001_baseline.sql"


def _strip_line_comments(sql: str) -> str:
    """``--`` 行コメントを除去する (リテラル内に ``--`` は含まれない前提)。"""
    lines: list[str] = []
    for line in sql.splitlines():
        idx = line.find("--")
        lines.append(line if idx < 0 else line[:idx])
    return "\n".join(lines)


def _split_top_level_commas(body: str) -> list[str]:
    """括弧深度 0 のカンマで本体を分割する (CHECK(...) 内のカンマを保護)。"""
    parts: list[str] = []
    depth = 0
    current: list[str] = []
    for ch in body:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append("".join(current))
            current = []
        else:
            current.append(ch)
    if current:
        parts.append("".join(current))
    return parts


def _parse_create_tables(sql: str) -> dict[str, str]:
    """``CREATE TABLE <name> ( <body> )`` を {table: body} で返す。"""
    tables: dict[str, str] = {}
    pattern = re.compile(
        r"CREATE\s+TABLE\s+(\w+)\s*\((.*?)\)\s*;",
        re.IGNORECASE | re.DOTALL,
    )
    for match in pattern.finditer(sql):
        tables[match.group(1)] = match.group(2)
    return tables


def _column_name(clause: str) -> str | None:
    """列定義句から列名を返す。テーブル制約句 (FOREIGN KEY 等) は None。"""
    stripped = clause.strip()
    if not stripped:
        return None
    first = stripped.split(None, 1)[0]
    upper = first.upper()
    if upper in {"FOREIGN", "PRIMARY", "UNIQUE", "CHECK", "CONSTRAINT"}:
        return None
    return first.strip('"')


def _columns_of(body: str) -> set[str]:
    names: set[str] = set()
    for clause in _split_top_level_commas(body):
        name = _column_name(clause)
        if name is not None:
            names.add(name)
    return names


_CHECK_LITERAL = re.compile(r"'((?:[^']|'')*)'")


def _check_enums_of(table: str, body: str) -> dict[tuple[str, str], frozenset[str]]:
    """列ごとの CHECK enum リテラル集合を {(table, column): {values}} で返す。

    リテラルを持たない CHECK (boolean の TRUE/FALSE 等) は集合が空になるため
    結果から除外し、enum 制約のみを比較対象とする。
    """
    result: dict[tuple[str, str], frozenset[str]] = {}
    for clause in _split_top_level_commas(body):
        column = _column_name(clause)
        if column is None or "CHECK" not in clause.upper():
            continue
        values = {m.group(1) for m in _CHECK_LITERAL.finditer(clause)}
        if values:
            result[(table, column)] = frozenset(values)
    return result


_FK_RE = re.compile(
    r"FOREIGN\s+KEY\s*\(\s*(\w+)\s*\)\s*REFERENCES\s+(\w+)\s*\(\s*(\w+)\s*\)",
    re.IGNORECASE,
)


def _foreign_keys_of(table: str, body: str) -> set[tuple[str, str, str, str]]:
    """(child_table, child_column, parent_table, parent_column) の集合を返す。"""
    fks: set[tuple[str, str, str, str]] = set()
    for clause in _split_top_level_commas(body):
        match = _FK_RE.search(clause)
        if match is not None:
            fks.add((table, match.group(1), match.group(2), match.group(3)))
    return fks


_UNIQUE_INDEX_RE = re.compile(
    r"CREATE\s+UNIQUE\s+INDEX\s+(\w+)\s+ON\s+(\w+)\s*\(\s*([\w,\s]+?)\s*\)\s*;",
    re.IGNORECASE | re.DOTALL,
)


def _unique_indexes_of(sql: str) -> set[tuple[str, str, str]]:
    """(index_name, table, normalized_columns) の集合を返す。"""
    indexes: set[tuple[str, str, str]] = set()
    for match in _UNIQUE_INDEX_RE.finditer(sql):
        cols = ",".join(c.strip() for c in match.group(3).split(","))
        indexes.add((match.group(1), match.group(2), cols))
    return indexes


# UNIQUE / 非 UNIQUE を問わず全 index を捕捉 (FK インデックスを含む)。
_ANY_INDEX_RE = re.compile(
    r"CREATE\s+(?:UNIQUE\s+)?INDEX\s+(\w+)\s+ON\s+(\w+)\s*\(\s*([\w,\s]+?)\s*\)\s*;",
    re.IGNORECASE | re.DOTALL,
)


def _all_indexes_of(sql: str) -> set[tuple[str, str, str]]:
    """(index_name, table, normalized_columns) の集合を返す (UNIQUE 含む全 index)。"""
    indexes: set[tuple[str, str, str]] = set()
    for match in _ANY_INDEX_RE.finditer(sql):
        cols = ",".join(c.strip() for c in match.group(3).split(","))
        indexes.add((match.group(1), match.group(2), cols))
    return indexes


def _parse(path: Path) -> dict[str, object]:
    sql = _strip_line_comments(path.read_text(encoding="utf-8"))
    tables = _parse_create_tables(sql)
    columns = {t: _columns_of(body) for t, body in tables.items()}
    check_enums: dict[tuple[str, str], frozenset[str]] = {}
    foreign_keys: set[tuple[str, str, str, str]] = set()
    for table, body in tables.items():
        check_enums.update(_check_enums_of(table, body))
        foreign_keys |= _foreign_keys_of(table, body)
    return {
        "tables": set(tables),
        "columns": columns,
        "check_enums": check_enums,
        "foreign_keys": foreign_keys,
        "unique_indexes": _unique_indexes_of(sql),
        "all_indexes": _all_indexes_of(sql),
    }


def test_baseline_files_exist() -> None:
    assert _POSTGRES_SQL.is_file()
    assert _SQLITE_SQL.is_file()


def test_table_sets_are_equal() -> None:
    pg = _parse(_POSTGRES_SQL)
    lite = _parse(_SQLITE_SQL)
    assert pg["tables"] == lite["tables"]
    # 6 ルートエンティティが揃っていることを保証 (回帰防止)。
    assert pg["tables"] == {
        "source_records",
        "advisories",
        "draft_posts",
        "review_events",
        "publications",
        "audit_events",
    }


def test_column_sets_are_equal_per_table() -> None:
    pg = _parse(_POSTGRES_SQL)["columns"]
    lite = _parse(_SQLITE_SQL)["columns"]
    assert pg == lite


def test_check_enum_sets_are_equal() -> None:
    pg = _parse(_POSTGRES_SQL)["check_enums"]
    lite = _parse(_SQLITE_SQL)["check_enums"]
    assert pg == lite


def test_audit_event_type_has_15_values() -> None:
    pg = _parse(_POSTGRES_SQL)["check_enums"]
    enum = pg[("audit_events", "event_type")]  # type: ignore[index]
    assert len(enum) == 15


def test_foreign_key_sets_are_equal() -> None:
    pg = _parse(_POSTGRES_SQL)["foreign_keys"]
    lite = _parse(_SQLITE_SQL)["foreign_keys"]
    assert pg == lite


def test_unique_index_sets_are_equal() -> None:
    pg = _parse(_POSTGRES_SQL)["unique_indexes"]
    lite = _parse(_SQLITE_SQL)["unique_indexes"]
    assert pg == lite
    assert (
        "ux_publications_idempotency_key",
        "publications",
        "idempotency_key",
    ) in pg  # type: ignore[operator]


def test_index_sets_are_equal_across_dialects() -> None:
    pg = _parse(_POSTGRES_SQL)["all_indexes"]
    lite = _parse(_SQLITE_SQL)["all_indexes"]
    assert pg == lite


def test_all_foreign_keys_have_supporting_index() -> None:
    """全 FK 列に対応するインデックスが存在すること (spec ルール: FK は常にインデックス化)。"""
    parsed = _parse(_POSTGRES_SQL)
    foreign_keys = parsed["foreign_keys"]
    indexes = parsed["all_indexes"]
    indexed_cols = {(table, cols) for _name, table, cols in indexes}  # type: ignore[misc]
    for child_table, child_col, _parent_table, _parent_col in foreign_keys:  # type: ignore[misc]
        assert (child_table, child_col) in indexed_cols, (
            f"FK {child_table}.{child_col} に対応するインデックスが無い"
        )
