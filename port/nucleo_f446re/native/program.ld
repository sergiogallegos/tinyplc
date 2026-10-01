/* Standalone native module placement, used by plcpack and placement tests.
 * The host selects one advertised inactive slot; no on-device fixups/imports.
 * This script intentionally owns no firmware or gateway storage. */
ENTRY(tinyplc_scan)
MEMORY { PROGRAM (rx) : ORIGIN = TINYPLC_CODE_BASE, LENGTH = 16K }
SECTIONS {
  .text : { KEEP(*(.text*)) . = ALIGN(4); } > PROGRAM
  .rodata : { KEEP(*(.rodata*)) . = ALIGN(4); } > PROGRAM
  .ARM.extab : { *(.ARM.extab*) } > PROGRAM
  .ARM.exidx : { *(.ARM.exidx*) } > PROGRAM
  .forbidden : {
    *(.data*) *(.bss*) *(COMMON) *(.tdata*) *(.tbss*)
    *(.init_array*) *(.fini_array*) *(.preinit_array*) *(.ctors*) *(.dtors*)
  } > PROGRAM
  /DISCARD/ : { *(.comment) *(.note*) *(.ARM.attributes) }
  ASSERT(TINYPLC_CODE_BASE == 0x20010000 || TINYPLC_CODE_BASE == 0x20014000,
         "unsupported program slot")
  ASSERT(SIZEOF(.forbidden) == 0, "native module must not own writable globals or constructors")
}
