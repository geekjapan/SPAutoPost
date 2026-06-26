# Delta Spec: SharePoint Publishing — Publish Gate（追記分）

> 正本 `openspec/specs/sharepoint-publishing/spec.md` に追記する差分。
> 既存 Requirements はそのまま維持し、以下 Requirement を追加する。

## ADDED Requirements

### Requirement: approved 状態の DraftPost のみ publish ゲートを通過できる

SPAutoPost は `DraftPost.status` が `"approved"` でない場合、SharePoint への投稿処理（dry-run 含む）を開始してはならない（SHALL NOT）。ゲート違反は `PublishGateError` として送出し、失敗 Publication は記録しない。

#### Scenario: approved でない draft は publish 経路で即座に拒否される
- **WHEN** `status="generated"` の DraftPost で `publish_site_page()` が呼ばれる
- **THEN** `PublishGateError` が送出され、Publication / AuditEvent は記録されない

#### Scenario: approved draft は publish 経路を通過できる
- **WHEN** `status="approved"` の DraftPost で `publish_site_page()` が呼ばれる
- **THEN** ゲートは通過し、dry-run または live publish が続行する
