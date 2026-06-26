## ADDED Requirements

### Requirement: 監査イベントに必須項目を記録する
システムは、すべての監査イベントに `audit_event_id`・`event_type`・`correlation_id`・`result`・`created_at` を含めなければならない（SHALL）。

#### Scenario: 必須項目の完全性
- **WHEN** 任意の監査イベントが記録される
- **THEN** audit_event_id・event_type・correlation_id・result・created_at がすべて存在する

### Requirement: 規定のイベント種別のみを使用する
システムは、`source_fetch`・`source_parse`・`normalize`・`triage`・`draft_generate`・`draft_validate`・`review`・`approve`・`reject`・`regenerate`・`publish_dry_run`・`publish_create`・`publish_update`・`publish_result`・`error` のいずれかの event_type のみを使用しなければならない（SHALL）。

#### Scenario: 不正な event_type の拒否
- **WHEN** 規定外の event_type で監査イベントを記録しようとする
- **THEN** システムはエラーを返し、不正なイベントを記録しない

### Requirement: ログへの機微情報出力を禁止する
システムは、API key・access token・refresh token・client secret・certificate private key・cookie・authorization header・不要な個人情報を監査ログに出力してはならない（SHALL NOT）。

#### Scenario: 機微情報のマスク
- **WHEN** 監査ログに認証情報を含む可能性がある操作を記録する
- **THEN** 機微情報はログに含まれず、Secret 値が平文で記録されない

### Requirement: correlation_id で一連の処理を追跡する
システムは、1 回の実行単位・1 draft generation 単位・1 publication attempt 単位に correlation_id を付与しなければならない（SHALL）。

#### Scenario: correlation_id による処理追跡
- **WHEN** 一連の処理（収集→正規化→生成→レビュー→投稿）が実行される
- **THEN** 各ステップの監査ログに同一 correlation_id が付与されている

### Requirement: Prompt と LLM 出力の保存は最小化する
MVP では、prompt 全文と LLM 出力全文を監査ログに直接出力してはならない（SHALL NOT）。`prompt_version` と `generation_input_hash` を保存する。LLM 出力本文は DraftPost として保存する。

#### Scenario: prompt_version の記録
- **WHEN** LLM によって原稿が生成される
- **THEN** 監査ログに prompt_version が記録され、raw prompt 全文は含まれない

### Requirement: 失敗時の監査情報を記録する
システムは、失敗イベントに `operation`・`error_code`・`error_message`・`correlation_id`・`created_at` を記録しなければならない（SHALL）。`retryable`・`failure_count`・`target` など追加コンテキストは `related_ids` に格納する。

#### Scenario: 投稿失敗の記録
- **WHEN** SharePoint への投稿が失敗する
- **THEN** error_code・error_message・operation を含む失敗監査ログが記録される

### Requirement: レビュー・承認の監査情報を記録する
システムは、review / approve / reject イベントに `draft_id`・`reviewer`・`action`・`previous_status`・`next_status`・`created_at` を記録しなければならない（SHALL）。

#### Scenario: 承認イベントの記録
- **WHEN** レビュアーが DraftPost を承認する
- **THEN** draft_id・reviewer・previous_status・next_status を含む approve イベントが記録される
