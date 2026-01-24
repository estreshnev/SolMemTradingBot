from collections import OrderedDict
from typing import Generic, TypeVar

T = TypeVar("T")


class IdempotencyStore(Generic[T]):
    """In-memory LRU store for deduplication by key.

    For production, swap with Redis-backed implementation.
    """

    def __init__(self, max_size: int = 10000):
        self._max_size = max_size
        self._store: OrderedDict[str, T] = OrderedDict()

    def contains(self, key: str) -> bool:
        """Check if key exists (and refresh its position)."""
        if key in self._store:
            self._store.move_to_end(key)
            return True
        return False

    def add(self, key: str, value: T) -> None:
        """Add key-value pair, evicting oldest if at capacity."""
        if key in self._store:
            self._store.move_to_end(key)
            return

        self._store[key] = value

        while len(self._store) > self._max_size:
            self._store.popitem(last=False)

    def get(self, key: str) -> T | None:
        """Get value by key, or None if not found."""
        return self._store.get(key)

    def clear(self) -> None:
        """Clear all entries."""
        self._store.clear()

    def __len__(self) -> int:
        return len(self._store)
