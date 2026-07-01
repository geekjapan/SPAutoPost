## 1. 仕様確認

- [x] 1.1 Issue #81 と PR #77/#78/#79/#80 の承認ゲート関連記述を確認する
- [x] 1.2 `src/spautopost/config.py`、`docs/specs/llm-provider.md`、`openspec/specs/llm-provider/spec.md` の差分を確認する

## 2. Docs / Spec 更新

- [x] 2.1 `llm-provider` の OpenSpec delta に承認フラグの受け入れ条件を明記する
- [x] 2.2 `docs/specs/llm-provider.md` と `openspec/specs/llm-provider/spec.md` に同じ承認モデルを反映する

## 3. 検証

- [x] 3.1 `openspec validate issue-81-llm-production-approval-gate --strict` を実行する
- [x] 3.2 既存の設定バリデーションテストを実行し、runtime behavior が変わっていないことを確認する
