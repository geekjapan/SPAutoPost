# Deployment skeleton (Azure Container Apps)

Issue #25 / OpenSpec change `issue-25-add-azure-container-apps-deployment-skeleton`.

運用コアを Azure Container Apps / Container Apps Jobs に載せるための **最小 skeleton**。
本番 Azure リソース・本番 Secret 登録・本格 IaC（Bicep）・deploy automation・本格
Admin UI は M1 非対象（`docs/specs/deployment.md` の Non-Goals）。

## 構成

| ファイル | 役割 |
|----------|------|
| `Dockerfile.core` | Python core image。`spautopost-job` を ENTRYPOINT にし、baseline migration SQL を含める |
| `Dockerfile.admin` | Admin API（TypeScript skeleton, Issue #31）の image |
| `jobs.example.yaml` | Container Apps Jobs の command / schedule / secretRef 参照 skeleton |
| `config.hosted.example.yml` | hosted 設定例（production / postgresql / `env:` 参照） |
| `hosted.env.example` | hosted で必要な env / secret 参照例（placeholder のみ） |

## local 実行 vs Azure 想定実行

| | local | Azure（hosted, 想定） |
|--|-------|----------------------|
| 実行形態 | `spautopost <command>` を端末で実行 | Container Apps Jobs が image を起動し `spautopost-job <job-name>` を実行 |
| 設定 | `config/default.yml`（`config.example.yml` 由来）を基底に任意の `config/<env>.yml` を overlay | image に焼いた `config/default.yml`（`config.hosted.example.yml` 由来, production） |
| storage | sqlite（`sqlite_path`） | postgresql（`database_url`, Azure Database for PostgreSQL） |
| Secret | 端末の環境変数 | Container Apps secret ref → 環境変数として注入 |
| publish | 既定 dry-run。publish は人間ゲート | 同左。`publish-approved` job は guarded stub（publish しない） |

local 実行手順はリポジトリ直下 `README.md` の「起動方法（開発）」を参照。

## Job 名と CLI command のマッピング

Container Apps Jobs は job 名 1 つを args に渡し、`spautopost-job`
（`src/spautopost/job_entrypoint.py`）が安全な CLI command に解決する。

| job 名 | 解決される CLI command | 備考 |
|--------|------------------------|------|
| `dry-run` | `spautopost --dry-run validate-config` | 外部通信なし。健全性確認 |
| `collect` | `spautopost --dry-run run-sample-source-job` | M1 は deterministic sample source |
| `generate` | `spautopost --dry-run run-sample-source-job` | M1 は collect と同じ pipeline |
| `publish-approved` | （CLI を呼ばない guarded stub, exit 4） | 常に人間ゲート。publish しない |

> `publish-approved` は publish を一切行わず exit code 4 で終了する。実 publish 経路は
> 承認フロー確定後の後続 Issue で実装する。

## ビルド（参考）

```sh
# build context は repo root
docker build -f deploy/Dockerfile.core  -t spautopost-core  .
docker build -f deploy/Dockerfile.admin -t spautopost-admin .

# image 単体での健全性確認（secret ref を placeholder env で渡す）
docker run --rm --env-file deploy/hosted.env.example spautopost-core dry-run
```

> 注: `hosted.env.example` は placeholder のみ。実値は使わず、hosted では Container
> Apps secret ref から注入する。`config/*.yml` と `data/` は `.dockerignore` で image
> に入らない（実 Secret 混入防止）。
