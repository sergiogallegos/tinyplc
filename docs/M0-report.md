# M0 verification report

Date: 2026-09-30. M0 host scaffold is complete; target build and hardware acceptance remain pending.

## Works and was verified on host

- `make sim` builds a C11 native executable with warnings treated as errors.
- `make run` prints `M0 scans=5 period_ms=10 output=1` and exits successfully.
- `make test` passes the native scheduling smoke test (1/1). This verifies build/start/completion and the placeholder result; it does not validate timing, VM semantics, or a protocol.
- Installed verification environment: CMake 4.4.3, Apple Clang 21.0.0, macOS arm64.
- Board profile, example ST, documentation, standalone blink source, and MIT license are present. No dependency was installed.

## Hardware and target evidence

No firmware was built with GNU Arm GCC, flashed, or tested physically. `make blink` was attempted and failed at configuration because `arm-none-eabi-gcc` is absent. OpenOCD is also absent. A usbmodem device path was observed but its identity was not verified and it was not opened. Board blink acceptance remains pending. Hardware pin claims cite ST UM1724; button polarity remains a board-revision assumption pending schematic/physical verification.

## Reproduce

```sh
make sim
make run
make test
```

With the selected locally available target tools and a confirmed NUCLEO-F446RE, `make blink` builds `build/blink/blink.elf`; `make flash-blink` programs/verifies/resets the board. See [setup.md](setup.md) for the expected tool/log versions, visual LD2 behavior, and overwrite notice.

## Remaining

Install or provide the target toolchain only with user approval, confirm board identity/revision and BTN polarity, then build/flash/visually verify the standalone blink. M1 adds the actual tag DB, VM, image validator, and native tests. M2–M6 remain planned. No compiler/CLI command is claimed to work in this milestone.
