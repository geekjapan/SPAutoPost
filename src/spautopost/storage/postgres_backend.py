"""PostgreSQL backend (正本方言、psycopg 遅延 import)。

正本: openspec/.../specs/storage-* と docs/specs/data-model.md。

方針:
- psycopg はこのモジュールの :func:`build_postgres_storage` 内でのみ import する
  (sqlite 経路では import されない / optional extra)。
- JSON 列は JSONB、timestamp は timestamptz、bool は boolean でネイティブ往復する。
  psycopg は dict/list <-> JSONB を ``Jsonb`` アダプタ経由で、timezone-aware
  datetime <-> timestamptz を自動変換する。
- ``create_if_absent`` は ``INSERT ... ON CONFLICT (idempotency_key) DO NOTHING``
  で race-safe に作成し、衝突時は既存行を読み直す。
- 制約違反 (UNIQUE / NOT NULL / CHECK / FK) は ``ConstraintViolationError`` に
  包む (Secret 非含有のメッセージ)。
- timestamp 復元時は tz-aware UTC に正規化する (DTO の境界検査と一致)。

SQLite backend と共有 contract suite で同一挙動を検証する。
"""

from __future__ import annotations

import json
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import fields
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .errors import ConstraintViolationError, StorageError
from .migrate import DEFAULT_MIGRATIONS_ROOT, run_migrations
from .migrate import pending_migrations as _pending_migrations
from .models import (
    Advisory,
    AuditEvent,
    DraftPost,
    Publication,
    ReviewEvent,
    SourceRecord,
)

if TYPE_CHECKING:
    from .port import StoragePort

# JSON (JSONB) として往復する Sequence/Mapping 系フィールド名 (sqlite と同一集合)。
_JSON_FIELDS: frozenset[str] = frozenset(
    {
        "cve_ids",
        "jvn_ids",
        "vendor_advisory_ids",
        "references",
        "tags",
        "advisory_ids",
        "required_actions",
        "admin_actions",
        "validation_warnings",
        "review_comments",
        "related_ids",
    }
)

# psycopg のパラメタプレースホルダ。
_PLACEHOLDER = "%s"


def _jsonable(value: Any) -> Any:
    """Sequence/Mapping を JSON 化可能な list/dict へ正規化する。"""
    if isinstance(value, Mapping):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


def _field_names(dto_cls: type) -> list[str]:
    return [f.name for f in fields(dto_cls)]


# DTO ごとの datetime フィールド名キャッシュ。
_DATETIME_FIELDS: dict[type, frozenset[str]] = {}


def _datetime_fields(dto_cls: type) -> frozenset[str]:
    cached = _DATETIME_FIELDS.get(dto_cls)
    if cached is None:
        names = {f.name for f in fields(dto_cls) if "datetime" in str(f.type)}
        cached = frozenset(names)
        _DATETIME_FIELDS[dto_cls] = cached
    return cached


def _to_db_value(field_name: str, value: Any) -> Any:
    """DTO の値を psycopg のパラメタ値へ変換する。

    JSONB は :class:`psycopg.types.json.Jsonb` でラップする。timestamptz / boolean
    は psycopg がネイティブに扱うためそのまま渡す。
    """
    if value is None:
        return None
    if field_name in _JSON_FIELDS:
        from psycopg.types.json import Jsonb

        return Jsonb(_jsonable(value))
    return value


def _from_db_value(field_name: str, dto_cls: type, value: Any) -> Any:
    """psycopg の列値を DTO のフィールド値へ復元する。"""
    if value is None:
        return None
    if field_name in _JSON_FIELDS:
        loaded = value if not isinstance(value, str) else json.loads(value)
        return _restore_sequence(field_name, loaded)
    if field_name in _datetime_fields(dto_cls) and isinstance(value, datetime):
        return value.astimezone(UTC)
    return value


def _restore_sequence(field_name: str, loaded: Any) -> Any:
    """JSONB から復元した list/dict を DTO 期待の型へ整える。"""
    if field_name == "related_ids":
        return loaded
    if isinstance(loaded, list):
        return tuple(loaded)
    return loaded


def _wrap_integrity(exc: Exception) -> ConstraintViolationError:
    """psycopg の制約違反例外を Secret 非含有のメッセージで包む。"""
    return ConstraintViolationError(f"constraint violation: {type(exc).__name__}")


class _TxState:
    """トランザクション境界の状態を保持する可変ホルダ。

    ``transaction()`` スコープ内では ``in_transaction`` が True になり、各 repository
    の書き込みは個別 commit を抑止する。これにより複数操作が 1 つの原子的な作業単位
    として扱われ、途中失敗時にスコープ全体が rollback される。
    """

    __slots__ = ("in_transaction",)

    def __init__(self) -> None:
        self.in_transaction = False


class _Repository:
    """単一テーブル向けの汎用 CRUD 実装 (psycopg)。"""

    def __init__(self, conn: Any, table: str, dto_cls: type, pk: str, tx_state: _TxState) -> None:
        self._conn = conn
        self._table = table
        self._dto_cls = dto_cls
        self._pk = pk
        self._tx_state = tx_state
        self._columns = _field_names(dto_cls)

    def _maybe_commit(self) -> None:
        """トランザクションスコープ外でのみ commit する (スコープ内は CM が担う)。"""
        if not self._tx_state.in_transaction:
            self._conn.commit()

    def _maybe_rollback(self) -> None:
        """トランザクションスコープ外でのみ rollback する。

        スコープ内では例外を ``transaction()`` CM まで伝播させ、CM が作業単位全体を
        rollback する (個別操作のみの巻き戻しを避ける)。
        """
        if not self._tx_state.in_transaction:
            self._conn.rollback()

    def _integrity_error(self) -> type[Exception]:
        import psycopg

        error_cls: type[Exception] = psycopg.errors.IntegrityError
        return error_cls

    def _row_to_dto(self, row: Mapping[str, Any]) -> Any:
        kwargs = {name: _from_db_value(name, self._dto_cls, row[name]) for name in self._columns}
        return self._dto_cls(**kwargs)

    def _insert(self, dto: Any, *, on_conflict_update: bool) -> Any:
        cols = self._columns
        placeholders = ", ".join(_PLACEHOLDER for _ in cols)
        quoted = ", ".join(f'"{c}"' for c in cols)
        values = [_to_db_value(c, getattr(dto, c)) for c in cols]
        suffix = ""
        if on_conflict_update:
            updates = ", ".join(f'"{c}" = EXCLUDED."{c}"' for c in cols if c != self._pk)
            suffix = f" ON CONFLICT ({self._pk}) DO UPDATE SET {updates}"
        sql = (
            f"INSERT INTO {self._table} ({quoted}) "  # noqa: S608
            f"VALUES ({placeholders}){suffix}"
        )
        try:
            with self._conn.cursor() as cur:
                cur.execute(sql, values)
            self._maybe_commit()
        except self._integrity_error() as exc:
            self._maybe_rollback()
            raise _wrap_integrity(exc) from exc
        return dto

    def get(self, key: str) -> Any:
        # 識別子 (table/pk) は内部定数のみ。値は常にプレースホルダ。S608 は誤検知。
        with self._conn.cursor() as cur:
            cur.execute(
                f"SELECT * FROM {self._table} "  # noqa: S608
                f"WHERE {self._pk} = {_PLACEHOLDER}",
                (key,),
            )
            row = cur.fetchone()
        return self._row_to_dto(row) if row is not None else None

    def list(self, *, limit: int = 100, offset: int = 0) -> Sequence[Any]:
        with self._conn.cursor() as cur:
            cur.execute(
                f"SELECT * FROM {self._table} "  # noqa: S608
                f"ORDER BY created_at ASC, {self._pk} ASC "
                f"LIMIT {_PLACEHOLDER} OFFSET {_PLACEHOLDER}",
                (limit, offset),
            )
            rows = cur.fetchall()
        return [self._row_to_dto(r) for r in rows]


class _UpsertRepository(_Repository):
    """upsert (INSERT ... ON CONFLICT DO UPDATE) を露出する repository。"""

    def upsert(self, dto: Any) -> Any:
        return self._insert(dto, on_conflict_update=True)


class _AppendOnlyRepository(_Repository):
    """append-only repository (append のみ、upsert を露出しない)。"""

    def append(self, dto: Any) -> Any:
        return self._insert(dto, on_conflict_update=False)


class _PublicationRepository(_Repository):
    """publications 用 repository (idempotency 制約付き)。"""

    def upsert(self, dto: Publication) -> Publication:
        self._insert(dto, on_conflict_update=True)
        return dto

    def create_if_absent(self, publication: Publication) -> tuple[Publication, bool]:
        """``ON CONFLICT (idempotency_key) DO NOTHING`` で race-safe に作成する。"""
        cols = self._columns
        placeholders = ", ".join(_PLACEHOLDER for _ in cols)
        quoted = ", ".join(f'"{c}"' for c in cols)
        values = [_to_db_value(c, getattr(publication, c)) for c in cols]
        sql = (
            f"INSERT INTO {self._table} ({quoted}) "  # noqa: S608
            f"VALUES ({placeholders}) "
            "ON CONFLICT (idempotency_key) DO NOTHING "
            f"RETURNING {self._pk}"
        )
        try:
            with self._conn.cursor() as cur:
                cur.execute(sql, values)
                inserted = cur.fetchone() is not None
            self._maybe_commit()
        except self._integrity_error() as exc:
            self._maybe_rollback()
            raise _wrap_integrity(exc) from exc
        if inserted:
            return publication, True
        existing = self.get_by_idempotency_key(publication.idempotency_key)
        if existing is None:  # pragma: no cover - 競合直後の理論的すり抜け
            raise StorageError("create_if_absent conflict but row not found on re-read")
        return existing, False

    def get_by_idempotency_key(self, idempotency_key: str) -> Publication | None:
        with self._conn.cursor() as cur:
            cur.execute(
                f"SELECT * FROM {self._table} "  # noqa: S608
                f"WHERE idempotency_key = {_PLACEHOLDER}",
                (idempotency_key,),
            )
            row = cur.fetchone()
        return self._row_to_dto(row) if row is not None else None


class PostgresStorage:
    """``StoragePort`` を満たす PostgreSQL backend。"""

    def __init__(
        self,
        database_url: str,
        *,
        migrations_root: Path = DEFAULT_MIGRATIONS_ROOT,
    ) -> None:
        import psycopg
        from psycopg.rows import dict_row

        self._migrations_root = migrations_root
        # row_factory=dict_row で列名アクセスを sqlite_backend と揃える。
        # 接続失敗は Secret 非含有のメッセージへ正規化する (database_url が
        # traceback / locals キャプチャ経由で漏れるのを防ぐため StorageError に包む)。
        try:
            self._conn = psycopg.connect(database_url, row_factory=dict_row)
        except psycopg.OperationalError as exc:
            raise StorageError(
                "postgresql connection failed: check database_url and network reachability"
            ) from exc
        self._tx_state = _TxState()
        tx = self._tx_state
        self._source_records = _UpsertRepository(
            self._conn, "source_records", SourceRecord, "source_record_id", tx
        )
        self._advisories = _UpsertRepository(self._conn, "advisories", Advisory, "advisory_id", tx)
        self._draft_posts = _UpsertRepository(self._conn, "draft_posts", DraftPost, "draft_id", tx)
        self._review_events = _AppendOnlyRepository(
            self._conn, "review_events", ReviewEvent, "review_event_id", tx
        )
        self._publications = _PublicationRepository(
            self._conn, "publications", Publication, "publication_id", tx
        )
        self._audit_events = _AppendOnlyRepository(
            self._conn, "audit_events", AuditEvent, "audit_event_id", tx
        )

    @property
    def source_records(self) -> _UpsertRepository:
        return self._source_records

    @property
    def advisories(self) -> _UpsertRepository:
        return self._advisories

    @property
    def draft_posts(self) -> _UpsertRepository:
        return self._draft_posts

    @property
    def review_events(self) -> _AppendOnlyRepository:
        return self._review_events

    @property
    def publications(self) -> _PublicationRepository:
        return self._publications

    @property
    def audit_events(self) -> _AppendOnlyRepository:
        return self._audit_events

    def migrate(self) -> None:
        run_migrations(
            self._conn,
            self._migrations_root,
            "postgresql",
            placeholder=_PLACEHOLDER,
        )

    def pending_migrations(self) -> list[str]:
        return _pending_migrations(self._conn, self._migrations_root, "postgresql")

    @contextmanager
    def transaction(self) -> Iterator[None]:
        """複数 repository 操作を 1 つの原子的な作業単位として束ねる。

        スコープ内では各 operation の個別 commit が抑止され、スコープ正常終了時に
        まとめて commit、途中で例外が出た場合は作業単位全体を rollback する。
        ネストは想定しない (単一スレッド/単一接続)。
        """
        self._tx_state.in_transaction = True
        try:
            yield
            self._tx_state.in_transaction = False
            self._conn.commit()
        except Exception:
            self._tx_state.in_transaction = False
            self._conn.rollback()
            raise

    def close(self) -> None:
        self._conn.close()


def build_postgres_storage(
    database_url: str,
    *,
    migrations_root: Path = DEFAULT_MIGRATIONS_ROOT,
) -> StoragePort:
    """PostgreSQL backend を構築する (factory から利用)。

    psycopg はこの関数から構築する :class:`PostgresStorage` 内で import する
    (sqlite 経路では import されない)。psycopg 未導入時は ``StorageError``。
    """
    try:
        import psycopg  # noqa: F401  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - CI でのみ通る経路
        raise StorageError(
            "psycopg is required for the postgresql backend; install the 'postgres' optional extra"
        ) from exc

    return PostgresStorage(database_url, migrations_root=migrations_root)
