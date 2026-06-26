"""CollectionCheckpoint / CollectionCheckpointStore のテスト。"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from spautopost.collection_checkpoint import CollectionCheckpoint, CollectionCheckpointStore


@pytest.mark.unit
def test_save_and_load_checkpoint(tmp_path: Path) -> None:
    store = CollectionCheckpointStore(tmp_path / "checkpoints.json")
    ts = datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)
    cp = CollectionCheckpoint(source_name="test-source", last_collected_at=ts)

    store.save(cp)
    loaded = store.load("test-source")

    assert loaded is not None
    assert loaded.source_name == "test-source"
    assert loaded.last_collected_at == ts


@pytest.mark.unit
def test_load_missing_file_returns_none(tmp_path: Path) -> None:
    store = CollectionCheckpointStore(tmp_path / "nonexistent.json")
    result = store.load("any-source")
    assert result is None


@pytest.mark.unit
def test_load_missing_source_name_returns_none(tmp_path: Path) -> None:
    store = CollectionCheckpointStore(tmp_path / "checkpoints.json")
    ts = datetime(2026, 6, 1, tzinfo=UTC)
    store.save(CollectionCheckpoint(source_name="source-a", last_collected_at=ts))

    result = store.load("source-b")
    assert result is None


@pytest.mark.unit
def test_overwrite_checkpoint(tmp_path: Path) -> None:
    store = CollectionCheckpointStore(tmp_path / "checkpoints.json")
    ts1 = datetime(2026, 6, 1, tzinfo=UTC)
    ts2 = datetime(2026, 6, 2, tzinfo=UTC)

    store.save(CollectionCheckpoint(source_name="src", last_collected_at=ts1))
    store.save(CollectionCheckpoint(source_name="src", last_collected_at=ts2))

    loaded = store.load("src")
    assert loaded is not None
    assert loaded.last_collected_at == ts2


@pytest.mark.unit
def test_multiple_sources(tmp_path: Path) -> None:
    store = CollectionCheckpointStore(tmp_path / "checkpoints.json")
    ts_a = datetime(2026, 6, 1, tzinfo=UTC)
    ts_b = datetime(2026, 6, 3, tzinfo=UTC)

    store.save(CollectionCheckpoint(source_name="a", last_collected_at=ts_a))
    store.save(CollectionCheckpoint(source_name="b", last_collected_at=ts_b))

    assert store.load("a") is not None
    assert store.load("a").last_collected_at == ts_a  # type: ignore[union-attr]
    assert store.load("b") is not None
    assert store.load("b").last_collected_at == ts_b  # type: ignore[union-attr]


@pytest.mark.unit
def test_checkpoint_requires_timezone() -> None:
    naive = datetime(2026, 6, 1)
    with pytest.raises(ValueError, match="timezone"):
        CollectionCheckpoint(source_name="src", last_collected_at=naive)


@pytest.mark.unit
def test_parent_directory_is_created(tmp_path: Path) -> None:
    nested = tmp_path / "subdir" / "checkpoints.json"
    store = CollectionCheckpointStore(nested)
    ts = datetime(2026, 6, 1, tzinfo=UTC)
    store.save(CollectionCheckpoint(source_name="src", last_collected_at=ts))
    assert nested.exists()


@pytest.mark.unit
def test_load_with_corrupt_file_returns_none(tmp_path: Path) -> None:
    path = tmp_path / "checkpoints.json"
    path.write_text("NOT JSON", encoding="utf-8")
    store = CollectionCheckpointStore(path)
    result = store.load("src")
    assert result is None


@pytest.mark.unit
def test_load_with_non_dict_json_returns_none(tmp_path: Path) -> None:
    path = tmp_path / "checkpoints.json"
    path.write_text("[]", encoding="utf-8")
    store = CollectionCheckpointStore(path)
    assert store.load("src") is None


@pytest.mark.unit
def test_load_with_non_string_value_returns_none(tmp_path: Path) -> None:
    import json as _json

    path = tmp_path / "checkpoints.json"
    path.write_text(_json.dumps({"src": 12345}), encoding="utf-8")
    store = CollectionCheckpointStore(path)
    assert store.load("src") is None


@pytest.mark.unit
def test_save_recovers_when_file_contains_non_dict_json(tmp_path: Path) -> None:
    path = tmp_path / "checkpoints.json"
    path.write_text("[]", encoding="utf-8")
    store = CollectionCheckpointStore(path)
    ts = datetime(2026, 6, 1, tzinfo=UTC)
    store.save(CollectionCheckpoint(source_name="src", last_collected_at=ts))
    loaded = store.load("src")
    assert loaded is not None
    assert loaded.last_collected_at == ts
