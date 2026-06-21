# Initial System Specification

## Status

Proposed

## Overview

SPAutoPost は、社内 SharePoint お知らせ掲示板にセキュリティ対策情報、脆弱性情報、対応方法を掲載するための自動化プログラムです。

初期実装では、手動入力または簡易収集した脆弱性情報を正規化し、生成 AI を用いて掲示板向け原稿を作成し、人間レビューを経て SharePoint に下書きまたはテスト投稿します。

## System Boundary

### 初期段階で SPAutoPost が持つ責務

- 脆弱性情報の手動入力
- 脆弱性情報の簡易収集
- 情報の正規化
- 投稿要否・優先度の簡易判定
- 生成 AI による掲示板原稿作成
- 人間レビュー用の状態管理
- SharePoint への下書きまたは投稿
- 監査ログ

### 将来的に外部化可能な責務

- 本格 crawler
- 大量情報源の収集
- 社内資産台帳との詳細照合
- 脅威インテリジェンスの高度な相関分析
- SOC / SIEM / ITSM 連携

## Core Workflow

```text
Source Input / Collector
  -> Normalize Advisory
  -> Relevance and Triage
  -> Draft Composition by LLM
  -> Human Review
  -> Approval
  -> SharePoint Draft / Publish
  -> Audit Log
```

## Core Data Models

### Advisory

脆弱性またはセキュリティ注意喚起を表す正規化データです。

推奨フィールド:

- advisory_id
- source_type
- source_name
- source_url
- source_retrieved_at
- cve_ids
- jvn_ids
- vendor_advisory_ids
- title
- summary
- affected_products
- affected_versions
- severity
- cvss_version
- cvss_score
- cvss_vector
- exploit_status
- kev_status
- patch_available
- mitigation
- workaround
- references
- published_at
- updated_at
- source_confidence

### DraftPost

SharePoint 掲示板向けの原稿です。

推奨フィールド:

- draft_id
- advisory_ids
- title
- audience
- urgency
- summary_for_users
- impact
- required_actions
- admin_actions
- deadline
- references
- generated_by_provider
- prompt_version
- generation_input_hash
- status
- reviewer
- review_comments
- created_at
- updated_at

### Publication

SharePoint への投稿結果です。

推奨フィールド:

- publication_id
- draft_id
- target_site_id
- target_list_id
- target_page_id
- sharepoint_item_id
- sharepoint_page_id
- publication_status
- idempotency_key
- published_at
- error_code
- error_message

## State Model

DraftPost の推奨状態:

```text
created
  -> generated
  -> review_requested
  -> reviewed
  -> approved
  -> publishing
  -> published
```

例外状態:

```text
rejected
regeneration_requested
failed
cancelled
```

## LLM Provider Model

生成 AI provider は差し替え可能にします。

推奨 interface:

```text
Provider.generateDraft(input: DraftInput) -> DraftOutput
Provider.validateConfig() -> ProviderStatus
Provider.estimateCost(input: DraftInput) -> CostEstimate optional
```

provider 種別:

- production_api: 実稼働 API provider
- production_flow: Copilot Studio などの workflow/agent provider
- generic_api: その他 LLM API
- test_mock: fixture / mock
- test_manual: ChatGPT / Claude subscription 等を使う人間操作前提の検証

## SharePoint Publishing Model

SharePoint 投稿方式は、初期 Issue で確定します。

候補:

1. SharePoint List item
2. SharePoint Site Page

選定観点:

- 既存のお知らせ掲示板の実体
- 既存 UI との整合
- 下書きと公開の扱い
- 権限モデル
- 添付ファイル・画像・リンクの扱い
- API の安定性
- 監査ログ
- 既存運用への影響

## Security Requirements

- Microsoft Graph 権限は最小権限にする。
- SharePoint 投稿先を設定で固定し、任意 URL への投稿を許可しない。
- LLM provider へ渡す入力は最小化する。
- 出典情報と生成結果を紐づけ、根拠不明の文章を避ける。
- 投稿前に人間レビューを挟む。
- API キー、Secret、token、Cookie をログに出さない。
- 投稿処理は idempotency key を持つ。
- 失敗時の再試行で重複投稿しない。
- PoC や攻撃手順の詳細生成を避け、対応方法中心にする。

## Non-Functional Requirements

- CLI または batch 実行から開始できること。
- dry-run が可能であること。
- provider を設定で切り替えられること。
- source adapter を追加しやすいこと。
- crawler 分離後も normalized advisory import で継続利用できること。
- 監査ログから投稿根拠を追跡できること。

## Open Questions

- SharePoint お知らせ掲示板の実体は List か Site Page か。
- 投稿は下書き止まりか、承認後に公開まで行うか。
- 実稼働の第一 provider は Copilot Studio か Microsoft Foundry / Azure OpenAI か。
- ChatGPT / Claude subscription をテストでどこまで使うか。
- 社内資産との関連度判定に使う製品リストをどこで管理するか。
- 監査ログの保存先をどこにするか。
