CMAKE ?= cmake
CARGO ?= cargo
PYTHON ?= python3
CLANG ?= clang
LLVM_AS ?= llvm-as
LLVM_OPT ?= opt
OPENOCD ?= openocd
ARM_PREFIX ?= arm-none-eabi-
.DEFAULT_GOAL := compiler
.PHONY: test-abi compiler llvm-example aot-arm run test test-compiler test-llvm test-legacy sim run-legacy sanitize thread-sanitize blink flash-blink help
compiler:
	$(CARGO) build --workspace --locked --offline
llvm-example: compiler
	mkdir -p build/aot
	./target/debug/plcc examples/button_led.st -o build/aot/button_led.ll
	$(LLVM_AS) build/aot/button_led.ll -o build/aot/button_led.bc
	$(LLVM_OPT) -passes=verify -disable-output build/aot/button_led.bc
aot-arm: llvm-example
	$(CLANG) --target=thumbv7em-none-eabi -mcpu=cortex-m4 -mthumb -mfloat-abi=soft -ffreestanding -O2 -c build/aot/button_led.ll -o build/aot/button_led.arm.o
run: llvm-example
	$(CLANG) -O2 -Wall -Wextra -Werror -Wno-override-module -Icompiler sim/aot_main.c build/aot/button_led.ll -o build/aot/tinyplc-aot
	./build/aot/tinyplc-aot
test: test-compiler test-llvm test-legacy test-abi
test-abi:
	CLANG="$(CLANG)" $(PYTHON) -m unittest discover -s tests/abi -v
test-compiler:
	$(CARGO) test --workspace --locked --offline
test-llvm: compiler sim
	CLANG="$(CLANG)" LLVM_AS="$(LLVM_AS)" LLVM_OPT="$(LLVM_OPT)" $(PYTHON) -m unittest discover -s tests/llvm -v
# Historical bytecode implementation, retained as an independent semantic oracle.
sim:
	$(CMAKE) -S . -B build/sim
	$(CMAKE) --build build/sim
run-legacy: sim
	./build/sim/tinyplc-sim
test-legacy: sim
	ctest --test-dir build/sim --output-on-failure
sanitize:
	$(CMAKE) -S . -B build/sanitize -DTINYPLC_SANITIZE=ON -DCMAKE_BUILD_TYPE=Debug
	$(CMAKE) --build build/sanitize
	ctest --test-dir build/sanitize --output-on-failure
thread-sanitize:
	$(CMAKE) -S . -B build/thread-sanitize -DTINYPLC_THREAD_SANITIZE=ON -DCMAKE_BUILD_TYPE=Debug
	$(CMAKE) --build build/thread-sanitize
	ctest --test-dir build/thread-sanitize --output-on-failure
blink:
	$(CMAKE) -S . -B build/blink -DTINYPLC_BLINK=ON -DCMAKE_TOOLCHAIN_FILE=cmake/arm-none-eabi.cmake
	$(CMAKE) --build build/blink
flash-blink: blink
	$(OPENOCD) -f interface/stlink.cfg -f target/stm32f4x.cfg -c "program build/blink/blink.elf verify reset exit"
help:
	@echo "make compiler | llvm-example | aot-arm | run | test | test-compiler | test-llvm | test-abi | test-loader | loader-target-check"
	@echo "Historical checks: test-legacy | run-legacy | sanitize | thread-sanitize"
	@echo "Board bring-up: blink | flash-blink"

# Explicit local prerequisites only; no download and no flashing.
.PHONY: target-build target-verify
target-build: compiler
	$(PYTHON) scripts/build_target.py --kernel-archive "$(FREERTOS_ARCHIVE)" --gcc-prefix "$(ARM_PREFIX)"
target-verify:
	$(PYTHON) scripts/verify_target.py --gcc-prefix "$(ARM_PREFIX)"
	$(PYTHON) scripts/verify_placement.py --gcc-prefix "$(ARM_PREFIX)"

.PHONY: test-scan
test: test-scan
test-scan:
	mkdir -p build/scan
	$(CLANG) -std=c11 -O2 -Wall -Wextra -Werror -fsanitize=address,undefined -Iruntime/include runtime/src/scan.c tests/scan/scan_test.c -o build/scan/scan-test
	./build/scan/scan-test

.PHONY: test-frame
test: test-frame
test-frame:
	mkdir -p build/scan
	$(CLANG) -std=c11 -O2 -Wall -Wextra -Werror -fsanitize=address,undefined -Iport/nucleo_f446re/native tests/target/frame_test.c -o build/scan/frame-test
	./build/scan/frame-test

.PHONY: wire-generate test-wire
wire-generate:
	$(PYTHON) scripts/generate_wire.py
test: test-wire
test-wire:
	$(PYTHON) scripts/generate_wire.py --check
	CLANG="$(CLANG)" $(PYTHON) -m unittest discover -s tests/wire -v

# Uses the explicitly installed target linker; no downloads or hardware access.
.PHONY: test-loader
test-loader: compiler
	CLANG="$(CLANG)" ARM_LD="$(ARM_PREFIX)ld" $(PYTHON) -m unittest discover -s tests/loader -v

.PHONY: loader-target-check
test: test-loader
loader-target-check:
	$(PYTHON) scripts/check_loader_target.py --gcc-prefix "$(ARM_PREFIX)"

.PHONY: test-engineering
test: test-engineering
test-engineering: compiler
	CLANG="$(CLANG)" $(PYTHON) -m unittest discover -s tests/engineering -v
