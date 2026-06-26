"""SQLite backend (ローカル/テスト用、stdlib sqlite3、新規依存なし)。

正本: openspec/.../specs/storage-* と docs/specs/data-model.md。

方針:
- ``PRAGMA foreign_keys=ON`` で FK を強制する。
- JSON 列は ``json.dumps`` の TEXT。timestamp は正準 ISO-8601 UTC 文字列
  (``isoformat(timespec='seconds')``、例 ``2024-01-01T00:00:00+00:00``)。
- bool は INTEGER 0/1。
- ``create_if_absent`` は単一ライター (逐次) で整合を保つ。
- 制約違反 (UNIQUE / NOT NULL / CHECK / FK) は ``ConstraintViolationError`` に包む。

PostgreSQL backend (Block 9) と共有 contract suite で同一挙動を検証する。
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import fields
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from .errors import ConstraintViolationError
from .migrate import DEFAULT_MIGRATIONS_ROOT, run_migrations
from .migrate import pending_migrations as _pending_migrations
from .models import (
    AdminCommand,
    Advisory,
    AuditEvent,
    DraftPost,
    Publication,
    ReviewEvent,
    SourceRecord,
)

# JSON (TEXT) として往復する Sequence/Mapping 系フィールド名。
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
        "payload",
    }
)

# bool として往復する (INTEGER 0/1) フィールド名。
_BOOL_FIELDS: frozenset[str] = frozenset({"retryable"})


def _field_names(dto_cls: type) -> list[str]:
    return [f.name for f in fields(dto_cls)]


def _to_db_value(field_name: str, value: Any) -> Any:
    """DTO の値を SQLite 列値へ変換する。"""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds")
    if field_name in _BOOL_FIELDS:
        return 1 if value else 0
    if field_name in _JSON_FIELDS:
        return json.dumps(_jsonable(value), ensure_ascii=False, sort_keys=False)
    return value


def _jsonable(value: Any) -> Any:
    """Sequence/Mapping を JSON 化可能な list/dict へ正規化する。"""
    if isinstance(value, Mapping):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


def _from_db_value(field_name: str, dto_cls: type, value: Any) -> Any:
    """SQLite 列値を DTO のフィールド値へ復元する。"""
    if value is None:
        return None
    if field_name in _BOOL_FIELDS:
        return bool(value)
    if field_name in _JSON_FIELDS:
        loaded = json.loads(value)
        return _restore_sequence(field_name, loaded)
    if _is_datetime_field(dto_cls, field_name):
        return datetime.fromisoformat(value)
    return value


# DTO ごとの datetime フィールド名キャッシュ。
_DATETIME_FIELDS: dict[type, frozenset[str]] = {}


def _is_datetime_field(dto_cls: type, field_name: str) -> bool:
    cached = _DATETIME_FIELDS.get(dto_cls)
    if cached is None:
        names: set[str] = set()
        for f in fields(dto_cls):
            ann = str(f.type)
            if "datetime" in ann:
                names.add(f.name)
        cached = frozenset(names)
        _DATETIME_FIELDS[dto_cls] = cached
    return field_name in cached


def _restore_sequence(field_name: str, loaded: Any) -> Any:
    """JSON から復元した list/dict を DTO 期待の型へ整える。

    DTO の Sequence フィールドは tuple を既定とするため tuple 化する
    (references / related_ids のような Mapping 群は内容を保持)。
    """
    if field_name == "related_ids":
        return loaded
    if isinstance(loaded, list):
        return tuple(loaded)
    return loaded


def _wrap_integrity(exc: sqlite3.IntegrityError) -> ConstraintViolationError:
    """sqlite3.IntegrityError を Secret 非含有のメッセージで包む。"""
    return ConstraintViolationError(f"constraint violation: {exc}")


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
    """単一テーブル向けの汎用 CRUD 実装 (upsert/get/list)。"""

    def __init__(
        self,
        conn: sqlite3.Connection,
        table: str,
        dto_cls: type,
        pk: str,
        tx_state: _TxState,
    ) -> None:
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

    def _row_to_dto(self, row: Any) -> Any:
        kwargs = {name: _from_db_value(name, self._dto_cls, row[name]) for name in self._columns}
        return self._dto_cls(**kwargs)

    def _insert_or_replace(self, dto: Any, *, replace: bool) -> Any:
        cols = self._columns
        placeholders = ", ".join("?" for _ in cols)
        quoted = ", ".join(f'"{c}"' for c in cols)
        verb = "INSERT OR REPLACE" if replace else "INSERT"
        values = [_to_db_value(c, getattr(dto, c)) for c in cols]
        try:
            self._conn.execute(
                f"{verb} INTO {self._table} ({quoted}) VALUES ({placeholders})",
                values,
            )
            self._maybe_commit()
        except sqlite3.IntegrityError as exc:
            self._maybe_rollback()
            raise _wrap_integrity(exc) from exc
        return dto

    def get(self, key: str) -> Any:
        # 識別子 (table/pk) は内部定数のみ。値は常にプレースホルダ。S608 は誤検知。
        cur = self._conn.execute(
            f"SELECT * FROM {self._table} WHERE {self._pk} = ?",  # noqa: S608
            (key,),
        )
        row = cur.fetchone()
        return self._row_to_dto(row) if row is not None else None

    def list(self, *, limit: int = 100, offset: int = 0) -> Sequence[Any]:
        cur = self._conn.execute(
            f"SELECT * FROM {self._table} "  # noqa: S608
            f"ORDER BY created_at ASC, {self._pk} ASC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        return [self._row_to_dto(r) for r in cur.fetchall()]


class _UpsertRepository(_Repository):
    """upsert (INSERT OR REPLACE) を露出する repository。"""

    def upsert(self, dto: Any) -> Any:
        return self._insert_or_replace(dto, replace=True)


class _AppendOnlyRepository(_Repository):
    """append-only repository (append のみ、upsert を露出しない)。"""

    def append(self, dto: Any) -> Any:
        return self._insert_or_replace(dto, replace=False)


class _PublicationRepository(_Repository):
    """publications 用 repository (idempotency 制約付き)。"""

    def upsert(self, dto: Publication) -> Publication:
        # idempotency_key の UNIQUE を尊重するため、PK 更新は許容するが、
        # 別 PK が同一 idempotency_key を取ると UNIQUE 違反になる (テスト期待)。
        existing = self.get(dto.publication_id)
        if existing is None:
            self._insert_or_replace(dto, replace=False)
            return dto
        return self._update(dto)

    def _update(self, dto: Publication) -> Publication:
        cols = [c for c in self._columns if c != self._pk]
        assignments = ", ".join(f'"{c}" = ?' for c in cols)
        values = [_to_db_value(c, getattr(dto, c)) for c in cols]
        values.append(getattr(dto, self._pk))
        try:
            self._conn.execute(
                # 識別子は内部定数、値はプレースホルダ。S608 は誤検知。
                f"UPDATE {self._table} SET {assignments} "  # noqa: S608
                f"WHERE {self._pk} = ?",
                values,
            )
            self._maybe_commit()
        except sqlite3.IntegrityError as exc:
            self._maybe_rollback()
            raise _wrap_integrity(exc) from exc
        return dto

    def create_if_absent(self, publication: Publication) -> tuple[Publication, bool]:
        """単一ライター (逐次) で idempotency_key 単位の作成を行う。"""
        existing = self.get_by_idempotency_key(publication.idempotency_key)
        if existing is not None:
            return existing, False
        self._insert_or_replace(publication, replace=False)
        return publication, True

    def get_by_idempotency_key(self, idempotency_key: str) -> Publication | None:
        cur = self._conn.execute(
            f"SELECT * FROM {self._table} "  # noqa: S608
            "WHERE idempotency_key = ?",
            (idempotency_key,),
        )
        row = cur.fetchone()
        return self._row_to_dto(row) if row is not None else None


class _AdminCommandRepository(_Repository):
    """admin_commands 用 repository (append-only queue + claim)。"""

    def append(self, command: AdminCommand) -> AdminCommand:
        return cast(AdminCommand, self._insert_or_replace(command, replace=False))

    def claim_pending(
        self,
        *,
        command_type: str | None = None,
        limit: int = 100,
    ) -> Sequence[AdminCommand]:
        if self._tx_state.in_transaction:
            return self._claim_pending_locked(command_type, limit)
        self._conn.execute("BEGIN IMMEDIATE")
        self._tx_state.in_transaction = True
        try:
            commands = self._claim_pending_locked(command_type, limit)
            self._tx_state.in_transaction = False
            self._conn.commit()
            return commands
        except Exception:
            self._tx_state.in_transaction = False
            self._conn.rollback()
            raise

    def _claim_pending_locked(self, command_type: str | None, limit: int) -> Sequence[AdminCommand]:
        if command_type is not None:
            cur = self._conn.execute(
                f"SELECT * FROM {self._table} "  # noqa: S608
                "WHERE status = 'pending' AND command_type = ? "
                "ORDER BY created_at ASC, command_id ASC LIMIT ?",
                (command_type, limit),
            )
        else:
            cur = self._conn.execute(
                f"SELECT * FROM {self._table} "  # noqa: S608
                "WHERE status = 'pending' ORDER BY created_at ASC, command_id ASC LIMIT ?",
                (limit,),
            )
        rows = cur.fetchall()
        ids = [row["command_id"] for row in rows]
        if ids:
            marks = ", ".join("?" for _ in ids)
            self._conn.execute(
                f"UPDATE {self._table} SET status = 'processing' "  # noqa: S608
                f"WHERE command_id IN ({marks})",
                ids,
            )
        return [self._row_to_dto(dict(row) | {"status": "processing"}) for row in rows]

    def complete(self, command_id: str) -> None:
        self._finish(command_id, status="succeeded")

    def fail(
        self,
        command_id: str,
        *,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None:
        self._finish(
            command_id,
            status="failed",
            error_code=error_code,
            error_message=error_message,
        )

    def _finish(
        self,
        command_id: str,
        *,
        status: str,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None:
        try:
            self._conn.execute(
                f"UPDATE {self._table} "  # noqa: S608
                "SET status = ?, error_code = ?, error_message = ?, processed_at = ? "
                "WHERE command_id = ?",
                (
                    status,
                    error_code,
                    error_message,
                    _to_db_value("processed_at", datetime.now(UTC)),
                    command_id,
                ),
            )
            self._maybe_commit()
        except sqlite3.IntegrityError as exc:
            self._maybe_rollback()
            raise _wrap_integrity(exc) from exc


class SQLiteStorage:
    """``StoragePort`` を満たす SQLite backend。"""

    def __init__(
        self,
        sqlite_path: str,
        *,
        migrations_root: Path = DEFAULT_MIGRATIONS_ROOT,
    ) -> None:
        self._migrations_root = migrations_root
        self._conn = sqlite3.connect(sqlite_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.commit()
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
        self._admin_commands = _AdminCommandRepository(
            self._conn, "admin_commands", AdminCommand, "command_id", tx
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

    @property
    def admin_commands(self) -> _AdminCommandRepository:
        return self._admin_commands

    def migrate(self) -> None:
        run_migrations(self._conn, self._migrations_root, "sqlite")
        # migration 中の DDL コミットで PRAGMA が無効化されないよう再設定。
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.commit()

    def pending_migrations(self) -> list[str]:
        return _pending_migrations(self._conn, self._migrations_root, "sqlite")

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


def build_sqlite_storage(
    sqlite_path: str,
    *,
    migrations_root: Path = DEFAULT_MIGRATIONS_ROOT,
) -> SQLiteStorage:
    """SQLite backend を構築する (factory から利用)。"""
    return SQLiteStorage(sqlite_path, migrations_root=migrations_root)
