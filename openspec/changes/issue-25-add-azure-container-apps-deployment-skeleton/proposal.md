## Why

Issue #25 では、運用コアを利用者端末ではなく Azure Container Apps / Container Apps Jobs 側に載せる方針（`docs/specs/deployment.md`, `docs/specs/architecture.md`）に沿って、最小の deployment skeleton を用意する必要がある。本格 IaC・本番リソース・本番 Secret 登録・本格 Admin UI は M1 の非対象であり、ここでは「container image build 前提」と「scheduled job から SPAutoPost CLI を安全に呼べる構成」と「local / hosted 設定分離」の縦串だけを確立する。

## What Changes

- Python core 用の container image build 前提（`deploy/Dockerfile.core`）を追加し、CLI を job entrypoint として固定する。
- Container Apps Jobs の entrypoint 方針として薄い wrapper（`spautopost-job <job-name>`）を追加し、job 名を安全な CLI command にマッピングする。
- scheduled job command skeleton として dry-run / collect / generate / publish-approved の 4 経路を定義する。`publish-approved` は常に human gate であり、wrapper は決して publish せず guarded stub として終了する。
- hosted 用の config 例（`deploy/config.hosted.example.yml`）と env / secret reference 例（`deploy/hosted.env.example`）を追加し、local（`config.example.yml` / sqlite）と hosted（production / postgresql / `env:` 参照）の設定分離を明示する。
- Container Apps Jobs の command / schedule / secretRef 構成を示す参照マニフェスト skeleton（`deploy/jobs.example.yaml`）を追加する。
- README に local 実行と Azure 想定実行の違いを追記する。
- 本番 Azure リソース、本番 Secret、本格 IaC（Bicep）、deploy automation、本格 Admin UI は追加しない。

## Capabilities

### New Capabilities

- `deployment-skeleton`: SPAutoPost を Azure Container Apps / Jobs に載せるための container image build 前提、job entrypoint 方針、scheduled job command skeleton、local/hosted 設定分離を扱う。

### Modified Capabilities

- なし。

## Impact

- `deploy/`
- `src/spautopost/job_entrypoint.py`
- `pyproject.toml`（`spautopost-job` console script）
- `tests/`
- `README.md`
- `openspec/changes/issue-25-add-azure-container-apps-deployment-skeleton/`
