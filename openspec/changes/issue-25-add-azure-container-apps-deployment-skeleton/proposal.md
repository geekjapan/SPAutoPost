## Why

MVP の運用コアは Azure Container Apps / Azure Container Apps Jobs に寄せる方針だが、現状は container image build、Jobs から呼ぶ command entrypoint、local / hosted 設定分離の最小 skeleton が不足している。Issue #25 / M1 の受け入れ条件を満たすため、Azure リソースを作成せずに再現可能な deployment skeleton を追加する。

## What Changes

- Python core 用 `Dockerfile.core` と TypeScript Admin API 用 `Dockerfile.admin` を追加する。
- Azure Container Apps Jobs から SPAutoPost CLI を呼ぶ entrypoint wrapper skeleton を追加する。
- scheduled job 用に dry-run / collect / generate / publish-approved の安全な command skeleton を用意する。
- local 用 config example と hosted 用 config example を分け、Secret は `env:` 参照または Azure secret reference 例だけで示す。
- README / docs に local run と Azure-intended run の違い、Docker build、Jobs command 例、非対象範囲を追記する。
- 追加した CLI / wrapper の挙動に対する最小テストを追加する。
- Azure リソース作成、本番 Secret 登録、本格 IaC、monitoring、Admin UI 完成、本番 DB 最終決定は行わない。

## Capabilities

### New Capabilities

- `azure-container-apps-deployment`: M1 hosted PoC 用の container image build、Container Apps / Jobs entrypoint、scheduled job command skeleton、local / hosted config separation、Secret reference 例を扱う。

### Modified Capabilities

<!-- 既存 OpenSpec capability の requirement は変更しない。 -->

## Impact

- **コード**: Python CLI に安全な scheduled job skeleton command を追加する。entrypoint wrapper script を追加する。
- **Docker**: core / admin の Dockerfile を追加する。
- **設定例**: local / hosted example config を追加または更新する。Secret の実値は含めない。
- **ドキュメント**: README または deployment docs に local run と Azure-intended run の差分を追記する。
- **テスト**: CLI skeleton command と wrapper の最小テストを追加する。
- **セキュリティ**: 実 Secret、production token、Cookie、外部 account 操作、実 publish、Azure resource creation は扱わない。
