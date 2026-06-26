# Delta Spec: llm-provider

## MODIFIED Requirements

### Requirement: build_llm_provider が generic_api provider を構築する

`build_llm_provider` 関数は `config.provider` が `"generic_api"` の場合に `GenericApiLLMProvider` を返さなければならない（SHALL）。

`"test_mock"` の挙動は変更されない。

#### Scenario: generic_api が選択されたとき GenericApiLLMProvider が返される

- **WHEN** `build_llm_provider(LLMConfig(provider="generic_api", endpoint_url=..., model=..., auth_env_var=...))` を呼ぶ
- **THEN** `GenericApiLLMProvider` のインスタンスが返される

#### Scenario: test_mock は従来どおり MockLLMProvider を返す

- **WHEN** `build_llm_provider(LLMConfig(provider="test_mock", prompt_version="v1"))` を呼ぶ
- **THEN** `MockLLMProvider` のインスタンスが返される
