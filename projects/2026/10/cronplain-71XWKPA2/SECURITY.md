# Security policy

## Supported versions

| Version | Supported |
| --- | --- |
| 0.1.x | Yes |

## Scope

Cronplain parses text and computes calendar answers. It performs no network
I/O, reads no files, executes no code from its input, and spawns no
processes. The practical security surface is parser robustness: any input
must fail as a library error rather than crash or loop.

## Reporting a vulnerability

Open a private security advisory through this repository's security tab. Do
not open a public issue for anything exploitable. Include the offending
input, the version, and the observed behavior; a fix or an assessment
arrives within a few days.

## Handling untrusted input

Expressions from users or configuration can be passed straight to `parse()`.
Malformed shapes raise `CronError`, iteration is bounded in both directions,
and nothing in the library interprets input beyond calendar semantics.
