## Why

SPAutoPost の投稿先である SharePoint お知らせ掲示板の実体（Site Page / News article）と必要な Graph 権限、下書き/公開の扱いが Spec として未確定であり、M1 実装着手前に契約として固定する必要がある。

## What Changes

- `docs/specs/sharepoint-publishing.md` の Open Questions を解消し、M1 受け入れ条件を満たす完全な Spec に更新する
- Graph 権限セット（最小権限）を明示的に列挙する
- 下書き/公開/更新/失敗時動作のライフサイクルを確定する
- News promote（`PromoteNewsArticle` 相当）を M1 スコープに含めるか否かを決定し記録する
- 投稿先設定項目（`sharepoint.*`）の完全な定義を確定する

## Capabilities

### New Capabilities

- `sharepoint-publishing`: SharePoint Site Page / News article への投稿契約（Graph 権限・ライフサイクル・設定・冪等性・エラー処理）を定義する Spec

### Modified Capabilities

（既存の `openspec/specs/` に該当スペックなし）

## Impact

- `docs/specs/sharepoint-publishing.md`：Open Questions 解消、権限・ライフサイクル完全定義
- Issue #2 受け入れ条件（5 項目）をすべて満たすことが目標
- 実装コードへの影響なし（M1 実装 Issue #9 / #20 が後続）
