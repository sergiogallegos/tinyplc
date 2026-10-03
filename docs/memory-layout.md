# STM32 experimental memory layout (R2.3–R3.3)

The `port/nucleo_f446re/native/` target links the pinned FreeRTOS MPU port with
project-owned startup, a privileged scan supervisor and an unprivileged native
worker. The old blink target is unchanged. It has physical I/O and protected
native execution and a downloadable image loader/serial task. [Execution boundary](native-isolation.md).

## Reserved regions

| Region | Address | Reservation | Intended policy |
| --- | --- | --- | --- |
| Privileged flash | 0x08000000 | 64 KiB | Supervisor/kernel executable, inaccessible to user tasks |
| System-call flash | 0x08010000 | 4 KiB | Read/execute veneers and immutable PLC return gateway |
| Privileged RAM | 0x20000000 | 64 KiB | Kernel/supervisor data, including top 4 KiB reserved for MSP |
| Code slot A | 0x20010000 | 16 KiB | Immutable native program code and constants |
| Code slot B | 0x20014000 | 16 KiB | Second program slot; RX when active, staging RW/XN only in comms |
| Input image | 0x20018000 | 512 B | User read-only, non-executable |
| Working state and diagnostic space | 0x20018200 | 512 B | User read/write, non-executable |
| Worker stack | 0x20018800 | 2 KiB | User read/write, non-executable |

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
permission correction. R2.6 additionally routes every unprivileged SVC through
a checked, return-only gateway; this is not a complete adversarial audit of the port.

ELF write flags on initialization buffers do not implement MPU permissions.
The board fault matrix separately exercises hardware permissions.
Code A is loaded by startup from its flash load address before the scheduler.
R3.3 overlays only the inactive slot writable/non-executable during END, then
seals it. Boundary activation changes the worker mapping and read-only dispatch
descriptor together; state resets to zero. See [transport](engineering-transport.md).

## Runtime behavior

Startup initializes data/BSS and copies compiled ST to code A. The immutable
return gateway executes from firmware flash. Privileged NOLOAD diagnostic storage is excluded from BSS
clearing so an IWDG reset can report its cause. The supervisor configures GPIO,
uses a private stack in privileged RAM, and schedules a restricted unprivileged
worker on the separately mapped 2 KiB stack. Scan, worker, comms and idle use static TCBs.

PendSV and SysTick use the FreeRTOS handlers. The SVC router delegates privileged
startup to FreeRTOS and checks all user returns. Fault and TIM2 handlers support
contained abort or watchdog reset. The user ABI forbids FP; CP10/11 remain
available only to privileged context handling. See [R2.6 evidence](R2.6-report.md).

The boot example has three tags and a statically linked native entry; R3.3
can replace it with a validated 1..64-tag image. Its
trusted return gateway is in the firmware-owned system-call flash window,
outside both payload slots. No current API can rewrite code A.
See [package ownership and placement](native-package.md).

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
section flags, vector/handler addresses, RAM entry and firmware gateway placement. It then
attempts a link with excess input storage and requires the linker assertion
to reject it. These checks validate the artifact, not physical MPU enforcement.

## Measured build footprint

Historical R2.4 baseline (GCC 13.3.1 and the pinned kernel). Current R2.6
usage and separate-task stack observations are in [the R2.6 report](R2.6-report.md):

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

## Hardware verification

R2.3/R2.4 established RAM instruction fetch and initial scheduler integration.
R2.5 added physical I/O; R2.6 exercises unprivileged permissions, deadline abort
and reset fallback. The [R2.7 package policy](native-package.md) selects fixed-slot host linking. A discovered USB
serial path alone is not identity.

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
The test expects the exact physical button/LED example, not arbitrary user logic.
For the isolated fault matrix, use `scripts/prepare_isolation_tests.py` as
described in [native-isolation.md](native-isolation.md).

## R3.3 integrated budget

The current build consumes 25,096 bytes of privileged flash and 528 bytes of
system-call/gateway flash. Privileged RAM reaches 50,556 bytes including alignment
gaps: 668 bytes of data, 46,424 bytes of BSS, and 36 retained diagnostic bytes.
The 4 KiB MSP reservation leaves 10,884 bytes of headroom in the 64 KiB region.
This includes the 24,240-byte loader, 4 KiB comms stack and 5 KiB timestamped RX
ring. Code/input/working/worker-stack regions are separate and unchanged.
Future monitor buffers must fit this remaining budget and be remeasured.
See [R3.3 measurements](R3.3-report.md).


## R3.5 baseline for R4 planning

The integrated R3.5 image uses 58,428 bytes of privileged RAM including
alignment gaps. The raw 7,108-byte gap to 64 KiB includes the mandatory 4,096-byte
MSP reservation in `native/memory.ld`; additional static headroom is 3,012 bytes.
[R4.1](online-state.md) caps planned additional checkpoint/request/diagnostic
storage at 1,024 bytes and reuses pinned per-slot schemas. This is a design
budget, not a measured R4 implementation. R4.2 must retain the linker assertion
and remeasure stack and whole-scan timing.


## R4 integrated budget

R4's update object occupies 424 target bytes; boot metadata now reuses the
loader slot table. Integrated privileged RAM is 58,740 bytes (312 more than
R3.5), leaving 2,700 bytes beyond the mandatory 4 KiB MSP reservation.
Privileged flash is 28,656 bytes and call/gateway flash remains 528 bytes.
Existing native slots, input/working regions and worker stack are unchanged.
See [R4.2 checks](R4.2-report.md) and [R4.3 measurements](R4.3-report.md).
