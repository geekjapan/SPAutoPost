# Review and Approval Workflow Specification

## Status

Proposed

## Purpose

この Spec は、AI が生成した SharePoint 掲示板原稿を人間がレビューし、承認、差し戻し、再生成、公開へ進めるための状態遷移と操作ルールを定義します。

## Principle

MVP では、AI 生成文の完全自動公開を禁止します。

- AI 生成後は必ず review_requested にする。
- approved でない DraftPost は publish できない。
- reviewer が出典、表現、対象、対応方法、緊急度を確認する。

## Actors

- generator: LLM provider またはシステム
- reviewer: セキュリティ担当者
- approver: 公開承認者。MVP では reviewer と兼務可
- publisher: SharePoint 投稿処理を実行する service principal またはユーザー

## State Transition

```text
created
  -> generated
  -> review_requested
  -> reviewed
  -> approved
  -> publishing
  -> published
```

例外:

```text
review_requested -> regeneration_requested -> generated
review_requested -> rejected
approved -> publishing -> failed
publishing -> published
publishing -> failed
```

## State Definitions

### created

Advisory から DraftPost の枠が作成された状態。

### generated

LLM または template により本文が生成された状態。

### review_requested

人間レビュー待ち。

### reviewed

reviewer が内容を確認し、コメントを残した状態。承認前の中間状態。

### approved

公開可能と判断された状態。

### publishing

SharePoint 投稿処理中。

### published

SharePoint に投稿済み。

### rejected

公開しないと判断された状態。

### regeneration_requested

再生成が必要な状態。

### failed

生成、検証、投稿のいずれかに失敗した状態。

## Review Checklist

reviewer は最低限次を確認します。

- 出典が存在する
- 出典リンクが正しい
- 対象製品・対象サービスが正しい
- 社内利用者に必要な対応が明確
- 管理者向け対応が実行可能
- 緊急度が妥当
- 攻撃手順や PoC 詳細が含まれていない
- 不確実な点が断定されていない
- SharePoint 掲載に適した表現である

## Approval Rule

approval 条件:

- validation error がない
- dangerous detail warning がない
- unsupported claim warning が reviewer によって解消または許容されている
- required_actions が明確
- references がある

## Regeneration Rule

再生成する条件:

- 文体が不適切
- 情報が不足
- 一般利用者向け説明が難しすぎる
- 管理者向け対応が曖昧
- 出典にない断定が含まれる
- 危険な詳細が含まれる

再生成時は、previous draft と reviewer comment を保存します。

## Audit Requirements

記録する項目:

- draft_id
- reviewer
- action
- comment
- previous_status
- next_status
- validation_warnings
- timestamp

## Related Issues

- #19 Implement review and approval workflow
- #8 Implement draft composition template for SharePoint announcements
- #18 Add AI output validation and source-grounding checks
- #20 Implement SharePoint publish idempotency and state tracking
