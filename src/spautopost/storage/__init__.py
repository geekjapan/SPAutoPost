"""SPAutoPost ストレージレイヤ（repository パターン）。

設計の正本:
- openspec/changes/issue-28-implement-postgresql-storage-baseline/design.md
- docs/specs/data-model.md / docs/specs/audit-log.md / docs/specs/sharepoint-publishing.md

このパッケージは ORM 非依存のストレージポート（Protocol）と、それを満たす
backend（SQLite / PostgreSQL）を提供する。呼び出し側へ SQL・方言・DB ドライバを
露出しない。
"""

from __future__ import annotations

from .errors import (
    ConstraintViolationError,
    MigrationDriftError,
    StorageConfigError,
    StorageError,
    UnknownProviderError,
)
from .models import (
    Advisory,
    AuditEvent,
    DraftPost,
    Publication,
    ReviewEvent,
    SourceRecord,
)

__all__ = [
    "Advisory",
    "AuditEvent",
    "ConstraintViolationError",
    "DraftPost",
    "MigrationDriftError",
    "Publication",
    "ReviewEvent",
    "SourceRecord",
    "StorageConfigError",
    "StorageError",
    "UnknownProviderError",
]
