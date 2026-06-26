## 1. OpenSpec change

- [x] 1.1 `graph-delegated-publishing` capability の proposal / spec / design を作成する。
- [x] 1.2 hosted 本番認証（managed identity / app-only）と live Graph 自動テストを scope 外に保つ。

## 2. Config と依存

- [x] 2.1 `pyproject.toml` に任意 extra `graph = ["msal>=1.28"]` を追加する。
- [x] 2.2 `config.py` の `_SECTION_KEYS["graph"]` に `client_id` / `scopes` を追加し、`GraphConfig` dataclass と検証を実装する（`client_id` は env 参照可、非機密）。
- [x] 2.3 `config.example.yml` の `graph` セクションに `client_id` を追記する（Secret は直書きしない）。

## 3. graph.auth（delegated device code）

- [x] 3.1 `graph/auth.py` に `Identity` / `AuthResult` dataclass と `GraphTokenProvider` Protocol を定義する。
- [x] 3.2 MSAL を遅延 import する `DelegatedDeviceCodeAuth.acquire()` を実装し、device code 表示・サインイン・`id_token_claims` からの `Identity` 抽出を行う（network 行は no-cover）。
- [x] 3.3 access token / refresh token 等の Secret をログ・戻り値・例外に含めないことを保証する。

## 4. graph.sharepoint_client（Graph Site Page）

- [x] 4.1 `graph/sharepoint_client.py` に `SharePointPagesClient` Protocol を定義する。
- [x] 4.2 payload → Graph Site Page リクエスト本文を組み立てる純関数 `build_create_page_request` と、応答 JSON → page ID を抽出する純関数 `parse_page_id` を実装する。
- [x] 4.3 `urllib` を使う `GraphSharePointPagesClient.create_site_page` / `publish_site_page` を実装する（I/O 行は no-cover、純関数へ委譲）。

## 5. graph.publisher（オーケストレーション）

- [x] 5.1 `build_idempotency_key`（draft_id・site_id・page_library_id・advisory_ids・正規化 title の SHA-256）を実装する。
- [x] 5.2 `Publication` / `AuditEvent` の組み立て（dry_run / published / failed と publish_dry_run / publish_create / publish_result / error）を実装する。
- [x] 5.3 `publish_site_page(...)` を実装する: idempotency 確認 → dry-run ゲート → live 認証・投稿 → 結果記録、失敗は捕捉して `failed` 記録（例外を伝播させない）。
- [x] 5.4 `actor`（サインイン user principal）と `service_principal`（client_id）を `AuditEvent` に記録する。

## 6. CLI

- [x] 6.1 `cli.py` に `publish-draft <advisory_file>` を追加する（既定 dry-run、`--no-dry-run` で live）。
- [x] 6.2 advisory ロード → MockLLMProvider で draft 生成 → `publish_site_page` 呼び出し → `StoragePort` 記録 → redaction 付き JSON 出力を実装する。

## 7. テスト

- [x] 7.1 `tests/graph/test_publisher.py`: dry-run / live 成功 / live 失敗 / idempotency skip を fake provider・fake client・sqlite storage で検証する。
- [x] 7.2 `tests/graph/test_sharepoint_client.py`: `build_create_page_request` / `parse_page_id` の純関数を検証する。
- [x] 7.3 `tests/graph/test_idempotency.py`（または publisher テスト内）: idempotency_key の決定論性と投稿先差での差異を検証する。
- [x] 7.4 `tests/test_cli.py` に `publish-draft` の dry-run 経路（Secret redaction・Publication/AuditEvent 記録）を追加する。
- [x] 7.5 conftest の test config に `graph.client_id` を追加し、Secret を `AuditEvent` に含めないことを検証する。

## 8. Runbook / docs

- [x] 8.1 `docs/runbooks/graph-delegated-poc.md` を作成する（public client アプリ登録・必要 scope・環境変数・実行手順・dry-run/実投稿の切り替え・hosted は #27 へ）。

## 9. 検証と PR

- [x] 9.1 `pytest --cov=spautopost --cov-report=term-missing`（カバレッジ 80% 以上）
- [x] 9.2 `ruff check src tests && ruff format --check src tests`
- [x] 9.3 `mypy src`
- [x] 9.4 `openspec validate issue-32-implement-local-graph-delegated-posting-poc --strict`
- [x] 9.5 `git diff --check`
- [ ] 9.6 ecc:code-review / security review（auth / publish carve-out）→ PR
