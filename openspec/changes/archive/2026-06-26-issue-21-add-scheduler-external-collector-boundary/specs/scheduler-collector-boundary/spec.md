## ADDED Requirements

### Requirement: manual run と scheduled run の実行方式が RunMode で区別される

システムは `RunMode` として `"manual"` または `"scheduled"` を明示的に表現しなければならない（SHALL）。
`JobContext` は RunMode を持ち、`job_entrypoint` はジョブ実行時に RunMode を付与しなければならない（MUST）。

#### Scenario: manual run の RunMode が正しい
- **WHEN** `job_entrypoint.main(["dry-run"])` を呼び出す
- **THEN** `JobContext.run_mode` が `"manual"` である

#### Scenario: scheduled run の RunMode が正しい
- **WHEN** `job_entrypoint.main(["collect"])` を呼び出す
- **THEN** `JobContext.run_mode` が `"scheduled"` である

### Requirement: 差分収集のチェックポイントが保存・復元できる

システムは最終収集時刻を `CollectionCheckpoint` として永続化し、次回収集時に読み込めなければならない（SHALL）。

#### Scenario: チェックポイントの保存と読み込み
- **WHEN** `CollectionCheckpointStore.save()` でチェックポイントを保存する
- **THEN** 同じ path から `CollectionCheckpointStore.load()` で復元できる
- **AND** `last_collected_at` が一致する

#### Scenario: チェックポイントが存在しない場合
- **WHEN** チェックポイントファイルが存在しない状態で `load()` を呼び出す
- **THEN** `None` を返す（例外を投げない）

### Requirement: external collector からの file import が schema 検証を通る

システムは外部 collector から受け取った JSON/YAML ファイルを import する前に schema 検証を実行しなければならない（MUST）。不正なデータは fail fast で reject し、ログに出力する。

必須フィールド: `schema_version`, `producer`, `generated_at`, `advisories`。
各 advisory には最低限 `title` と 1 件以上の `references` が必要。

#### Scenario: 有効なファイルを import する
- **WHEN** 有効な import ファイルを `import_from_file()` に渡す
- **THEN** `ImportResult.accepted_count` が 0 より大きい
- **AND** `ImportResult.rejected_count` が 0 である

#### Scenario: 必須フィールドが欠けているファイルを reject する
- **WHEN** `schema_version` または `producer` が欠けているファイルを渡す
- **THEN** `ExternalCollectorImportError` が発生する

#### Scenario: advisory の title が空のレコードを reject する
- **WHEN** advisory の `title` が空文字のレコードを含むファイルを渡す
- **THEN** そのレコードは `ImportResult.rejected_count` に計上される
- **AND** 他の有効なレコードは取り込まれる

### Requirement: import された advisory は StoragePort を経由して保存される

import 境界で schema 検証を通過した advisory は `SourceRecord` と `Advisory` DTO に変換され、`StoragePort` 経由で保存されなければならない（SHALL）。Secret はログにもコードにも出力しない。

#### Scenario: import 後にストレージへ保存される
- **WHEN** 有効な import ファイルを処理する
- **THEN** `SourceRecord.source_type` が `"external_collector"` である
- **AND** `Advisory` が StoragePort の `advisories.upsert()` で保存される

### Requirement: 失敗時に指数バックオフで retry できる

システムは `with_retry(fn, config)` で失敗した callable を指数バックオフで再試行できなければならない（SHALL）。最大試行回数を超えた場合は最後の例外を再発生させる。

#### Scenario: retry が成功する
- **WHEN** callable が 2 回失敗してから成功する（max_attempts=3）
- **THEN** `with_retry` は成功した戻り値を返す

#### Scenario: 全試行が失敗する
- **WHEN** callable が max_attempts 回すべて失敗する
- **THEN** 最後の例外が再発生する

### Requirement: import schema が docs に記載されている

`docs/specs/external-collector-boundary.md` の import schema は、実装と整合した具体的な JSON 例を含まなければならない（SHALL）。

#### Scenario: docs の schema が実装と一致する
- **WHEN** `docs/specs/external-collector-boundary.md` を参照する
- **THEN** `schema_version`, `producer`, `generated_at`, `advisories` の必須性が明記されている
- **AND** advisory の最小フィールドが具体例つきで示されている

### Requirement: crawler 分離後も SPAutoPost 本体の変更が最小で済む

`ExternalCollectorImportPort` Protocol を定義し、file import 実装とは切り離す。将来の API / queue 実装者は Protocol を実装するだけで SPAutoPost の呼び出し側を変更しなくてよい（SHALL）。

#### Scenario: 新しい import 方式を追加する
- **WHEN** API import の実装者が `ExternalCollectorImportPort` を実装する
- **THEN** `ExternalCollectorImporter` を差し替えるだけで SPAutoPost 本体のコードを変更しなくてよい
