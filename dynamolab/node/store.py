from datetime import datetime, timezone
from typing import Optional


class KeyValueStore:
    def __init__(self):
        self.records = {}

    def _now_ms(self) -> int:
        return int(datetime.now(timezone.utc).timestamp() * 1000)

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def put(self, key: str, value: str, version: Optional[int] = None):
        record = {
            "key": key,
            "value": value,
            "version": version if version is not None else self._now_ms(),
            "deleted": False,
            "updated_at": self._now_iso()
        }

        existing = self.records.get(key)

        if existing is None or record["version"] >= existing["version"]:
            self.records[key] = record

        return self.records[key]

    def get(self, key: str):
        record = self.records.get(key)

        if record is None or record["deleted"]:
            return None

        return record

    def delete(self, key: str, version: Optional[int] = None):
        record = {
            "key": key,
            "value": None,
            "version": version if version is not None else self._now_ms(),
            "deleted": True,
            "updated_at": self._now_iso()
        }

        existing = self.records.get(key)

        if existing is None or record["version"] >= existing["version"]:
            self.records[key] = record

        return self.records[key]

    def debug(self):
        return {
            "count": len(self.records),
            "keys": list(self.records.keys()),
            "records": self.records
        }