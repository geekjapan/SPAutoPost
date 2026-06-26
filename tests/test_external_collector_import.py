"""external_collector_import のテスト。"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from spautopost.external_collector_import import (
    ExternalCollectorImportError,
    FileExternalCollectorImporter,
    ImportResult,
    import_from_file,
)
from spautopost.storage.sqlite_backend import build_sqlite_storage

_NOW = datetime(2026, 6, 26, 9, 0, 0, tzinfo=UTC)

_VALID_ADVISORY = {
    "title": "Test Advisory",
    "summary": "A test advisory",
    "severity": "high",
    "cve_ids": ["CVE-2026-0001"],
    "references": [{"label": "Test Ref", "url": "https://example.com/advisory", "type": "vendor"}],
}

_VALID_PAYLOAD = {
    "schema_version": "1.0",
    "producer": "test-collector",
    "generated_at": "2026-06-26T09:00:00Z",
    "advisories": [_VALID_ADVISORY],
}


def _make_json(tmp_path: Path, data: object, name: str = "import.json") -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def _make_yaml(tmp_path: Path, data: object, name: str = "import.yaml") -> Path:
    path = tmp_path / name
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    return path


def _build_storage(tmp_path: Path) -> object:
    storage = build_sqlite_storage(tmp_path / "test.sqlite3")
    storage.migrate()
    return storage


@pytest.mark.unit
def test_valid_json_import(tmp_path: Path) -> None:
    path = _make_json(tmp_path, _VALID_PAYLOAD)
    storage = _build_storage(tmp_path)
    result = import_from_file(path, storage, now=_NOW)  # type: ignore[arg-type]

    assert result.accepted_count == 1
    assert result.rejected_count == 0
    assert len(result.advisories) == 1
    assert result.advisories[0].title == "Test Advisory"


@pytest.mark.unit
def test_valid_yaml_import(tmp_path: Path) -> None:
    path = _make_yaml(tmp_path, _VALID_PAYLOAD)
    storage = _build_storage(tmp_path)
    result = import_from_file(path, storage, now=_NOW)  # type: ignore[arg-type]

    assert result.accepted_count == 1
    assert result.rejected_count == 0


@pytest.mark.unit
def test_source_type_is_external_collector(tmp_path: Path) -> None:
    path = _make_json(tmp_path, _VALID_PAYLOAD)
    storage = _build_storage(tmp_path)
    result = import_from_file(path, storage, now=_NOW)  # type: ignore[arg-type]

    assert result.source_records[0].source_type == "external_collector"
    assert result.source_records[0].source_name == "test-collector"


@pytest.mark.unit
def test_advisory_has_external_collector_tag(tmp_path: Path) -> None:
    path = _make_json(tmp_path, _VALID_PAYLOAD)
    storage = _build_storage(tmp_path)
    result = import_from_file(path, storage, now=_NOW)  # type: ignore[arg-type]

    tags = result.advisories[0].tags
    assert "external_collector" in tags
    assert "producer:test-collector" in tags


@pytest.mark.unit
def test_missing_schema_version_raises(tmp_path: Path) -> None:
    data = {**_VALID_PAYLOAD}
    del data["schema_version"]
    path = _make_json(tmp_path, data)
    storage = _build_storage(tmp_path)
    with pytest.raises(ExternalCollectorImportError, match="schema_version"):
        import_from_file(path, storage, now=_NOW)  # type: ignore[arg-type]


@pytest.mark.unit
def test_missing_producer_raises(tmp_path: Path) -> None:
    data = {**_VALID_PAYLOAD}
    del data["producer"]
    path = _make_json(tmp_path, data)
    storage = _build_storage(tmp_path)
    with pytest.raises(ExternalCollectorImportError, match="producer"):
        import_from_file(path, storage, now=_NOW)  # type: ignore[arg-type]


@pytest.mark.unit
def test_missing_generated_at_raises(tmp_path: Path) -> None:
    data = {**_VALID_PAYLOAD}
    del data["generated_at"]
    path = _make_json(tmp_path, data)
    storage = _build_storage(tmp_path)
    with pytest.raises(ExternalCollectorImportError, match="generated_at"):
        import_from_file(path, storage, now=_NOW)  # type: ignore[arg-type]


@pytest.mark.unit
def test_missing_advisories_raises(tmp_path: Path) -> None:
    data = {**_VALID_PAYLOAD}
    del data["advisories"]
    path = _make_json(tmp_path, data)
    storage = _build_storage(tmp_path)
    with pytest.raises(ExternalCollectorImportError, match="advisories"):
        import_from_file(path, storage, now=_NOW)  # type: ignore[arg-type]


@pytest.mark.unit
def test_advisory_with_empty_title_is_rejected(tmp_path: Path) -> None:
    bad = {**_VALID_ADVISORY, "title": "  "}
    data = {**_VALID_PAYLOAD, "advisories": [bad]}
    path = _make_json(tmp_path, data)
    storage = _build_storage(tmp_path)
    result = import_from_file(path, storage, now=_NOW)  # type: ignore[arg-type]

    assert result.accepted_count == 0
    assert result.rejected_count == 1
    assert "title" in result.rejected_records[0].reason


@pytest.mark.unit
def test_advisory_without_references_is_rejected(tmp_path: Path) -> None:
    bad = {**_VALID_ADVISORY, "references": []}
    data = {**_VALID_PAYLOAD, "advisories": [bad]}
    path = _make_json(tmp_path, data)
    storage = _build_storage(tmp_path)
    result = import_from_file(path, storage, now=_NOW)  # type: ignore[arg-type]

    assert result.rejected_count == 1
    assert "references" in result.rejected_records[0].reason


@pytest.mark.unit
def test_mixed_valid_and_invalid_advisories(tmp_path: Path) -> None:
    bad = {**_VALID_ADVISORY, "title": ""}
    good = _VALID_ADVISORY
    data = {**_VALID_PAYLOAD, "advisories": [bad, good]}
    path = _make_json(tmp_path, data)
    storage = _build_storage(tmp_path)
    result = import_from_file(path, storage, now=_NOW)  # type: ignore[arg-type]

    assert result.accepted_count == 1
    assert result.rejected_count == 1


@pytest.mark.unit
def test_invalid_cve_id_is_rejected(tmp_path: Path) -> None:
    bad = {**_VALID_ADVISORY, "cve_ids": ["INVALID-ID"]}
    data = {**_VALID_PAYLOAD, "advisories": [bad]}
    path = _make_json(tmp_path, data)
    storage = _build_storage(tmp_path)
    result = import_from_file(path, storage, now=_NOW)  # type: ignore[arg-type]

    assert result.rejected_count == 1


@pytest.mark.unit
def test_invalid_severity_is_rejected(tmp_path: Path) -> None:
    bad = {**_VALID_ADVISORY, "severity": "extreme"}
    data = {**_VALID_PAYLOAD, "advisories": [bad]}
    path = _make_json(tmp_path, data)
    storage = _build_storage(tmp_path)
    result = import_from_file(path, storage, now=_NOW)  # type: ignore[arg-type]

    assert result.rejected_count == 1


@pytest.mark.unit
def test_malformed_json_raises(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("NOT JSON", encoding="utf-8")
    storage = _build_storage(tmp_path)
    with pytest.raises(ExternalCollectorImportError):
        import_from_file(path, storage, now=_NOW)  # type: ignore[arg-type]


@pytest.mark.unit
def test_file_external_collector_importer_is_port(tmp_path: Path) -> None:
    """FileExternalCollectorImporter が ExternalCollectorImportPort の duck typing を満たす。"""
    path = _make_json(tmp_path, _VALID_PAYLOAD)
    importer = FileExternalCollectorImporter(path=path)
    assert hasattr(importer, "import_advisories")
    assert callable(importer.import_advisories)


@pytest.mark.unit
def test_idempotent_import(tmp_path: Path) -> None:
    """同じファイルを 2 回 import しても advisory が重複しない（upsert）。"""
    path = _make_json(tmp_path, _VALID_PAYLOAD)
    storage = _build_storage(tmp_path)

    result1 = import_from_file(path, storage, now=_NOW)  # type: ignore[arg-type]
    result2 = import_from_file(path, storage, now=_NOW)  # type: ignore[arg-type]

    assert result1.accepted_count == 1
    assert result2.accepted_count == 1
    # upsert なので同じ advisory_id が上書きされ、合計 1 件のみ残る
    all_advisories = storage.advisories.list()  # type: ignore[union-attr]
    ids = {a.advisory_id for a in all_advisories}
    assert len(ids) == 1


@pytest.mark.unit
def test_import_result_is_frozen() -> None:
    result = ImportResult(
        accepted_count=0,
        rejected_count=0,
        rejected_records=(),
        source_records=(),
        advisories=(),
    )
    with pytest.raises(AttributeError):
        result.accepted_count = 1  # type: ignore[misc]
