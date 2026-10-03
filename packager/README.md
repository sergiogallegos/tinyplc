# plcpack — host-native package builder

`plcpack` compiles the ST subset through our Rust frontend and LLVM, links for
one reserved slot, reads compiler-exported tag metadata from the linked ELF,
and writes an unsigned lab package. All code runs on the PC; there is no
upload or board access. Dependencies are the project's own compiler/contract
crates and Rust's standard library, plus installed LLVM and ARM GNU ld tools.

```sh
cargo build --workspace --locked --offline
./target/debug/plcpack examples/button_led.st --slot B -o build/button-b.tplc \
  --clang /path/to/clang --ld /path/to/arm-none-eabi-ld
```

Tools default to `clang` and `arm-none-eabi-ld` on PATH. Use absolute tool paths
when overriding them. The output parent directory must exist. The CLI refuses
to overwrite its ST input and finishes compilation/link validation before
writing output. A failed compile leaves an existing output untouched. Temporary
build directories are uniquely created and cleaned after success or failure.

The pipeline emits ABI 2 LLVM IR, compiles with Cortex-M4/Thumb/soft-float flags
at O2, then uses the project's fixed-slot link script. The ELF reader checks
ARM ELF32 identity, EABI/float mode, bounded/nonoverlapping allocated sections,
no writable/zero-fill payload, no remaining relocations or undefined imports
(including weak imports), one text section and a Thumb function entry. It
extracts ABI, count, names, types and classes from `tinyplc_*` exported symbols.
It does not accept a separate user-edited tag database. The built-in board
profile maps BOOL INPUT BTN and BOOL OUTPUT LED; internal variables have no
physical binding.

The packager pads the payload to four bytes, serializes the generated contract
fields and computes schema/package CRCs. It is a trusted host build tool, not
an ELF loader on the MCU and not a signature service. Package A and B are
separate placement artifacts, even if a particular example produces identical
payload bytes. The engineering CLI checks that the package matches the available slot and
the base returned by DOWNLOAD_BEGIN. See [wire contract](../docs/wire-format.md),
[C staging](../docs/native-loader.md) and [R3.2 evidence](../docs/R3.2-report.md).

For TON, package [ton_led.st](../examples/ton_led.st) in the same way. The
compiler adds timer state and a frozen millisecond clock binding automatically;
the board must run the R5.1 firmware. See [TON semantics](../docs/ton.md).
