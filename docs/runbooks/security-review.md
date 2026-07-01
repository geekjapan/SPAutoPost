# Security Review Runbook

## Status

Draft

## Purpose

この runbook は、SPAutoPost を本番運用に近づける前に確認すべきセキュリティレビュー項目を定義します。

## Review Scope

対象:

- Secret 管理
- Microsoft Graph 権限
- SharePoint 投稿先
- LLM provider 入力制限
- AI 出力検査
- 監査ログ
- dependency / supply chain
- GitHub Actions
- 運用手順

## Checklist

Issue #22 / M6 の本番前レビューでは、`docs/runbooks/production-hardening.md` の production security review checklist も併用します。

### Repository

- [ ] Secret が commit されていない
- [ ] `.env` が gitignore されている
- [ ] sample config に実値が含まれていない
- [ ] dependency lockfile が確認されている
- [ ] 不要な生成物が commit されていない
- [ ] generated artifact / CI log / audit log に Secret が出ていない

### Configuration

- [ ] production config で dry-run / publish 設定が明示されている
- [ ] allow_publish は意図的に有効化されている
- [ ] SharePoint target は固定されている
- [ ] provider は本番用とテスト用が分離されている
- [ ] test_manual provider は本番無効

### Microsoft Graph

- [ ] 権限が最小化されている
- [ ] 投稿対象 site/list/page が限定されている
- [ ] application / delegated permission の選定理由が記録されている
- [ ] 本番 app と開発 app が分離されている
- [ ] credential rotation 方針がある
- [ ] rate limit / timeout / authorization failure の扱いが runbook に記録されている

### LLM Provider

- [ ] 業務データ投入可否が確認されている
- [ ] provider へ渡す入力が最小化されている
- [ ] Secret / 個人情報 / 内部構成情報を渡していない
- [ ] prompt version が記録される
- [ ] output validation が有効
- [ ] ChatGPT / Claude subscription の UI 自動操作を実装していない
- [ ] provider terms / data retention / region / SLA / rate limit を確認している

### Publishing Safety

- [ ] approved でない draft は publish できない
- [ ] dry-run が動作する
- [ ] idempotency_key がある
- [ ] retry で重複投稿しない
- [ ] 誤投稿時の修正・削除手順がある

### Audit Log

- [ ] source / provider / prompt / review / publication が追跡できる
- [ ] correlation_id がある
- [ ] Secret がログに出ていない
- [ ] error_code が記録される
- [ ] retryable / failure_count / target が失敗イベントから確認できる
- [ ] 監査ログの保存先と保持方針がある、または未決事項として Issue 化されている

### CI/CD

- [ ] secret scanning が有効
- [ ] dependency scanning が有効または代替手段がある
- [ ] GitHub Actions の permissions が最小化されている
- [ ] PR template の security checklist が使われている

## Review Output

レビュー結果は Issue または decision record に記録します。

推奨項目:

- review date
- reviewer
- scope
- findings
- risk level
- remediation issue
- accepted risk

## Related Issues

- #5 Define security, secrets, audit, and compliance baseline
- #22 Production hardening runbook, observability, and security review

## Related Runbooks

- `docs/runbooks/production-hardening.md`
- `docs/runbooks/operation.md`
- `docs/runbooks/incident-response.md`
