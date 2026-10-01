# R1: Rust frontend and LLVM ahead-of-time execution

Architecture revision, 2026-09-30. The selected product path replaces the
Python compiler and bytecode VM with a standard-library Rust frontend and
PC-side LLVM AOT. Historical implementations remain independent test oracles.

## Implemented

- Positioned handwritten lexer/parser, declaration resolution, BOOL/DINT type
  checks and a separate typed PLC IR. Input assignment and malformed programs
  are rejected with source locations; resource bounds reject oversized input.
- Textual LLVM IR generation without LLVM bindings or third-party Rust crates.
  Explicit wrapping arithmetic, guarded division, eager logic and forward
  control flow preserve the documented ST subset.
- Research C scan ABI and exported names/types/classes. Success commits working
  state; division/type faults clear output cells and preserve internal values.
- Rust CLI, golden LLVM fixture, C AOT demo, host execution tests at O0/O2 and
  Cortex-M4 ARM object generation. No automatic installs.
- Rewritten current architecture diagrams and roadmap; dated M0–M2 records
  explicitly labelled historical. Educational reading guide studies Rusty, matiec and
  OpenPLC as design references, without importing their implementation.

## Verification

Passed: `make test`, `make run`, `make aot-arm`, `cargo fmt --all -- --check`,
and `cargo clippy --workspace --all-targets --offline --locked -- -D warnings`.

The Rust suite has nine frontend/semantic/limits/golden tests. The LLVM suite
has five tests, including 109 programs (100 seeded random programs), three
scans per program at O0 and O2: 654 native scan comparisons with independent
Python and C references. It also checks IR validity, metadata, fault positions,
state preservation, CLI behavior and ARM ELF machine identity. Historical
CTest runs three entries including 15 Python test methods and eight C groups.
The AOT demo reports `R1 AOT scans=5 LED=1 N=2`.

Observed tools: Rust/Cargo 1.98.1, LLVM 23.1.2, CMake 4.4.3, Python 3.14.7,
Apple Clang 21.0.0 for historical C builds; macOS arm64. The manifest declares
Rust 1.74 as the minimum, but that version was not separately exercised.

## Boundaries and next gate

The ARM artifact is an ELF relocatable object, not an uploadable image. No
board was flashed or hardware-tested for R1. Native packaging, relocation,
FreeRTOS supervision, MPU isolation, deadline abort, serial engineering
commands, snapshots and online migration/rollback remain unimplemented.
The C host demo is finite and does not establish deterministic scheduling.

R2 must freeze the target ABI and package requirements, establish measured
memory/stack budgets, run a small native function on F446, and prove isolation,
deadline handling and reset recovery before R3 adds downloads. Host semantic
comparisons cannot establish MCU timing or native fault containment.

Markdown links and diagram source are checked; rendered Mermaid layout has
not been visually verified in this environment.
