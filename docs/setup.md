# Setup and reproduction

## Toolchain choice

Use CMake + arm-none-eabi-gcc + OpenOCD. CMake builds the portable C core natively and the target glue separately, exposing startup, linker scripts, flags, and memory layout for study. Direct register access avoids importing an entire HAL. Compared with an opaque board framework this keeps the educational path explicit, while the necessary FreeRTOS kernel can be pinned separately in M4. Builds use existing tools and never download or install packages automatically.

The selected reproduction baseline is CMake **4.4.3**, host Apple Clang **21.0.0**, GNU Arm Toolchain **13.3.Rel1** (`arm-none-eabi-gcc 13.3.1`), OpenOCD **0.12.0**, and Python **3.11.9** for future host tools. FreeRTOS-Kernel **V11.1.0** is the selected M4 baseline, not fetched at M0. These are explicit selected versions, not a claim they are latest. Host builds allow CMake >=3.28 and Python tools will support >=3.11. M0 host was exercised using the installed compiler/CMake; Python is not used by M0. Future dependencies will have exact locked versions before inclusion.

Official distributions: [CMake](https://cmake.org/download/), [GNU Arm 13.3.Rel1](https://developer.arm.com/downloads/-/arm-gnu-toolchain-downloads), [OpenOCD](https://openocd.org/pages/getting-openocd.html), [FreeRTOS-Kernel V11.1.0](https://github.com/FreeRTOS/FreeRTOS-Kernel/tree/V11.1.0). Keep locally extracted tools in a directory you choose and add their `bin` directories to PATH. Any installation is a separate explicit user-approved step. A full target reproduction lock including download checksums is required before M4 acceptance; M0 does not yet claim target reproducibility has been verified.

## Host

```sh
make sim
make run
make test
make sanitize
make thread-sanitize
```

Expected executable line: `M1 scans=5 period_ms=10 LED=1 N=2 generation=1`.
Expected CTest summary: `100% tests passed, 0 tests failed out of 2`.
The native test binary also reports eight groups, 4000 image mutations, and 2000 concurrent activation handoffs. Build artifacts stay under `build/`. Address/undefined-behavior and thread sanitizer builds use separate directories and require compiler sanitizer support; they install nothing. This finite demonstration executes the real C VM; TCP arrives in M3.

## Board bring-up

M0 blink is deliberately separate from the PLC firmware. It boots from flash using a small project-owned vector table, initializes C data/BSS, enables GPIOA, configures PA5 as output, and polls SysTick at the reset-default 16 MHz HSI clock. LD2 alternates 500 ms on / 500 ms off. FreeRTOS replaces this bring-up target at M4; do not infer RTOS or VM operation from a blink.

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

Expected paths depend on the Mac. The blink target emits no UART output. M4 will supply exact serial commands and observed levels for B1 (released/pressed) and prove `LED := NOT BTN;` on hardware.
