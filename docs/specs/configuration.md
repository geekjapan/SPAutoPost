# Configuration Specification

## Status

Proposed

## Purpose

この Spec は、SPAutoPost の設定ファイル、環境変数、provider 切替、SharePoint 投稿先、source adapter、dry-run、feature flag の扱いを定義します。

## Principles

- Secret は config file に直書きしない。
- 環境ごとに config を分離する。
- 投稿先は明示的に固定する。
- dry-run を既定値にできる。
- provider と source adapter は設定で切り替え可能にする。

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

llm:
  provider: mock
  prompt_version: v1

sharepoint:
  mode: list-item
  default_draft: true
  allow_publish: false
  tenant_id: env:SPAUTOPOST_TENANT_ID
  site_id: env:SPAUTOPOST_SHAREPOINT_SITE_ID
  list_id: env:SPAUTOPOST_SHAREPOINT_LIST_ID

sources:
  manual:
    enabled: true
    input_dir: ./samples/advisories
  nvd:
    enabled: false
    api_key: env:SPAUTOPOST_NVD_API_KEY
  myjvn:
    enabled: false

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

- SPAUTOPOST_TENANT_ID
- SPAUTOPOST_SHAREPOINT_SITE_ID
- SPAUTOPOST_SHAREPOINT_LIST_ID
- SPAUTOPOST_SHAREPOINT_PAGE_LIBRARY_ID
- SPAUTOPOST_AZURE_OPENAI_ENDPOINT
- SPAUTOPOST_AZURE_OPENAI_DEPLOYMENT
- SPAUTOPOST_AZURE_OPENAI_API_KEY
- SPAUTOPOST_NVD_API_KEY

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

## Dry Run

`dry_run: true` の場合:

- SharePoint には投稿しない
- LLM provider 呼び出しは provider 設定に従う
- publish payload preview を出力できる
- audit log は dry-run として記録する

## Validation

起動時に検査する項目:

- environment
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
