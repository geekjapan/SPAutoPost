## ADDED Requirements

### Requirement: ValidationIssue と ValidationResult の型定義

システムは `ValidationIssue` および `ValidationResult` を frozen dataclass として定義しなければならない（SHALL）。

- `ValidationIssue`: `severity: Literal["error", "warning", "info"]`, `code: str`, `message: str`, `reviewer_hint: str | None`
- `ValidationResult`: `issues: Sequence[ValidationIssue]`, `regeneration_hints: Sequence[str]`, `reviewer_warnings: Sequence[str]`（`has_errors`・`has_warnings` は derived property、`__post_init__` で全シーケンスを tuple に強制）

#### Scenario: ValidationResult が issues から has_errors を自動導出する
- **WHEN** severity が "error" の `ValidationIssue` を含む `ValidationResult` を生成する
- **THEN** `has_errors` が `True` となること

#### Scenario: ValidationResult がエラーなしの場合に has_errors が False になる
- **WHEN** severity が "warning" のみの `ValidationIssue` を含む `ValidationResult` を生成する
- **THEN** `has_errors` が `False` となること

### Requirement: required sections check

`validate_draft_output` 関数は `DraftOutput` の必須フィールドが空でないことを検証しなければならない（SHALL）。

対象フィールド: `title`, `summary_for_users`, `impact`, `required_actions`

欠落または空文字列の場合は `code="missing_required_section"`, `severity="error"` の `ValidationIssue` を発行する。
`required_actions` については、空シーケンスだけでなく空白のみの文字列しか含まないシーケンスも「空」として扱う。

#### Scenario: 必須セクションがすべて存在する場合
- **WHEN** title, summary_for_users, impact, required_actions がすべて非空の DraftOutput を検証する
- **THEN** `missing_required_section` エラーが発行されないこと

#### Scenario: title が空文字列の場合
- **WHEN** title が空文字列の DraftOutput を検証する
- **THEN** `code="missing_required_section"` かつ `severity="error"` の ValidationIssue が発行されること

#### Scenario: required_actions が空リストの場合
- **WHEN** required_actions が空リストの DraftOutput を検証する
- **THEN** `code="missing_required_section"` かつ `severity="error"` の ValidationIssue が発行されること

#### Scenario: required_actions が空白文字列のみを含む場合
- **WHEN** required_actions が `('',)` や `('   ',)` のみの DraftOutput を検証する
- **THEN** `code="missing_required_section"` かつ `severity="error"` の ValidationIssue が発行されること

### Requirement: references check（出典根拠チェック）

`validate_draft_output` 関数は references が空の場合に警告を発行しなければならない（SHALL）。

出典がない場合は `code="no_references"`, `severity="warning"` の `ValidationIssue` を発行し、`reviewer_hint` に「出典情報を確認してください」を設定する。
`references` のシーケンス自体が非空でも、有効な `url` 文字列を持つエントリが 1 件もない場合は同様に警告を発行する。

#### Scenario: references が存在する場合
- **WHEN** references に 1 件以上の有効な url を持つエントリを持つ DraftOutput を検証する
- **THEN** `no_references` 警告が発行されないこと

#### Scenario: references が空リストの場合
- **WHEN** references が空リストの DraftOutput を検証する
- **THEN** `code="no_references"` かつ `severity="warning"` の ValidationIssue が発行され、reviewer_hint が設定されること

#### Scenario: references が url を持たないエントリのみの場合
- **WHEN** references が `({'label': 'vendor'},)` のような url なしエントリの DraftOutput を検証する
- **THEN** `code="no_references"` かつ `severity="warning"` の ValidationIssue が発行されること

### Requirement: unsupported claim check（根拠なし断定チェック）

`validate_draft_output` 関数は出典なし断定を示すパターンを検出した場合に警告を発行しなければならない（SHALL）。

検出条件: `warnings` フィールドが空 かつ `validation_hints` に `guardrail:no_unsupported_claims` が含まれていない場合。
発行する issue: `code="unsupported_claim_risk"`, `severity="warning"`, `reviewer_hint` に確認依頼を設定する。
`validation_hints` が `None` の場合は空シーケンスとして扱う（防御的プログラミング）。

#### Scenario: guardrail が設定済みの場合
- **WHEN** validation_hints に "guardrail:no_unsupported_claims" を含む DraftOutput を検証する
- **THEN** `unsupported_claim_risk` 警告が発行されないこと

#### Scenario: guardrail も warnings も存在しない場合
- **WHEN** validation_hints が空かつ warnings が空の DraftOutput を検証する
- **THEN** `code="unsupported_claim_risk"` かつ `severity="warning"` の ValidationIssue が発行されること

### Requirement: dangerous detail guardrail（攻撃手順・PoC 抑制）

`validate_draft_output` 関数は、生成テキストに攻撃手順・PoC・exploit 詳細を示すパターンが含まれる場合にエラーを発行しなければならない（SHALL）。

検出対象フィールド: `title`, `summary_for_users`, `impact`, および `required_actions`, `admin_actions` のすべてのテキスト。
発行する issue: `code="dangerous_detail_detected"`, `severity="error"`, `reviewer_hint` に除去・差替依頼を設定する。

検出パターン例（英日両方）:
- `exploit code`, `proof of concept`, `poc`, `attack steps`, `payload`, `reverse shell`, `shellcode`
- `攻撃手順`, `悪用コード`, `exploit コード`

実装上の注意: `re.ASCII` フラグを使用し `\b` をASCII文字のみ基準の単語境界として動作させることで、
日本語に隣接するパターン（`PoCが発見` 等）を正しく検出しつつ `epoch`/`pocket` 等への誤検出を防ぐ。

#### Scenario: 攻撃手順を含まない通常の原稿
- **WHEN** 攻撃手順・PoC に関するパターンを含まない DraftOutput を検証する
- **THEN** `dangerous_detail_detected` エラーが発行されないこと

#### Scenario: required_actions に "exploit コード" が含まれる場合
- **WHEN** required_actions のいずれかに "exploit コード" を含む DraftOutput を検証する
- **THEN** `code="dangerous_detail_detected"` かつ `severity="error"` の ValidationIssue が発行されること

#### Scenario: validation_hints に guardrail:no_attack_steps_or_poc が設定済みかつテキストに危険パターンなし
- **WHEN** validation_hints に "guardrail:no_attack_steps_or_poc" を含み、本文に危険パターンがない DraftOutput を検証する
- **THEN** `dangerous_detail_detected` エラーが発行されないこと

### Requirement: uncertainty wording check（不確実性ラベルチェック）

`validate_draft_output` 関数は、`uncertainty_notes` が空の場合に reviewer に確認を促す info を発行しなければならない（SHALL）。

発行する issue: `code="no_uncertainty_notes"`, `severity="info"`, `reviewer_hint` に不確実情報の確認依頼を設定する。

#### Scenario: uncertainty_notes が存在する場合
- **WHEN** uncertainty_notes に 1 件以上のエントリを持つ DraftOutput を検証する
- **THEN** `no_uncertainty_notes` info が発行されないこと

#### Scenario: uncertainty_notes が空の場合
- **WHEN** uncertainty_notes が空リストの DraftOutput を検証する
- **THEN** `code="no_uncertainty_notes"` かつ `severity="info"` の ValidationIssue が発行されること

### Requirement: regeneration request reason（再生成要求理由）

`validate_draft_output` 関数は `has_errors` が `True` の場合に再生成要求理由をまとめた文字列リストを `ValidationResult.regeneration_hints` として提供しなければならない（SHALL）。

`regeneration_hints` は error severity の issue の `message` を集約したリスト。エラーがない場合は空リスト。

#### Scenario: error が存在する場合に regeneration_hints が設定される
- **WHEN** missing_required_section エラーを含む ValidationResult を取得する
- **THEN** `regeneration_hints` が非空であること

#### Scenario: error がない場合に regeneration_hints が空になる
- **WHEN** error severity の issue がない ValidationResult を取得する
- **THEN** `regeneration_hints` が空リストであること

### Requirement: reviewer warning の集約

`validate_draft_output` 関数は `reviewer_hint` を持つ issue の hint を `ValidationResult.reviewer_warnings` として集約しなければならない（SHALL）。

#### Scenario: reviewer_hint を持つ issue が存在する場合
- **WHEN** reviewer_hint が設定された ValidationIssue を含む ValidationResult を取得する
- **THEN** `reviewer_warnings` にその hint が含まれること

#### Scenario: reviewer_hint を持つ issue がない場合
- **WHEN** すべての ValidationIssue の reviewer_hint が None の ValidationResult を取得する
- **THEN** `reviewer_warnings` が空リストであること

### Requirement: validate_draft_output の公開 API

`src/spautopost/llm/validation.py` は `validate_draft_output`, `ValidationResult`, `ValidationIssue` を `__all__` でエクスポートしなければならない（SHALL）。
`src/spautopost/llm/__init__.py` の `__all__` にこれらを追加しなければならない（SHALL）。

#### Scenario: llm パッケージから validate_draft_output をインポートできる
- **WHEN** `from spautopost.llm import validate_draft_output` を実行する
- **THEN** ImportError が発生しないこと
