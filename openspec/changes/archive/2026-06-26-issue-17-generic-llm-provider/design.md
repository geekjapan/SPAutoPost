## Context

現状の `src/spautopost/llm/__init__.py` の `build_llm_provider` は `test_mock` のみ対応。`generic_api` は `LLMProviderConfigError` を返す状態。`LLMConfig` には `provider` と `prompt_version` しかなく、endpoint/auth 設定フィールドが存在しない。

`docs/specs/llm-provider.md`（Issue #15 確定版）の `generic_api` 要件：
- endpoint / model / auth / request / response mapping を設定または adapter で分離
- 公式 API のみ（非公式 API・UI scraping 禁止）
- 認証情報は env 経由のみ（`secrets.py` の `env:VAR` パターン）
- 監査必須項目：provider_name, provider_type, model, prompt_version, generation_input_hash, generated_at

## Goals / Non-Goals

Goals:
- OpenAI-compatible（`/v1/chat/completions`）API を設定で有効化できる
- request は `DraftInput` → システムプロンプト + ユーザーメッセージに変換（テンプレート固定）
- response は `choices[0].message.content` → `DraftOutput` に変換（フィールドマッピング固定）
- auth header（`Authorization: Bearer <token>`）は env 経由、ログ非出力
- timeout / retry を設定可能
- `ProviderMetadata` に監査項目を含める
- `validate_config()` で endpoint URL・auth env var 存在を確認

Non-Goals:
- streaming response のサポート
- vendor 固有の非 OpenAI-compatible API（Anthropic native 等）—別 adapter で対応
- UI 自動操作・scraping（`test_manual` の範囲）
- rate limit の自動バックオフ（タイムアウトのみ対応）

## Decisions

### D1: 新ファイル `generic_provider.py` に分離
`__init__.py` は巨大化しないよう provider 実装を別ファイルへ。`MockLLMProvider` と同じパターン。

### D2: HTTP には stdlib `urllib.request` を使用
新規依存なし（pyproject.toml の `requests` 追加不要）。OpenAI-compatible の単純 POST なら十分。

### D3: request/response mapping は実装に固定（設定ではなく）
テンプレートは `DraftInput` → OpenAI messages 変換の単一実装。将来 mapping を設定外出しする際は config フィールドを追加する。
ponytail: 現状 1 実装なので実装固定。複数 vendor 差が出たら設定化する。

### D4: `LLMConfig` に generic_api 向けフィールドを追加
```
endpoint_url: str | None        # "env:LLM_ENDPOINT" 参照可
model: str | None
auth_env_var: str | None        # env var 名（値そのものでなく名前）
timeout_seconds: int            # default 30
max_retries: int                # default 3
```
`_SECTION_KEYS["llm"]` へ追加キーを追記。`test_mock` 利用時はこれらを None/default のまま無視する。

### D5: auth header 値はコード内で保持しない
`generate_draft` 実行時に `os.environ[auth_env_var]` を都度取得し、変数の寿命を最小化。ログ・例外メッセージには含めない。

## Risks / Trade-offs

- [urllib の timeout は接続タイムアウトのみ適用] → read_timeout は Python 3.12 以降で対応済み（`urllib.request.urlopen(req, timeout=N)` で接続＋読み取りタイムアウト両方に適用される）
- [retry は固定待機（指数バックオフなし）] → rate limit が問題になったら exponential backoff を追加する。現時点では YAGNI
- [response mapping が JSON parse 失敗した場合] → `provider_response_invalid` エラーとして `LLMProviderError` を送出、retry 対象外

## Migration Plan

1. `LLMConfig` 拡張（後方互換）
2. `generic_provider.py` 新規作成（TDD）
3. `build_llm_provider` を `generic_api` に routing
4. テスト更新（`test_build_llm_provider_rejects_unimplemented_provider_types` から `generic_api` を除外）
5. lint / type check / テスト実行

## Open Questions

- 本番利用時の `production_approved` フラグ（spec に記載）は M3 対応範囲。現実装では `validate_config` が設定の構造的正当性のみ確認し、承認フラグチェックは Issue #16/17 本番対応時に追加する。
