# Decision Records

このディレクトリには、設計判断や運用判断の記録を置きます。

## 目的

後から見たときに、なぜその設計・運用・制約を選んだのかを追跡できるようにします。

## 記録する判断

次のような判断は、Issue / PR だけでなく decision record として残すことを推奨します。

- アーキテクチャ選定
- 外部サービス選定
- 認証・認可方式
- API 利用方式
- データ保持方針
- 監査ログ方針
- 投稿失敗時の再試行・ロールバック方針
- セキュリティ上の重要判断
- 将来の互換性に影響する判断

## ファイル命名

推奨形式:

```text
YYYY-MM-DD-short-title.md
```

例:

```text
2026-06-22-github-driven-workflow.md
```

## 推奨テンプレート

```markdown
# <Decision Title>

## Status

Proposed / Accepted / Deprecated / Superseded

## Context

## Decision

## Consequences

## Related

- Issue:
- PR:
- Spec:
```
