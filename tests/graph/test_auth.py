"""delegated auth の純関数・構築バリデーションのテスト（network 非依存）。"""

from __future__ import annotations

import pytest

from spautopost.graph.auth import (
    AuthResult,
    DelegatedDeviceCodeAuth,
    Identity,
    identity_from_claims,
)
from spautopost.graph.errors import GraphAuthError


def test_identity_from_claims_maps_fields() -> None:
    identity = identity_from_claims(
        {"preferred_username": "u@example.com", "name": "User", "oid": "oid-1"}
    )
    assert identity.user_principal_name == "u@example.com"
    assert identity.display_name == "User"
    assert identity.object_id == "oid-1"


def test_identity_from_claims_falls_back_to_upn() -> None:
    identity = identity_from_claims({"upn": "legacy@example.com"})
    assert identity.user_principal_name == "legacy@example.com"
    assert identity.display_name is None


def test_identity_from_claims_empty() -> None:
    identity = identity_from_claims({})
    assert identity.user_principal_name is None
    assert identity.object_id is None


def test_delegated_auth_requires_tenant_and_client() -> None:
    with pytest.raises(GraphAuthError):
        DelegatedDeviceCodeAuth(tenant_id="", client_id="c")
    with pytest.raises(GraphAuthError):
        DelegatedDeviceCodeAuth(tenant_id="t", client_id="")


def test_delegated_auth_constructs_with_defaults_and_overrides() -> None:
    # msal を import せず（acquire を呼ばない）構築のみ検証する。
    default_auth = DelegatedDeviceCodeAuth(tenant_id="t", client_id="c")
    assert default_auth._scopes == ("Sites.ReadWrite.All",)
    # 空 scopes は既定にフォールバックする。
    empty_auth = DelegatedDeviceCodeAuth(tenant_id="t", client_id="c", scopes=())
    assert empty_auth._scopes == ("Sites.ReadWrite.All",)
    custom_auth = DelegatedDeviceCodeAuth(
        tenant_id="t", client_id="c", scopes=["Sites.Selected"], prompt=lambda _m: None
    )
    assert custom_auth._scopes == ("Sites.Selected",)


def test_auth_result_repr_hides_token() -> None:
    result = AuthResult(
        access_token="super-secret-token",  # noqa: S106 - テスト用ダミー
        identity=Identity(user_principal_name="u@example.com", display_name="U"),
    )
    assert "super-secret-token" not in repr(result)
