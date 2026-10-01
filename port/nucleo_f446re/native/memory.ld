/* R2.3 experimental layout. See docs/memory-layout.md and ST DS10693/PM0214. */
ENTRY(Reset_Handler)
MEMORY {
  PRIV_FLASH (rx) : ORIGIN = 0x08000000, LENGTH = 64K
  CALL_FLASH (rx) : ORIGIN = 0x08010000, LENGTH = 4K
  PRIV_RAM (rw) : ORIGIN = 0x20000000, LENGTH = 64K
  CODE_A (rx) : ORIGIN = 0x20010000, LENGTH = 16K
  CODE_B (rx) : ORIGIN = 0x20014000, LENGTH = 16K
  INPUTS (r) : ORIGIN = 0x20018000, LENGTH = 512
  WORK (rw) : ORIGIN = 0x20018200, LENGTH = 512
  USER_STACK (rw) : ORIGIN = 0x20018800, LENGTH = 2K
}
__privileged_functions_start__ = ORIGIN(PRIV_FLASH);
__privileged_functions_end__ = ORIGIN(PRIV_FLASH) + LENGTH(PRIV_FLASH);
/* Limit the port's unprivileged flash region to the system-call veneers. */
__FLASH_segment_start__ = ORIGIN(CALL_FLASH);
__FLASH_segment_end__ = ORIGIN(CALL_FLASH) + LENGTH(CALL_FLASH);
__privileged_data_start__ = ORIGIN(PRIV_RAM);
__privileged_data_end__ = ORIGIN(PRIV_RAM) + LENGTH(PRIV_RAM);
__SRAM_segment_start__ = 0x20000000;
__SRAM_segment_end__ = 0x20020000;
_estack = ORIGIN(PRIV_RAM) + LENGTH(PRIV_RAM);
SECTIONS {
  .isr_vector : { KEEP(*(.isr_vector)) } > PRIV_FLASH
  .text : { *(privileged_functions)
    *(EXCLUDE_FILE (*user_program.o) .text*)
    *(EXCLUDE_FILE (*user_program.o) .rodata*) } > PRIV_FLASH
  .ARM.exidx : { *(.ARM.exidx*) } > PRIV_FLASH
  .syscalls : {
    __syscalls_flash_start__ = .;
    KEEP(*(freertos_system_calls))
    __syscalls_flash_end__ = .;
  } > CALL_FLASH
  .gateway : { KEEP(*(.user_gate)) } > CALL_FLASH
  .data : {
    . = ALIGN(4); _sdata = .; *(privileged_data) *(.data*)
    . = ALIGN(4); _edata = .;
  } > PRIV_RAM AT > PRIV_FLASH
  _sidata = LOADADDR(.data);
  .bss (NOLOAD) : {
    . = ALIGN(8); _sbss = .; *(.bss*) *(COMMON)
    . = ALIGN(8); _ebss = .;
  } > PRIV_RAM
  .retained (NOLOAD) : { KEEP(*(.retained)) } > PRIV_RAM
  .user_program : {
    _suser = .;
    KEEP(*user_program.o(.text* .rodata*))
    . = ALIGN(4); _euser = .;
  } > CODE_A AT > PRIV_FLASH
  _siuser = LOADADDR(.user_program);
  .code_b (NOLOAD) : { . += LENGTH(CODE_B); } > CODE_B
  .inputs (NOLOAD) : { KEEP(*(.inputs)) } > INPUTS
  .working (NOLOAD) : { KEEP(*(.working)) } > WORK
  .user_stack (NOLOAD) : { KEEP(*(.user_stack)) } > USER_STACK
  /DISCARD/ : { *(.comment) *(.note*) }
  ASSERT(ADDR(.retained) + SIZEOF(.retained) <= _estack - 4096, "privileged RAM overflow: reserve 4K MSP")
  ASSERT(ADDR(.gateway) + SIZEOF(.gateway) <= ORIGIN(CALL_FLASH) + LENGTH(CALL_FLASH), "firmware gateway overflow")
  ASSERT(SIZEOF(.user_program) <= LENGTH(CODE_A), "code A overflow")
  ASSERT(SIZEOF(.inputs) <= LENGTH(INPUTS), "input region overflow")
  ASSERT(SIZEOF(.working) <= LENGTH(WORK), "working region overflow")
  ASSERT(SIZEOF(.user_stack) == LENGTH(USER_STACK), "stack reservation mismatch")
  ASSERT((ORIGIN(CODE_A) & (LENGTH(CODE_A)-1)) == 0, "code A MPU alignment")
  ASSERT((ORIGIN(CODE_B) & (LENGTH(CODE_B)-1)) == 0, "code B MPU alignment")
  ASSERT((ORIGIN(INPUTS) & (LENGTH(INPUTS)-1)) == 0, "inputs MPU alignment")
  ASSERT((ORIGIN(WORK) & (LENGTH(WORK)-1)) == 0, "work MPU alignment")
  ASSERT((ORIGIN(USER_STACK) & (LENGTH(USER_STACK)-1)) == 0, "stack MPU alignment")
}
