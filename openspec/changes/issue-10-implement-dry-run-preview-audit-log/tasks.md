## 1. OpenSpec artifacts

- [x] 1.1 Issue #10 / M1 / specs に沿った proposal / spec / tasks を作成する

## 2. Dry-run preview と監査イベント

- [x] 2.1 `DraftOutput` から Site Page 投稿予定 payload（draft-composition.md 必須セクション）を組み立てる `dry_run.py` を追加する
- [x] 2.2 `publish_dry_run` 成功イベントと `error` 失敗イベントを既存 `AuditEvent` model で組み立てる（provider / prompt version / generation_input_hash / 投稿先 / operation / result / error）
- [x] 2.3 payload / 監査イベント組み立ての unit test を追加する

## 3. CLI dry-run

- [x] 3.1 `spautopost preview-draft <advisory-file>` コマンドを追加する（test_mock provider で生成、実投稿・外部 API・Secret 解決なし）
- [x] 3.2 投稿予定 payload と監査イベントを表示し、`env:` 参照・Secret を redaction する
- [x] 3.3 CLI dry-run preview / Secret 非漏洩 / invalid input の test を追加する

## 4. Docs

- [x] 4.1 README に preview-draft dry-run の使い方を追記する

## 5. Verification

- [x] 5.1 `ruff check .` / `ruff format --check src tests` / `mypy src` / `pytest --cov=spautopost --cov-report=term-missing` を実行する
- [x] 5.2 `openspec validate issue-10-implement-dry-run-preview-audit-log --strict` を実行する
