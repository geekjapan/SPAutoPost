## Why

Issue #12 (Milestone M2) では、日本語の脆弱性対策情報を SPAutoPost の `Advisory` model に取り込むため、MyJVN / JVN iPedia adapter が必要である。既存の NVD adapter は英語 CVE 情報を扱えるが、社内掲示板向けには日本語 title / summary / mitigation と JVN ID の保持が必要になる。

## What Changes

- `spautopost.myjvn_adapter` を追加し、`getVulnOverviewList` 相当の概要取得と `getVulnDetailInfo` 相当の詳細取得を実装する。
- transport 注入により test では live MyJVN API を呼ばず、default transport は stdlib `urllib` のみを使う。
- MyJVN XML から JVN ID / CVE ID / 日本語 title / summary / mitigation / CVSS / affected product hint / references / published / updated を `Advisory` に正規化する。
- `SourceRecord.source_type = "myjvn"`、per-JVN `source_url`、`retrieved_at`、`raw_hash`、`parser_version` を保持する。
- MyJVN API の利用規約と出典表示要請を `docs/specs/source-collection.md` に明記する。
- unit / fixture tests を追加し、外部通信なしで概要・詳細・error handling を検証する。
- **Non-goals**: OVAL / XCCDF / VRDA 取り込み、全 MyJVN API 実装、scheduler / CLI wiring。

## Capabilities

### New Capabilities

- `myjvn-source-adapter`: MyJVN HND XML adapter with injectable transport and Advisory normalization.

### Modified Capabilities

- `source-collection`: MyJVN adapter の取得範囲、正規化項目、利用規約・出典表示要件を明確化する。

## Impact

- **Code**: `src/spautopost/myjvn_adapter.py` を追加する。
- **Tests**: `tests/spautopost/test_myjvn_adapter.py` を追加する。live network は使わない。
- **Docs**: `docs/specs/source-collection.md` の MyJVN 節を更新する。
- **Runtime / DB**: storage schema 変更なし。
- **Security**: MyJVN は認証不要。secret / credential を扱わない。
