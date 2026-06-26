## Why

SPAutoPost が SharePoint Site Page / News を Microsoft Graph 経由で投稿するにあたり、local PoC・Azure hosted runtime・本番定期実行それぞれの認証方式を決定する必要がある。MVP 実装前に認証モデルを確定し、Graph permission の最小化方針と SharePoint 対象範囲の限定方針を仕様に明記する。

## What Changes

- `docs/specs/graph-authentication.md` を更新し、全受け入れ条件を明文化する
  - local PoC: delegated permission（Device Code Flow）を採用
  - Azure hosted runtime: user-assigned managed identity を第一候補、application permission / app-only access を fallback
  - managed identity: 採用（user-assigned を選択、Container Apps App と Jobs で共有）
  - delegated permission の本番定期実行除外を明記
  - 必要最小 Graph permission の列挙と `Sites.Selected` 優先方針
  - SharePoint 対象 site を config で限定する方針

## Capabilities

### New Capabilities

- `graph-authentication-model`: Microsoft Graph 認証方式の決定仕様。local PoC・Azure hosted runtime・managed identity 採否・delegated permission 本番除外・Graph permission 最小化・SharePoint 対象範囲限定を定義する

### Modified Capabilities

（なし）

## Impact

- `docs/specs/graph-authentication.md`: 主要更新対象（受け入れ条件の全項目を反映）
- `docs/specs/security-baseline.md`: Graph permission 方針との整合確認（更新不要の場合あり）
- 後続 Issue #32（local Graph delegated posting PoC）と #9（SharePoint connector PoC）の実装方針に影響
