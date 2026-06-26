"""Python 所有の storage port。

- entity read/write store: ``save(entity_type, obj)`` / ``get(entity_type, id)``
- command queue: ``append_command`` / ``claim_pending_commands`` /
  ``complete_command`` / ``fail_command``

adapter（sqlite / postgres）は ``_SqlStorage`` を継承し、SQL 方言差
（placeholder, JSON 列, timestamp, SKIP LOCKED）だけを上書きする。
queryable 列のみ column 化し、残りは JSON 列（attributes / payload）に逃がす。
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from .serialization import dumps_json, loads_json, now_iso, to_iso_utc

# Sensitive Data Policy: AdminCommand payload からこれらのキーを除去する。
_SECRET_KEY_RE = re.compile(
    r"^(api_?key|access_?token|refresh_?token|client_?secret|private_?key"
    r"|password|cookie|authorization|secret)$",
    re.IGNORECASE,
)


def _scrub_payload(payload: dict) -> dict:
    return {k: v for k, v in payload.items() if not _SECRET_KEY_RE.match(k)}


@dataclass(frozen=True)
class Table:
    """1 entity の論理 schema（promoted column と JSON 列）。"""

    table: str
    pk: str
    columns: tuple[str, ...]          # column 化された queryable/制約フィールド
    ts_columns: frozenset[str] = field(default_factory=frozenset)
    json_column: str = "attributes"   # 残り全フィールドの格納先


# canonical entity の column 構成（SQL baseline と一致させること）。
ENTITIES: dict[str, Table] = {
    "source_record": Table(
        "source_records", "source_record_id",
        ("source_record_id", "source_type", "retrieved_at", "raw_hash", "parser_version"),
        frozenset({"retrieved_at"}),
    ),
    "advisory": Table(
        "advisories", "advisory_id",
        ("advisory_id", "severity", "created_at", "normalized_at", "published_at", "updated_at"),
        frozenset({"created_at", "normalized_at", "published_at", "updated_at"}),
    ),
    "draft_post": Table(
        "draft_posts", "draft_id",
        ("draft_id", "status", "created_at", "updated_at"),
        frozenset({"created_at", "updated_at"}),
    ),
    "review_event": Table(
        "review_events", "review_event_id",
        ("review_event_id", "draft_id", "action", "created_at"),
        frozenset({"created_at"}),
    ),
    "publication": Table(
        "publications", "publication_id",
        ("publication_id", "draft_id", "publication_status", "idempotency_key",
         "created_at", "updated_at"),
        frozenset({"created_at", "updated_at"}),
    ),
    "audit_event": Table(
        "audit_events", "audit_event_id",
        ("audit_event_id", "event_type", "correlation_id", "result", "created_at"),
        frozenset({"created_at"}),
    ),
}

# AdminCommand queue（ADR admin-core-boundary）。payload を JSON 列に持つ。
_ADMIN_TABLE = Table(
    "admin_commands", "command_id",
    ("command_id", "command_type", "target_draft_id", "requested_by", "idempotency_key",
     "status", "error_code", "error_message", "correlation_id", "created_at", "processed_at"),
    frozenset({"created_at", "processed_at"}),
    json_column="payload",
)


class StoragePort(ABC):
    """canonical entity と AdminCommand queue の永続化インターフェース。"""

    @abstractmethod
    def save(self, entity_type: str, obj: dict) -> None: ...

    @abstractmethod
    def get(self, entity_type: str, entity_id: str) -> dict | None: ...

    @abstractmethod
    def append_command(self, command: dict) -> None: ...

    @abstractmethod
    def claim_pending_commands(self, limit: int = 10) -> list[dict]: ...

    @abstractmethod
    def complete_command(self, command_id: str) -> None: ...

    @abstractmethod
    def fail_command(self, command_id: str, error_code: str | None = None,
                     error_message: str | None = None) -> None: ...


class _SqlStorage(StoragePort):
    """SQL adapter 共通実装。方言差はフック override で吸収する。"""

    PH = "?"           # placeholder（postgres は "%s"）
    DIALECT = "sqlite"

    conn = None        # adapter の __init__ が設定

    def close(self) -> None:
        if self.conn is not None:
            self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # --- 方言フック（postgres adapter で override） -----------------------
    def _json_param(self, obj):
        return dumps_json(obj)

    def _ts_param(self, value):
        return to_iso_utc(value)

    # --- 内部ヘルパ -------------------------------------------------------
    def _split(self, obj: dict, spec: Table):
        """obj を promoted column 値リストと JSON 列値に分ける。

        キーが存在する場合は None（SQL NULL）も column に含める。これにより
        UPSERT で nullable 列を NULL にクリアできる。
        """
        data = dict(obj)  # 入力を mutate しない
        cols, params = [], []
        for c in spec.columns:
            if c not in data:
                continue
            v = data.pop(c)
            if v is not None and c in spec.ts_columns:
                v = self._ts_param(v)
            cols.append(c)
            params.append(v)
        cols.append(spec.json_column)
        params.append(self._json_param(data))
        return cols, params

    def _merge(self, row: dict, spec: Table) -> dict:
        """DB 行を 1 つの entity dict に復元する。"""
        result = dict(loads_json(row.get(spec.json_column)))
        for c in spec.columns:
            v = row.get(c)
            if v is None:
                continue
            result[c] = to_iso_utc(v) if c in spec.ts_columns else v
        return result

    # --- entity store -----------------------------------------------------
    def save(self, entity_type: str, obj: dict) -> None:
        spec = ENTITIES[entity_type]
        cols, params = self._split(obj, spec)
        placeholders = ", ".join([self.PH] * len(cols))
        updates = ", ".join(f"{c}=excluded.{c}" for c in cols if c != spec.pk)
        sql = (
            f"INSERT INTO {spec.table} ({', '.join(cols)}) VALUES ({placeholders}) "
            f"ON CONFLICT ({spec.pk}) DO UPDATE SET {updates}"
        )
        cur = self.conn.cursor()
        cur.execute(sql, params)

    def get(self, entity_type: str, entity_id: str) -> dict | None:
        spec = ENTITIES[entity_type]
        cur = self.conn.cursor()
        cur.execute(f"SELECT * FROM {spec.table} WHERE {spec.pk} = {self.PH}", (entity_id,))
        row = cur.fetchone()
        return self._merge(dict(row), spec) if row is not None else None

    # --- command queue ----------------------------------------------------
    def append_command(self, command: dict) -> None:
        data = dict(command)
        # payload は _split に渡す前に取り出し、secret を除去してから JSON 列に書く。
        # _split に渡すと {"payload": {...}} と二重にラップされてしまうため。
        payload = _scrub_payload(data.pop("payload", None) or {})
        data.setdefault("status", "pending")
        data.setdefault("created_at", now_iso())
        cols, params = self._split(data, _ADMIN_TABLE)
        # _split の末尾要素は json_column（payload）のプレースホルダ。
        # data はこの時点で空なので {} が入っている。実際の payload に差し替える。
        params[-1] = self._json_param(payload)
        placeholders = ", ".join([self.PH] * len(cols))
        sql = f"INSERT INTO {_ADMIN_TABLE.table} ({', '.join(cols)}) VALUES ({placeholders})"
        cur = self.conn.cursor()
        cur.execute(sql, params)

    def complete_command(self, command_id: str) -> None:
        cur = self.conn.cursor()
        cur.execute(
            f"UPDATE admin_commands SET status='succeeded', processed_at={self.PH} "
            f"WHERE command_id={self.PH}",
            (self._ts_param(now_iso()), command_id),
        )

    def fail_command(self, command_id: str, error_code: str | None = None,
                     error_message: str | None = None) -> None:
        cur = self.conn.cursor()
        cur.execute(
            f"UPDATE admin_commands SET status='failed', error_code={self.PH}, "
            f"error_message={self.PH}, processed_at={self.PH} WHERE command_id={self.PH}",
            (error_code, error_message, self._ts_param(now_iso()), command_id),
        )

    def _command_from_row(self, row) -> dict:
        # _merge は json_column の内容をトップレベルに展開するため AdminCommand には使えない。
        # payload は nested dict として返し、promoted column は直接マップする。
        row = dict(row)
        result = {}
        for c in _ADMIN_TABLE.columns:
            v = row.get(c)
            if v is not None and c in _ADMIN_TABLE.ts_columns:
                v = to_iso_utc(v)
            result[c] = v
        result["payload"] = loads_json(row.get("payload") or "{}")
        return result
