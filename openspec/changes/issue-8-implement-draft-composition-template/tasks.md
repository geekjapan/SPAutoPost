## 1. Template

- [x] 1.1 SharePoint announcements 向け prompt / article template 定数を追加する
- [x] 1.2 Advisory / DraftInput から DraftOutput を生成する composition function を追加する

## 2. Provider integration

- [x] 2.1 `MockLLMProvider` の fallback draft を composition template 経由にする
- [x] 2.2 prompt version、references、user/admin sections、guardrail hints を DraftOutput に残す

## 3. Verification

- [x] 3.1 composition template の unit test を追加する
- [x] 3.2 `pytest`、`ruff check`、`mypy`、`openspec validate issue-8-implement-draft-composition-template --strict` を通す
