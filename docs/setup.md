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
