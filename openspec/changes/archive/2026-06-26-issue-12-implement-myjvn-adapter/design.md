## Context

Issue #12 は MyJVN / JVN iPedia から日本語の脆弱性対策情報を取得し、既存の `Advisory` DTO に正規化する adapter を追加する。既存の `NvdSourceAdapter` と `SourceAdapter` Protocol を踏襲し、新規依存は追加しない。

## Decisions

- HTTP transport は `urllib` ベースの関数を default とし、unit test では transport を差し替える。
- XML parser は stdlib `xml.etree.ElementTree` を使う。
- `fetch()` は `getVulnOverviewList` 相当として概要XMLを取得し、`SourceDocument` を返す。
- 詳細取得は `fetch_detail(jvn_ids)` で `getVulnDetailInfo` 相当を実行する。`SourceFetchQuery` に `jvn_id` が無いため、既存DTOを広げずに adapter 固有メソッドに留める。
- `Advisory` に mitigation 専用フィールドは無いため、詳細XMLの `Solution` は日本語 `summary` に `対策:` として含める。
- MyJVN API の利用規約・出典表示は code ではなく `docs/specs/source-collection.md` に運用ルールとして明記する。

## Risks

- MyJVN XML は namespace 付きで、概要と詳細の構造が異なる。テストfixtureで代表fieldだけを固定し、OVAL/XCCDF/VRDA は対象外にする。
- API側の利用条件や出典表示要請は将来変わる可能性がある。運用時は公式ページの確認を前提にする。

## Non-goals

- OVAL / XCCDF / VRDA の取り込み。
- 全 MyJVN API の wrapper 化。
- scheduled job / CLI への wiring。
