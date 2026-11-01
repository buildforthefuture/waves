# Security Policy

## Supported versions

| Version | Supported |
| --- | --- |
| 0.1.x | yes |

## Reporting a vulnerability

Open an issue in this repository's issue tracker and mark it as a security report. Describe the
affected version, the input sequence, and the unexpected behavior without disclosing working exploit
details in the public text; maintainers will follow up and coordinate disclosure. Please do not
include real ledger data from any production system in reports.

## Scope notes

Ledgerpost is an in-process library: it performs no network or filesystem input and output, holds no
credentials, and writes nothing on its own. The classes of concern are therefore:

- Construction bypasses that let an unbalanced transaction exist
- Race conditions that apply a transaction twice under one request key
- Unbounded growth from hostile keys, account names, or metadata
- Import surface that grows past the standard library

Reports about deployment concerns — durability of idempotency claims, transaction boundaries with
external databases — are welcome as issues as well.

## Handling hostile input

Values that cross a trust boundary (request keys, account names, transaction ids, metadata) are
bounded in length, reject control characters, and are copied into immutable structures at
construction. Amounts are integers; floats are refused rather than coerced. The library never logs
and never prints.
