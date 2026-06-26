## Context

- M1 では `test_mock` + template で DraftPost 生成を完了。M3 から実 LLM を使う
- Issue #15 で `production_api` = Azure OpenAI / Foundry に決定。認証方式は API key（M3）/ managed identity（将来）
- 既存パターン: Secret は `env:NAME` 参照で config に書き、`secrets.py` で解決
- `LLMProvider` Protocol と `DraftInput` / `DraftOutput` はすでに確定（Issue #6）
- HTTP クライアントはランタイム依存を増やさず stdlib `urllib.request` を使う（Issue #15 の制約）

## Goals / Non-Goals

**Goals**:
- `AzureOpenAIProvider` が `LLMProvider` を実装し、`build_llm_provider("production_api")` で取得できる
- API key を `env:` 参照で安全に取得し、ログ・例外に漏洩させない
- timeout・retry・error mapping を実装する
- 監査 metadata（hash / model / token_usage）を `DraftOutput.source_mapping` に付与する
- CI でモック HTTP を使ってテストが完結する（実 endpoint 不要）

**Non-Goals**:
- managed identity 認証（将来の optional extra）
- streaming レスポンス
- 非同期（async/await）実装
- cost 推定（`estimate_cost`）の実装
- output validation（Issue #18 スコープ）

## Decisions

### 1. HTTP クライアントは stdlib urllib.request を使う

`httpx` / `requests` / `openai` SDK は新規 runtime 依存になる。Issue #15 の「新規依存最小」制約に従い、stdlib `urllib.request` を使う。Connection pool や HTTP/2 は不要（呼び出し頻度が低い batch job）。

代替: `openai` Python SDK → Azure OpenAI を完全サポートするが、`openai>=1.0` は大きな依存チェーン（`httpx` 含む）を引き込む。M3 では不採用。

### 2. 認証方式は API key のみサポート（M3）

managed identity は `azure-identity` パッケージが必要で新規依存になる。M3 では `env:AZURE_OPENAI_API_KEY` を `api-key` ヘッダに設定する方式のみ実装する。`auth_type: managed_identity` は config に定義するが、`AzureOpenAIProvider` がその値を検出したら `validate_config` で `valid=False`・`LLMProviderConfigError` にする（将来実装への準備）。

### 3. レスポンス変換は JSON + 必須フィールド存在チェック

`response_format: {"type": "json_object"}` を使い、system prompt で `DraftOutput` フィールドを JSON で出力するよう指示する。LLM は JSON を保証しないため、パース失敗・必須フィールド欠損は `LLMProviderError(is_retryable=False)` として扱う（プロンプト改善が先決）。

代替: Pydantic で validate → 新規依存。stdlib `json.loads` + 手動チェックで十分。

### 4. Retry は指数バックオフ、backoff は `time.sleep` で実装

429 / 5xx / timeout は retryable。401 / 403 / 400 は non-retryable。backoff は `2^attempt * base_delay_secs`（デフォルト 1 秒）にジッターなし（batch job のため競合は無視）。テストでは `time.sleep` をモックする。

### 5. 監査 metadata は DraftOutput.source_mapping に格納

`DraftOutput` の既存フィールド `source_mapping: Mapping[str, str]` を使い、`provider_name` / `model` / `prompt_version` / `token_usage`（JSON 文字列）を格納する。LLM audit log への実際の書き込みは将来の audit log モジュール（Issue #10 スコープ）が `source_mapping` を読む設計。

### 6. production_approved フラグ

設定バリデーション時に `production_approved: true` を確認する。未設定・false の場合、`validate_config` が `valid=False` を返し、`generate_draft` は `LLMProviderError` を送出する。これは #15 spec の「`llm.production_approved` フラグが `true` でない状態で production_api を使用しようとする → エラー」要件を実装する。

## Risks / Trade-offs

- `urllib.request` は connection pool なし → 高頻度呼び出し時のレイテンシ増大リスク → batch job 用途のため許容。頻度増加時に `httpx` に切り替え可能
- JSON パース失敗が production で頻発する可能性 → プロンプト調整で対処。`LLMProviderError(is_retryable=False)` で上位に通知
- managed identity 未実装 → production 環境では API key を Azure Key Vault から注入する運用で補う
- テストで `time.sleep` をモックしないと retry テストが遅い → `_sleep_fn` 注入パターンで解決

## Migration Plan

1. 既存 `build_llm_provider` が `production_api` 未サポートで `LLMProviderConfigError` を送出していた箇所を `AzureOpenAIProvider` 返却に差し替える
2. `config.py` の `llm` セクションに `azure` サブセクション追加（既存 `test_mock` config は変更なし）
3. `tests/llm/test_azure_openai.py` 追加（mock HTTP）
4. `config.example.yml` に azure provider 設定例を追加

Rollback: `build_llm_provider` の `production_api` ブランチを削除し、`LLMProviderConfigError` に戻すだけ。

## Open Questions

- `response_format: json_object` が Foundry endpoint で利用可能か否か（モデル依存）→ M3 本番接続テスト時に確認
- managed identity 実装時の optional extra 名（`azure` / `azure-identity`）→ 将来 Issue で決定
