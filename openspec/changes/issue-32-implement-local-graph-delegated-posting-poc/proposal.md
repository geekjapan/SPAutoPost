## Why

Issue #32 (Milestone M1, Phase 4) では、SharePoint 投稿方式が固まるまでの疎通確認として、手元環境で delegated permission を使い Microsoft Graph 経由で SharePoint Site Page / News へ投稿する最小 PoC が必要です。既存の `spautopost.dry_run` は Site Page payload と監査イベントの組み立てまでを持つが、実際に Graph を呼び出して投稿し、その結果を `Publication` / `AuditEvent` として永続化する縦串が欠けています。

## What Changes

- `spautopost.graph` サブパッケージを追加し、delegated（device code flow）認証と SharePoint Site Page 投稿の最小経路を実装する。
  - `graph.auth`: `GraphTokenProvider` Protocol と、Microsoft 公式 MSAL を使った `DelegatedDeviceCodeAuth`（device code flow）。サインインしたユーザーの `Identity`（UPN / 表示名）を access token と一緒に返す。MSAL は任意 extra (`spautopost[graph]`) として遅延 import する。
  - `graph.sharepoint_client`: `SharePointPagesClient` Protocol と、stdlib `urllib` を使う `GraphSharePointPagesClient`（Site Page の作成と publish）。Graph リクエスト本文の組み立てと応答の page ID 抽出は I/O から分離した純関数にする。
  - `graph.publisher`: dry-run ゲート、idempotency_key 生成、`Publication` / `AuditEvent` の組み立てと `StoragePort` への永続化を行う `publish_site_page` オーケストレーション。
- CLI に `publish-draft <advisory_file>` サブコマンドを追加する。既定は dry-run。`--no-dry-run` のときのみ実認証・実投稿経路に入る。
- `config` の `graph` セクションに公開クライアント用 `client_id`（任意 `scopes`）を追加する。`tenant_id` は既存の `sharepoint.tenant_id` を再利用する。
- 投稿者情報（delegated でサインインした user principal）を `actor`、登録アプリ（client_id）を `service_principal` として `AuditEvent` に記録する。
- 運用者向け runbook（`docs/runbooks/graph-delegated-poc.md`）を追加し、public client アプリ登録・環境変数・実行手順・dry-run/実投稿の切り替えを説明する。
- `pyproject.toml` に任意 extra `graph = ["msal>=1.28"]` を追加する。
- **非対象（Non-goals）**: hosted runtime の本番認証方式決定（#27）、user-assigned managed identity / app-only 実装、本番公開、複数 site 投稿、News の promote 詳細、添付・画像、live Graph を叩く自動テスト。

## Capabilities

### New Capabilities

- `graph-delegated-publishing`: local PoC として delegated（device code）認証で Microsoft Graph に接続し、SharePoint Site Page を dry-run または実投稿し、結果を `Publication` と投稿者入り `AuditEvent` として記録する経路。

### Modified Capabilities

<!-- 既存 OpenSpec capability の要件は変更しない。`graph` config キー追加は本 change の新 capability 内で完結する。 -->

## Impact

- **Code**: `src/spautopost/graph/`（auth / sharepoint_client / publisher）を新規追加。`config.py` の `graph` セクション許可キーを拡張。`cli.py` に `publish-draft` を追加。
- **Tests**: `tests/graph/` を追加。auth・client・publisher は fake token provider / fake pages client を注入して network 非依存で検証する。実 MSAL / 実 urllib 経路は純関数のみテストし、network 行は no-cover とする。
- **Dependencies**: 任意 extra `msal`（device code 認証）を追加。core ランタイム依存（`pyyaml` のみ）は据え置き。Graph への HTTP は stdlib `urllib` で行い、新規 HTTP クライアント依存は足さない。
- **Runtime / Security**: 既定 dry-run。`--no-dry-run` + 運用者が用意した実 credential のときのみ実投稿。Secret は repo / config に保存せず env 参照のみ。投稿前承認（`security.require_approval`）と auto-publish 抑止（`security.block_auto_publish`）の方針を尊重する。hosted 本番認証方式は #27 に残す。
