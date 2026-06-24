## ADDED Requirements

### Requirement: 正規化済みコアエンティティと必須項目

システムは正規化済みコアデータモデルとして `SourceRecord` / `Advisory` / `DraftPost` / `ReviewEvent` / `Publication` / `AuditEvent` の各エンティティを定義しなければならない（SHALL）。各エンティティの必須項目は `docs/specs/data-model.md`（normative reference）に従い、最低限 `Advisory` は `advisory_id` / `title` / `summary` / `source_refs` / `references` / `created_at` / `normalized_at` を、`DraftPost` は `draft_id` / `advisory_ids` / `title` / `audience` / `urgency` / `summary_for_users` / `impact` / `required_actions` / `status` を、`Publication` は `publication_id` / `draft_id` / `target_type` / `target_site_id` / `publication_status` / `idempotency_key` を、`AuditEvent` は `audit_event_id` / `event_type` / `correlation_id` / `result` / `created_at` を必須として持たなければならない（SHALL）。各エンティティは外部 ID とは独立した内部 ID 文字列を持たなければならない（SHALL）。

#### Scenario: 4 つのコアエンティティが定義されている
- **WHEN** データモデル定義を検査する
- **THEN** `Advisory` / `DraftPost` / `Publication` / `AuditEvent` が必須項目付きで定義されており、出典・レビューを成立させる `SourceRecord` / `SourceRef` / `ReviewEvent` も定義されている

#### Scenario: 必須項目を欠いたエンティティは不適合
- **WHEN** `Publication` が `idempotency_key` を持たない、または `Advisory` が `source_refs` を持たない
- **THEN** そのレコードはデータモデルに不適合と判定できる

### Requirement: 出典から投稿結果までのトレーサビリティ

システムは出典（source）→ AI 生成（draft generation）→ レビュー（review）→ 投稿結果（publication result）の連鎖を ID 参照で追跡可能にしなければならない（SHALL）。`Advisory.source_refs` は各情報源を `source_record_id` で参照し、`DraftPost.advisory_ids` は元の `Advisory` を、`ReviewEvent.draft_id` と `Publication.draft_id` は対象 `DraftPost` を、`AuditEvent.related_ids` は関連エンティティ（識別可能な型プレフィックス付き ID、またはエンティティ型と ID のペア）を参照しなければならない（SHALL）。任意の `Publication` から逆方向に `DraftPost` → `Advisory` → `SourceRecord` まで辿れなければならない（SHALL）。

#### Scenario: 投稿結果から出典まで遡及できる
- **WHEN** ある `Publication` を起点に参照をたどる
- **THEN** `draft_id` 経由で `DraftPost`、`advisory_ids` 経由で `Advisory`、`source_refs` 経由で `SourceRecord` まで到達できる

#### Scenario: レビュー履歴が原稿に紐づく
- **WHEN** ある `DraftPost` のレビュー履歴を参照する
- **THEN** `draft_id` で紐づく `ReviewEvent` 群（action と reviewer を含む）を取得できる

### Requirement: 投稿の idempotency key

システムは `Publication` に `idempotency_key`（必須）を持たせ、投稿先と `DraftPost` の組み合わせから決定的に導出しなければならない（SHALL）。同一の投稿先・原稿に対する重複投稿は同一 `idempotency_key` により検出可能でなければならない（SHALL）。`idempotency_key` の導出に Secret 値を含めてはならない（SHALL NOT）。

#### Scenario: 重複投稿が同一キーになる
- **WHEN** 同一 `DraftPost` を同一投稿先に再投稿しようとする
- **THEN** 同一の `idempotency_key` が導出され、重複として識別できる

### Requirement: AI 生成の provenance メタデータ

システムは AI が生成した `DraftPost` に対し、生成の素性を追跡できるメタデータを保持しなければならない（SHALL）。最低限 `generated_by_provider`（provider 名）、`provider_type`（`production_api` / `production_flow` / `generic_api` / `test_mock` / `test_manual`）、`prompt_version`、`generation_input_hash` を記録できなければならない（SHALL）。`generation_input_hash` は AI に渡した正規化済み入力から決定的に導出しなければならない（SHALL）。

#### Scenario: 生成 provenance を記録する
- **WHEN** AI provider が `DraftPost` を生成する
- **THEN** provider 名・provider type・prompt version・generation_input_hash を当該 `DraftPost` に記録できる

#### Scenario: 同一入力が同一 input hash になる
- **WHEN** 同一の正規化済み入力で生成を 2 回行う
- **THEN** 同一の `generation_input_hash` が導出される

### Requirement: external collector 分離後も使える input model

システムは将来 crawler / collector を分離した場合でも、正規化済み advisory を import して同一の `Advisory` モデルへ変換できる input model を維持しなければならない（SHALL）。import schema は最低限 `schema_version` / `producer` / `generated_at` と advisory 配列を含み、各 advisory は `title` / `summary` / `references` と enum 制約済みフィールドを持たなければならない（SHALL、詳細は `docs/specs/external-collector-boundary.md` を normative reference とする）。import は `producer` と `external_advisory_id` の組み合わせ、または `source_url` や `raw_hash` により一意に重複を識別できなければならない（SHALL）。`cve_ids` / `jvn_ids` は関連付けと検索のための属性であり、それだけを dedupe 主キーとして扱ってはならない（SHALL NOT）。

#### Scenario: 正規化済み import が Advisory に変換される
- **WHEN** external collector が `schema_version` 付きの正規化済み advisory を file import する
- **THEN** 各レコードは内部 `Advisory` モデル（`source_refs` 付き）へ変換でき、ランタイムの後続処理（draft composition 以降）が collector の有無に依存しない

#### Scenario: import の重複を識別できる
- **WHEN** 同一 producer から同一 external_advisory_id を持つレコードを再 import する
- **THEN** 重複として識別できる

### Requirement: データモデルに Secret を保存しない

システムはデータモデルのいかなるエンティティにも Secret 値（API key / access token / refresh token / client secret / private key / cookie / authorization header）を保存してはならない（SHALL NOT）。投稿先識別子等が `env:` 参照である場合、永続化・表示の対象は参照名のみとし、解決済み Secret 値を保持してはならない（SHALL NOT）。

#### Scenario: Secret はモデルに含まれない
- **WHEN** 任意のエンティティのフィールド集合を検査する
- **THEN** token / key / secret / cookie / authorization header を保持するフィールドが存在しない
