## 1. OpenSpec change

- [x] 1.1 `design-document-review` capability の proposal / design / spec を作成する
- [x] 1.2 `openspec validate issue-23-review-finalize-detailed-design-documents --strict` を docs 編集前に通す

## 2. Docs review matrix

- [x] 2.1 Issue #23 対象文書セットを `docs/design-documents.md` の central matrix に整理する
- [x] 2.2 M0 Accepted / near-Accepted 文書と M1+ deferred 文書を分類する
- [x] 2.3 SharePoint 未決事項を #2、LLM provider strategy 未決事項を #15 に route する
- [x] 2.4 implementation-before-spec gap を既存 Issue にだけ紐づける

## 3. Verification and PR

- [x] 3.1 `openspec validate issue-23-review-finalize-detailed-design-documents --strict` を通す
- [x] 3.2 `openspec validate --changes --strict` を通す
- [x] 3.3 `git diff --check` を通す
- [ ] 3.4 Conventional commit を作成し、branch を push する
- [ ] 3.5 PR を作成する
