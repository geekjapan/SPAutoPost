# Deployment Specification

## Status

Proposed

## Purpose

この Spec は、SPAutoPost の M1 hosted PoC を Azure 上に載せるための deployment skeleton を定義します。

## M1 Target

M1 では、再現可能な最小 deployment skeleton を作成します。

対象:

- Azure Container Apps Admin UI/API
- Azure Container Apps Jobs
- Azure Database for PostgreSQL Flexible Server
- environment variables
- container image build
- GitHub Actions skeleton
- Bicep skeleton

## Runtime Components

```text
Azure Container Apps Environment
  ├─ Admin UI/API App
  ├─ Scheduled Jobs
  ├─ PostgreSQL
  └─ External Services
```

## App Components

### Admin UI/API App

- TypeScript / Node.js
- Entra ID login
- DraftPost management
- Review / Approval API
- PostgreSQL access

### Scheduled Jobs

- Python core command image
- collect-advisories
- normalize-and-triage
- generate-drafts
- publish-approved
- M1 skeleton では Jobs entrypoint wrapper から CLI command を呼び出す。未実装 command は no-op stub とし、実 publish や外部 API 呼び出しは行わない。

### PostgreSQL

- M1 hosted PoC の正本 DB
- schema migration baseline
- local/test SQLite adapter は別扱い

## Infrastructure as Code

M1 では Bicep を第一候補とします。

推奨構成:

```text
infra/
  bicep/
    main.bicep
    container-apps.bicep
    jobs.bicep
    postgres.bicep
```

## Container Build

推奨構成:

```text
Dockerfile.core
Dockerfile.admin
```

または monorepo 構成に応じて `apps/core/Dockerfile`、`apps/admin/Dockerfile` とします。

この repo の M1 skeleton では monorepo root に次を置きます。

- `Dockerfile.core`: Python core / scheduled jobs image。`spautopost` CLI と PostgreSQL extra を含む。
- `Dockerfile.admin`: TypeScript / Node.js Admin API skeleton image。
- `scripts/aca-job-entrypoint.sh`: Container Apps Jobs から dry-run / collect / generate / publish-approved を dispatch する wrapper。

## GitHub Actions Skeleton

M1 では build / test / container image build の skeleton を作ります。

例:

```text
.github/workflows/
  ci.yml
  build-core.yml
  build-admin.yml
```

本番 deploy automation は M6 で強化します。

## Configuration

設定は `docs/specs/configuration.md` に従います。

必要項目:

- database connection setting
- SharePoint target site / page library
- Graph auth mode
- LLM provider selection
- dry-run / publish flag
- Entra ID admin auth setting

local / hosted の分離:

- local: `config.local.example.yml` を `config/default.yml` にコピーし、SQLite と dry-run を使う。
- hosted: `config.hosted.example.yml` を基に、PostgreSQL と Azure 側の environment variables / secret references を使う。
- Secret 実値は repo に保存しない。設定ファイルには `env:NAME` 参照のみを書く。

Container Apps Jobs command 例:

```sh
aca-job-entrypoint dry-run --env production --config-dir /app/config
aca-job-entrypoint collect --env production --config-dir /app/config
aca-job-entrypoint generate --env production --config-dir /app/config
aca-job-entrypoint publish-approved --env production --config-dir /app/config
```

## Non-Goals

- 本番運用 IaC の完成
- 本格 monitoring
- Log Analytics 連携
- Blue/green deployment
- DR / HA 設計

## Related Issues

- #24 Finalize Azure hosted core architecture
- #25 Add Azure Container Apps deployment skeleton
- #28 Implement PostgreSQL storage baseline
- #31 Implement TypeScript Node.js Admin UI API skeleton
