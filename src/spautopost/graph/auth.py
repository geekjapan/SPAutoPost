"""delegated（device code flow）認証。

local PoC 専用。Microsoft 公式の ``msal`` を遅延 import して device code flow で
access token を取得し、サインインしたユーザーの :class:`Identity` を返す。

Secret（access token / refresh token）は repr / ログ / 例外メッセージに出さない。
hosted runtime の本番認証方式（managed identity / app-only）は本モジュールの対象外で、
決定は Issue #27 に委ねる（docs/specs/graph-authentication.md）。
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from .errors import GraphAuthError

# delegated PoC の既定 scope。
# ponytail: 広めの Sites.ReadWrite.All を使う。app-only / managed identity へ移行する際は
# Sites.Selected + 対象 site への grant に絞る（graph-authentication.md / Issue #27）。
DEFAULT_GRAPH_SCOPES: tuple[str, ...] = ("Sites.ReadWrite.All",)

AUTHORITY_TEMPLATE = "https://login.microsoftonline.com/{tenant_id}"


@dataclass(frozen=True)
class Identity:
    """サインインしたユーザーの最小 identity（AuditEvent の actor に使う）。"""

    user_principal_name: str | None
    display_name: str | None
    object_id: str | None = None


@dataclass(frozen=True)
class AuthResult:
    """取得した access token とサインインユーザーの identity。

    ``access_token`` は ``repr=False`` で repr に出さない（誤ログ防止）。
    """

    access_token: str = field(repr=False)
    identity: Identity


@runtime_checkable
class GraphTokenProvider(Protocol):
    """Graph access token の取得を抽象化する（実 MSAL / テスト fake を差し替え可能）。"""

    def acquire(self) -> AuthResult: ...


def identity_from_claims(claims: Mapping[str, object]) -> Identity:
    """id_token claims から :class:`Identity` を取り出す（network 非依存・純関数）。"""
    upn = claims.get("preferred_username") or claims.get("upn")
    name = claims.get("name")
    oid = claims.get("oid")
    return Identity(
        user_principal_name=str(upn) if upn else None,
        display_name=str(name) if name else None,
        object_id=str(oid) if oid else None,
    )


class DelegatedDeviceCodeAuth:
    """device code flow による delegated 認証（public client、secret 不要）。"""

    def __init__(
        self,
        *,
        tenant_id: str,
        client_id: str,
        scopes: Sequence[str] = DEFAULT_GRAPH_SCOPES,
        prompt: Callable[[str], None] | None = None,
    ) -> None:
        if not tenant_id or not client_id:
            raise GraphAuthError("delegated device code auth requires tenant_id and client_id")
        self._tenant_id = tenant_id
        self._client_id = client_id
        self._scopes = tuple(scopes) or DEFAULT_GRAPH_SCOPES
        self._prompt = prompt or print

    def acquire(self) -> AuthResult:  # pragma: no cover - interactive / network
        import msal

        app = msal.PublicClientApplication(
            self._client_id,
            authority=AUTHORITY_TEMPLATE.format(tenant_id=self._tenant_id),
        )
        flow = app.initiate_device_flow(scopes=list(self._scopes))
        if "user_code" not in flow:
            error_msg = flow.get("error_description") or flow.get("error") or "unknown error"
            raise GraphAuthError(f"failed to initiate device code flow: {error_msg}")
        # flow["message"] は「このコードを入力してサインインせよ」という案内文（Secret ではない）。
        self._prompt(flow["message"])
        result = app.acquire_token_by_device_flow(flow)
        if "access_token" not in result:
            error_msg = result.get("error_description") or result.get("error") or "unknown error"
            raise GraphAuthError(f"device code auth failed: {error_msg}")
        return AuthResult(
            access_token=result["access_token"],
            identity=identity_from_claims(result.get("id_token_claims", {})),
        )
