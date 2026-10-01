# Host tools (M2)

> Historical M0–M2 record. The selected architecture is now the
> [Rust frontend → LLVM AOT → C/RTOS runtime](../README.md).
> Bytecode/Python remain independent test references, not the product path.

Python 3.11+ and its standard library are sufficient; no installation, package
manager, pytest, or network is needed. Run from the repository root:

```sh
make test
host/plcc examples/button_led.st -o build/button_led.tplc
host/plcc --disassemble build/button_led.tplc
./build/sim/vm-runner build/button_led.tplc 4096 1 0 0
```

Compilation writes a 157-byte image. The final command runs one execution with
BTN=1, LED=0, N=0 and prints:

```json
{"accepted":true,"fault":0,"pc":24,"opcode":255,"values":[1,0,1]}
```

`host/plcc source.st` defaults to `source.tplc`. `--board path.json` overrides
the default NUCLEO profile. `-d`/`--disassemble` validates an image before
printing it; `-o` saves the listing. Errors print `file:line:column: message`
for source diagnostics and exit with status 1. Failed compilation leaves an
existing output untouched. The module entry point is equivalent:

```sh
PYTHONPATH=host python3 -m tinyplc examples/button_led.st -o build/button_led.tplc
```

Read [the language contract](../docs/language.md) for exact syntax, precedence,
limits, and arithmetic. `compiler.py` separates the positioned lexer, AST
parser, declaration/type analysis, and emitter. `image.py` independently checks
headers, CRC, tags, instruction boundaries, forward control flow, and typed
stack merges. It also formats the disassembly. `reference.py` interprets these
validated instructions with Python integers, explicitly wrapping DINT values.

The Python API takes an explicit profile and represents runtime values as
unsigned 32-bit cells in declaration order:

```python
from tinyplc.compiler import compile_source
from tinyplc.image import load_profile
from tinyplc.reference import run

profile = load_profile()
image = compile_source("PROGRAM Main VAR n : DINT; END_VAR n := n + 1; END_PROGRAM", profile)
first = run(image, profile)                  # zero-initialized, values=(1,)
second = run(image, profile, first.values)   # values=(2,)
```

`run` returns values, numeric fault, fault/HALT PC, and opcode. Values are raw
working state: earlier assignments remain visible if a later instruction
faults. This mirrors `plc_vm_run`, not the transactional scan wrapper. Callers
must decide whether to commit working values. Repeated calls start a fresh
operand stack; explicitly pass prior values to retain state.

`vm-runner` is a native test adapter built against the production C core. It
validates using fixed BTN/LED bindings, takes an image path, instruction budget,
and optional complete u32 value array, and emits one JSON result. It does not
implement transport, scheduling, latching, or physical I/O. Malformed images
report `accepted:false`; adapter usage/I/O errors exit with status 2.

CTest sets `PYTHONPATH` and the correct native executable for each build. To
run just the host tests after building:

```sh
PYTHONPATH=host TINYPLC_VM_RUNNER="$PWD/build/sim/vm-runner" python3 -m unittest discover -s host/tests -v
```

The 15 test methods include fixed bytecode/disassembly fixtures, diagnostics,
limits, operator edges, compiled button scans, 200 generated typed ASTs over
three executions each (seed `0x4d32`), and 200 image mutations (seed `0xc0de`).
Random programs are checked against a test-owned AST evaluator as well as both
bytecode VMs. Fault code/PC/opcode and partial working values are compared.
Malformed image acceptance is checked separately; runtime differential tests
use validated images. The full suite also runs with instrumented C executables
via `make sanitize` and `make thread-sanitize`.

TCP/serial transport and `plctool` remain M3 work.
