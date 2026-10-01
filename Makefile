CMAKE ?= cmake
OPENOCD ?= openocd
.PHONY: sim run test sanitize thread-sanitize blink flash-blink help
sim:
	$(CMAKE) -S . -B build/sim
	$(CMAKE) --build build/sim
run: sim
	./build/sim/tinyplc-sim
test: sim
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
	@echo "make sim | run | test | sanitize | thread-sanitize | blink | flash-blink"
