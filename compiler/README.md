# Rust ST frontend and LLVM IR compiler

This is tinyplc's primary compiler. It uses Rust's standard library only and
emits textual LLVM IR without embedding LLVM libraries. The selected pipeline
is ST → Rust frontend → typed PLC IR → LLVM IR → PC-side LLVM AOT → native
controller image → C/RTOS runtime. The packager and board loader are implemented. [TON](../docs/ton.md) is the
first R5 language extension and requires native ABI 2.

```sh
make compiler
./target/debug/plcc examples/button_led.st -o /tmp/button_led.ll
make llvm-example
make run
make aot-arm
make test
```

`plcc source.st` defaults to `source.ll`; `-o` selects a path.
`--abi 1` (default) selects the original host interface; `--abi 2` selects
separate frozen-input and working-state buffers for target integration. Errors include
file, line and column. Compilation errors leave an existing output untouched.
The CLI currently uses the built-in NUCLEO logical bindings (BTN BOOL input,
LED BOOL output). Library callers can supply explicit `Binding` records;
custom JSON profiles are not a CLI feature yet. No dependency installation or
native execution occurs when invoking `plcc`.

`lexer.rs` creates positioned tokens. `parser.rs` builds an arena-backed AST.
`semantic.rs` resolves declarations and produces the separate typed IR in
`ir.rs`. `llvm.rs` lowers that IR into SSA instructions and forward basic blocks.
This structure allows later language extensions without mixing syntax and
machine-code generation. See [language.md](../docs/language.md) for the subset.

## Research scan ABI v1

[scan_abi.h](scan_abi.h) declares the generated module interface:

```c
uint32_t tinyplc_scan(uint32_t *cells, uint32_t count,
                     tinyplc_diagnostic *diagnostic);
```

One module exports a scan function and these constants:

| Symbol | Representation |
| --- | --- |
| `tinyplc_abi_version` | u32 = 1, identifying this research call ABI |
| `tinyplc_tag_count` | u32 number of cells |
| `tinyplc_tag_names` | count × 32 NUL-padded uppercase ASCII bytes |
| `tinyplc_tag_types` | count bytes: BOOL=1, DINT=2, TIME=3 |
| `tinyplc_tag_classes` | count bytes: INPUT=1, OUTPUT=2, VAR=3 |

Each tag occupies a u32 cell at `4 * declaration_index`. BOOL is exactly 0/1;
DINT values are 32-bit bit patterns. Callers provide initialized, aligned,
valid, non-overlapping cell/diagnostic storage. `count` describes available
cells. Start at zero and sample inputs before each call; reuse state across
successful calls. The function has no globals containing mutable PLC state.

Return codes: 0 success; 4 insufficient cell count; 5 division by zero;
8 invalid BOOL cell; 9 invalid TIME cell. The diagnostic contains u32 line/column: the division
operator or invalid BOOL declaration, or zero/zero for success/count failure.
On success, OUTPUT and VAR cells commit and INPUT cells remain untouched.
On 5/8/9, OUTPUT cells clear and previous VAR values remain. On 4, cells remain
untouched because the provided storage may be too small to clear outputs.
The future supervisor must still apply the physical fault policy in every case.

Working values use bounded local allocations. Arithmetic wraps; division is
explicitly checked. The emitted module contains no target triple or data layout;
the LLVM driver selects the target. No `nsw`/`nuw` promises change DINT semantics.
R1 does not generate a full debugger source map, but division/type diagnostics
retain positions through optimized execution.

This ABI is for statically linked tests. It is **not** the native download
format, an unprivileged gateway, or the final board runtime ABI. It supplies
neither scheduling, deadlines, fault latching, snapshots nor an instruction
budget. Its source language has no loops, but compiler structure alone does
not prove execution deadlines. No arbitrary pointers or direct peripheral
access are exposed by the ST subset.

## AOT and verification

`make run` compiles the IR to host machine code and links `sim/aot_main.c`.
Expected result: `R1 AOT scans=5 LED=1 N=2`.

`make aot-arm` compiles to a relocatable Cortex-M4 ELF object with a soft-float
ABI. It is not an uploadable `.bin`, a linked firmware image, or evidence of
board execution. No target runtime libraries or MCU toolchain are downloaded.

`make test-compiler` runs Rust syntax/type/limit/golden tests. `make test-llvm`
requires LLVM, Python and a C build; it verifies both ABI variants, executes
109 programs per ABI at O0 and O2 (including 100 seeded random programs), compares
three scans each with independent Python/C references, checks metadata/faults,
and cross-compiles the corpus to an ARM object. `make test` also runs the
historical oracle regression suite. `make sanitize` and `make thread-sanitize`
currently instrument that historical C suite, not the new AOT code.

Tested tool versions and current limitations are in
[R1-report.md](../docs/R1-report.md). LLVM reference:
[language semantics](https://llvm.org/docs/LangRef.html).

## Design references

Compiler-stage reading references include Rusty and matiec. This compiler is
project-owned code; no implementation from either project is incorporated.
See [credits and official documentation](../docs/references.md) and the
[study notes](../docs/education.md) for the exact lessons and source links.

R2.1 specifies [target ABI draft 2](../docs/native-abi.md) with separate input
and working buffers. Use `--abi 2` for this interface. Never cast a function pointer between ABI
versions. The R2.4 board build explicitly selects version 2.
