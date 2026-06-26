## Why

Issue #36 (M1): Admin UI/API で確定した DraftPost を専用 SharePoint Site Page / News article として実際に投稿する機能が必要。`job_entrypoint.py` の `publish-approved` は現在スタブ（`EXIT_PUBLISH_GATED`）で、実投稿ロジックが未実装。`docs/specs/sharepoint-publishing.md` が Publication 記録・冪等性・AuditEvent 記録を必須としているため、本 change でこれらを実装する。

## What Changes

- `src/spautopost/sharepoint_publisher.py` を新規追加する。内容:
  - `GraphClient` Protocol（Site Page 作成・公開の抽象）
  - `MicrosoftGraphClient`（stdlib `urllib.request` + bearer token）
  - `NoopGraphClient`（dry-run / テスト用）
  - `build_idempotency_key()`
  - `build_page_html()`（DraftPost → SharePoint 投稿用 HTML）
  - `publish_approved_draft()`（idempotency check・状態遷移・Publication + AuditEvent 記録・実投稿）
- `src/spautopost/errors.py` に `PublishError` / `GraphAuthError` を追加する。
- `src/spautopost/cli.py` に `publish-approved` コマンドを追加する（pending `publish_request` AdminCommand を処理）。
- `src/spautopost/job_entrypoint.py` の `publish-approved` スタブを実コマンドに置き換える。
- `tests/test_sharepoint_publisher.py` を追加する（冪等性・状態遷移・dry-run・AuditEvent・エラーハンドリング）。

**非対象**: Microsoft Graph の認証トークン取得（Issue #32 / #27 に委ねる）、複数 site 同時投稿、page layout 設計、添付ファイル対応。

## Capabilities

### New Capabilities

- `approved-draft-publish`: approved な DraftPost を専用 SharePoint Site Page / News article として投稿し、Publication と AuditEvent を記録する。冪等性キーにより重複投稿を防ぐ。dry-run では実投稿しない。

## Impact

- **新規コード**: `src/spautopost/sharepoint_publisher.py`、`tests/test_sharepoint_publisher.py`
- **変更**: `src/spautopost/errors.py`（2 エラークラス追加）、`src/spautopost/cli.py`（publish-approved コマンド追加）、`src/spautopost/job_entrypoint.py`（スタブ → 実コマンド）
- **依存関係**: 追加なし（stdlib `urllib.request` + `hashlib` + `dataclasses.replace`）
- **セキュリティ**: Graph bearer token は環境変数 `SPAUTOPOST_GRAPH_ACCESS_TOKEN` のみから取得。実投稿は `approved` DraftPost + `allow_publish=true` 設定の両方が必要。dry-run では実 Graph API 呼び出しを行わない。
- **人間ゲート**: publish 操作は Admin UI/API 経由の人間確認（`publish_request` コマンド）が前提。自動投稿なし。
