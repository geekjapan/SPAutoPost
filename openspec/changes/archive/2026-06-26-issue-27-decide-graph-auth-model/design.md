## Context

SPAutoPost は Azure Container Apps / Jobs 上で動作し、Microsoft Graph 経由で SharePoint Site Page / News 記事を投稿する。MVP 実装前に認証モデルを確定する必要がある。

現在の `docs/specs/graph-authentication.md` は認証の候補と方向性を記載しているが、Issue #27 の受け入れ条件（local PoC・Azure hosted runtime・managed identity 採否・delegated permission の本番除外・Graph permission 最小化）を満たす形式的な決定として明文化されていない。

関連する制約:
- Azure hosted runtime は unattended（非対話型）実行が前提
- Container Apps App と Container Apps Jobs で identity を統一したい
- Graph permission は audit / compliance のため最小化が必要
- local 開発者は対話型認証を使いたい

## Goals / Non-Goals

**Goals:**
- local PoC 認証方式（delegated permission / Device Code Flow）を決定・明記する
- Azure hosted runtime 認証方式（user-assigned managed identity first）を決定・明記する
- managed identity 採用を正式決定し、user-assigned を選択する根拠を示す
- delegated permission を本番定期実行に使わないことを明示する
- 必要最小 Graph permission と `Sites.Selected` 優先方針を明記する
- SharePoint 対象 site を config で限定する方針を明記する
- `docs/specs/graph-authentication.md` を更新して全受け入れ条件を満たす

**Non-Goals:**
- 本番 app registration / managed identity の実際の作成・設定
- Azure Key Vault や Secret 管理の実装
- SharePoint connector PoC の実装（Issue #9, #32 で実施）
- 本番 tenant での admin consent / permission grant

## Decisions

### Decision 1: local PoC 認証方式 → delegated permission（Device Code Flow）

**選択**: Device Code Flow による delegated permission

**根拠**:
- local 開発環境ではブラウザ認証が可能であり、対話型フローが最もシンプル
- 開発初期に app registration の application permission 設定や managed identity の Azure 環境設定なしに Graph 疎通確認ができる
- `msal` / `azure-identity` の `DeviceCodeCredential` で実装できる

**代替案**:
- Client Credentials Flow（app secret）: 開発環境でも Secret 管理が必要になり煩雑
- Interactive Browser Credential: ヘッドレス環境では使えない

### Decision 2: Azure hosted runtime → user-assigned managed identity（第一候補）

**選択**: user-assigned managed identity を第一候補、application permission を fallback

**根拠**:
- Secret を持たない運用ができ、rotation・leakage リスクがない
- Container Apps App と Jobs で同一 identity を共有しやすい
- Azure リソース管理ポリシーと整合する（system-assigned は resource 依存でライフサイクルが変わる）
- `DefaultAzureCredential` / `ManagedIdentityCredential` で実装できる

**代替案**:
- system-assigned managed identity: resource 単位で identity が変わりアクセス制御が分散する
- application permission（client secret）: Secret 管理が必要、leakage リスクがある

**Fallback 条件**: M1 検証で managed identity への Graph permission 付与（`Sites.Selected`）が組織ポリシー上不可能であると確認された場合のみ application permission を使用する。

### Decision 3: delegated permission → 本番定期実行に使わない

**選択**: 本番 Azure Container Apps Jobs では delegated permission を使用しない

**根拠**:
- 定期実行ジョブはユーザーのセッション・ブラウザ・refresh token の生存に依存してはならない
- token 切れによるジョブ失敗リスクが高い
- unattended 実行に適さない

### Decision 4: Graph permission → Sites.Selected 優先、最小権限

**選択**: `Sites.Selected` を第一候補、投稿操作に必要な最小セット

**必要最小 permission（暫定）**:

| Permission | 種別 | 用途 |
|---|---|---|
| `Sites.Selected` | Application | 対象 site への読み書き（推奨） |
| `Pages.ReadWrite.All` | Application | Site Page / News 記事の作成・更新（Sites.Selected 対応状況による） |

**根拠**:
- `Sites.Selected` は特定 site のみを対象とした permission 付与が可能で最小権限要件を満たす
- `Sites.ReadWrite.All` は tenant 全体へのアクセスを許容するため本番では避ける
- `Pages.ReadWrite.All` は `Sites.Selected` と組み合わせて site page 操作に必要な場合がある（M1 検証で確認）

**M1 で確認すること**: `Sites.Selected` + `Pages.ReadWrite.All` の組み合わせで Site Page / News の作成・更新・公開が可能か。

## Risks / Trade-offs

- [managed identity への `Sites.Selected` 付与が組織ポリシーでブロックされる可能性] → M1 検証で早期確認する。不可能な場合 application permission fallback に切り替える。
- [Device Code Flow のトークンキャッシュを誤って repo にコミットするリスク] → `.gitignore` で token cache ファイルを除外する。MSAL の token cache 保存先を明示する。
- [`Pages.ReadWrite.All` が `Sites.Selected` と組み合わせ可能か不確定] → M1 の SharePoint connector PoC（Issue #9, #32）で検証する。不可能なら代替 permission を評価する。

## Open Questions

- `Sites.Selected` permission は managed identity に付与できるか（M1 検証）
- `Pages.ReadWrite.All` は `Sites.Selected` スコープ内で有効か（M1 検証）
- application permission fallback を使う場合の Secret 管理は Azure Key Vault か（Issue #22 で決定）
