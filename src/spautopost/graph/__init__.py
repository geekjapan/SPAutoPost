"""Microsoft Graph delegated posting PoC（local 専用）。

hosted runtime の本番認証方式（managed identity / app-only）は本パッケージの対象外。
決定は Issue #27 / docs/specs/graph-authentication.md に残す。
"""

from __future__ import annotations

from .auth import (
    DEFAULT_GRAPH_SCOPES,
    AuthResult,
    DelegatedDeviceCodeAuth,
    GraphTokenProvider,
    Identity,
    identity_from_claims,
)
from .errors import GraphApiError, GraphAuthError, GraphError
from .publisher import (
    PublishResult,
    build_idempotency_key,
    normalize_title,
    publish_site_page,
)
from .sharepoint_client import (
    CreatedPage,
    GraphSharePointPagesClient,
    SharePointPagesClient,
    build_create_page_request,
    page_name_from_title,
    parse_page_id,
)

__all__ = [
    "DEFAULT_GRAPH_SCOPES",
    "AuthResult",
    "CreatedPage",
    "DelegatedDeviceCodeAuth",
    "GraphApiError",
    "GraphAuthError",
    "GraphError",
    "GraphSharePointPagesClient",
    "GraphTokenProvider",
    "Identity",
    "PublishResult",
    "SharePointPagesClient",
    "build_create_page_request",
    "build_idempotency_key",
    "identity_from_claims",
    "normalize_title",
    "page_name_from_title",
    "parse_page_id",
    "publish_site_page",
]
