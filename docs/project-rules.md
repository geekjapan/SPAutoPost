# SPAutoPost Project Rules

## 1. 基本方針

SPAutoPost は GitHub 駆動方式で管理します。

このリポジトリでは、ユーザーが GitHub に記載した Spec / Milestone / Issue を正本とします。Claude Code / Codex などの実装エージェントは、それらを参照し、Issue を OpenSpec change に落とし込んでから実装します。

## 2. 正本の定義

正本とは、実装・レビュー・判断の根拠として扱う情報です。

正本に含まれるもの:

- GitHub Issue
- GitHub Milestone
- このリポジトリ内の Spec
- このリポジトリ内の project rules
- 承認済み Pull Request
- OpenSpec change。ただし上位の Spec / Issue と矛盾しない範囲

正本に含まれないもの:

- チャット上だけの会話
- AI が生成した未反映の提案
- ローカル環境だけに存在するメモ
- Issue に紐づかない実装エージェントの独自判断

## 3. Milestone の役割

Milestone は作業フェーズまたはリリース単位を表します。

Milestone には、可能な限り次を記載します。

- 目的
- 対象範囲
- 非対象範囲
- 完了条件
- 含める Issue
- 主要なリスクまたは保留事項

実装エージェントは、Milestone の目的から外れる Issue を勝手に追加・変更しません。

## 4. Issue の役割

Issue は OpenSpec change および実装作業の基本単位です。

Issue には、可能な限り次を記載します。

- 背景
- 目的
- 対象範囲
- 非対象範囲
- 受け入れ条件
- 関連 Spec
- 関連 OpenSpec change
- 検証方法
- セキュリティ・運用上の注意点

Issue の範囲が曖昧な場合、実装エージェントは推測で実装を進めず、Issue の明確化を要求します。

## 5. Spec の役割

Spec は、機能・運用・制約・品質要件などを定義する文書です。

Spec は `docs/specs/` 配下に置くことを標準とします。OpenSpec の仕様管理ファイルが導入された場合は、OpenSpec 側の構成に合わせて配置して構いません。ただし GitHub repo 内に存在することを必須とします。

Spec には、少なくとも次を含めることを推奨します。

- 対象機能または対象領域
- ユースケース
- 入力・出力
- 状態遷移
- エラー時動作
- 権限・認証・認可
- データ保持
- 監査ログ
- 外部サービス連携
- 非機能要件
- セキュリティ要件

## 6. OpenSpec change の扱い

OpenSpec change は、Issue を実装可能な変更単位に分解したものです。

原則:

- 1 Issue = 1 OpenSpec change
- change ID は Issue 番号を含める
- change の内容は Issue と矛盾させない
- 実装前に change の意図、影響範囲、検証方法を明確にする
- 仕様変更が発生した場合は、実装だけでなく Spec / OpenSpec も更新する

## 7. Pull Request の扱い

Pull Request は、Issue に対する実装成果として作成します。

PR には次を明記します。

- 対応 Issue
- 対応 Milestone
- 対応 OpenSpec change
- 実装内容
- 検証結果
- 仕様差分
- セキュリティ・運用上の注意点

PR は Issue の完了条件を満たして初めて完了とします。

マルチエージェント運用での PR の進め方（auto-merge ゲートと人間エスカレーション条件）は `docs/runbooks/multi-agent-orchestration.md`「自律度と人間ゲート」に従います。

## 8. 変更管理

仕様変更、スコープ変更、設計判断の変更は、GitHub 上に記録します。

軽微な実装判断を除き、次の変更は Issue または Spec に反映してください。

- 機能追加
- API 仕様変更
- データモデル変更
- 認証・認可の変更
- 外部サービス連携方式の変更
- 保存データ・ログ項目の変更
- 投稿動作、再試行、重複防止、失敗時動作の変更
- セキュリティ・プライバシーに影響する変更

## 9. セキュリティ・コンプライアンス方針

SPAutoPost は名称上、自動投稿や外部サービス連携を含む可能性があります。そのため、次を基本方針とします。

- 明示的に許可されたアカウント、投稿先、API のみを扱う。
- spam、なりすまし、無断投稿、規約回避、レート制限回避に転用される実装を避ける。
- 秘密情報は GitHub にコミットしない。
- ログに秘密情報や不要な個人情報を出力しない。
- 投稿処理は冪等性を考慮し、重複投稿を防ぐ。
- 外部 API のレート制限、利用規約、失敗時挙動を Spec または Issue に明記する。
- 監査可能性を確保するため、投稿要求・結果・エラーは必要最小限で記録する。

## 10. AI 実装エージェントの責務

Claude Code / Codex は、実装者として次を守ります。

- GitHub 上の正本を読む。
- Issue の範囲内で作業する。
- OpenSpec change を作成・更新する。
- 実装とテストを行う。
- PR に検証結果を記載する。
- 不明点を推測で埋めず、Issue 更新を要求する。

AI 実装エージェントは、仕様決定者ではありません。仕様の追加・変更は GitHub 上の正本に反映されたものだけを有効とします。

複数エージェントを Orca worktree で並列運用する場合は、`AGENTS.md`「自律マルチエージェント運用」と `docs/runbooks/multi-agent-orchestration.md` に従い、agmsg（team=spautopost）で協調し、auto-merge の carve-out（仕様不足・認証/認可/Secret/投稿・Spec 差分・CI 未整備など）では人間ゲートを通します。
