# OpenSpec Workflow

## 目的

この文書は、GitHub Issue を OpenSpec change に落とし込み、Claude Code / Codex が実装するための標準手順を定義します。

## 基本モデル

```text
GitHub Milestone
  └─ GitHub Issue
       └─ OpenSpec change
            └─ implementation branch
                 └─ Pull Request
```

GitHub の Milestone / Issue / Spec が正本です。OpenSpec change は、それらを実装可能な変更単位に整理するための作業成果です。

## 1. Milestone の確認

実装エージェントは、作業開始前に対象 Milestone を確認します。

確認項目:

- Milestone の目的
- 含まれる Issue
- 完了条件
- 非対象範囲
- 優先順位
- 保留事項

## 2. Issue の確認

Issue では次を確認します。

- 背景
- 目的
- 対象範囲
- 非対象範囲
- 受け入れ条件
- 関連 Spec
- セキュリティ・運用上の注意点
- 検証方法

必要な情報が欠落している場合、OpenSpec change 作成前に Issue の更新を求めます。

## 3. OpenSpec change の作成

推奨 change ID:

```text
issue-<issue-number>-<short-kebab-title>
```

例:

```text
issue-12-add-post-scheduler
issue-18-fix-duplicate-post-prevention
```

change には次を含めます。

- 対応 Issue
- 背景
- 変更目的
- 仕様差分
- 非対象範囲
- 影響範囲
- 移行・互換性
- セキュリティ影響
- 検証方法

## 4. 実装

実装は change に基づいて行います。

原則:

- Issue の範囲を超えない。
- Spec と矛盾しない。
- 仕様追加が必要な場合は、先に Issue / Spec / OpenSpec change を更新する。
- テスト可能な形で実装する。
- 外部 API 連携は失敗、再試行、レート制限、重複防止を考慮する。

## 5. 検証

Pull Request 前に、最低限次を確認します。

- OpenSpec change と実装の整合
- Issue の受け入れ条件
- テスト結果
- lint / format / type check
- 秘密情報の混入有無
- ログへの機微情報出力有無
- 自動投稿処理の冪等性、重複防止、失敗時動作

## 6. Pull Request

PR には次を記載します。

```text
## 対応
- Issue:
- Milestone:
- OpenSpec change:

## 変更概要

## 検証結果

## 仕様差分

## セキュリティ・運用上の注意点
```

## 7. 完了条件

Issue は次を満たして完了とします。

- 受け入れ条件を満たしている。
- 対応する OpenSpec change が更新済み。
- 必要な Spec が更新済み。
- テスト・検証結果が PR に記録されている。
- セキュリティ・運用上の懸念が解消または明示されている。
- PR がマージされている。マルチエージェント運用では、CI グリーンかつ carve-out 非該当であれば auto-merge してよい。carve-out（仕様不足・認証/認可/Secret/投稿・Spec 差分・CI 未整備など）に該当する場合は人間がレビュー・マージする。詳細は `docs/runbooks/multi-agent-orchestration.md`「自律度と人間ゲート」。
