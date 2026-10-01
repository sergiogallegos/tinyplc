# M2: compiler, disassembler, and differential verification

> Historical M0–M2 record. The selected architecture is now the
> [Rust frontend → LLVM AOT → C/RTOS runtime](../README.md).
> Bytecode/Python remain independent test references, not the product path.

## Implemented

- Python 3.11+ host package and executable `host/plcc`, with no third-party
  dependencies or installation step. Compilation emits the existing v1 binary
  image; disassembly validates before printing tag metadata and instructions.
- Positioned ASCII lexer, recursive-descent AST parser, declaration resolution,
  type checking, board-profile I/O checking, and bytecode emission. The complete
  supported grammar, precedence, unary rules, bounds, and diagnostics are in
  [language.md](language.md).
- BOOL/DINT expressions, assignments, nested IF/ELSIF/ELSE, eager logic, signed
  comparisons/division, and modulo-2^32 arithmetic. Inputs are read-only. Images
  have canonical tag names, exact maximum stack, forward branches, and CRC32.
- Independent Python image validation and reference bytecode execution,
  including fault code, PC, opcode, and partial working values.
- Native `vm-runner` adapter linked to the production C validator and VM. The
  C core and scheduled simulator behavior did not need changes.
- Fifteen Python test methods integrated into CTest alongside the two existing
  native entries. Standard-library `unittest` replaces the proposed pytest;
  no packages were installed. Native CMake now requires Python 3.11+.

## Host evidence

Verified on macOS arm64 with Apple Clang 21.0.0, CMake 4.4.3, and Python 3.14.7.
Python 3.11 is the declared minimum; it was not separately executed on this
host. Native builds retain warnings as errors.

Tests cover a fixed complete image/CRC and disassembly, button-program golden
code, source diagnostic positions, invalid syntax/types/bindings, capacity
boundaries, operator precedence, arithmetic edge cases, all v1 opcodes,
branch paths, eager evaluation faults, instruction budgets (including HALT),
invalid BOOL cells, and repeated compiled button scans.

Differential tests generate 200 well-typed expression ASTs inside conditional
programs using seed `0x4d32`, each over three executions (600 comparisons).
A test-owned AST evaluator checks source meaning independently of the compiler
and both bytecode interpreters. Python and C must agree on all cells, fault,
PC, and opcode, including partial assignments before divide-by-zero or budget
faults. Separate malformed-image fixtures and 200 seeded mutations (`0xc0de`)
compare Python/C validation acceptance. These supplement M1's native mutation
and concurrency tests, not replace them. Fixed seeds aid reproduction; this
finite corpus is not exhaustive verification.

```sh
make test-legacy
make sanitize
make thread-sanitize
make run-legacy
host/plcc examples/button_led.st -o build/button_led.tplc
host/plcc --disassemble build/button_led.tplc
./build/sim/vm-runner build/button_led.tplc 4096 1 0 0
```

Each test configuration passes all three CTest entries. ASan/UBSan and TSan
instrument the C executables, including the VM used by differential tests;
they do not instrument Python. No sanitizer findings were reported.

The example compiles to 157 bytes: three tags, 25 code bytes, maximum stack 2.
The native adapter's one-scan result is:

```json
{"accepted":true,"fault":0,"pc":24,"opcode":255,"values":[1,0,1]}
```

Across logical BTN inputs `[0,1,1,0,0]`, both VMs finish with BTN=0, LED=1,
N=2. The unchanged scheduled simulator prints:

```text
M1 scans=5 period_ms=10 LED=1 N=2 generation=1
```

The pre-existing build caches referenced the former `toyplc` workspace path;
refreshing each with `cmake --fresh` resolved that local build issue. See
[setup](setup.md) for cache-refresh commands and [host tools](../host/README.md)
for API and CLI usage.

## Scope limits and next milestone

No firmware was flashed or hardware-tested. GPIO polarity, target memory,
RTOS timing, and M0 board acceptance remain unverified. The reference VM and
native adapter expose standalone working-state semantics; transactional scan
commit and fault latching continue to belong to the M1 C runtime wrapper.

The compiler's default profile is the repository's NUCLEO JSON file; custom
profiles are supported by Python, while the test adapter intentionally has
fixed BTN/LED bindings. There is no installable wheel or transport client.

M2 stops here. M3 is next: protocol framing, TCP simulator, basic activation
and coherent snapshots, and `plctool` end to end. Migration/rollback remain M5.

Reproduction aliases above follow the current Makefile; recorded milestone
results describe the implementation at the time of that milestone.
