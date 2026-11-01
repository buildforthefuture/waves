"""Idempotency stores: the protocol backends implement and a reference store."""

from __future__ import annotations

import threading
from typing import Protocol

from .model import Outcome


class IdempotencyStore(Protocol):
    """Storage contract the posting engine relies on.

    Implementations must make :meth:`put_if_absent` atomic: when two
    callers race on the same key, exactly one receives ``True`` and the
    other receives the value the winner stored.  A durable backend owns
    the transactional boundary that keeps stored keys and ledger rows in
    step; see the architecture notes for the details.
    """

    def get(self, key: str) -> Outcome | None:
        """Return the outcome recorded for ``key``, or ``None``."""
        ...

    def put_if_absent(self, key: str, value: Outcome) -> tuple[bool, Outcome]:
        """Record ``value`` under ``key`` if the key is free.

        Returns ``(True, value)`` when this call claimed the key and
        ``(False, winner)`` when an outcome was already recorded.
        """
        ...


class MemoryIdempotencyStore:
    """Thread-safe in-memory reference implementation.

    Keys live for the lifetime of the process.  A deployment that must
    survive restarts supplies its own implementation backed by the same
    database as the ledger, inside one transaction boundary.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._values: dict[str, Outcome] = {}

    def get(self, key: str) -> Outcome | None:
        with self._lock:
            return self._values.get(key)

    def put_if_absent(self, key: str, value: Outcome) -> tuple[bool, Outcome]:
        with self._lock:
            existing = self._values.get(key)
            if existing is not None:
                return False, existing
            self._values[key] = value
            return True, value

    def __len__(self) -> int:
        with self._lock:
            return len(self._values)
