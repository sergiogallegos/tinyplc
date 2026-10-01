# R2.2: toolchain and FreeRTOS port selection

Selection baseline, 2026-09-30. The machine-readable pin is
[config/target-lock.json](../config/target-lock.json). This completes selection
and source review, not a firmware build or hardware compatibility claim.
No kernel source is vendored and no tools are installed by this change.

## Selected versions

| Component | Selection | Evidence at R2.2 selection (see later updates below) |
| --- | --- | --- |
| Rust / Cargo | 1.98.1 | Installed version check passed |
| LLVM Clang / llvm-as / opt | 23.1.2 | Installed version check and R1/R2.1 object tests passed |
| CMake | 4.4.3 | Installed version check passed |
| Firmware C compiler | Arm GNU Toolchain 13.3.Rel1, GCC 13.3.1 | Selected, not installed; target build pending |
| Flash/debug tool | OpenOCD 0.12.0 | Selected, not installed; no flashing performed |
| FreeRTOS-Kernel | V11.3.1, commit `3a22924e0a9ddbbc8b0758881c33b3422a5cc20d` | Upstream archive downloaded to temporary review storage and SHA-256 verified |

The earlier M0 V11.1.0 proposal is superseded. V11.3.1 includes relevant MPU
wrapper fixes; selection does not imply an exhaustive security audit.
[Upstream release](https://github.com/FreeRTOS/FreeRTOS-Kernel/releases/tag/V11.3.1).
Firmware uses GCC because we select the upstream GCC port; the ST program
continues to use LLVM AOT. Tool versions are pins, not hashes of local binaries
or a complete hermetic build. Record platform-specific compiler distribution
checksums before target reproduction acceptance.

## Port and build policy

Select `portable/GCC/ARM_CM4_MPU` with wrappers v2. Include its `port.c`,
`mpu_wrappers_v2_asm.c`, and `portable/Common/mpu_wrappers_v2.c`, plus required
kernel sources. Do not select ordinary `ARM_CM4F` or a Cortex-M33 port.
The port requires hardware floating-point support during compilation.
[Reviewed port source](https://github.com/FreeRTOS/FreeRTOS-Kernel/blob/3a22924e0a9ddbbc8b0758881c33b3422a5cc20d/portable/GCC/ARM_CM4_MPU/port.c).

Firmware flags: `-mcpu=cortex-m4 -mthumb -mfpu=fpv4-sp-d16 -mfloat-abi=softfp
-std=c11 -ffreestanding -fno-common -ffunction-sections -fdata-sections -O2
-fno-lto`. User objects retain `-mfloat-abi=soft` and the integer-only ABI.
Both use the base argument convention; firmware can save FP context. This
must still be checked at the final link and on hardware. No hard-float ABI or
cross-toolchain LTO. Inspect emitted instructions, attributes and helper imports.
[Arm AAPCS32](https://github.com/ARM-software/abi-aa/blob/main/aapcs32/aapcs32.rst).

Required configuration policy (not a complete FreeRTOSConfig.h):

- `configUSE_MPU_WRAPPERS_V1=0`, `configENABLE_ACCESS_CONTROL_LIST=1`.
- `configALLOW_UNPRIVILEGED_CRITICAL_SECTIONS=0`.
- `configSUPPORT_STATIC_ALLOCATION=1`, `configSUPPORT_DYNAMIC_ALLOCATION=0`;
  do not link a heap implementation. Allocate restricted tasks statically.
- `configTOTAL_MPU_REGIONS=8`; assertions and stack-overflow checks enabled.
- Bound `configSYSTEM_CALL_STACK_SIZE` and protected kernel object pool in
  R2.3; measure all stacks. Do not choose sizes solely to silence build errors.

There are three configurable task regions plus its stack region on this port.
Tentative use: immutable RAM code, frozen inputs, writable working data including
untrusted diagnostics; the stack is separate. Alignment and region overlaps
must be resolved in R2.3, including privileged call stacks and supervisor data.
[Port definitions](https://github.com/FreeRTOS/FreeRTOS-Kernel/blob/3a22924e0a9ddbbc8b0758881c33b3422a5cc20d/portable/GCC/ARM_CM4_MPU/portmacro.h).

## Required hardening before user execution

The reviewed port's default general-peripheral region is unprivileged
read/write. Its null-region path can grant broad RAM access. These defaults
do **not** meet tinyplc's isolation policy. Before R2.4/R2.6, introduce a minimal,
reviewed patch/configuration making peripheral access privileged-only, use
explicit restricted-task regions, and test forbidden GPIO/DMA/runtime access.
Higher-numbered MPU regions override lower ones; a low-priority user region
cannot undo a broad higher-priority permission grant. Also audit unprivileged
flash exposure so only intended entry/trampoline/system-call code is reachable.
[Port setup and region storage](https://github.com/FreeRTOS/FreeRTOS-Kernel/blob/3a22924e0a9ddbbc8b0758881c33b3422a5cc20d/portable/GCC/ARM_CM4_MPU/port.c).

This port is the selected integration base, not already a tinyplc sandbox.
Required patches must retain upstream notices and be recorded separately from
the pristine-source checksums.

## Startup, exceptions and linker ownership

Project-owned startup initializes data/BSS, board clocks and fault output policy.
The native target routes PendSV to `xPortPendSVHandler` and SysTick to
`xPortSysTickHandler`. One project-owned SVC router delegates privileged startup
to the unchanged `vPortSVCHandler` and validates every unprivileged completion.
Project handlers own MemManage/BusFault/UsageFault/HardFault and the independent
deadline timer, with contained abort or watchdog reset recovery. ELF checks
verify these vector bindings; see [the execution boundary](native-isolation.md).

MPU wrappers v2 use a privileged system-call stack and validate entry/exit
locations. Keep the kernel's SVC namespace and handler intact. The R2.6 PLC completion gateway is coordinated with these
mechanisms and rejects direct user kernel calls; ABI 2 currently exposes no user-callable services. Numeric SVC
values are not permission to call kernel operations.
[Wrapper implementation](https://github.com/FreeRTOS/FreeRTOS-Kernel/blob/3a22924e0a9ddbbc8b0758881c33b3422a5cc20d/portable/Common/mpu_wrappers_v2.c).

R2.3 must provide the port's FLASH/SRAM segment, privileged function/data and
system-call boundary symbols and corresponding sections, with power-of-two
alignment and overlap assertions. The blink linker script has none of this
protection layout. Configure interrupt priorities with STM32's implemented
priority bits; deadline handling must respect the kernel's masking/API rules.
Do not infer recovery or worst-case timing from merely linking successfully.

## Provenance and reproduction

FreeRTOS uses the MIT license. If integrated, retain `LICENSE.md` and the source
copyright notices; it remains third-party code alongside project-owned PLC
logic. [Pinned license](https://github.com/FreeRTOS/FreeRTOS-Kernel/blob/3a22924e0a9ddbbc8b0758881c33b3422a5cc20d/LICENSE.md).

The lock records the immutable archive URL, complete archive SHA-256 and hashes
of eight reviewed files. Given an explicitly downloaded archive/extracted tree:

```sh
python3 scripts/check_target.py --archive /path/to/kernel.tar.gz
python3 scripts/check_target.py --source /path/to/FreeRTOS-Kernel
python3 scripts/check_target.py --tools host
python3 scripts/check_target.py --tools target
```

The source check covers the listed files only. The archive check covers all
archive bytes. All commands are offline; missing tools or mismatches fail.
A matching version string does not verify a tool binary's origin.
Next: install/provide the selected target tools through an explicit setup step,
then R2.3 firmware layout/build measurements and board instruction-fetch tests.

R2.3 update: the selected GCC distribution was downloaded to temporary storage,
checked against Arm's published SHA-256 and used for the [layout build](memory-layout.md).
The source review above remains the baseline; build-time integration now applies
the documented peripheral-permission patch. Hardware validation remains pending.

R2.4 update: hardware tests used xPack OpenOCD v0.12.0-7, whose reported
version is `0.12.0+dev-02228-ge5888bda3-dirty`. This is a documented tool
distribution change from the pristine 0.12.0 proposal. Its archive digest is
pinned and the [board report](R2.4-report.md) records successful use.
