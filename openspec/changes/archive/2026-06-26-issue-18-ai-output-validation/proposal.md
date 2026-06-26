## Why

LLM が生成した DraftOutput をそのまま SharePoint に公開すると、出典にない断定・攻撃手順の混入・必須項目の欠落といったリスクが残る。M3 で production LLM provider（#16/#17）を導入する前に、生成物の安全性を機械的に検証する仕組みが必要。

## What Changes

- `src/spautopost/llm/validation.py` を新規追加し、`DraftOutput` の構造・安全性・出典根拠を検証する `validate_draft_output()` 関数を実装する
- 検証結果を表す `ValidationResult` / `ValidationIssue` データクラスを新規追加する
- `MockLLMProvider.generate_draft` が返す `DraftOutput` の `validation_hints` を利用し、guardrail チェックと統合する
- `tests/llm/test_validation.py` を新規追加し TDD で検証する

## Capabilities

### New Capabilities

- `ai-output-validation`: DraftOutput の required sections check・references check・unsupported claim check・dangerous detail guardrail・uncertainty wording check・regeneration request reason・reviewer warning を提供する検証モジュール

### Modified Capabilities

（なし）

## Impact

- 追加ファイル: `src/spautopost/llm/validation.py`, `tests/llm/test_validation.py`
- 既存の `DraftOutput`, `LLMProvider` interface には破壊的変更なし
- `DraftOutput.validation_hints` / `warnings` / `uncertainty_notes` フィールドを検証インプットとして活用
- セキュリティ: LLM 出力に攻撃手順・PoC が混入しても reviewer warning として検出できる
