## ADDED Requirements

### Requirement: Manual advisory input parsing

システムは YAML または JSON の手動入力ファイルから `Advisory` を生成しなければならない（SHALL）。入力は `title`、`summary`、`references` を必須項目として扱わなければならない（SHALL）。

#### Scenario: YAML input から Advisory を生成する
- **WHEN** ユーザーが有効な YAML advisory file を指定する
- **THEN** システムは既存 `Advisory` model の instance を生成する

#### Scenario: JSON input から Advisory を生成する
- **WHEN** ユーザーが有効な JSON advisory file を指定する
- **THEN** システムは既存 `Advisory` model の instance を生成する

#### Scenario: 必須項目不足を検出する
- **WHEN** 入力が `title`、`summary`、または `references` を欠く
- **THEN** システムは validation error を返し、`Advisory` を生成しない

### Requirement: Manual advisory validation

システムは手動入力の CVE ID、JVN ID、URL、severity、urgency、references を検証しなければならない（SHALL）。無効な値を検出した場合は、どの項目が問題かを示す validation error を返さなければならない（SHALL）。

#### Scenario: CVE ID / JVN ID を検証する
- **WHEN** 入力に形式不正な CVE ID または JVN ID が含まれる
- **THEN** システムは validation error を返す

#### Scenario: URL を検証する
- **WHEN** 入力の reference URL が HTTP / HTTPS URL として不正である
- **THEN** システムは validation error を返す

#### Scenario: severity / urgency を検証する
- **WHEN** 入力の severity または urgency が許可値以外である
- **THEN** システムは validation error を返す

#### Scenario: references を検証する
- **WHEN** 入力の references が空、または label / url / type を欠く
- **THEN** システムは validation error を返す

### Requirement: Dry-run preview for manual advisory input

システムは CLI から手動入力ファイルを dry-run で読み込み、正規化結果を確認できなければならない（SHALL）。dry-run preview は SharePoint 投稿、外部 API 呼び出し、永続化を行ってはならない（SHALL NOT）。

#### Scenario: dry-run で読み込み結果を確認する
- **WHEN** ユーザーが `spautopost --dry-run import-advisory <file>` を実行する
- **THEN** システムは normalized advisory preview を表示し、外部 API 呼び出しと投稿を行わない

### Requirement: Sample manual advisory files

システムは手動入力のサンプル advisory file を提供しなければならない（SHALL）。

#### Scenario: sample advisory が存在する
- **WHEN** 開発者が `samples/advisories/` を確認する
- **THEN** YAML または JSON の sample advisory file が存在する
