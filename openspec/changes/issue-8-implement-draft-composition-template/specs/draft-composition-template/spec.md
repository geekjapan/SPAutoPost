## ADDED Requirements

### Requirement: SharePoint announcement draft template

システムは Advisory から SharePoint announcements 向け DraftOutput を生成しなければならない（SHALL）。DraftOutput は title、summary_for_users、impact、required_actions、admin_actions、deadline または urgency、references を保持しなければならない（SHALL）。

#### Scenario: Advisory から DraftOutput を生成する

- **WHEN** Advisory 相当の DraftInput を composition template に渡す
- **THEN** SharePoint announcements 向けの title、summary_for_users、impact、required_actions、admin_actions を持つ DraftOutput が返る

### Requirement: References are retained

システムは DraftInput.references を DraftOutput.references に保持しなければならない（SHALL）。システムは入力にない URL を DraftOutput.references に追加してはならない（SHALL NOT）。

#### Scenario: 出典リンクを保持する

- **WHEN** references を含む DraftInput から draft を生成する
- **THEN** DraftOutput.references は入力 references と同じ URL を保持する

### Requirement: User and administrator sections

システムは一般利用者向け説明を `summary_for_users` と `required_actions` に、管理者向け説明を `admin_actions` に分離しなければならない（SHALL）。

#### Scenario: 利用者向けと管理者向けを分離する

- **WHEN** mixed audience の DraftInput から draft を生成する
- **THEN** DraftOutput は一般利用者向け欄と管理者向け欄の両方を持つ

### Requirement: Draft guardrails

システムは過剰断定、出典にない被害断定、PoC や攻撃手順の詳細化を避ける guardrail を template に含めなければならない（SHALL）。不明点は本文で断定せず reviewer 向け warning または uncertainty note として扱わなければならない（SHALL）。

#### Scenario: guardrail を記録する

- **WHEN** draft を生成する
- **THEN** DraftOutput.validation_hints または warnings に guardrail / human review の情報が含まれる

### Requirement: Prompt version is recorded

システムは draft 生成時に DraftInput.prompt_version を生成結果の監査可能な情報として保持しなければならない（SHALL）。

#### Scenario: prompt version を保持する

- **WHEN** prompt_version を持つ DraftInput から draft を生成する
- **THEN** DraftOutput.source_mapping または provider metadata から prompt_version を確認できる
