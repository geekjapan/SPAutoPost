## ADDED Requirements

### Requirement: Admin API は Entra ID 認証済み principal を必須にする

Admin API は、read / write を問わず、すべての保護対象 endpoint に対し Entra ID 認証済みの管理者 principal を必須にしなければならない（SHALL）。認証済み principal を解決できない要求にはドメインデータを返さず、AdminCommand も作成してはならず（MUST NOT）、authentication error（401）を返さなければならない（SHALL）。

#### Scenario: 未認証 read を拒否する
- **WHEN** 認証済み principal が無い状態で `GET /api/drafts` を要求する
- **THEN** Admin API は DraftPost data を返さず authentication error（401）を返す

#### Scenario: 未認証 write を拒否する
- **WHEN** 認証済み principal が無い状態で write endpoint（approve / reject / edit / publish-request）を要求する
- **THEN** Admin API は AdminCommand を作成せず authentication error（401）を返す

### Requirement: 認証済み principal を Entra ID claim から導出する

Admin API は、認証済み principal の id / principal name / display name（取得可能な場合）と role 集合を、Entra ID の認証結果（claim）から導出しなければならない（SHALL）。principal id を導出できない場合は認証失敗として扱わなければならない（SHALL）。

#### Scenario: Entra principal を解決する
- **WHEN** Entra ID 認証済みの要求が届く
- **THEN** Admin API は principal id / principal name / display name / roles を claim から解決し、後続の認可と audit に利用する

#### Scenario: principal id を欠く要求を拒否する
- **WHEN** 認証済みを示す入力に principal id 相当の値が含まれない
- **THEN** Admin API は principal を確立せず authentication error（401）を返す

### Requirement: Entra role/group を Admin role へ mapping する

Admin API は、Entra ID の app role または group claim を viewer / reviewer / approver / publisher / admin の最小 role へ mapping しなければならない（SHALL）。mapping 対象外の値を Admin role として採用してはならない（MUST NOT）。有効な Admin role を1つも持たない principal の保護対象要求は authorization error（403）を返さなければならない（SHALL）。

#### Scenario: role claim を Admin role に対応づける
- **WHEN** 認証済み principal が approver に対応する Entra role/group を持つ
- **THEN** Admin API はその principal を approver として扱い、approve / reject を許可する

#### Scenario: role を持たない principal を拒否する
- **WHEN** 認証済みだが Admin role に mapping される role/group を1つも持たない principal が保護対象 endpoint を要求する
- **THEN** Admin API は要求を拒否し authorization error（403）を返す

### Requirement: 管理者操作の user principal を AuditEvent へ伝播し secret を出さない

Admin API は、state-changing な管理者操作について、認証済み user principal（id、可能なら name / display / roles）を、Python core が AuditEvent を記録できる形で AdminCommand へ伝播しなければならない（SHALL）。access token / refresh token / id token raw / cookie / authorization header を audit 記録・ログへ出力してはならない（MUST NOT）。

#### Scenario: 管理者操作に user principal を紐づける
- **WHEN** 認証済み管理者が approve を要求する
- **THEN** enqueue される AdminCommand は要求元 user principal id を伴い、Python core はそれを AuditEvent の actor として記録できる

#### Scenario: secret を audit へ出さない
- **WHEN** 管理者操作を処理する
- **THEN** token / cookie / authorization header は AuditEvent にもログにも記録されない

### Requirement: dev 認証代替は明示設定でのみ有効で本番では無効

Admin API は、local dev 用の認証代替（dev principal/role 注入）を、明示的な opt-in 設定でのみ有効化しなければならない（SHALL）。既定（設定なし）は Entra ID 認証必須の本番安全側でなければならない（SHALL）。dev 認証代替と production 指定が同時に与えられた場合は起動を失敗させ（fail closed）、dev 代替を本番で有効にしてはならない（MUST NOT）。

#### Scenario: 既定は Entra 認証必須
- **WHEN** 認証 mode の明示設定が無い状態で Admin API を起動する
- **THEN** Admin API は Entra ID 認証済み principal を要求し、dev header principal を受け付けない

#### Scenario: dev 代替の本番有効化を fail closed にする
- **WHEN** dev 認証代替が production 指定と同時に設定される
- **THEN** Admin API は起動を失敗させ、要求を処理しない

### Requirement: Admin login と Graph service 認証を分離する

Admin API/UI のログイン認証（Entra ID user authentication）と、SPAutoPost が Microsoft Graph を呼び出す service 認証は分離して扱わなければならない（SHALL）。管理者のログイン token を、定期 job / publisher の Graph 呼び出し認証へ流用してはならない（MUST NOT）。

#### Scenario: login token を Graph job に流用しない
- **WHEN** 管理者が Entra ID でログインして approve する
- **THEN** その user の login/delegated token は定期 job の Graph 呼び出し認証に利用されない
