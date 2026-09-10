"""Data plane facade: cache + vectors + blobs."""

from eci.agents.memory import VectorMemory
from eci.data.blobs import BlobStore
from eci.data.cache import Cache

__all__ = ["Cache", "BlobStore", "VectorMemory", "DataPlane"]


class DataPlane:
    name = "data"

    def __init__(self, cache_capacity: int = 1024) -> None:
        self.cache = Cache(capacity=cache_capacity)
        self.vectors = VectorMemory()
        self.blobs = BlobStore()

    def start(self) -> None: ...
    def stop(self) -> None: ...
    def health(self) -> dict:
        return {"ok": True, "cache": self.cache.stats(),
                "vectors": len(self.vectors), "blobs": len(self.blobs)}
