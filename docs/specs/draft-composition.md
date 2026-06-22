# Draft Composition Specification

## Status

Proposed

## Purpose

この Spec は、脆弱性情報を社内 SharePoint お知らせ掲示板向けの日本語原稿へ変換する際の構成、文体、必須項目、禁止事項、出典表示、AI 出力検査を定義します。

## Target Audience

- general_users: 一般利用者向け
- administrators: 管理者・運用担当者向け
- mixed: 一般利用者向け本文と管理者向け補足を併記

MVP では mixed を標準とします。

## Draft Structure

必須セクション:

1. 件名
2. 概要
3. 影響
4. 対象
5. 利用者が行う対応
6. 管理者が行う対応
7. 対応期限または推奨対応時期
8. 参考情報

推奨セクション:

- 緊急度
- 悪用確認状況
- 回避策
- 更新履歴
- 問い合わせ先

## Title Rule

件名は短く、対象と対応要否が分かる形にします。

例:

```text
[重要] <製品名> の脆弱性対応について
[緊急] <製品名> の更新プログラム適用のお願い
[注意喚起] <サービス名> 利用時の確認事項について
```

禁止:

- 不必要に不安を煽る表現
- 出典にない被害断定
- 攻撃者名や攻撃手法を過度に強調する表現

## Urgency Labels

- emergency: 既に悪用確認済み、または即時対応が必要
- high: 重要度が高く、短期対応が必要
- normal: 通常の更新・確認を促す
- low: 参考情報または低優先度

## Writing Style

原則:

- 日本語
- 簡潔
- 一般利用者にも理解できる表現
- 管理者向けの技術詳細は別セクションに分離
- 断定は出典がある場合に限定
- 不確実な点は不確実と明示

避ける表現:

- 「必ず侵害されます」など根拠のない断定
- PoC、exploit 手順、攻撃コードの説明
- 詳細な悪用条件の列挙
- 対応不能な不安喚起

## Source Grounding

DraftPost は Advisory.references に基づいて作成します。

要件:

- 参考情報セクションに出典リンクを残す
- 出典にない URL を生成しない
- 影響製品、対応方法、緊急度は Advisory の項目を使う
- AI が補った推測は本文に混ぜず、review warning として扱う

## Prompt Template Requirements

prompt template には次を含めます。

- role: 社内セキュリティ担当者として、社内掲示板向け原稿を作成する
- input schema: Advisory / references / urgency / audience
- output schema: DraftOutput
- safety rule: 攻撃手順や PoC を説明しない
- grounding rule: 出典にない内容を断定しない
- review rule: 不明点は reviewer warning に出す

## Validation Rules

必須検査:

- title がある
- summary_for_users がある
- impact がある
- required_actions がある
- references がある
- unsupported claim warning がない、または reviewer に表示される
- dangerous detail warning がない

警告:

- 対象製品が不明
- 対応期限が不明
- patch_available が unknown
- exploit_status が unknown
- 出典が 1 件のみ

## Human Review Checklist

reviewer は次を確認します。

- 出典リンクが正しい
- 対象製品が社内利用製品と一致する
- 利用者向け対応が過不足ない
- 管理者向け対応が実行可能
- 緊急度が妥当
- 攻撃手順や危険な詳細が含まれていない
- SharePoint に掲載して問題ない表現である

## Related Issues

- #8 Implement draft composition template for SharePoint announcements
- #18 Add AI output validation and source-grounding checks
- #19 Implement review and approval workflow
