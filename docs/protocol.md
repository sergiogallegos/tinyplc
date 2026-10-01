# Native engineering protocol v1 (R3.1)

The byte contract is frozen. The portable package validator/staging and Rust
packager are implemented. [R3.3](engineering-transport.md) adds the UART parser,
board integration and INFO/download/activate/status CLI. Tag reads/writes and
rollback remain unsupported and are not advertised. The normative [wire specification](wire-format.md) defines
framing, CRC coverage, every command/response, errors, expiry, retries and
activation outcomes. [Generated layouts and IDs](wire-layouts.md) come from
[`contract/wire.json`](../contract/wire.json), shared by Rust and C.

| Command | Purpose |
| --- | --- |
| INFO | Discover profile, capabilities, slot ownership and transfer progress |
| DOWNLOAD_BEGIN | Reserve an inactive slot and learn its exact link base |
| DOWNLOAD_CHUNK | Transfer contiguous bytes with a bounded last-chunk retry |
| DOWNLOAD_END | Validate the complete package and assign a READY generation |
| ACTIVATE | Queue a READY generation for a scan boundary |
| ROLLBACK | Optional R4 boundary request for the retained previous image |
| READ_TAGS | Read bounded pages from one owned coherent snapshot |
| WRITE_TAG | Optional queued VAR write with generation/boundary acknowledgement |
| GET_STATUS | Observe actual execution, request outcome, fault and timing |

A5 framing bounds messages at 262 bytes. Every response includes status; errors
contain status only. CRC detects corruption and does not authorize native code.
The first profile is explicitly unsigned, local-lab UART over the ST-LINK USB
bridge. No network endpoint or cryptographic replay protection exists.

ACTIVATE OK means queued, not running. INFO and GET_STATUS resolve uncertain
outcomes; a transport timeout is not permission to repeat a mutation blindly.
Package placement and ownership requirements are in [native-package.md](native-package.md).
Exact wire rules and [golden fixtures](../tests/wire/fixtures) supersede the
earlier proposal; see the [R3.1 report](R3.1-report.md) for verification limits.
