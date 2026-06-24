## Context

Issue #25 は、SPAutoPost を Azure Container Apps / Azure Container Apps Jobs に載せるための M1 deployment skeleton を求めている。既存実装は Python CLI / Batch command、TypeScript Admin API skeleton、SQLite / PostgreSQL storage provider、`config.example.yml` を持つが、container image build と Jobs entrypoint の形は未整備である。

正本は GitHub Issue #25、`docs/specs/deployment.md`、`docs/specs/architecture.md` とする。Azure resource 作成、production Secret 登録、実 publish、本格 IaC は対象外である。

## Goals / Non-Goals

**Goals:**

- 現在の repo shape に合う `Dockerfile.core` / `Dockerfile.admin` を追加する。
- Container Apps Jobs が同じ wrapper から `spautopost` CLI command を呼べる形にする。
- dry-run / collect / generate / publish-approved の job command skeleton を安全に用意する。
- local は SQLite / dry-run、hosted は PostgreSQL / env secret reference という設定分離を明示する。
- README / docs とテストで skeleton の使い方と安全境界を確認できるようにする。

**Non-Goals:**

- Azure resource の作成、Bicep 完成、GitHub Actions deploy automation。
- production Secret の登録、実値の保存、token / cookie / credential の出力。
- Microsoft Graph / SharePoint / 外部 source / LLM production API の実呼び出し。
- Admin UI の完成、本番 DB 設計の最終決定、本格 monitoring。

## Decisions

1. **Dockerfile は repo root に置く**
   - `docs/specs/deployment.md` が `Dockerfile.core` / `Dockerfile.admin` を推奨しており、現状は monorepo root に Python core と `admin-api/` がある。
   - 代替の `apps/*/Dockerfile` は現状の directory shape と合わないため採用しない。

2. **Jobs entrypoint は shell wrapper にする**
   - Azure Container Apps Jobs の command / args から `scripts/aca-job-entrypoint.sh <job>` を呼ぶだけで command mapping を固定できる。
   - Python に wrapper を寄せる案は、container startup policy の説明としては重く、既存 CLI と責務が重なるため採用しない。

3. **未実装の job は安全な CLI skeleton にする**
   - `collect-advisories` は現状の安全な sample source job を再利用できる。
   - `generate-drafts` と `publish-approved` はまだ完全な domain command がないため、external API / SharePoint publish を行わない JSON stub とする。
   - `publish-approved` は `--no-dry-run` でも実 publish せず、承認済み publish pipeline 実装 Issue まで no-op とする。

4. **設定例は root の example yml と docs で分ける**
   - `.gitignore` は `config/*.yml` を無視するため、tracked example は root に置く。
   - local example は SQLite / dry-run、hosted example は PostgreSQL / `env:` reference を示す。実 Secret 値は含めない。

## Risks / Trade-offs

- **Risk: skeleton command を本番実装と誤解する** -> README と command output に `status: "stub"` / no external calls を明記する。
- **Risk: hosted config example に Secret 実値が混入する** -> `env:NAME` 参照だけを記載し、PR 前に diff を確認する。
- **Risk: Docker build が optional postgres extra を含まない** -> core image は hosted 想定のため `.[postgres]` を install する。
- **Risk: Admin API container は DB 接続がなければ起動後に実 API が失敗する** -> Dockerfile は build/run skeleton に限定し、Secret / DB は hosted env vars で渡す前提にする。
