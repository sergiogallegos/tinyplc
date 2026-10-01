# Setup and reproduction

## Primary Rust and LLVM path

Use installed Rust/Cargo, LLVM (`clang`, `llvm-as`, `opt`), CMake >=3.28,
a host C compiler and Python >=3.11. The compiler has no third-party crates;
Cargo runs offline with its lockfile. LLVM is invoked as an external PC tool.
Nothing is downloaded or installed by these commands.

Verified here: Rust/Cargo 1.98.1, LLVM 23.1.2, Apple Clang 21.0.0 for the
historical C core, CMake 4.4.3 and Python 3.14.7 on macOS arm64. These are
observed versions, not a portable toolchain lock. LLVM tools should belong
to the same installation; Apple's bundled Clang alone does not supply them all.
Override `CLANG`, `LLVM_AS`, `LLVM_OPT`, `CARGO`, `PYTHON` or `CMAKE` as needed.

```sh
make compiler
make run
make aot-arm
make test
cargo fmt --all -- --check
cargo clippy --workspace --all-targets --offline --locked -- -D warnings
```

The host demo prints `R1 AOT scans=5 LED=1 N=2`. ARM code generation produces
`build/aot/button_led.arm.o`; it is a relocatable object, not a downloadable
program. The tests execute native host code at O0 and O2 and verify ARM object
generation. See [R1 results](R1-report.md) and [compiler ABI](../compiler/README.md).

Example explicit LLVM selection on a Homebrew installation:

```sh
make run CLANG=/opt/homebrew/opt/llvm/bin/clang LLVM_AS=/opt/homebrew/opt/llvm/bin/llvm-as LLVM_OPT=/opt/homebrew/opt/llvm/bin/opt
```

## Historical reference checks

```sh
make run-legacy
make test-legacy
make sanitize
make thread-sanitize
```

These exercise the old C VM and Python compiler used as independent semantic
oracles. Sanitizer targets currently cover that historical suite, not LLVM AOT
code. The old simulator prints `M1 scans=5 period_ms=10 LED=1 N=2 generation=1`.
If the checkout moved, use `cmake --fresh -S . -B build/sim` to refresh paths.

## Board bring-up

M0 blink is deliberately separate from the PLC firmware. It boots from flash using a small project-owned vector table, initializes C data/BSS, enables GPIOA, configures PA5 as output, and polls SysTick at the reset-default 16 MHz HSI clock. LD2 alternates 500 ms on / 500 ms off. FreeRTOS replaces this bring-up target at R2; do not infer RTOS or VM operation from a blink.

First confirm tool versions:

```sh
arm-none-eabi-gcc --version
openocd --version
make blink
```

Expected compiler version contains `13.3.1`; OpenOCD contains `0.12.0`; build ends with `Built target blink` and creates `build/blink/blink.elf` plus `blink.map`. Missing tools should fail explicitly rather than trigger installation.

Connect the NUCLEO-F446RE via ST-LINK CN1 with a USB data cable, keeping the factory ST-LINK/target jumpers installed. **The next command replaces the board's existing firmware**:

```sh
make flash-blink
```

Expected OpenOCD log includes `Programming Finished`, `Verified OK`, and reset/shutdown messages (format varies). Visually confirm LD2 repeats roughly one second cycles. A successful flash log alone does not prove the LED behavior. If no probe is present expect an ST-LINK connection error; stop and inspect connection/jumpers rather than declaring success.

Discover serial ports without opening them:

```sh
python3 -c 'import glob; print("\n".join(glob.glob("/dev/tty.usbmodem*") + glob.glob("/dev/cu.usbmodem*")))'
```

Expected paths depend on the Mac. The blink target emits no UART output. The native board port will supply exact serial commands and observed levels for B1 (released/pressed) and prove `LED := NOT BTN;` on hardware.

See [references and acknowledgments](references.md) for related work and official
technology documentation, and [tasks](tasks.md) for implementation status.

`make test-abi` runs the R2.1 C/LLVM call-contract fixtures at O0/O2 and
cross-compiles both sides for Cortex-M. It is included in `make test`.

R2.2 [pins tools and the FreeRTOS MPU port](target-toolchain.md). Run
`python3 scripts/check_target.py --tools host` or `--tools target` for offline
version checks. GCC/OpenOCD were exercised from temporary local storage;
these checks do not install them or imply a firmware build.

For the separate R2.3 firmware target, follow [memory-layout.md](memory-layout.md).
Use explicit `FREERTOS_ARCHIVE` and `ARM_PREFIX` arguments; the build performs
no downloads or flashing. The selected GCC was exercised from temporary local
storage during R2.3. No global tool installation was made.

[R2.4](R2.4-report.md) records successful board execution. The current target
build requires `make compiler` first and installed LLVM for ABI 2 user code.
The hardware test uses a checksum-pinned xPack OpenOCD distribution from
temporary storage; its exact development version is recorded in the report.

R2.6 update: physical GPIO scans now execute ST in a separate unprivileged
worker, with checked return, deadline abort and reset fallback. See the
[execution boundary and test commands](native-isolation.md) and
[hardware report](R2.6-report.md). R2.7 selects fixed-slot host linking and moves the gateway to firmware flash.
See the [R2 report](R2-report.md); [R3.1](R3.1-report.md) now freezes package/frame encoding. [R3.2](R3.2-report.md) adds portable validation/staging and the Rust packager;
UART transport and board activation are next.

`make target-verify` also links the current program independently for slots A
and B, checks prohibited imports/globals and address-dependent fixups, and
writes `build/placement/report.json`. Its raw `.bin` files are placement
experiments, not downloadable packages. See [R2](R2-report.md).

## R3.2 native package build and staging tests

Install/use the pinned ARM GNU toolchain as well as LLVM. The full test target
now includes Rust-packager/C-loader integration, so it needs the target linker:

```sh
make test ARM_PREFIX=/path/to/bin/arm-none-eabi-
make loader-target-check ARM_PREFIX=/path/to/bin/arm-none-eabi-
./target/debug/plcpack examples/button_led.st --slot B -o build/button-b.tplc \
  --clang /path/to/clang --ld /path/to/bin/arm-none-eabi-ld
```

`test-loader` runs focused host tests. The target check compiles a relocatable
ARM object and checks static RAM/undefined symbols; it does not flash or activate
anything. See [packager usage](../packager/README.md), [loader ownership](native-loader.md)
and the [R3.2 report](R3.2-report.md).

## R3.3 serial engineering

After installing the native firmware, use the local callout device:

```sh
./target/debug/plctool /dev/cu.usbmodem2103 info
./target/debug/plctool /dev/cu.usbmodem2103 status
```

[The transport guide](engineering-transport.md) shows slot selection, package
build, download and explicit activation. [R3.3](R3.3-report.md) gives the separate
lab-board fault-test command and measured results. Host tests now also use a
POSIX pseudo-terminal and the system `stty`; they do not access the board.
