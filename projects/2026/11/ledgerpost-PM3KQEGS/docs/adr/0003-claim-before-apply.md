# ADR 0003: Claim before apply

- Status: accepted
- Date: 2026-11-01

## Context

Two orderings are possible for idempotent posting. Apply first and record second: a crash between
the two steps replays the application. Claim first and apply second: a crash between the two steps
records an outcome that was never applied. Under concurrency, apply-first needs extra locking in
the engine to stop two threads both applying; claim-first inherits the serialization from the
store's atomic claim.

## Decision

`PostingEngine.post` claims the key with `put_if_absent` before touching the ledger. The claim
winner applies; losers return the recorded transaction as a replay. The engine holds no lock of
its own.

## Consequences

- Concurrent same-key posting cannot double-apply, by construction rather than by discipline
- The engine stays lock-free; `Ledger.apply` carries the only lock on the write path
- On a valid transaction the apply step cannot raise (construction already guaranteed balance), so
  the gap between claim and apply is negligible in-process
- For out-of-process durability the backend must make the claim and the posting one transaction;
  this is documented as a backend contract, not emulated here
