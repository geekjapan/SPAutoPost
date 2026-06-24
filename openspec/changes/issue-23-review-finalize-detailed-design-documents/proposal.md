## Why

Issue #23 は、詳細設計文書セットを M0 で実装エージェントが参照できる状態に整理するための docs-only review である。現状は各文書に Status と Related Issues があるが、M0 で Accepted / near-Accepted と見なす文書、M1 以降へ deferred とする文書、未決事項の集約先が 1 か所で追跡できない。

この change は、対象文書セットの review status を中央 matrix にまとめ、SharePoint 投稿方式の未決事項を #2、LLM provider 戦略の未決事項を #15 へ明示的に route する。

## What Changes

- Issue #23 対象文書の central status / review matrix を `docs/design-documents.md` に追加する。
- M0 Accepted / near-Accepted と、M1 以降で確定する deferred 文書を分類する。
- SharePoint publishing / board contract の未決事項は #2 に集約し、この change では決めないことを明示する。
- LLM provider strategy の未決事項は #15 に集約し、この change では決めないことを明示する。
- 実装が先行しているが既存 Issue で追跡できる spec gap を matrix から参照する。
- **非対象**: runtime code、migration、auth、Secret、external service、Azure resource、SharePoint publish behavior の変更。

## Capabilities

### New Capabilities

- `design-document-review`: Issue #23 対象文書の M0 review result、deferred milestone、未決事項 routing、implementation-before-spec gap links を中央 matrix として管理する。

### Modified Capabilities

<!-- 既存 OpenSpec capability の requirement は変更しない。 -->

## Impact

- **ドキュメント**: `docs/design-documents.md` に M0 review matrix と follow-up routing を追加する。
- **OpenSpec**: `design-document-review` capability を追加する。
- **コード / DB / runtime**: 変更なし。
- **依存関係**: 追加なし。
- **セキュリティ**: Secret、認証情報、実 SharePoint target、provider credential、Azure resource は扱わない。
