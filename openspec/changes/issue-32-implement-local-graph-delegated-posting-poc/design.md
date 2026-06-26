## Context

`docs/specs/graph-authentication.md`（Accepted）は local PoC で delegated permission を許容し、hosted 本番は user-assigned managed identity を第一候補とする方針を定義済み。`docs/specs/sharepoint-publishing.md`（Accepted）は投稿対象を SharePoint Site Page / News、既定 draft、承認後投稿、idempotency_key、`Publication` / `AuditEvent` 記録を定義済み。

既存コードには、Site Page payload と監査イベントの組み立て（`spautopost.dry_run`）、frozen-dataclass DTO（`Publication` / `AuditEvent` 等、`storage/models.py`）、`StoragePort`（`PublicationRepository.create_if_absent` / `AuditEventRepository.append`）、config ローダ（`graph` セクションは `local_poc_auth` / `hosted_auth` のみ許可）が揃っている。欠けているのは「実認証 → 実 Graph 投稿 → 結果の永続化」の縦串。本 change はこの Phase 4（#32）の最小経路を埋める。

制約: core ランタイム依存は `pyyaml` のみ。Secret は repo / config に保存しない。auth / publish は人間ゲートの carve-out 対象。CI は live Graph を叩けない。

## Goals / Non-Goals

**Goals:**

- delegated（device code）認証で Graph に接続し、SharePoint Site Page を実投稿できる最小経路。
- dry-run 既定で、`--no-dry-run` のときのみ実投稿。
- 投稿結果を `Publication`、投稿者を含む経過を `AuditEvent` として永続化。
- network 非依存で 80% 以上をテストできる構造（Protocol + fake 注入、純関数分離）。

**Non-Goals:**

- hosted 本番認証方式の決定・実装（#27 / managed identity / app-only）。
- News の promote 詳細、複数 site 投稿、添付・画像、page layout / web parts 設計。
- token cache の作り込み、live Graph を叩く自動テスト。

## Decisions

### 1. 認証ライブラリは MSAL を任意 extra として採用（device code flow）

OAuth2 device code flow（public client、secret 不要）を採用する。実装は Microsoft 公式の `msal` を使い、`pyproject.toml` の任意 extra `graph = ["msal>=1.28"]` に置く（既存 `postgres` extra と同じパターン）。core 依存は据え置き、`graph.auth` 内で遅延 import する。

- 代替案: stdlib `urllib` で device code を手書き（依存ゼロ、~40 行）。却下理由: 認証は人間ゲート carve-out かつ ECC/kernel が「auth は vetted library 優先・自前実装回避」を求める。token 取得・将来の refresh を公式実装に委ねる方が安全。
- MSAL の `acquire_token_by_device_flow` 応答の `id_token_claims`（`preferred_username` / `name`）から `Identity` を得る。`/me` への追加 Graph 呼び出しは不要。

### 2. Graph への HTTP は stdlib `urllib`、新規 HTTP 依存は足さない

Site Page 作成・publish の Graph 呼び出しは `urllib.request` で行う。`requests` / `httpx` は追加しない（ponytail: stdlib が HTTP を満たす）。リクエスト本文組み立て（payload → Graph リソース）と応答パース（JSON → page ID）は純関数に切り出し、I/O 行のみ薄く保つ。

### 3. Protocol 境界で network を注入差し替え可能にする

`GraphTokenProvider`（`acquire() -> AuthResult(access_token, identity)`）と `SharePointPagesClient`（`create_site_page` / `publish_site_page`）を Protocol 化。実装は `DelegatedDeviceCodeAuth` / `GraphSharePointPagesClient`。テストは fake を注入し、publisher のオーケストレーション（dry-run・成功・失敗・idempotency）を network 非依存で網羅する。実 adapter の network 行は `# pragma: no cover`、純関数は単体テストで担保。

### 4. publisher が idempotency と記録を一手に持つ

`graph.publisher.publish_site_page(draft, config, *, dry_run, token_provider, client, store, now, ids...)`:

1. `build_idempotency_key`（draft_id・site_id・page_library_id・advisory_ids・正規化 title の SHA-256）。`sharepoint-publishing.md` の推奨要素に準拠。
2. `get_by_idempotency_key`：既存が `published` / `publishing` なら新規作成せず返す。
3. dry-run: payload 組み立て → `dry_run` `Publication` + `publish_dry_run` `AuditEvent` を記録して返す（認証・Graph 呼び出しなし）。
4. live: `token_provider.acquire()` → `client.create_site_page()` →（任意 publish）→ `published` `Publication` + `publish_create` / `publish_result` `AuditEvent`。
5. 失敗: 例外を捕捉し `failed` `Publication` + `error` `AuditEvent`（`error_code` / `retryable`）を記録、例外は伝播させない。

idempotency_key 生成と record 組み立ては publisher 内に置く（1 機能のためにモジュールを増やさない）。`Publication` / `AuditEvent` は frozen DTO を新規生成（不変方針）。

### 5. config は `graph.client_id`（任意 `scopes`）を追加、`tenant_id` は再利用

`config.py` の `_SECTION_KEYS["graph"]` に `client_id` を追加（public client id は機密でないため平文 / env 参照どちらも可）。`tenant_id` は `sharepoint.tenant_id` を再利用し重複させない。scopes は `graph.publisher` のモジュール定数 `DEFAULT_GRAPH_SCOPES = ("Sites.ReadWrite.All",)` を既定とし、`graph.scopes` で上書き可能にする（マジック値回避 + 将来 `Sites.Selected` へ絞る upgrade path をコメントで明示）。

### 6. CLI `publish-draft <advisory_file>`

`preview-draft` と同じく manual advisory → MockLLMProvider で draft 生成。その後 `publish_site_page` を呼ぶ。dry-run は token/client 不要。live のみ `DelegatedDeviceCodeAuth` / `GraphSharePointPagesClient` を構築（msal 遅延 import）。出力は `redact_config` で `env:` / Secret を秘匿。`StoragePort` は `build_storage` で構築し migrate 後に記録。

## Risks / Trade-offs

- [MSAL 依存追加] → 任意 extra に隔離。core / CI は不要。実 auth は運用者環境でのみ動作。
- [実 adapter が CI で未実行] → network 行を no-cover、純関数（本文組み立て・page ID 抽出・idempotency_key）と publisher を fake で網羅し、品質の要を testable 側へ寄せる。
- [delegated で投稿者に個人アカウントが見える] → Issue #32 / spec が PoC 範囲で許容。`AuditEvent.actor` に記録し説明責任を担保。hosted 本番は #27。
- [`--no-dry-run` の誤実行で実投稿] → 既定 dry-run、明示 opt-out 必須、`security.require_approval` / `block_auto_publish` 方針を尊重、runbook で手順を明示。auth/publish の人間ゲート carve-out として apply 前に coordinator へ decision_gate で確認。
- [Sites.ReadWrite.All は広め] → PoC では delegated の現実解。定数化し、`Sites.Selected`（app-only）への upgrade path をコメントで残す。

## Migration Plan

- 新規モジュール追加のみ。既存 DTO / schema / storage は変更しない（migration 不要）。
- config は `graph.client_id` 追加（任意キー、既存設定は後方互換）。
- ロールバックは `src/spautopost/graph/` と CLI サブコマンド・config 許可キー・extra の revert で完結。

## Open Questions

- News としての promote 操作（`publish_site_page` の publish 段）を本 PoC に含めるか、page 作成のみに留めるか。→ 既定は作成のみ、publish は任意段として実装し runbook で案内。
- `Sites.ReadWrite.All` を delegated PoC の既定とするかの最終承認（auth/publish carve-out として coordinator 確認）。
