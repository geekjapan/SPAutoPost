## ADDED Requirements

### Requirement: idempotency_key の NOT NULL + UNIQUE 制約

システムは `publications.idempotency_key` を NOT NULL 列として定義し、その上に UNIQUE index（例: `ux_publications_idempotency_key`）を作成しなければならない（SHALL）。NOT NULL とすることで、PostgreSQL における複数 NULL のすり抜け（NULL は不等価扱い）を封鎖しなければならない（SHALL）。

#### Scenario: 同一 idempotency_key の重複挿入を拒否する
- **WHEN** 既存と同一の `idempotency_key` を持つ Publication を挿入しようとする
- **THEN** UNIQUE 制約違反となり、`StorageError` を送出する

#### Scenario: 異なる idempotency_key は両方保存される
- **WHEN** 異なる `idempotency_key` を持つ 2 件の Publication を作成する
- **THEN** 両方が保存される

### Requirement: create_if_absent による race-safe な作成

システムは `PublicationRepository.create_if_absent` を提供し、戻り値として `(publication, created: bool)` を返さなければならない（SHALL）。同一 `idempotency_key` で 2 回目以降の `create_if_absent` は新規作成せず既存行と `created=False` を返さなければならない（SHALL）。PostgreSQL backend は `ON CONFLICT` により race-safe に動作しなければならず（SHALL）、SQLite backend は単一ライター（逐次）として整合を保たなければならない（SHALL）。システムは `get_by_idempotency_key` による検索を提供しなければならない（SHALL）。

#### Scenario: 初回作成と再呼び出し
- **WHEN** 同一 `idempotency_key` で `create_if_absent` を 2 回呼び出す
- **THEN** 1 回目は `created=True`、2 回目は同じ行と `created=False` を返す

#### Scenario: idempotency_key で検索する
- **WHEN** 既存 Publication の `idempotency_key` で `get_by_idempotency_key` を呼び出す
- **THEN** 対応する Publication を返し、存在しない場合は `None` を返す

### Requirement: null / 空キーの境界拒否

システムは DTO / port の境界で `idempotency_key` が null または空文字（空白のみを含む）である Publication を拒否しなければならない（SHALL）。`idempotency_key` の導出ロジックは本 change のスコープ外であり、#20 が所有する。本 change は制約の強制と null/空キーの拒否のみを行う。

#### Scenario: null キーを拒否する
- **WHEN** `idempotency_key` が null の Publication を作成しようとする
- **THEN** 境界で `StorageError` を送出し、永続化しない

#### Scenario: 空キーを拒否する
- **WHEN** `idempotency_key` が空文字または空白のみの Publication を作成しようとする
- **THEN** 境界で `StorageError` を送出し、永続化しない
