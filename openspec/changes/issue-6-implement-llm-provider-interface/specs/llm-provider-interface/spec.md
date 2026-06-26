## ADDED Requirements

### Requirement: LLM provider interface

システムは LLM provider を Python interface として表現しなければならない（SHALL）。interface は少なくとも `validate_config()`、`generate_draft(input: DraftInput)`、`get_provider_metadata()` を提供しなければならない（SHALL）。実 provider 固有の SDK、HTTP client、認証情報を呼び出し側へ露出してはならない（SHALL NOT）。

#### Scenario: 呼び出し側が provider 実装に依存しない

- **WHEN** 業務ロジックが draft を生成する
- **THEN** `LLMProvider` interface の method だけを呼び出せる

### Requirement: DraftInput と DraftOutput

システムは provider へ渡す `DraftInput` と provider から返す `DraftOutput` を定義しなければならない（SHALL）。`DraftInput` は advisory、target audience、target language、urgency、template ID、prompt version、references を保持しなければならない（SHALL）。`DraftOutput` は title、summary for users、impact、required actions、references を保持しなければならない（SHALL）。これらの DTO は Secret、token、cookie、authorization header を保持してはならない（SHALL NOT）。

#### Scenario: draft DTO を import できる

- **WHEN** provider 実装またはテストが `DraftInput` / `DraftOutput` を import する
- **THEN** 追加の外部依存なしで DTO を利用できる

### Requirement: deterministic mock provider

システムは `test_mock` provider を提供しなければならない（SHALL）。`test_mock` は外部通信してはならず（SHALL NOT）、同じ fixture と input に対して同じ `DraftOutput` を返さなければならない（SHALL）。

#### Scenario: fixture response を返す

- **WHEN** fixture 付きの mock provider に `DraftInput` を渡す
- **THEN** fixture と同じ `DraftOutput` を返す

#### Scenario: fixture なしでも deterministic response を返す

- **WHEN** fixture なしの mock provider に同じ `DraftInput` を複数回渡す
- **THEN** 同じ `DraftOutput` を返す

### Requirement: provider metadata と validation

システムは provider の種類、名前、model または deployment name、prompt version を metadata として取得できなければならない（SHALL）。provider は自身の config を検証し、valid / issues / provider metadata を含む status を返さなければならない（SHALL）。validation error は Secret 値を含めてはならない（SHALL NOT）。

#### Scenario: mock provider config を検証する

- **WHEN** `test_mock` provider の config を検証する
- **THEN** Secret 値を要求せず valid な status を返す

#### Scenario: 未実装 production provider を構築しない

- **WHEN** `production_api` / `production_flow` / `generic_api` / `test_manual` が選択される
- **THEN** provider type は表現できるが、この change では実 provider を構築しない
