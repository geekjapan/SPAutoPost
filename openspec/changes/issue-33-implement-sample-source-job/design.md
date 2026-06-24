## Context

Issue #33 は M1 Phase 2 の Python core source and draft pipeline に属する。
既存実装には `SourceRecord` / `Advisory` / `DraftPost` DTO、`StoragePort`、deterministic `MockLLMProvider` があるため、新しい adapter framework や crawler は不要。

## Goals / Non-Goals

**Goals:**

- deterministic sample source から投稿候補を取得する。
- source metadata を `SourceRecord` として保存し、同じ候補から `Advisory` を作る。
- 既存 LLM provider interface に `DraftInput` を渡し、`DraftPost` を生成・保存する。
- scheduled job skeleton として CLI からも呼べる。

**Non-Goals:**

- 実 crawler、実外部 API、実 SharePoint publish は実装しない。
- 高精度 dedupe や本格 adapter interface は追加しない。
- 認証、Secret、外部アカウント操作は扱わない。

## Decisions

- sample source はコード内 fixture とする。外部通信なしで M1 縦串を検証でき、Issue の非対象範囲に入らない。
- job は `run_sample_source_job(storage, provider, now=None)` の小さい関数に集約する。CLI は storage/provider を組み立ててこの関数を呼ぶだけにする。
- `SourceRecord.raw_hash` と内部 ID は fixture payload から deterministic に作る。高精度 dedupe ではなく、同じ sample の再実行で upsert が同じ行に落ちる最小 idempotency とする。
- draft generation は既存 `MockLLMProvider` / template を使う。新しい provider や prompt は追加しない。

## Risks / Trade-offs

- sample fixture は本番 source の網羅性を示さない → 本格 adapter は別 Issue で扱う。
- ID は sample payload hash ベースのみ → 複数 source や高度な重複判定が必要になったら adapter / normalization 側で拡張する。
- CLI は draft 生成までで publish しない → human review / publish gate は後続 Issue の責務とする。
