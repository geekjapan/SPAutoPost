# Configuration Specification

## Status

Accepted for M0

config 構造・環境変数・database provider 分離・secret 参照・feature flag・dry-run の基礎契約は Issue #4 の application skeleton change（configuration capability）で確定・archive 済み。詳細は `docs/design-documents.md` の Review & Status Matrix (Issue #23) を参照。

## Purpose

この Spec は、SPAutoPost の設定ファイル、環境変数、provider 切替、SharePoint 投稿先、database、source adapter、dry-run、feature flag の扱いを定義します。

## Principles

- Secret は config file に直書きしない。
- 環境ごとに config を分離する。
- 投稿先は明示的に固定する。
- dry-run を既定値にできる。
- provider と source adapter は設定で切り替え可能にする。
- M1 hosted PoC の正本 database は PostgreSQL とする。
- local/test では SQLite adapter を許容する。

## Config File

推奨ファイル:

```text
config/default.yml
config/development.yml
config/test.yml
config/production.yml
```

MVP では `config.example.yml` を提供し、実 config は gitignore します。

## Example

```yaml
app:
  environment: development
  dry_run: true
  log_level: info

server:
  admin_ui_enabled: true
  admin_api_enabled: true
  auth_provider: entra_id

storage:
  provider: postgresql # postgresql | sqlite
  database_url: env:SPAUTOPOST_DATABASE_URL
  sqlite_path: ./data/spautopost.dev.sqlite3

llm:
  provider: test_mock # production_api | production_flow | generic_api | test_mock | test_manual
  prompt_version: v1

sharepoint:
  mode: site-page                           # "site-page" 固定（M1）
  default_draft: true
  allow_publish: false
  tenant_id: env:SPAUTOPOST_TENANT_ID
  site_id: env:SPAUTOPOST_SHAREPOINT_SITE_ID
  page_library_id: env:SPAUTOPOST_SHAREPOINT_PAGE_LIBRARY_ID
  dedicated_site: true                      # 必須: 専用サイトのみ許可（M1）
  news_promote: false                       # M1: News promote 未実装
  idempotency_scope: site-and-page-library  # 必須

sources:
  manual:
    enabled: true
    input_dir: ./samples/advisories
  nvd:
    enabled: false
    api_key: env:SPAUTOPOST_NVD_API_KEY
  myjvn:
    enabled: false

graph:
  local_poc_auth: delegated
  hosted_auth: managed_identity # user-assigned managed identity（#27 確定）、fallback は app_only

security:
  block_auto_publish: true
  require_approval: true
  redact_secrets_in_logs: true
```

## Environment Variables

推奨 prefix:

```text
SPAUTOPOST_
```

例:

- SPAUTOPOST_DATABASE_URL
- SPAUTOPOST_TENANT_ID
- SPAUTOPOST_SHAREPOINT_SITE_ID
- SPAUTOPOST_SHAREPOINT_PAGE_LIBRARY_ID
- SPAUTOPOST_AZURE_OPENAI_ENDPOINT
- SPAUTOPOST_AZURE_OPENAI_DEPLOYMENT
- SPAUTOPOST_AZURE_OPENAI_API_KEY
- SPAUTOPOST_NVD_API_KEY

## Database Configuration

M1 hosted PoC:

- provider: postgresql
- database_url: env:SPAUTOPOST_DATABASE_URL

local/test:

- provider: sqlite
- sqlite_path: local path

実装要件:

- database_url の値をログに出さない。
- hosted environment では postgresql を既定とする。
- sqlite は local/test/offline dry-run 用に限定する。
- migration は PostgreSQL schema を基準にする。

## Secret Reference

config には `env:NAME` のような参照だけを書きます。

実装要件:

- 起動時に Secret が未設定なら validation error
- validation error でも Secret 値を表示しない
- debug log に Secret を出力しない

## Feature Flags

推奨 flag:

- enable_nvd
- enable_myjvn
- enable_kev
- enable_vendor_feed
- enable_sharepoint_publish
- enable_site_page_publish
- enable_generic_llm_provider
- enable_manual_test_provider
- enable_admin_ui
- enable_admin_api

## Dry Run

`dry_run: true` の場合:

- SharePoint には投稿しない
- LLM provider 呼び出しは provider 設定に従う
- publish payload preview を出力できる
- audit log は dry-run として記録する

## Validation

起動時に検査する項目:

- environment
- storage provider
- database connection setting
- provider selection
- SharePoint mode
- required target IDs
- allow_publish と require_approval の整合
- Secret reference の存在
- unknown config key

## Related Issues

- #4 Initialize application skeleton and configuration policy
- #6 Implement LLM provider interface with mock provider
- #9 Implement SharePoint connector proof-of-concept
- #10 Implement dry-run preview and minimal audit log
- #28 Implement PostgreSQL storage and migration baseline
