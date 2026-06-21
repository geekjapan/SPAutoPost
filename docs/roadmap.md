# SPAutoPost Roadmap

## ロードマップ方針

SPAutoPost は、社内 SharePoint 掲示板へのセキュリティ情報掲載を段階的に自動化します。

初期段階では、脆弱性情報の収集、整理、生成 AI による掲示板原稿作成、SharePoint への下書き投稿までを一体で実装します。将来的には、クローラーや情報整理機能を別プログラムへ分離し、SPAutoPost は「正規化済みセキュリティ情報を社内掲示板へ安全に掲載する投稿基盤」に責務を絞ります。

## 推奨 Milestone

この環境では GitHub Milestone を直接作成できないため、以下を GitHub Milestone 名として作成することを推奨します。

### M0: Project Foundation

目的:

- プロジェクトの目的、責務、運用ルール、基本設計を確定する。
- GitHub Issue / OpenSpec change 駆動で実装できる状態にする。

完了条件:

- Product Brief がある。
- 初期アーキテクチャ Spec がある。
- Issue テンプレート、PR テンプレート、AGENTS.md がある。
- 主要な初期 Issue が作成されている。

### M1: MVP Manual-to-SharePoint Draft

目的:

- 手動入力またはサンプル脆弱性情報から、生成 AI を用いて掲示板向け原稿を作成し、SharePoint に下書きまたはテスト投稿できる状態にする。

対象:

- 手動入力
- LLM provider 抽象化
- mock provider
- 最小の SharePoint connector
- 下書き投稿またはテスト投稿
- 最小監査ログ

非対象:

- 完全自動公開
- 本格クローラー
- 複雑な社内資産照合

### M2: Vulnerability Collection and Normalization

目的:

- 脆弱性情報を複数情報源から収集し、共通データモデルに正規化する。

対象:

- NVD adapter
- MyJVN adapter
- CISA KEV または KEV 相当情報の取り込み口
- ベンダーアドバイザリ/RSS adapter interface
- 重複排除
- 深刻度・悪用状況・社内関係度による優先度付け

非対象:

- すべてのベンダー情報源の網羅
- 社内資産台帳との完全連携

### M3: AI Drafting and Provider Strategy

目的:

- Copilot Studio、Microsoft Foundry / Azure OpenAI、その他 LLM API、テスト用 ChatGPT/Claude サブスクリプションを、用途別に扱える provider abstraction を整備する。

対象:

- provider interface
- production provider
- test provider
- prompt template
- source-grounded drafting
- 出典保持
- AI 出力検証
- 禁止表現・過剰断定の抑制

非対象:

- 規約上不明確なチャット UI の自動操作
- 出典なしの自動生成文の公開

### M4: Review, Approval, and Publishing Workflow

目的:

- 人間レビュー、承認、公開、差し戻し、再生成を扱える投稿ワークフローを実装する。

対象:

- draft / reviewed / approved / published / failed の状態管理
- SharePoint 投稿の冪等性
- 重複投稿防止
- 投稿結果の記録
- 投稿前チェックリスト

非対象:

- 完全自動承認
- 多段承認の複雑なワークフロー

### M5: Automation and External Collector Boundary

目的:

- スケジューラ、自動収集、外部 crawler / collector との責務境界を整える。

対象:

- 定期実行
- 差分収集
- 外部 collector からの normalized advisory import
- queue / file / API 境界
- 失敗時再試行

非対象:

- 外部 collector 本体の本格実装

### M6: Production Hardening

目的:

- 実稼働に必要なセキュリティ、監査、運用、観測性、障害対応を整備する。

対象:

- Secret 管理
- 権限最小化
- 監査ログ
- エラーハンドリング
- rate limit 対応
- リトライ/バックオフ
- テレメトリ
- runbook
- セキュリティレビュー

## 初期リリースの推奨順序

1. M0 で仕様と運用の土台を固定する。
2. M1 で手動入力から SharePoint 下書きまでの縦串を作る。
3. M2 で脆弱性収集を追加する。
4. M3 で AI provider と原稿品質を強化する。
5. M4 でレビュー/承認/公開ワークフローを整える。
6. M5 で自動化と外部 collector 分離に備える。
7. M6 で本番運用に耐える形にする。

## 重要な設計判断

- SharePoint 投稿方式は、List item と Site Page のどちらを使うかを初期 Issue で確定する。
- 実稼働では、API と監査性を持つ provider を優先する。
- ChatGPT / Claude のサブスクリプションは、テスト用途として扱う場合でも、規約、自動化可否、業務データ投入可否を明示的に確認する。
- 生成 AI の出力は、出典情報と構造化入力に基づく source-grounded drafting を基本とする。
- 初期段階では人間レビューを必須とし、完全自動公開は将来検討とする。
