## Context

現在 `src/spautopost/llm/` には `DraftOutput` 型と `MockLLMProvider` があり、`compose_sharepoint_draft` が生成物に `validation_hints` / `warnings` / `uncertainty_notes` を付与している。しかし「どのチェックが通ったか」「reviewer が確認すべき点はどこか」を構造的に表現する validator モジュールは存在しない。M3 で production LLM provider を接続する前に、出力安全性を機械的に確認できる仕組みを整備する。

## Goals / Non-Goals

**Goals:**

- `validate_draft_output(draft: DraftOutput) -> ValidationResult` を純粋関数として実装する
- required sections check・references check・unsupported claim check・dangerous detail guardrail・uncertainty wording check・regeneration request reason・reviewer warning の 7 種類のチェックを提供する
- `ValidationResult` は severity 付きの `ValidationIssue` リストを持ち、`has_errors` / `has_warnings` で判定できる
- テストカバレッジ 80% 以上、TDD で実装する

**Non-Goals:**

- LLM API 呼び出しや SharePoint 連携は行わない
- 既存の `DraftOutput` / `LLMProvider` interface を変更しない
- AI によるセマンティック解析（ベクトル類似度など）は行わない（ルールベース）
- `DraftPost`（storage モデル）への直接バリデーションは対象外

## Decisions

### D1: 純粋関数アプローチ

`validate_draft_output(draft: DraftOutput) -> ValidationResult` を副作用のない純粋関数として実装する。クラスベースのバリデータは YAGNI — 今後のチェック追加は関数に `_check_*` ヘルパーを追加すれば済む。

### D2: ValidationIssue に severity / code / message / reviewer_hint を持たせる

```python
@dataclass(frozen=True)
class ValidationIssue:
    severity: Literal["error", "warning", "info"]
    code: str            # 例: "missing_required_section", "no_references"
    message: str
    reviewer_hint: str | None = None
```

severity "error" は必須項目欠落・dangerous detail 検出、"warning" は出典なし主張・不確実性未記録、"info" は reviewer check point。

### D3: dangerous detail 検出はキーワードリスト（ルールベース）

攻撃手順・PoC を検出するために正規表現パターンリストを使用する。LLM 評価は M3 以降でよい。false positive は警告（warning）どまりとし、自動却下はしない（人間レビューフローで判断）。

### D4: `validation_hints` との統合

`DraftOutput.validation_hints` に含まれる `guardrail:*` タグは、チェック済みであることを示す情報として活用する。ただし存在しない場合でも checker は独立して実行する。

## Risks / Trade-offs

- [Risk] キーワードベース検出の false positive → Mitigation: severity を "warning" に留め、reviewer が最終判断する
- [Risk] 日本語・英語混在テキストのパターンマッチングが難しい → Mitigation: 代表的なパターンを英日両方でカバーし、unit test でスモークテストする
- [Trade-off] ルールベースは LLM 意味解析より精度が低いが、M1/M3 段階ではシンプルさを優先する
