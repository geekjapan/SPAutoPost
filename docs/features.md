# Feature Decomposition

## 1. Source Collection

脆弱性情報、セキュリティアップデート、注意喚起を外部情報源から取得する機能です。

初期対象:

- 手動入力
- NVD
- MyJVN
- CISA KEV または KEV 相当情報
- ベンダーアドバイザリ/RSS

主要責務:

- 情報源別 adapter
- 差分取得
- 取得時刻の記録
- 取得失敗時の再試行
- 情報源 URL と取得メタデータの保持

将来方針:

- 本格 crawler / collector は別プログラムへ分離可能にする。
- SPAutoPost は normalized advisory を受け取れる import interface を持つ。

## 2. Normalization

情報源ごとの差を吸収し、共通データモデルに変換する機能です。

主要責務:

- CVE ID / JVN ID / vendor advisory ID の統合
- title / summary / severity / affected products / mitigation / references の正規化
- CVSS / KEV / exploit status / patch availability の保持
- 重複排除
- source confidence の記録

## 3. Relevance and Triage

社内掲示板に掲載すべきか、どの優先度で扱うかを判断する機能です。

主要責務:

- 深刻度評価
- 悪用確認済み情報の考慮
- 社内利用製品との関連度
- 投稿要否判定
- 一般ユーザー向け/管理者向けの分類
- 緊急度ラベル付け

初期段階では、社内資産台帳との完全照合は行わず、手動タグまたは製品キーワードで扱います。

## 4. Draft Composition

正規化済み情報を、社内 SharePoint 掲示板向け文章へ変換する機能です。

主要責務:

- 生成 AI provider 呼び出し
- prompt template 管理
- source-grounded drafting
- 日本語文体統一
- 一般利用者向け説明
- 管理者向け対応事項
- 注意喚起レベルの表現制御
- 出典リンクの保持

## 5. LLM Provider Abstraction

複数の生成 AI エンジンを差し替え可能にする抽象層です。

実稼働候補:

- Copilot Studio
- Microsoft Foundry / Azure OpenAI
- その他 LLM API

テスト候補:

- mock provider
- local fixture provider
- ChatGPT subscription を使った手動/半手動検証 provider
- Claude subscription を使った手動/半手動検証 provider

注意:

- サブスクリプション型チャット UI を自動操作する設計は、規約・監査・安定性の観点から実稼働対象にしない。
- API 利用可能な provider と、人間操作前提の test provider を分離する。

## 6. Review and Approval

AI が生成した掲示板原稿を確認・修正・承認する機能です。

主要責務:

- draft 状態管理
- reviewer コメント
- 再生成
- 承認
- 差し戻し
- 公開前チェック

初期段階では、完全自動公開ではなく人間レビューを必須にします。

## 7. SharePoint Publishing

承認済み原稿を SharePoint お知らせ掲示板へ投稿する機能です。

候補方式:

- SharePoint List item として投稿
- SharePoint Site Page として投稿

主要責務:

- Microsoft Graph 認証
- 投稿先 site / list / page の指定
- 下書き投稿
- 公開または公開要求
- 投稿結果の保存
- 重複投稿防止
- 失敗時再試行

## 8. Audit and Observability

監査、障害対応、運用確認のための記録機能です。

主要責務:

- 取得元情報
- AI provider
- prompt version
- 生成結果
- reviewer
- approval status
- SharePoint 投稿結果
- error log
- correlation ID

ログには、API キー、トークン、Cookie、認証ヘッダ、不要な個人情報を出力しません。

## 9. Configuration and Secrets

環境ごとの設定と秘密情報を管理する機能です。

主要責務:

- provider 設定
- SharePoint site/list/page 設定
- source adapter 設定
- feature flag
- secret 参照
- dry-run 設定

秘密情報はリポジトリに保存しません。

## 10. Scheduler and Automation

定期実行や差分収集を行う機能です。

主要責務:

- 手動実行
- dry-run
- schedule 実行
- 差分検出
- retry/backoff
- duplicate guard

初期段階では、cron 相当または手動 CLI で十分とし、本格ジョブ基盤は後続で検討します。
