## 1. OpenSpec artifacts

- [x] 1.1 Issue #7 / M1 / specs に沿った proposal / design / spec / tasks を作成する

## 2. Manual advisory parser

- [x] 2.1 YAML / JSON ファイルを読み込んで既存 `Advisory` DTO に変換する module を追加する
- [x] 2.2 required fields、CVE ID、JVN ID、URL、references、severity、urgency の validation を実装する
- [x] 2.3 valid input と invalid input の unit test を追加する

## 3. CLI dry-run preview

- [x] 3.1 `spautopost import-advisory <file>` コマンドを追加する
- [x] 3.2 `--dry-run` で normalized advisory preview を表示する test を追加する

## 4. Samples and docs

- [x] 4.1 `samples/advisories/` に YAML / JSON sample advisory を追加する
- [x] 4.2 README に manual advisory dry-run の使い方を追記する

## 5. Verification

- [x] 5.1 `ruff check .` / `ruff format --check src tests` / `mypy src` / `pytest --cov=spautopost --cov-report=term-missing` を実行する
- [x] 5.2 `openspec validate issue-7-implement-manual-advisory-input --strict` を実行する
