# A small PLC whose architecture can be read

The goal is the PLC equivalent of a small educational ML engine: preserve the
important boundaries, make each implementation readable, and demonstrate them
with executable tests. Small language coverage is intentional. Production
architecture is a source of lessons, not a claim of production readiness.

## What we build and what we reuse

| Piece | Ownership and reason |
| --- | --- |
| ST lexer, parser, semantic checks, typed PLC IR | Our Rust code, standard library only; every language decision is visible |
| LLVM IR emitter and tag schema | Our code; PLC arithmetic and fault behavior remain explicit |
| Optimization and CPU instruction selection | External LLVM tools on the PC; writing a CPU backend would obscure the PLC lesson |
| Native package, loader, engineering protocol | Our planned bounded implementation; no general desktop dynamic linker |
| Scan state, I/O policy, snapshots, migration | Our planned C supervisor; explicit state ownership |
| Scheduling and context switching | FreeRTOS kernel, pinned and reviewed when integrated |
| Board support | Small project-owned startup, linker layout and register-level drivers |
| Verification | Cargo tests, standard-library Python harnesses and independent historical C/Python oracles |

“Minimal dependencies” applies to the project implementation. A compiler,
linker, build tools and test runners are still prerequisites. No crate packages
are required and builds do not install software. Zero third-party code is not
compatible with explicitly choosing LLVM and FreeRTOS.

## Lessons from Rusty

[Rusty's technical overview](https://plc-lang.github.io/rusty/technical/overview.html)
describes parsing, indexing, annotation, validation, LLVM generation and linking.
Our takeaway is to preserve those responsibilities even when several fit in a
small module. Resolve names and types before emission; keep source positions
through diagnostics; separate language semantics from target code generation.
A compiler symbol index resolves source names. Our emitted tag dictionary is a
separate runtime-facing artifact for monitoring and state compatibility.

Rusty handles a much wider language and uses a larger implementation toolkit.
Its [Cargo manifest](https://github.com/PLC-lang/rusty/blob/master/Cargo.toml)
includes lexer, CLI, LLVM-binding and serialization dependencies. tinyplc uses
a handwritten lexer/parser/CLI and textual LLVM IR to keep the learning surface
small. We study the design without importing or copying implementation code.
The [validation notes](https://github.com/PLC-lang/rusty/blob/master/book/src/arch/validation.md)
also motivate separating syntax failures from semantic failures with precise
locations. Our current diagnostics use one-based line and column.

## Lessons from OpenPLC Runtime

The referenced repository is **OpenPLC Runtime v4**, a hosted C/C++ runtime
with a Python engineering API. Its current documented flow compiles uploaded
generated sources into shared libraries on the runtime host. tinyplc instead
performs target AOT on the PC and will upload a bounded native package to an
MCU without a compiler or Linux dynamic linker.
[OpenPLC README](https://github.com/Autonomy-Logic/openplc-runtime).

The useful design lessons are concrete:

| Observed upstream boundary | tinyplc decision |
| --- | --- |
| Task bodies execute through a runtime-controlled interface; scan timing and completion are tracked separately | C owns releases, timing, fault policy and physical output commit |
| Located values are copied into program storage before execution, with changed outputs journaled afterwards | Frozen input image and private working state, then one owner commits results |
| The dispatcher has higher priority than application workers | An independent protected deadline guard must remain able to stop user execution |
| Lifecycle management owns creation, publication and teardown of tasks | Reserve slots and generations; never reclaim code or metadata while execution/readers reference it |

These observations come from
[plc_state_manager.cpp](https://github.com/Autonomy-Logic/openplc-runtime/blob/main/core/src/plc_app/plc_state_manager.cpp).
Our single-task prototype does not reproduce its multitask dispatcher, POSIX
threads, signals or C++ exception recovery. Cortex-M faults require an explicit
protected exception/context recovery design, not a translation of Linux signals.

[image_tables.h](https://github.com/Autonomy-Logic/openplc-runtime/blob/main/core/src/plc_app/image_tables.h)
separates located I/O tables, generated debug entry points, symbol resolution
and synchronized access. It recommends copying data before slow work. Our
adaptation uses tag IDs/offsets and owned snapshots, with boundary-applied
write requests. A symbol address alone is insufficient for coherent monitoring;
lifetime, type, generation and access policy are part of the contract.

[plc_main.c](https://github.com/Autonomy-Logic/openplc-runtime/blob/main/core/src/plc_app/plc_main.c)
illustrates initialization before accepting commands and stopping execution
before destroying drivers. tinyplc's corresponding tests must cover commands
during initialization, repeated activation, failed loading and cleanup. The
small system still needs complete lifecycle behavior.

No OpenPLC code or dependencies are incorporated. This is a source study,
not a runtime audit or evidence that its Linux mechanisms establish MCU timing
or isolation. See [the native roadmap](native-roadmap.md) for our acceptance gates.

## Lessons from matiec

[matiec](https://github.com/sm1820/matiec) provides another useful route:
IEC textual languages → syntax tree → semantic analysis → generated C → an
external native compiler. Its README describes an older IEC edition and a
broader language scope than tinyplc. It is a historical implementation
reference, not our definition of current IEC conformance.

The [semantic stage](https://github.com/sm1820/matiec/blob/master/stage3/stage3.cc)
orders flow analysis, constant propagation, declaration checks, datatype
candidate narrowing, assignment checks and range checks. The lesson is that
semantic passes have prerequisites. For our small explicit BOOL/DINT subset,
a simpler resolved typed IR is sufficient. As arrays, overloaded operations or
function blocks arrive, add explicit passes and rejection tests rather than
letting LLVM diagnose source-language mistakes. Do not inherit C integer
behavior accidentally when adding constant folding.

Its [C accessor layer](https://github.com/sm1820/matiec/blob/master/lib/C/accessor.h)
separates ordinary, external and located variables, initialization and access,
and includes retained/forced-value flags. This illustrates why monitoring,
forcing and retention are runtime semantics, not merely names attached to
addresses. Our initial ABI has simple typed cells; forcing and retention are
deferred. If added, ordinary assignment, operator writes and persistent force
must have distinct policies, applied through the scan owner.

We retain Rust → LLVM IR as the single primary backend. Studying matiec does
not add a generated-C backend, Flex/Bison, or its runtime library. No source
has been copied. Tests should encode our documented subset; disagreements
with other compilers require checking each language contract, not assuming
one implementation is an unquestionable oracle.

## Reading order and experiments

1. Read [the language](language.md), then compile `examples/button_led.st`.
2. Follow `compiler/src/lexer.rs`, `parser.rs`, `semantic.rs`, and `ir.rs`.
   The expression arena keeps nodes in creation order; semantic analysis turns
   unresolved names into checked tag indices before code generation.
3. Read `llvm.rs` beside the golden `compiler/tests/button_led.ll`. Trace a
   tag load, an IF branch, division checks and the success/fault commit paths.
4. Read [scan_abi.h](../compiler/scan_abi.h) and `sim/aot_main.c`; run `make run`.
   This demonstrates actual compiled code called through a C interface.
5. Run `make test`. Change one arithmetic edge case and inspect diagnostics;
   compare optimized AOT behavior with independent interpreter results.
6. Read [runtime ownership](architecture.md) and [native target gates](native-roadmap.md)
   before implementing the MCU supervisor. Host execution is only the first gate.

## Why the NUCLEO-F446RE

A button, LED, debugger and serial bridge make the first I/O experiment small.
The STM32F446RE supplies Cortex-M4F native execution, an eight-region MPU,
512 KB flash and 128 KB main SRAM. That is a useful constrained platform for
learning memory layouts, task stacks and bounded native loading, without
requiring a Linux distribution on the controller.
[ST datasheet](https://www.st.com/resource/en/datasheet/stm32f446re.pdf).

The memory budget and protection layout must be measured, not assumed to fit.
Start with a small linked function and a reserved SRAM block; then prove
fault containment and deadline handling before adding online updates. The
board's logic-level pins are not industrial field I/O. Ethernet, larger state,
isolated I/O and product assurance are separate extensions, not prerequisites
for demonstrating the core. See the README's board mapping and references.

LLVM portability preserves much of the frontend, but a RISC-V or other ARM
port still needs a target ABI, linker/memory map, drivers, interrupt handling
and its own tests. A small implementation should expose those costs clearly.

Research references were reviewed on 2026-09-30; linked upstream branches and
documentation can evolve. These projects are references, not dependencies.

See [references and acknowledgments](references.md) for related work and official
technology documentation, and [tasks](tasks.md) for implementation status.
