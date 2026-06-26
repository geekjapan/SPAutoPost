"""差分収集チェックポイント: 最終収集時刻をファイルに永続化する。

正本: openspec/changes/issue-21-add-scheduler-external-collector-boundary/

責務: source ごとの最終収集時刻を JSON ファイルに保存・読み込みする。
非責務: StoragePort への保存、並行実行制御（単一プロセス前提）。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True)
class CollectionCheckpoint:
    """差分収集の基点となる最終収集時刻。"""

    source_name: str
    last_collected_at: datetime

    def __post_init__(self) -> None:
        ts = self.last_collected_at
        if ts.tzinfo is None or ts.utcoffset() is None:
            raise ValueError("last_collected_at must include timezone")


class CollectionCheckpointStore:
    """ファイルベースのチェックポイントストア。"""

    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self, source_name: str) -> CollectionCheckpoint | None:
        """チェックポイントを読み込む。ファイルが存在しない場合は None を返す。"""
        if not self._path.exists():
            return None
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
        if not isinstance(data, dict):
            return None
        raw = data.get(source_name)
        if not isinstance(raw, str):
            return None
        try:
            ts = datetime.fromisoformat(raw)
        except ValueError:
            return None
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        return CollectionCheckpoint(source_name=source_name, last_collected_at=ts.astimezone(UTC))

    def save(self, checkpoint: CollectionCheckpoint) -> None:
        """チェックポイントを保存する。既存のエントリを上書きする。"""
        data: dict[str, str] = {}
        if self._path.exists():
            try:
                loaded = json.loads(self._path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    data = loaded
            except (json.JSONDecodeError, OSError):
                pass
        data[checkpoint.source_name] = checkpoint.last_collected_at.isoformat()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
