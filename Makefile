CMAKE ?= cmake
OPENOCD ?= openocd
.PHONY: sim run test blink flash-blink help
sim:
	$(CMAKE) -S . -B build/sim
	$(CMAKE) --build build/sim
run: sim
	./build/sim/toyplc-sim
test: sim
	ctest --test-dir build/sim --output-on-failure
blink:
	$(CMAKE) -S . -B build/blink -DTOYPLC_BLINK=ON -DCMAKE_TOOLCHAIN_FILE=cmake/arm-none-eabi.cmake
	$(CMAKE) --build build/blink
flash-blink: blink
	$(OPENOCD) -f interface/stlink.cfg -f target/stm32f4x.cfg -c "program build/blink/blink.elf verify reset exit"
help:
	@echo "make sim | run | test | blink | flash-blink"
