## 1. graph-authentication.md の更新

- [x] 1.1 `docs/specs/graph-authentication.md` に local PoC 認証方式（delegated permission / Device Code Flow）を明記する
- [x] 1.2 `docs/specs/graph-authentication.md` に Azure hosted runtime 認証方式（user-assigned managed identity 第一候補、app-only access fallback）を明記する
- [x] 1.3 `docs/specs/graph-authentication.md` に managed identity 採否の決定（user-assigned 採用、system-assigned 不採用）を明記する
- [x] 1.4 `docs/specs/graph-authentication.md` に delegated permission を本番定期実行に使わないことを明記する
- [x] 1.5 `docs/specs/graph-authentication.md` に必要最小 Graph permission の一覧（`Sites.Selected` 優先）を明記する
- [x] 1.6 `docs/specs/graph-authentication.md` に SharePoint 対象 site を config で限定する方針を明記する

## 2. 整合性確認

- [x] 2.1 `docs/specs/security-baseline.md` の Graph permission 方針が更新した `graph-authentication.md` と矛盾しないことを確認する（必要なら更新する）
- [x] 2.2 Issue #27 の受け入れ条件（6 項目）がすべて `docs/specs/graph-authentication.md` に反映されていることを確認する
