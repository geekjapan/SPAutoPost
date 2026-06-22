# Specs

このディレクトリには、SPAutoPost の仕様を配置します。

## 位置づけ

Spec は GitHub repo 上の正本です。実装エージェントは、Issue と関連 Spec を確認してから OpenSpec change を作成し、実装します。

## Spec 一覧

| Spec | Status | 主な関連 Issue | 内容 |
|---|---|---|---|
| `initial-system.md` | Proposed | #1 | 初期システム境界、ワークフロー、主要データモデル |
| `architecture.md` | Accepted for MVP direction | #4, #6, #7, #9, #10, #21, #23, #26, #28, #29 | Azure hosted core、Python CLI/Batch、SQLite、Admin API/UI in M1、Azure Container Apps / Jobs |
| `admin-authentication.md` | Accepted for MVP direction | #26, #29 | Admin API / UI の Microsoft Entra ID ログイン認証 |
| `graph-authentication.md` | Proposed | #2, #9, #24, #27 | Microsoft Graph service authentication の比較と決定論点 |
| `sharepoint-publishing.md` | Accepted for MVP publishing mode | #2, #9, #20 | SharePoint Site Page / News 投稿方式、権限、下書き、公開、冪等性 |
| `data-model.md` | Proposed | #3, #10, #20, #28 | Advisory / DraftPost / Publication / AuditEvent |
| `llm-provider.md` | Proposed | #6, #15, #16, #17, #18 | LLM provider 分類、実稼働/テスト分離、入力制限 |
| `draft-composition.md` | Proposed | #8, #18, #19 | 掲示板原稿構成、文体、出典、AI 出力検査 |
| `source-collection.md` | Proposed | #7, #11, #12, #13, #21 | 脆弱性情報源 adapter、差分取得、出典保持 |
| `normalization-and-triage.md` | Proposed | #14, #18, #19 | 名寄せ、重複排除、優先度判定、掲載候補判定 |
| `review-approval-workflow.md` | Proposed | #19, #20, #26, #29 | 人間レビュー、承認、差し戻し、公開制御 |
| `audit-log.md` | Proposed | #5, #10, #19, #22, #29 | 監査ログ、correlation ID、保存禁止項目、user principal 記録 |
| `security-baseline.md` | Proposed | #5, #15, #22, #27, #29 | Secret、権限最小化、LLM 入力制限、投稿安全性 |
| `configuration.md` | Proposed | #4, #6, #9, #10 | config、環境変数、feature flag、dry-run |
| `error-handling.md` | Proposed | #10, #20, #21, #22 | error code、retry/backoff、停止条件 |
| `external-collector-boundary.md` | Proposed | #13, #21 | crawler / collector 外部化時の import 境界 |

全体の設計書面一覧は `docs/design-documents.md` を参照してください。

## 推奨構成

Spec には、可能な限り次を含めます。

- 背景
- 目的
- ユースケース
- 対象範囲
- 非対象範囲
- 入力
- 出力
- 状態遷移
- エラー時動作
- 権限・認証・認可
- 外部サービス連携
- レート制限
- 再試行
- 重複防止
- データ保持
- 監査ログ
- セキュリティ要件
- 非機能要件
- 受け入れ条件

## ファイル命名

推奨形式:

```text
<area>.md
<feature-name>.md
```

例:

```text
architecture.md
sharepoint-publishing.md
admin-authentication.md
graph-authentication.md
llm-provider.md
audit-log.md
```

## 変更ルール

- 仕様変更は Issue と紐づけます。
- 実装だけを変更し、Spec を放置しないでください。
- 仕様が未確定の場合は、未確定であることを明記します。
- セキュリティ、外部 API、投稿動作に関わる仕様は推測で補完しません。
- Status を Accepted にする場合は、関連 Issue または decision record で判断根拠を残してください。
