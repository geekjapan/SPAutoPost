# Security Baseline Specification

## Status

Approved

## Purpose

この Spec は、SPAutoPost の Secret 管理、権限最小化、LLM 入力制限、ログ禁止事項、投稿安全性、実装エージェント向け安全要件を定義します。

## Security Principles

- 最小権限
- Secret 非コミット
- ログへの機微情報出力禁止
- 投稿先固定
- 人間レビュー前提
- 出典に基づく原稿生成
- 冪等性による重複投稿防止
- 攻撃手順・PoC 詳細の生成抑制

## Secrets

保存禁止:

- API key
- access token
- refresh token
- client secret
- certificate private key
- cookie
- authorization header

許容される参照方式:

- environment variable
- GitHub Actions secrets
- Azure Key Vault 等の secret store
- managed identity

禁止:

- `.env` のコミット
- config file への Secret 直書き
- test fixture への実 Secret 混入
- log / exception message への Secret 出力

## Microsoft Graph Permissions

方針:

- 投稿対象 SharePoint site / list / page に必要な権限だけを付与する。
- 広範な tenant 全体権限は避ける。
- delegated permission と application permission の採否を明示する。
- 本番用 app registration と開発用 app registration を分離する。
- permission は decision record と runbook に記録する。

## LLM Input Control

LLM provider に渡す入力は最小化します。

渡してよい情報:

- 公開された脆弱性情報
- CVE / JVN / vendor advisory の要約
- 参考 URL
- 一般化された社内向け文体指示
- 明示的に許可された製品名またはカテゴリ

原則渡さない情報:

- Secret
- 個人情報
- 社内ネットワーク構成
- 内部 IP / hostname
- 認証方式の詳細
- 未公開インシデント情報
- 攻撃者に有益な内部防御状況

## Output Safety

AI 出力は次を満たす必要があります。

- 出典にない事実を断定しない
- 攻撃手順や PoC を説明しない
- 対応方法中心にする
- 一般利用者向けと管理者向けを分ける
- 不確実な事項は不確実と示す
- 人間レビュー前に公開しない

## Auto-Publish Safety Policy

**初期対象外: 自動公開は MVP 範囲外とする。**

- LLM 出力を人間レビューなしに SharePoint へ自動公開してはならない。
- すべての DraftPost は approved ステータスになるまで publish できない。
- 自動公開（approved フロー不通過の publish）は将来的に個別 Issue で設計・承認を経てから追加する。

## Posting Safety

- SharePoint 投稿先は config で固定する。
- 任意 URL への投稿を禁止する。
- dry-run を提供する。
- approved でない DraftPost は publish できない。
- idempotency_key により重複投稿を防ぐ。
- failed retry は backoff と duplicate guard を通す。

## Dependency and Supply Chain

本番前に次を確認します。

- dependency scanning
- secret scanning
- lockfile review
- license review if required
- GitHub Actions permission review
- artifact / build output の Secret 混入確認

## Implementation Agent Rules

実装エージェントは次をしてはいけません。

- Issue にない仕様を追加する
- 投稿先を任意 URL にする
- Secret を repo に保存する
- LLM 出力を自動公開する
- 非公式 UI scraping による ChatGPT / Claude 自動操作を実装する
- rate limit 回避や規約回避を意図した実装を行う

## Required Checks Before Production

- Secret 混入チェック
- Graph permission review
- LLM provider data handling review
- SharePoint test posting
- dry-run verification
- duplicate posting test
- audit log review
- rollback / correction procedure

## Related Issues

- #5 Define security, secrets, audit, and compliance baseline
- #10 Implement dry-run preview and minimal audit log
- #15 Define LLM provider strategy and production/test separation
- #22 Production hardening runbook, observability, and security review
