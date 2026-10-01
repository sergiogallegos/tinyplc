# M1: portable runtime core

Repository name is now **tinyplc**, with origin `git@github.com:sergiogallegos/tinyplc.git`. Public include paths and executable names use `tinyplc`. The existing local workspace folder can retain its old name.

## Implemented

- Portable C11 tags and lookup, typed values, input/VAR write restrictions, and output clearing.
- Little-endian v1 image parsing, CRC32, canonical tag metadata, supplied I/O binding checks, complete instruction decoding, forward-jump boundary checks, typed control-flow merges, and exact maximum-stack verification.
- Stack VM for every documented v1 opcode, wraparound DINT arithmetic, signed comparisons/division, budget enforcement, and fault PC/opcode diagnostics.
- Two fixed RAM slots, inactive-image staging, generation-checked activation requests, discard, and a scan-owned atomic pointer switch at a caller-designated boundary.
- Transactional scan wrapper: valid input samples remain visible, internal values persist only after successful execution, faults clear output tags and latch execution off, and valid activation recovers execution while retaining diagnostics.
- A five-scan native demonstration executes the hand-encoded button/LED program through this core; `N` finishes at 2 and `LED` at 1.
- Educational [core API guide](../core/README.md), updated README/bytecode contract, and sanitizer targets. No dependency installation.

## Host verification

Environment: macOS arm64, Apple Clang 21.0.0, CMake 4.4.3. Warnings are treated as errors. Native tests cover eight groups: tags/header/CRC, operators, branches, rejection/capacity limits, transactional faults, slot lifecycle, mutations, and producer/scan concurrency. Tests use 4000 deterministic image mutations and 2000 actual concurrent activation handoffs. AddressSanitizer/UndefinedBehaviorSanitizer and ThreadSanitizer builds run the same suite. These checks exercise memory, arithmetic, and ownership rules; they do not prove worst-case timing or every possible race.

```sh
make test
make sanitize
make thread-sanitize
make run
./build/sim/core-tests
```

Expected CTest summary for each test configuration: `100% tests passed, 0 tests failed out of 2`.

Expected simulator output:

```text
M1 scans=5 period_ms=10 LED=1 N=2 generation=1
```

The test executable reports eight groups passed and, on this host ABI, runtime=10104 bytes, program=4642 bytes, validator_workspace=18432 bytes. The validation workspace is caller-owned and outside the scan stack. Actual MCU RAM/stack/flash accounting remains a target build task.

## Hardware and scope limits

No firmware was flashed or hardware-tested in M1. M0's ARM build/blink acceptance remains pending the selected target tools. The simulator uses supplied logical inputs, so it does not verify BTN electrical polarity or GPIO timing. It does not yet load ST source or serve TCP.

M1 activates a program with zeroed state; migration, rollback, trial-scan reservations, snapshots, protocol commands, and real deadline/output enforcement remain later milestones as documented. The standalone VM mutates its supplied working values; callers wanting fault containment must use the scan wrapper. Direct live-tag access is scan-owner-only, not a comms API.

M2 is next: Python lexer/parser, semantic analysis, compiler, disassembler, reference interpreter, and differential tests against this C VM. Stop after this M1 report before beginning M2.
