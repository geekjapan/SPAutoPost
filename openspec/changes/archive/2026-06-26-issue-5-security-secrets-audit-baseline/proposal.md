## Why

SPAutoPost は社内掲示板投稿・生成 AI・外部情報源・Microsoft Graph を扱うため、Secret 漏洩・権限過剰・AI 入出力の安全性・投稿事故のリスクが初期段階から存在する。M0 フェーズで安全性と監査性の前提を Spec として確定し、以降の実装エージェントが安全な実装を行えるようにする。

## What Changes

- `docs/specs/security-baseline.md` を更新し、Secret 管理・Graph 権限最小化・LLM 入力制限・投稿安全性・エージェント向けルールを Approved 状態の Spec として確定する。
- `docs/specs/audit-log.md` を更新し、監査ログの必須項目・イベント種別・禁止事項・保持方針を Approved 状態の Spec として確定する。
- OpenSpec に `security-baseline` capability spec を追加し、受け入れ条件を形式化する。
- OpenSpec に `audit-log-baseline` capability spec を追加し、監査ログ要件を形式化する。

## Capabilities

### New Capabilities

- `security-baseline`: Secret 管理禁止事項・Graph 権限最小化・LLM 入力制限・出力安全性・投稿安全性・エージェントルールを定義する capability。
- `audit-log-baseline`: 監査ログの必須項目・イベント種別・ログ禁止事項・Prompt/Output 保存方針・失敗監査・保持方針を定義する capability。

### Modified Capabilities

（なし。既存 capability の要件変更は発生しない。）

## Impact

- `docs/specs/security-baseline.md`: Status を Approved に更新し、受け入れ条件に対応するセクション追加・補完。
- `docs/specs/audit-log.md`: Status を Approved に更新し、受け入れ条件に対応するセクション追加・補完。
- `openspec/specs/security-baseline/spec.md`: 新規作成。
- `openspec/specs/audit-log-baseline/spec.md`: 新規作成。
- 実装コード: なし（M0 は Spec 確定フェーズ。実装は M1 以降）。
- CI: なし（既存 lint/type check に影響なし）。
