import time
from dataclasses import dataclass
from typing import Any, Dict, Tuple


@dataclass
class TTLCache:
    ttl_seconds: int
    _store: Dict[str, Tuple[float, Any]]

    def __init__(self, ttl_seconds: int):
        self.ttl_seconds = ttl_seconds
        self._store = {}

    def get(self, key: str):
        item = self._store.get(key)
        if not item:
            return None
        exp, val = item
        if time.time() > exp:
            self._store.pop(key, None)
            return None
        return val

    def set(self, key: str, value: Any):
        self._store[key] = (time.time() + self.ttl_seconds, value)