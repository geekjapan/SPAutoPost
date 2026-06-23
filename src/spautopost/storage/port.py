"""ストレージポート（ORM 非依存の repository Protocol）。

正本: openspec/changes/issue-28-implement-postgresql-storage-baseline/specs/storage-port

方針:
- 呼び出し側へ SQL 文字列・psycopg・sqlite3・方言を露出しない。
- 各 repository は ``upsert`` / ``get(Optional)`` / ``list(決定論順 + limit/offset)``。
- ReviewEvent / AuditEvent は append-only（``append`` のみ、upsert なし）。
- Publication は idempotency 専用の ``create_if_absent`` / ``get_by_idempotency_key``。
- backend 全体は ``migrate`` / ``transaction`` / ``close`` を備える。
"""

from __future__ import annotations

from collections.abc import Sequence
from contextlib import AbstractContextManager
from typing import Protocol, runtime_checkable

from .models import (
    Advisory,
    AuditEvent,
    DraftPost,
    Publication,
    ReviewEvent,
    SourceRecord,
)

# list() のページング既定値（マジックナンバー回避）。
DEFAULT_LIST_LIMIT = 100
DEFAULT_LIST_OFFSET = 0


@runtime_checkable
class SourceRecordRepository(Protocol):
    """source_records の repository。"""

    def upsert(self, record: SourceRecord) -> SourceRecord: ...

    def get(self, source_record_id: str) -> SourceRecord | None: ...

    def list(
        self, *, limit: int = DEFAULT_LIST_LIMIT, offset: int = DEFAULT_LIST_OFFSET
    ) -> Sequence[SourceRecord]: ...


@runtime_checkable
class AdvisoryRepository(Protocol):
    """advisories の repository。"""

    def upsert(self, advisory: Advisory) -> Advisory: ...

    def get(self, advisory_id: str) -> Advisory | None: ...

    def list(
        self, *, limit: int = DEFAULT_LIST_LIMIT, offset: int = DEFAULT_LIST_OFFSET
    ) -> Sequence[Advisory]: ...


@runtime_checkable
class DraftPostRepository(Protocol):
    """draft_posts の repository。"""

    def upsert(self, draft: DraftPost) -> DraftPost: ...

    def get(self, draft_id: str) -> DraftPost | None: ...

    def list(
        self, *, limit: int = DEFAULT_LIST_LIMIT, offset: int = DEFAULT_LIST_OFFSET
    ) -> Sequence[DraftPost]: ...


@runtime_checkable
class ReviewEventRepository(Protocol):
    """review_events の repository（append-only）。"""

    def append(self, event: ReviewEvent) -> ReviewEvent: ...

    def get(self, review_event_id: str) -> ReviewEvent | None: ...

    def list(
        self, *, limit: int = DEFAULT_LIST_LIMIT, offset: int = DEFAULT_LIST_OFFSET
    ) -> Sequence[ReviewEvent]: ...


@runtime_checkable
class PublicationRepository(Protocol):
    """publications の repository（idempotency 制約付き）。"""

    def upsert(self, publication: Publication) -> Publication: ...

    def get(self, publication_id: str) -> Publication | None: ...

    def list(
        self, *, limit: int = DEFAULT_LIST_LIMIT, offset: int = DEFAULT_LIST_OFFSET
    ) -> Sequence[Publication]: ...

    def create_if_absent(self, publication: Publication) -> tuple[Publication, bool]:
        """``idempotency_key`` 単位で race-safe に作成する。

        戻り値は ``(publication, created)``。同一キーの 2 回目以降は既存行と
        ``created=False`` を返す。
        """
        ...

    def get_by_idempotency_key(self, idempotency_key: str) -> Publication | None: ...


@runtime_checkable
class AuditEventRepository(Protocol):
    """audit_events の repository（append-only）。"""

    def append(self, event: AuditEvent) -> AuditEvent: ...

    def get(self, audit_event_id: str) -> AuditEvent | None: ...

    def list(
        self, *, limit: int = DEFAULT_LIST_LIMIT, offset: int = DEFAULT_LIST_OFFSET
    ) -> Sequence[AuditEvent]: ...


@runtime_checkable
class StoragePort(Protocol):
    """6 エンティティの repository を束ねるストレージポート。

    呼び出し側はこの Protocol のメソッド・property のみに依存する。
    """

    @property
    def source_records(self) -> SourceRecordRepository: ...

    @property
    def advisories(self) -> AdvisoryRepository: ...

    @property
    def draft_posts(self) -> DraftPostRepository: ...

    @property
    def review_events(self) -> ReviewEventRepository: ...

    @property
    def publications(self) -> PublicationRepository: ...

    @property
    def audit_events(self) -> AuditEventRepository: ...

    def migrate(self) -> None:
        """baseline migration を適用する（再実行は no-op）。"""
        ...

    def pending_migrations(self) -> list[str]:
        """未適用 migration の version リストを返す（dry-run 用、DDL 非適用）。"""
        ...

    def transaction(self) -> AbstractContextManager[None]:
        """トランザクション境界を提供する context manager を返す。"""
        ...

    def close(self) -> None:
        """接続を閉じる。"""
        ...
