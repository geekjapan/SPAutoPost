## ADDED Requirements

### Requirement: Dry-run SharePoint payload preview

システムは生成済み原稿（`DraftOutput`）から SharePoint Site Page 投稿予定 payload を組み立て、実投稿せずに確認できなければならない（SHALL）。payload は `docs/specs/draft-composition.md` の必須セクション構成（概要・影響・対象・利用者が行う対応・管理者が行う対応・対応期限または推奨対応時期・参考情報）を保持しなければならない（SHALL）。dry-run preview は SharePoint への作成・更新、Microsoft Graph 接続、外部 API 呼び出し、永続化を行ってはならない（SHALL NOT）。

#### Scenario: 投稿予定 payload を確認する
- **WHEN** ユーザーが `spautopost preview-draft <advisory-file>` を実行する
- **THEN** システムは件名と必須セクションを含む投稿予定 payload を表示し、実投稿・外部 API 呼び出しを行わない

#### Scenario: 必須セクションを順序通り保持する
- **WHEN** dry-run preview が payload を組み立てる
- **THEN** payload は draft-composition.md の必須セクションを規定順で含む

### Requirement: Minimal audit event for dry-run

システムは dry-run の生成・preview に対し、最小限の `AuditEvent`（`publish_dry_run` / `success`）を組み立てなければならない（SHALL）。イベントは provider 名、provider type、prompt version、generation_input_hash、投稿先識別子、operation、result を最小限記録しなければならない（SHALL）。

#### Scenario: 生成 provenance を記録する
- **WHEN** dry-run preview が原稿を生成する
- **THEN** システムは provider 名・provider type・prompt version・generation_input_hash・operation=`dry-run`・result=`success` を持つ `publish_dry_run` イベントを組み立てる

### Requirement: Failure audit event for dry-run

システムは dry-run の原稿生成が失敗した場合、`error` / `failure` の `AuditEvent` を組み立て、error_code と error_message で失敗を追跡できなければならない（SHALL）。

#### Scenario: 生成失敗を追跡する
- **WHEN** dry-run preview の原稿生成が例外で失敗する
- **THEN** システムは event_type=`error`・result=`failure`・error_code・error_message を持つ監査イベントを表示する

### Requirement: Secret redaction in preview and audit output

システムは dry-run preview と監査イベント出力に Secret 値、token、`env:` 参照を含めてはならない（SHALL NOT）。投稿先識別子が `env:` 参照の場合は redaction しなければならない（SHALL）。

#### Scenario: 投稿先 Secret 参照を秘匿する
- **WHEN** 投稿先 site_id / page_library_id が `env:NAME` 参照である
- **THEN** システムは出力でこれらを `***` に置換し、解決済み Secret 値も `env:` 参照も出力しない
