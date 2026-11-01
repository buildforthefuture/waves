"""The posting engine: at-least-once requests in, exactly-once postings out."""

from __future__ import annotations

from .errors import InvalidRequestKeyError
from .ledger import Ledger
from .model import Outcome, Transaction
from .store import IdempotencyStore

MAX_KEY_LEN = 256


class PostingEngine:
    """Claims a request key, then applies the transaction at most once.

    The claim happens before any ledger mutation: whichever call wins
    :meth:`IdempotencyStore.put_if_absent` applies the transaction and
    reports a fresh outcome; every other call with the same key receives
    the recorded transaction flagged as a replay.  Delivery systems that
    retry, resending webhooks, and re-run jobs therefore cannot post a
    business event twice.
    """

    def __init__(self, ledger: Ledger, store: IdempotencyStore) -> None:
        self._ledger = ledger
        self._store = store

    def post(self, request_key: str, transaction: Transaction) -> Outcome:
        """Post ``transaction`` under ``request_key``.

        The first call applies the transaction and returns an outcome
        with ``replayed=False``.  Any later call with the same key
        applies nothing and returns the recorded transaction with
        ``replayed=True``.  Different keys may post equal transactions;
        each key posts at most once.
        """
        if not isinstance(request_key, str) or not request_key:
            raise InvalidRequestKeyError("request key must be a non-empty string")
        if len(request_key) > MAX_KEY_LEN:
            raise InvalidRequestKeyError(f"request key longer than {MAX_KEY_LEN} characters")
        if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in request_key):
            raise InvalidRequestKeyError("request key must not contain control characters")

        claimed, winner = self._store.put_if_absent(
            request_key, Outcome(transaction=transaction, replayed=False)
        )
        if claimed:
            self._ledger.apply(transaction)
            return Outcome(transaction=transaction, replayed=False)
        return Outcome(transaction=winner.transaction, replayed=True)
