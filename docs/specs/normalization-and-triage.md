# Normalization and Triage Specification

## Status

Proposed

## Purpose

この Spec は、複数情報源から取得した脆弱性情報を Advisory に統合し、重複排除、優先度付け、掲載要否判定を行うルールを定義します。

## Normalization Goals

- CVE / JVN / vendor advisory を同一 Advisory に名寄せする。
- 深刻度、悪用状況、修正有無、社内関連度を扱える形にする。
- AI 作文に使いやすい構造へ整える。
- 投稿の重複を防ぐための stable key を生成する。

## Identity Resolution

優先キー:

1. CVE ID
2. JVN ID
3. vendor advisory ID
4. canonical URL
5. normalized title + vendor + product + published_at

同一判定:

- 同じ CVE ID を持つ場合は原則同一 Advisory
- JVN ID と CVE ID が対応する場合は統合
- vendor advisory が CVE ID を含む場合は統合
- CVE ID がない vendor advisory は vendor/product/title/published_at で近似判定し、人間レビュー対象にする

## Field Merge Rule

- title: 日本語があれば MyJVN / JVN を優先。ただし vendor title を別名として保持してよい。
- summary: 日本語 summary を優先し、NVD description は補助情報とする。
- severity: CVSS score がある場合は CVSS に基づく。複数 source で差がある場合は最大値を保持し、差分を warning に残す。
- references: 重複 URL を除去してすべて保持する。
- mitigation: vendor / JVN の対応方法を優先する。
- exploit_status: KEV または信頼できる source を優先する。

## Severity Mapping

推奨:

- critical: CVSS >= 9.0
- high: 7.0 <= CVSS < 9.0
- medium: 4.0 <= CVSS < 7.0
- low: 0.1 <= CVSS < 4.0
- unknown: CVSS 不明

## Priority Score

初期の priority score は単純な加点方式とします。

例:

- critical: +40
- high: +30
- medium: +15
- KEV listed: +40
- exploit confirmed: +30
- patch available: +10
- internal relevance confirmed: +30
- internet-facing product suspected: +15
- source confidence low: -10

推奨 urgency:

- emergency: score >= 80
- high: 60 <= score < 80
- normal: 30 <= score < 60
- low: score < 30

## Internal Relevance

初期段階では完全な資産台帳連携を行いません。

代替手段:

- product keyword list
- manually maintained watchlist
- vendor watchlist
- reviewer override

internal_relevance:

- confirmed
- suspected
- unknown
- not_applicable

## Publication Candidate Rule

投稿候補とする条件例:

- emergency または high
- KEV listed
- 社内関連度 confirmed
- 利用者対応が必要
- 管理者対応を促す必要がある

投稿候補から除外する条件例:

- 社内関連度 not_applicable
- severity low かつ悪用情報なし
- 既に同一内容を掲載済み
- 出典が不足している

## Duplicate Post Guard

duplicate key の候補:

- cve_ids sorted
- jvn_ids sorted
- vendor_advisory_ids sorted
- normalized title hash
- target audience

Publication の idempotency_key と組み合わせて、再投稿を防ぎます。

## Reviewer Override

自動判定は最終判断ではありません。

reviewer は次を上書きできます。

- urgency
- audience
- publication_candidate
- internal_relevance
- deadline
- required_actions

上書きは AuditEvent に記録します。

## Related Issues

- #14 Implement normalization, deduplication, and priority scoring
- #18 Add AI output validation and source-grounding checks
- #19 Implement review and approval workflow
