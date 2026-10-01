CMAKE ?= cmake
CARGO ?= cargo
PYTHON ?= python3
CLANG ?= clang
LLVM_AS ?= llvm-as
LLVM_OPT ?= opt
OPENOCD ?= openocd
.DEFAULT_GOAL := compiler
.PHONY: compiler llvm-example aot-arm run test test-compiler test-llvm test-legacy sim run-legacy sanitize thread-sanitize blink flash-blink help
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
test: test-compiler test-llvm test-legacy
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
	@echo "make compiler | llvm-example | aot-arm | run | test | test-compiler | test-llvm"
	@echo "Historical checks: test-legacy | run-legacy | sanitize | thread-sanitize"
	@echo "Board bring-up: blink | flash-blink"
