# R2.3 experimental memory layout and firmware scaffold

The separate `port/nucleo_f446re/native/` target links the pinned FreeRTOS MPU
port with project-owned startup and a privileged periodic task. The old blink
target is unchanged. This is a buildable memory-layout experiment, not a native
loader, an unprivileged ST program or a completed PLC scan supervisor.

## Reserved regions

| Region | Address | Reservation | Intended policy |
| --- | --- | --- | --- |
| Privileged flash | 0x08000000 | 64 KiB | Supervisor/kernel executable, inaccessible to user tasks |
| System-call flash | 0x08010000 | 4 KiB | Read/execute veneers; controlled kernel entry |
| Privileged RAM | 0x20000000 | 64 KiB | Kernel/supervisor data, including top 4 KiB reserved for MSP |
| Code slot A | 0x20010000 | 16 KiB | Current RAM probe; eventual immutable native code |
| Code slot B | 0x20014000 | 16 KiB | Reserved only, no loader yet |
| Input image | 0x20018000 | 512 B | User read-only, non-executable |
| Working state and diagnostic space | 0x20018200 | 512 B | User read/write, non-executable |
| Task stack | 0x20018800 | 2 KiB | User read/write, non-executable |

Each MPU-sized reservation is aligned to its size. Regions leave deliberate
unused gaps and spare SRAM; no claim that every byte is consumed. Both code
slots are within SRAM1. STM32F446 main SRAM continues through 0x2001FFFF;
SRAM2 is not needed by this first layout. Flash beyond these reservations is
unused. [ST DS10693](https://www.st.com/resource/en/datasheet/stm32f446re.pdf).

`memory.ld` exports the pinned port's linker symbols, restricts the default
unprivileged flash window to the veneer reservation, and asserts capacity and
alignment. All ordinary firmware text/constants stay privileged. Three task
regions map code A, inputs and working state; the port supplies the stack
region. Privileged RAM has the highest region priority. The general-peripheral
mapping is changed to privileged-only in a generated build copy of upstream
`port.c`; the pristine extracted source and license are preserved. This is one
permission correction, not a complete audit of the port or SVC attack surface.

ELF write flags on initialization buffers do not implement MPU permissions.
The running port must program them correctly; that remains a hardware test.
Code A is loaded by startup from its flash load address before the scheduler.
Dynamic writable/non-executable staging and immutable activation are future
loader work; no code-slot download or online swap exists here.

## Scaffold behavior

Startup initializes C data/BSS, copies the RAM probe plus compiled ST code/metadata, enables FP
context support, and selects the vector table. The program configures PA5 and
holds LD2 off. It calls the RAM probe with 41 and expects 42, then starts a
static **privileged** restricted task and the static idle task. The periodic
task now calls the ABI 2 ST example with synthetic inputs, checks its results,
commits working values and records its stack high-water mark every 10 ms.
[Observed results](R2.4-report.md) establish privileged execution on the board.

SVC, PendSV and SysTick use the FreeRTOS handlers. Other vectors lead to a
minimal latch-and-stop handler that clears the LED output. It does not recover
an unprivileged task or keep communications alive; neither comms nor a deadline
guard/watchdog is present. R2.6 must supply those mechanisms. Tick scheduling
here is a scaffold, not demonstrated whole-scan deadline behavior.

## Reproduce the build

Provide the pinned FreeRTOS archive, LLVM, and an existing GCC 13.3.1 installation:

```sh
make compiler
make target-build FREERTOS_ARCHIVE=/path/to/kernel.tar.gz ARM_PREFIX=/path/to/bin/arm-none-eabi-
make target-verify ARM_PREFIX=/path/to/bin/arm-none-eabi-
```

The build verifies the complete kernel archive checksum and compiler version,
extracts under ignored `build/native/`, applies the narrowly scoped permission
change to a separate copy, and builds `tinyplc-layout.elf`, map, symbols and
`.su` stack-usage files. No command downloads, installs or flashes anything.
Upstream naked assembly wrappers alone suppress unused-parameter warnings;
other warnings remain errors. No heap implementation is linked. Project-owned
`memcpy`/`memset` supply the required C primitives; GCC `libgcc` is explicitly
allowed for firmware compiler support, not arbitrary user-program imports.
The resulting ELF has no unresolved symbols.

The verifier checks ELF32/ARM identity, section ranges, non-executable data
section flags, vector/handler addresses and RAM probe placement. It then
attempts a link with excess input storage and requires the linker assertion
to reject it. These checks validate the artifact, not physical MPU enforcement.

## Measured build footprint

GCC 13.3.1, pinned kernel and current R2.4 ST-native build:

| Region | Linker-reported bytes used |
| --- | ---: |
| Privileged flash including initial data/probe copies | 15,072 |
| Veneer flash | 440 |
| Privileged RAM data/BSS | 4,720 |
| Code A probe, compiled ST and metadata | 192 |
| Code B reservation (NOLOAD) | 16,384 |
| Inputs / working | 512 / 512 |
| Task stack reservation | 2,048 |

The privileged RAM number includes a 1,024-byte idle stack and two 1,412-byte
static task control blocks, including each port system-call stack. MSP has a
separate 4,096-byte reservation. Compiler local frame estimates include 48 bytes
for `scan` and 80 for `main`; they exclude callees, asynchronous exception frames
and assembly context-save requirements. They are not worst-case stack bounds.
Actual high-water marks, exception nesting and guard margins require board runs.

## Remaining acceptance

R2.3/R2.4 board results establish RAM instruction fetch, privileged scheduler
progress and initial stack usage. R2.6 still must test unprivileged access,
deadline abort and recovery. A discovered USB serial path alone is not identity.

To reproduce the explicitly authorized hardware test (replaces firmware):

```sh
python3 scripts/board_check.py --flash
/path/to/openocd -f interface/stlink.cfg -f target/stm32f4x.cfg -f build/native/board-check.tcl
```

The generator derives addresses from the built ELF symbol listing. The OpenOCD
script verifies F446/512 KiB identity before flashing, checks two execution
samples and peripheral permissions, then resumes the board. It prints
`TINYPLC_BOARD_CHECK_PASS` only after all checks. A failure stops the test for
diagnosis; never interpret a flash-verify line alone as execution success.
The test expects the exact synthetic-input example, not arbitrary user logic.
