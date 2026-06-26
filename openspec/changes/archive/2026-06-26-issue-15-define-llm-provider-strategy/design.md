## Context

SPAutoPost は複数の生成 AI provider を将来的に利用する。現時点では `docs/specs/llm-provider.md` に provider 分類・interface・禁止事項の概要は記載されているが、各 provider の利用条件・入力制限・監査項目が SHALL / MUST 形式でなく、シナリオも不足している。M3 の production provider 実装（#16 / #17）はこの Spec を契約として参照するため、Spec を今 確定する必要がある。

本 change は実装変更を伴わず、`docs/specs/llm-provider.md` のドキュメント更新のみを対象とする。

## Goals / Non-Goals

**Goals:**
- provider 分類ごとの利用条件を SHALL / MUST 形式で明文化する
- ChatGPT / Claude subscription を自動化前提にしない方針を明記する
- provider へ渡してよい情報と禁止情報を許可リスト / 禁止リストとして定義する
- prompt / output の保存方針を明文化する
- provider 切替方針を明文化する
- provider ごとの監査項目を定義する（必須 / 禁止の両方）
- `security-baseline.md` の LLM 入力制限セクションと整合させる

**Non-Goals:**
- production_api / generic_api / production_flow の実装（#16 / #17 / M3 以降）
- UI 自動操作の実装
- 契約・費用の確定
- provider 間の cost 比較・選定

## Decisions

### 決定 1: Spec は `docs/specs/llm-provider.md` を主体とし、openspec delta spec から apply する

既存 `docs/specs/llm-provider.md` に必要項目を追加する形を取る。新規ファイルは作成しない。これにより、#16 / #17 が参照する Spec ファイルパスが変わらない。

**代替案**: `docs/specs/llm-provider-strategy.md` として分離 → 参照 URL の変更が生じ、既存 Issue / ADR のリンクが無効になるため棄却。

### 決定 2: provider へ渡す情報を許可リスト方式で定義する

禁止リストのみ列挙する方式より、許可リスト + 禁止リストの両方を明示する方が実装時の判断に迷いが生じない。また、security-baseline.md の「LLM 入力制限」セクションと同一の分類方針を使用し、2 つのドキュメント間の矛盾を防ぐ。

### 決定 3: prompt 原文を保存しない

prompt のテキストそのものを保存すると、禁止情報（社内構成・未公開インシデント等）が意図せず混入するリスクがある。代わりに `generation_input_hash`（SHA-256）を記録することで、入力の追跡可能性と最小化を両立する。

### 決定 4: 本番環境での test provider 使用を設定バリデーションでブロックする

実行環境（`APP_ENV`）と `provider_type` の組み合わせをバリデーションで検証する。`production` 環境で `test_mock` / `test_manual` を設定した場合は起動時エラーとする。これにより、環境間の誤設定による本番 mock 動作を防ぐ。

## Risks / Trade-offs

- **リスク: security-baseline.md との重複記述** → 入力制限の正本は `llm-provider.md` とし、`security-baseline.md` の LLM 入力制限セクションは `llm-provider.md` へのリファレンスに置き換える（または内容を同期する）。apply 時に確認する。
- **リスク: M3 前提条件が陳腐化する** → preconditions チェックリストは Issue #16 / #17 ごとに記録・承認されるため、本 Spec の更新は不要。本 Spec が変わらない限りリスクは低い。
- **トレードオフ: SHA-256 ハッシュのみでは原文追跡不可** → デバッグ時に入力原文が必要な場合は手動再現が必要。許容できる（セキュリティ優先）。

## Open Questions

なし（carve-out 判断: security-baseline との整合は apply 前に確認済みとし、矛盾が生じた場合のみ coordinator に escalation する）。
