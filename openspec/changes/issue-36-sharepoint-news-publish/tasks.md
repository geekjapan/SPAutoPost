## 1. OpenSpec artifacts

- [x] 1.1 Issue #36 / M1 / specs に沿った proposal / spec / tasks を作成する

## 2. コアパブリッシャー実装

- [x] 2.1 `src/spautopost/errors.py` に `PublishError` / `GraphAuthError` を追加する
- [x] 2.2 `src/spautopost/sharepoint_publisher.py` を新規作成する（`GraphClient` Protocol・`NoopGraphClient`・`MicrosoftGraphClient`・`build_idempotency_key`・`build_page_html`・`publish_approved_draft`）
- [x] 2.3 冪等性・状態遷移・dry-run・AuditEvent・エラーハンドリングの unit test を追加する（TDD: テスト先行）

## 3. CLI / job entrypoint 更新

- [x] 3.1 `src/spautopost/cli.py` に `publish-approved` コマンドを追加する（pending `publish_request` AdminCommand を処理）
- [x] 3.2 `src/spautopost/job_entrypoint.py` の `publish-approved` スタブを実コマンドに置き換える
- [x] 3.3 CLI / job entrypoint の unit test を追加・更新する

## 4. Verification

- [x] 4.1 `ruff check .` / `ruff format --check src tests` / `mypy src` / `pytest --cov=spautopost --cov-report=term-missing` を実行する
- [x] 4.2 `openspec validate issue-36-sharepoint-news-publish --strict` を実行する
