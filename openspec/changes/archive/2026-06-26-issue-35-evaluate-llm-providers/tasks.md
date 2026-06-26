## 1. Spike 評価

- [x] 1.1 Azure OpenAI / Foundry の公開ドキュメントから利用条件・認証方式・入力データ制限を調査し評価メモを作成する
- [x] 1.2 generic API（OpenAI-compatible）adapter の interface 要件と利用条件上の制約を整理する
- [x] 1.3 test_manual provider の M1 手動取込フローを具体的に記述する

## 2. docs/specs/llm-provider.md 更新

- [x] 2.1 M1 Scope セクションを追加し、必須（test_mock）/ optional（test_manual）/ M3 以降（production_api, generic_api）を明記する
- [x] 2.2 Provider interface の確定版（ProviderMetadata を含む）を反映する
- [x] 2.3 test_manual provider の手動取込フローと禁止事項を明記する
- [x] 2.4 Azure OpenAI / Foundry の M3 前提条件（情報セキュリティ承認・認証方式確定など）を記載する

## 3. ADR 更新

- [x] 3.1 `docs/decisions/2026-06-22-llm-provider-strategy.md` の Consequences セクションに M1 スコープ判断（mock のみ必須、LLM API は M3 以降）を追記する

## 4. 検証と完了

- [x] 4.1 `openspec validate issue-35-evaluate-llm-providers --strict` を実行し全チェックが通ることを確認する
- [x] 4.2 更新した `docs/specs/llm-provider.md` と ADR の内容が Issue #35 の受け入れ条件を満たすことを確認する
- [x] 4.3 Issue #16 (#17) に M3 前提条件を blocked-by コメントとして追記する（任意・スキップ）
