## 1. テストファイルの準備（TDD: RED フェーズ）

- [ ] 1.1 `tests/llm/__init__.py` が存在しなければ作成する
- [ ] 1.2 `tests/llm/test_validation.py` を新規作成し、ValidationIssue / ValidationResult の型テストを追加（RED）
- [ ] 1.3 required sections check のテストを追加（RED）
- [ ] 1.4 references check のテストを追加（RED）
- [ ] 1.5 unsupported claim check のテストを追加（RED）
- [ ] 1.6 dangerous detail guardrail のテストを追加（RED）
- [ ] 1.7 uncertainty wording check のテストを追加（RED）
- [ ] 1.8 regeneration request reason のテストを追加（RED）
- [ ] 1.9 reviewer warning 集約のテストを追加（RED）
- [ ] 1.10 `from spautopost.llm import validate_draft_output` のインポートテストを追加（RED）

## 2. 実装（TDD: GREEN フェーズ）

- [ ] 2.1 `src/spautopost/llm/validation.py` を新規作成し、`ValidationIssue` dataclass を実装する
- [ ] 2.2 `ValidationResult` dataclass を実装する（has_errors, has_warnings, reviewer_warnings, regeneration_hints）
- [ ] 2.3 `_check_required_sections` ヘルパーを実装する
- [ ] 2.4 `_check_references` ヘルパーを実装する
- [ ] 2.5 `_check_unsupported_claims` ヘルパーを実装する
- [ ] 2.6 `_check_dangerous_details` ヘルパーを実装する（キーワードリスト英日）
- [ ] 2.7 `_check_uncertainty_notes` ヘルパーを実装する
- [ ] 2.8 `validate_draft_output` 関数を実装し、全チェックを呼び出して ValidationResult を返す
- [ ] 2.9 `__all__` にエクスポートを定義する

## 3. llm パッケージへの統合

- [ ] 3.1 `src/spautopost/llm/__init__.py` の `__all__` に `validate_draft_output`, `ValidationResult`, `ValidationIssue` を追加する
- [ ] 3.2 `__init__.py` からのインポートが動作することを確認する

## 4. テスト・品質確認（TDD: REFACTOR フェーズ）

- [ ] 4.1 `pytest tests/llm/test_validation.py -v` がすべてパスすることを確認する
- [ ] 4.2 `pytest --cov=spautopost.llm.validation --cov-report=term-missing` でカバレッジ 80% 以上を確認する
- [ ] 4.3 `ruff check src/spautopost/llm/validation.py` がパスすることを確認する
- [ ] 4.4 `mypy src/spautopost/llm/validation.py` がエラーなしで通ることを確認する
- [ ] 4.5 既存の `pytest tests/llm/test_provider.py` が引き続きパスすることを確認する（リグレッションチェック）

## 5. openspec アーカイブと PR

- [ ] 5.1 `openspec validate issue-18-ai-output-validation --strict` を実行し PASS を確認する
- [ ] 5.2 変更を git commit する（`feat: add AI output validation and source-grounding checks`）
- [ ] 5.3 `/opsx:archive issue-18-ai-output-validation` を実行し change をアーカイブする
- [ ] 5.4 GitHub に PR を作成する（base: main）
