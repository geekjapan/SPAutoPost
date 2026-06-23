## ADDED Requirements

### Requirement: ストレージポート（repository Protocol）

システムは ORM 非依存の Python Protocol としてストレージポートを定義しなければならない（SHALL）。ポートは SourceRecord / Advisory / DraftPost / ReviewEvent / Publication / AuditEvent の各 repository を提供し、SQL 文字列・DB ドライバ・方言（PostgreSQL / SQLite）を呼び出し側へ露出してはならない（SHALL NOT）。ポートは少なくとも `migrate()` / `transaction()` / `close()` と、各 repository の `upsert` / `get` / `list`、append-only な ReviewEvent・AuditEvent の追記操作を備えなければならない（SHALL）。

#### Scenario: 呼び出し側が SQL や方言を import しない
- **WHEN** 業務ロジックがストレージポート経由でデータを読み書きする
- **THEN** 業務ロジックは SQL 文字列・psycopg・sqlite3 を直接 import せず、ポートの抽象メソッドのみを呼び出す

#### Scenario: 両バックエンドで同一の挙動を示す
- **WHEN** 同じポート操作を PostgreSQL backend と SQLite backend に対して実行する
- **THEN** 共有 contract suite が両バックエンドで同一の観測可能な結果を返す

### Requirement: frozen-dataclass DTO

システムはポートが受け渡すエンティティを frozen-dataclass の DTO として表現しなければならない（SHALL）。DTO は Secret（API key / token / client secret 等）を保持してはならない（SHALL NOT）。全ての timestamp フィールドは tz-aware UTC でなければならず（SHALL）、naive datetime を受け取った場合は境界で `StorageError` を送出しなければならない（SHALL）。`draft_posts.summary_for_users` / `draft_posts.impact` / `publications.idempotency_key` は非 Optional（必須）として型付けしなければならない（SHALL）。

#### Scenario: DTO は不変である
- **WHEN** DTO インスタンスのフィールドを変更しようとする
- **THEN** frozen-dataclass により代入が拒否される（FrozenInstanceError）

#### Scenario: naive datetime を境界で拒否する
- **WHEN** tz 情報の無い datetime を持つ DTO を upsert しようとする
- **THEN** `StorageError` を送出し、永続化しない

#### Scenario: 必須フィールドは Optional ではない
- **WHEN** DraftPost / Publication の型を検査する
- **THEN** `summary_for_users` / `impact` / `idempotency_key` は `None` を許容しない型として定義されている

### Requirement: get は不在時に Optional を返す

各 repository の `get()` は対象が存在しない場合に例外を送出せず `None`（`Optional[T]`）を返さなければならない（SHALL）。

#### Scenario: 存在しない ID の get
- **WHEN** 存在しない ID で `get()` を呼び出す
- **THEN** 例外を送出せず `None` を返す

#### Scenario: 存在する ID の get
- **WHEN** 既存レコードの ID で `get()` を呼び出す
- **THEN** 対応する DTO を返す

### Requirement: list は決定論的順序とページングを保証する

各 repository の `list()` は `created_at ASC, 主キー ASC` の決定論的順序で結果を返さなければならない（SHALL）。`list()` は `limit` と `offset` によるページングを受け付けなければならない（SHALL）。

#### Scenario: 決定論的な並び順
- **WHEN** 複数レコードを `list()` で取得する
- **THEN** `created_at` 昇順、同値の場合は主キー昇順で安定して並ぶ

#### Scenario: limit と offset で分割取得する
- **WHEN** `limit` と `offset` を指定して `list()` を呼び出す
- **THEN** 指定された範囲のレコードのみを決定論的順序で返す

### Requirement: StorageConfig からのバックエンド選択（factory）

システムは検証済み `StorageConfig`（provider / database_url / sqlite_path）からバックエンドを構築する factory を提供しなければならない（SHALL）。factory はアクティブ provider の必須フィールドを assert し（postgresql は `database_url`、sqlite は `sqlite_path`）、アクティブでない provider 向けのクロス provider フィールドが設定されている場合は警告またはエラーで顕在化しなければならない（SHALL）。psycopg は postgresql 分岐でのみ遅延 import しなければならず（SHALL）、未知の provider に対しては防御的に `StorageError` を送出しなければならない（SHALL）。

#### Scenario: provider に応じて正しいバックエンドを構築する
- **WHEN** `provider=postgresql` の `StorageConfig` を factory に渡す
- **THEN** PostgreSQL backend が構築され、`provider=sqlite` の場合は SQLite backend が構築される

#### Scenario: psycopg 不在環境でも SQLite が利用できる
- **WHEN** psycopg がインストールされていない環境で `provider=sqlite` のバックエンドを構築・import する
- **THEN** psycopg の ImportError を発生させずに SQLite backend が利用できる

#### Scenario: 必須フィールド欠如を assert する
- **WHEN** `provider=postgresql` だが `database_url` が未設定の `StorageConfig` を渡す
- **THEN** `StorageError` を送出し、不足フィールドを示す（Secret 値は含めない）

#### Scenario: 未知の provider を防御的に拒否する
- **WHEN** 未知の `provider` 値を持つ `StorageConfig` を factory に渡す
- **THEN** `StorageError` を送出する

### Requirement: 新バックエンドの追加が呼び出し側を改修しない

ストレージポートは、新しい DB バックエンドが Protocol と共有 contract suite を満たす限り、業務ロジック（呼び出し側）を改修せずに差し替え可能でなければならない（SHALL）。

#### Scenario: Protocol 充足で差し替え可能
- **WHEN** Protocol と contract suite を満たす新バックエンドを factory に追加する
- **THEN** 業務ロジックのコードを変更せずに新バックエンドへ切り替えられる
