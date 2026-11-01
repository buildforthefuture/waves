# ADR 0001: Integer minor units as the only money representation

- Status: accepted
- Date: 2026-11-01

## Context

Monetary amounts that travel through binary floating-point values pick up representable-value
noise: sums drift by single minor units, comparisons misfire, and ledgers stop balancing. Existing
money types often accommodate floats for convenience and pay for it later in reconciliation.

## Decision

`Money` stores an `int` count of minor units plus a three-letter currency code. Floating-point and
boolean inputs raise `InvalidAmountError` at construction. Fractional division exists only as
`allocate` and `split`, both lossless by largest-remainder, and multiplication exists only as
integer `scaled`.

## Consequences

- Addition and comparison are exact; tests can assert literal equality
- Callers at the boundary (parsing user input, API payloads) convert to minor units themselves; the
  library refuses to guess an exponent table
- Currency-specific exponents (for example zero-decimal currencies) are a display concern for a
  later roadmap item, not a storage concern
- No rounding policy is needed anywhere in the core
