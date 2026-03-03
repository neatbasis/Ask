from __future__ import annotations

from ha_ask.storage.base import StorageBackend
from ha_ask.storage.memory import InMemoryStorageBackend
from ha_ask.storage.sqlite import SQLiteStorageBackend

_backend: StorageBackend = InMemoryStorageBackend()


def get_storage_backend() -> StorageBackend:
    return _backend


def set_storage_backend(backend: StorageBackend) -> None:
    global _backend
    _backend = backend


def reset_storage_backend() -> None:
    set_storage_backend(InMemoryStorageBackend())


__all__ = [
    "StorageBackend",
    "InMemoryStorageBackend",
    "SQLiteStorageBackend",
    "get_storage_backend",
    "set_storage_backend",
    "reset_storage_backend",
]
