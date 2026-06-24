## 1. Container build skeleton

- [x] 1.1 `Dockerfile.core` を追加し、Python core CLI と hosted PostgreSQL extra を image build できるようにする
- [x] 1.2 `Dockerfile.admin` を追加し、TypeScript Admin API skeleton を build / run できるようにする

## 2. Container Apps Jobs entrypoint

- [x] 2.1 Azure Container Apps Jobs 用 wrapper script を追加し、dry-run / collect / generate / publish-approved を CLI command に dispatch する
- [x] 2.2 Python CLI に safe scheduled job skeleton command を追加し、未実装 path は no-op stub として実 publish / 外部 API 呼び出しを行わない

## 3. Config and docs

- [x] 3.1 local / hosted の example config を分離し、Secret は `env:` 参照のみで示す
- [x] 3.2 README または deployment docs に local run と Azure-intended run、Docker build、Jobs command 例、非対象範囲を追記する

## 4. Tests and verification

- [x] 4.1 追加した CLI / wrapper behavior の最小テストを追加する
- [x] 4.2 `openspec validate issue-25-add-azure-container-apps-deployment-skeleton --strict` と関連 verification を実行する
