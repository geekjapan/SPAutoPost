## Context

Issue #25 は M1 の deployment skeleton に属する。既存実装には CLI / batch entrypoint（`spautopost`）、config loader（`config/<env>.yml` + `env:` secret 参照）、sqlite / postgresql storage、deterministic な sample-source job がある。よって新しい runtime framework は不要で、既存 CLI を Container Apps Jobs の command として呼べる薄い層と、設定分離の例示があればよい。

## Goals / Non-Goals

**Goals:**

- container image build 前提（Python core）を確立し、CLI を job entrypoint に固定する。
- scheduled job から CLI command を呼べる構成にする（dry-run / collect / generate / publish-approved）。
- local（sqlite / development）と hosted（postgresql / production / `env:` 参照）の設定を分離して例示する。
- Secret は env / secret reference のみで扱い、値はリポジトリに置かない。

**Non-Goals:**

- 本番 Azure リソース作成、本番 Secret 登録、本格 IaC（Bicep）完成、deploy automation。
- 本格 monitoring / Log Analytics、本格 Admin UI、本番 DB 確定。

## Decisions

- **Job entrypoint は薄い Python wrapper（`spautopost-job <job-name>`）**。Container Apps Jobs は job 名 1 つを args に渡し、wrapper が安全な CLI argv にマッピングする。安全方針（hosted は dry-run 既定、publish は常に human gate）をドキュメントだけでなくコードに置けるため、shell より wrapper を選ぶ。pytest でそのまま検証できる。
- **`publish-approved` は guarded stub**。CLI に publish command は無く、AGENTS.md でも publish は常に人間承認。wrapper は publish-approved を受けたら一切 publish せず専用 exit code で終了し、未実装かつ human-gated であることを明示する。
- **collect と generate は M1 では同じ sample-source pipeline に解決する**。M1 の Python core は collect+generate を 1 パスで行うため、別 command が無い。別経路が必要になったら CLI command 追加で分離する（job 名と wrapper マッピングは将来差し替え可能に保つ）。
- **image は hosted config 例を `config/default.yml` として焼き込む**。config loader は `config/default.yml` を基底に読むため、image を単体で起動可能にする最小構成として hosted 例を default に置く。Secret は `env:` 参照のままで、値は焼き込まない。
- **local / hosted 分離はファイルで明示**。local は既存 `config.example.yml`（sqlite / development）、hosted は `deploy/config.hosted.example.yml`（postgresql / production）。どちらも Secret は `env:` 参照のみ。
- **IaC は参照マニフェスト止まり**。`deploy/jobs.example.yaml` は Container Apps Jobs の command / schedule / secretRef 形を示す skeleton であり、Bicep / ARM の本実装は別 Issue とする（本格 IaC は非対象）。

## Risks / Trade-offs

- collect と generate が同一 pipeline → job 分割の意味は M1 では限定的。job 名は将来の分離を見越して別々に定義し、マッピングのみ共有する。
- image に hosted 例を焼き込む → 運用では実 config を mount / 上書きする前提。Secret は env のみで、焼き込み値は非機密のみ。
- publish-approved が常に no-op で終了 → scheduled 実行すると毎回非ゼロ終了になり得る。M1 は monitoring 非対象のため許容し、jobs マニフェストでは manual trigger（無効化）として記述する。
