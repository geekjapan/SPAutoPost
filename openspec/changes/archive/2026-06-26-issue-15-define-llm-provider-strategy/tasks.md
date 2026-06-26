## 1. docs/specs/llm-provider.md の更新

- [x] 1.1 production_api provider の利用条件（SHALL、承認・認証・rate limit・監査ログ）を追加する
- [x] 1.2 production_flow provider の利用条件（SHALL、schema・履歴追跡・用途限定・失敗時対応）を追加する
- [x] 1.3 generic_api provider の利用条件（SHALL、公式 API のみ・利用規約確認・Secret 管理）を追加する
- [x] 1.4 test_mock provider の要件（SHALL、外部通信なし・deterministic・Secret 不要）を追加する
- [x] 1.5 test_manual provider の禁止事項（MUST NOT、UI 自動化・業務データ投入・自動公開・provider_type 未記録）を追加する
- [x] 1.6 ChatGPT / Claude subscription を自動化前提にしない方針を明示する（MUST NOT）
- [x] 1.7 provider へ渡してよい情報（許可リスト）と禁止情報（禁止リスト）を追加する
- [x] 1.8 prompt / output 保存方針（generation_input_hash のみ保存・原文保存禁止）を追加する
- [x] 1.9 provider 切替方針（設定変更のみで切替可能・audit log 記録）を追加する
- [x] 1.10 production_api の監査項目（必須・禁止の両方）を追加する
- [x] 1.11 generic_api の監査項目を追加する
- [x] 1.12 test_mock の監査項目（基本項目のみ、token/cost 省略可）を追加する
- [x] 1.13 test_manual の監査項目（手動記録項目・manual_review_required）を追加する
- [x] 1.14 実稼働 provider とテスト provider の環境分離方針（APP_ENV 連動・本番での test provider 使用禁止）を追加する

## 2. docs/specs/security-baseline.md との整合確認

- [x] 2.1 `security-baseline.md` の「LLM Input Control」セクションと `llm-provider.md` の許可リスト / 禁止リストに矛盾がないことを確認する
- [x] 2.2 `security-baseline.md` から詳細ポリシーの正本として `llm-provider.md` への参照を追加する
