# R2 report — protected native execution and package requirements

Completed 2026-10-01 on NUCLEO-F446RE. R2 establishes the research execution
boundary: Rust ST → LLVM ARM code → fixed RAM entry → unprivileged FreeRTOS
worker, supervised by privileged C with physical I/O and fault containment.
R2.7 closes the stage with host-linked slot placement and package requirements.
The downloadable package encoder, parser and transport do not exist yet.

## Evidence across the stage

| Step | Result and evidence |
| --- | --- |
| R2.1 | [ABI 2](R2.1-report.md): separate frozen inputs and proposed working state |
| R2.2 | [Pinned toolchain and MPU port](R2.2-report.md) with provenance |
| R2.3 | [Reserved memory and RAM execution](R2.3-report.md) on the board |
| R2.4 | [LLVM-generated ST running on STM32](R2.4-report.md) |
| R2.5 | [Transactional scan, GPIO and timing](R2.5-report.md), including user-observed button behavior |
| R2.6 | [Privilege boundary, deadline and watchdog recovery](R2.6-report.md), 19 hardware cases |
| R2.7 | [Package requirements](native-package.md), A/B link proof, firmware-owned gateway and 20-case hardware regression below |

## R2.7 implementation and decisions

The PC resolves all code addresses for either slot A (`0x20010000`) or slot B
(`0x20014000`). Each slot reserves 16 KiB. The first package profile will carry
its exact link address, target/ABI information, entry offset, code bounds and
compiler-derived tag schema. The loader will reject wrong-slot artifacts,
imports, device relocation requests and writable program globals. Values
remain in runtime-owned input and working blocks passed through ABI 2.

`program.ld` and `verify_placement.py` link the example independently for both
slots and check the resulting ELF and raw payload. Both example payloads are
184 bytes, with Thumb entries `0x20010001` and `0x20014001`. Their identical
bytes do **not** establish general position independence. A separate absolute
self-pointer fixture confirms the host resolves address-dependent content for
each slot. Imports, undefined weak imports, writable data, slot overflow and
firmware-address placement are rejected. See [placement evidence](evidence/R2.7-placement.json).
These raw binaries are test artifacts, not accepted download packages.

The trusted 40-byte return gateway now resides at `0x080101e0` in firmware
flash, outside both program slots. It calls the statically linked RAM entry
through a long-distance indirect branch. The obsolete RAM probe is removed.
The loader's future dispatch descriptor, slot ownership and protection updates
are specified in [native-package.md](native-package.md), not implemented here.

The initial authenticity policy is explicitly **unsigned local lab code**.
CRC will detect corruption; it will not prove origin or safety. Unsupported
signed profiles must be rejected rather than silently downgraded. Exact field
offsets, identifiers, CRC coverage and generated Rust/C definitions are R3.1.

## Validation and measurements

`make test target-verify` passed with LLVM 23.1.2, Rust 1.98.1, GCC 13.3.1 and
the pinned FreeRTOS kernel. This includes Rust compiler tests, independent
O0/O2 native semantic comparisons, ABI fixtures, sanitized C transaction and
exception-frame checks, firmware ELF/vector/range checks, and A/B link checks.

All **20 hardware cases passed** after moving the gateway. The matrix covers
illegal data/code/peripheral access, execution permission faults, direct and
forged SVC calls, FPU use, infinite execution, attempted interrupt masking,
invalid stacks, division fault, gateway write and normal execution.
[Board observations](evidence/R2.7-board.txt) and [image hashes/symbols](evidence/R2.7-images.json)
preserve the measured results. The gateway-write attempt faults with CFSR
`0x82` at `0x080101ec`: output becomes zero and the previous internal value
`N=3` survives the rejected dirty working state. Normal button/LED firmware
was restored after the matrix.

| Current normal firmware measurement | Result |
| --- | --- |
| Privileged flash, including initial data/code copies | 18,552 bytes |
| System-call flash including 40-byte gateway | 520 bytes |
| Privileged RAM sections | 10,508 bytes |
| Firmware-linked code A payload | 176 bytes |
| Reserved worker stack | 2,048 bytes |
| Supervisor / worker stack minimum free in sample | 454 / 502 words of 512 |
| Normal maximum measured scan work | 2,177 cycles = 136.0625 µs at 16 MHz |
| Normal missed releases | 0 |
| Infinite-loop deadline handler entry | 160,237 cycles after scan start |
| Physical safe-output write | 23 cycles later: total 10.01625 ms |

The standalone payload additionally includes an 8-byte ARM exception index,
accounting for its 184-byte size. Stack and timing observations are fixture
measurements, not worst-case guarantees. Deadline interruption has finite
latency; the injected infinite scan misses one release. Invalid-stack cases
use watchdog reset instead of attempting to resume a damaged context. Reset
was observed by the 1.2-second debugger sample; exact reset latency was not
measured. Debug halts freeze the watchdog under this OpenOCD target setup.
The supervisor feeds it during healthy supervision of a latched safe fault,
so diagnostics remain available; an untrustworthy supervisor path stops feeding.

## Reproduce

Use the versions and archive checksums in [target-toolchain.md](target-toolchain.md)
and `config/target-lock.json`. Make LLVM tools available on `PATH`.

```sh
make test target-verify FREERTOS_ARCHIVE=/path/to/kernel.tar.gz ARM_PREFIX=/path/to/bin/arm-none-eabi-
python3 scripts/prepare_isolation_tests.py --kernel-archive /path/to/kernel.tar.gz --gcc-prefix /path/to/bin/arm-none-eabi-
```

The second command builds fixtures and emits `build/isolation/run.tcl`; it
performs no USB operation. To repeat the authorized lab-board regression:

```sh
openocd -f interface/stlink.cfg -f target/stm32f4x.cfg -f build/isolation/run.tcl
```

This flashes each fixture, checks target identity and results, and restores
normal firmware. Expect `TINYPLC_ISOLATION_PASS`. Preserve the manifest and log
before another fixture build overwrites local evidence.

## Remaining scope

Only the statically firmware-linked slot A program has been executed on the
board. Host linking of slot B does not prove dynamic activation or execution
there. There is no download loader, engineering transport, coherent monitor,
state migration or rollback yet. The tests exercise specific faults, not a
proof against every machine-code behavior, and this is not a safety PLC.

Next: **R3.1**, one shared machine-readable package/frame contract, generated
Rust/C definitions, compatibility rules and golden fixtures. Then implement
bounded staging/validation, UART transfer, boundary activation and snapshots.
