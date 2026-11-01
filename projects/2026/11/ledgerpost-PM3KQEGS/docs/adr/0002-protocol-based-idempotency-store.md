# ADR 0002: Protocol-based idempotency store with a process-local reference

- Status: accepted
- Date: 2026-11-01

## Context

The posting engine needs somewhere to record claims, but the right storage differs per deployment:
in-process dictionaries for tests and single-process services, relational rows for durable
systems. Shipping one hard-coded backend would couple the core to a dependency and a schema.

## Decision

The engine depends on a two-method `IdempotencyStore` protocol: `get(key)` and `put_if_absent(key,
value)`. Implementations must make `put_if_absent` atomic. The package ships
`MemoryIdempotencyStore`, a lock-guarded dictionary, as the reference and test backend. Durable
backends are the deployer's code; the documentation requires the key table to share a transaction
boundary with the ledger it guards.

## Consequences

- The core stays dependency-free and testable without infrastructure
- Restart-safe exactly-once is a property of the backend, not of this package; the README and
  architecture notes say so explicitly rather than implying it
- Alternate stores can be validated against the same race tests the engine uses
