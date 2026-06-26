## Why

M1 では、実投稿の前に人間が生成内容と投稿予定内容を確認できる必要がある（Issue #10）。実投稿せずに「生成された原稿」と「SharePoint へ送る予定の payload」を確認でき、誰が・どの provider / prompt version で・どの投稿先に・どんな結果になったかを最小限の監査ログとして残すことが求められる。`AuditEvent` model と LLM provider interface は既に存在するため、本 change はそれらを使って dry-run preview と最小監査ログを組み立てる。

## What Changes

- 生成済み `DraftOutput` から SharePoint Site Page 投稿予定 payload（`docs/specs/draft-composition.md` の必須セクション構成）を組み立てる preview 機能を追加する。
- dry-run の `publish_dry_run` 成功イベントと失敗時 `error` イベントを既存 `AuditEvent` model で組み立てる（provider 名 / provider type / prompt version / generation_input_hash / 投稿先 / operation / result / error を最小限記録）。
- preview と監査ログから Secret / token / `env:` 参照が漏れないよう redaction を保証する（`src/spautopost/secrets.py` を再利用）。
- CLI `spautopost preview-draft <advisory-file>` を追加する。手動 advisory を読み込み、test_mock provider で原稿を生成し、payload preview と監査イベントを表示する。外部 API 呼び出し・実投稿・Secret 保存は行わない。
- **非対象**: SIEM 連携、長期保存・保持期間設計、tamper-proof log、実 SharePoint への投稿、Microsoft Graph 接続、監査イベントの永続化。

## Capabilities

### New Capabilities

- `dry-run-preview`: 実投稿せずに投稿予定 payload を確認でき、最小監査イベントを Secret 漏洩なく組み立てる。

### Modified Capabilities

<!-- 既存 OpenSpec capability の requirement は変更しない。 -->

## Impact

- **新規コード**: `src/spautopost/dry_run.py`
- **CLI**: `spautopost preview-draft <advisory-file>` を追加する。
- **テスト**: payload preview / 監査イベント成功・失敗 / Secret 非漏洩 / CLI dry-run の unit test を追加する。
- **依存関係**: 追加なし。既存の LLM provider・`AuditEvent` model・`secrets` redaction・stdlib を使う。
- **セキュリティ**: 外部 API 呼び出し、実投稿、Secret 保存は行わない。`env:` 参照と投稿先識別子は redaction する。
