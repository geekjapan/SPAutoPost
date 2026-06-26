## Context

SPAutoPost は Secret・Microsoft Graph 権限・LLM 入出力・SharePoint 投稿を扱う。現在 `docs/specs/security-baseline.md` と `docs/specs/audit-log.md` が "Proposed" 状態で存在するが、OpenSpec の capability として形式化されておらず、受け入れ条件も未充足。M0 フェーズの完了には Spec を Approved 状態に引き上げ、実装エージェントが参照できる authority source を確立する必要がある。

## Goals / Non-Goals

**Goals:**
- `security-baseline` capability spec を OpenSpec に追加し、受け入れ条件を満たすセクションを定義する。
- `audit-log-baseline` capability spec を OpenSpec に追加し、監査ログ要件を形式化する。
- `docs/specs/security-baseline.md` と `docs/specs/audit-log.md` のステータスを Approved に更新する。
- 受け入れ条件（Secret 禁止事項・AI 入出力制限・監査ログ最小項目・自動公開抑制）をすべて充足する。

**Non-Goals:**
- 本番 Secret の登録・ローテーション。
- SIEM 連携・組織規程の策定。
- 実装コードの作成（M1 以降）。
- 監査ログ保持期間の本番値確定（本番投入前に別途確定）。

## Decisions

### D1: OpenSpec delta format で capability spec を新規追加する

`openspec/specs/security-baseline/spec.md` と `openspec/specs/audit-log-baseline/spec.md` を新規作成し、`## ADDED Requirements` ヘッダと `#### Scenario:` ブロックで要件を表現する。

**理由:** OpenSpec validate が delta 形式を要求する。既存の docs/specs/*.md は prose 形式であり、OpenSpec の検証対象外。分離することで prose spec（可読性）と formal spec（検証可能性）の両方を維持できる。

### D2: docs/specs/ の既存ファイルは Approved に昇格させるのみで、内容は最小変更にとどめる

docs/specs/security-baseline.md および audit-log.md の Status を Proposed → Approved に変更し、受け入れ条件に不足するセクションを補完する。大規模な書き換えはしない。

**理由:** 既存 Spec は内容として完成に近い。Status 更新と不足セクションの補完で受け入れ条件を充足できる。不要な差分を生まない。

### D3: 自動公開（auto-publish）を初期対象外とする安全方針を明記する

security-baseline capability spec に `approved でない DraftPost は publish できない` `LLM 出力を human review なしに自動公開しない` を ADDED Requirement として追加する。

**理由:** 受け入れ条件「自動公開を初期対象外とする安全方針が明記されている」を充足するため。

## Risks / Trade-offs

- [Risk] docs/specs/ の Status 更新が実際の実装と乖離する → Mitigation: Spec は実装の要件定義であり、実装前に Approved にすること自体が正しいフロー。実装後に要件が変わった場合は別 Issue で Spec を改訂する。
- [Risk] OpenSpec delta の Scenario ブロックが過剰に詳細になり保守コストが増す → Mitigation: Scenario は最小限（1〜2 件/要件）に留め、prose spec を正本とする。
