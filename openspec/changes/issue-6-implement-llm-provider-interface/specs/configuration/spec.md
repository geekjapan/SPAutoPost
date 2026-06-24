## MODIFIED Requirements

### Requirement: provider / source / 投稿先の切替設定

システムは LLM provider、source adapter、SharePoint 投稿先、storage provider を config で切り替え可能にしなければならない（SHALL）。LLM provider type は `production_api` / `production_flow` / `generic_api` / `test_mock` / `test_manual` のいずれかとして表現できなければならない（SHALL）。

#### Scenario: provider を設定で選択

- **WHEN** config の `llm.provider` を `test_mock` に設定して起動する
- **THEN** 選択された provider type が検証され、未知の値の場合は validation error となる

#### Scenario: storage provider を設定で選択

- **WHEN** config の `storage.provider` を `postgresql` または `sqlite` に設定する
- **THEN** 選択値が検証され、対応する接続設定（database_url / sqlite_path）が要求される
