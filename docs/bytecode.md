# Bytecode v1

> Historical M0–M2 record. The selected architecture is now the
> [Rust frontend → LLVM AOT → C/RTOS runtime](../README.md).
> Bytecode/Python remain independent test references, not the product path.

Implemented and tested by the M1 C core and M2 compiler/reference interpreter. See [language.md](language.md) for source semantics and [host tools](../host/README.md) for compilation and disassembly. All multibyte fields are little-endian, with no C struct padding.

## Image layout

| Header offset | Size | Field |
| --- | --- | --- |
| 0 | 4 | ASCII `TPLC` magic |
| 4 | 2 | format version = 1 |
| 6 | 2 | header size = 24 |
| 8 | 2 | code length, 1..2048 bytes |
| 10 | 2 | tag count, 0..64 |
| 12 | 2 | required max stack, 0..64 |
| 14 | 2 | flags = 0; reject unknown bits |
| 16 | 4 | total image bytes = 24 + 36 × tag_count + code_length |
| 20 | 4 | CRC32 of entire image with bytes 20..23 treated as zero |

CRC32 is CRC-32/ISO-HDLC: reflected polynomial `0xEDB88320`, initial `0xFFFFFFFF`, final XOR `0xFFFFFFFF`, check `123456789` → `0xCBF43926`. It detects corruption; it does not authenticate a program.

The header is followed by `tag_count` descriptors of 36 bytes, then code. Descriptor byte 0 is type (`1=BOOL`, `2=DINT`); byte 1 is class (`1=INPUT`, `2=OUTPUT`, `3=VAR`); bytes 2..3 are zero reserved; bytes 4..35 are a NUL-terminated uppercase ASCII identifier, 1..31 characters plus zero padding. Reject duplicate names, invalid identifiers, invalid types/classes, nonzero reserved fields, and missing terminators. A tag's index is its position in this table. Initial tag values are zero and are stored separately from the immutable image. I/O names/types are checked against the runtime's fixed board profile as well as by the compiler. Maximum image size is 4376 bytes; 2 KB limits code, not the complete image.

## Instructions

PC is a byte offset relative to code start. Tag operands are u8. Jump operands are absolute u16 code offsets. A value is a 32-bit cell; type checking occurs during validation. PUSH_CONST carries a u8 type followed by a 4-byte bit pattern. BOOL constants must be 0 or 1. Stack notation uses `a b` with b on top. All numeric comparisons produce BOOL; equality/inequality also accept two BOOLs of the same type.

| Opcode | Name | Operand bytes | Stack effect |
| --- | --- | --- | --- |
| 0x01 | PUSH_CONST | type:u8, value:u32 | → value |
| 0x02 | LOAD | tag:u8 | → tag value |
| 0x03 | STORE | tag:u8 | value → (updates tag; INPUT rejected) |
| 0x10 | ADD | none | DINT a b → a+b |
| 0x11 | SUB | none | DINT a b → a-b |
| 0x12 | MUL | none | DINT a b → a*b |
| 0x13 | DIV | none | DINT a b → a/b |
| 0x14 | NEG | none | DINT a → -a (unary minus) |
| 0x20 | AND | none | BOOL a b → a AND b |
| 0x21 | OR | none | BOOL a b → a OR b |
| 0x22 | XOR | none | BOOL a b → a XOR b |
| 0x23 | NOT | none | BOOL a → NOT a |
| 0x30 | EQ | none | a b → a=b |
| 0x31 | NE | none | a b → a<>b |
| 0x32 | LT | none | DINT a b → a<b |
| 0x33 | GT | none | DINT a b → a>b |
| 0x34 | LE | none | DINT a b → a<=b |
| 0x35 | GE | none | DINT a b → a>=b |
| 0x40 | JMP | target:u16 | → (branch) |
| 0x41 | JZ | target:u16 | BOOL condition → (branch if FALSE) |
| 0xFF | HALT | none | empty → end of scan |

For DINT arithmetic, operate on unsigned bit patterns, wrap modulo 2^32, and interpret results as signed for comparisons/division. Divide truncates toward zero. `INT32_MIN / -1` yields `INT32_MIN`; zero divisor faults. Logic evaluates both operands; short-circuiting is not part of v1.

## Worked encoding

With tag 0 = BTN and tag 1 = LED, `LED := NOT BTN;` encodes:

```text
offset  bytes   instruction       stack after
0       02 00   LOAD 0            [BTN]
2       23      NOT               [NOT BTN]
3       03 01   STORE 1           []
5       FF      HALT              []
```

The expression does not read GPIO. The port sampled GPIO into tag 0 before the VM ran, and will drive GPIO from tag 1 after successful execution. IF lowers to condition code, JZ over its THEN block, and JMP over subsequent ELSE blocks. ELSIF repeats that pattern.

## Validator and faults

Reject bad magic/version/CRC/lengths; extra/truncated bytes; unknown opcodes; malformed operands; unsupported I/O; out-of-range indices; writes to inputs; jumps outside code or into operands; backward/self jumps; mismatched operand types; stack underflow/overflow; inconsistent branch merges; missing HALT; and nonempty stack at a reachable HALT. Verify computed maximum depth equals the header declaration. Scan budget remains 4096 instructions even though forward-only accepted code is bounded.

Fault codes: NONE=0, INVALID_IMAGE=1, STACK=2, BAD_OPCODE=3, TAG_BOUNDS=4, DIV_ZERO=5, INSTRUCTION_BUDGET=6, SCAN_OVERRUN=7, TYPE=8. Structural rejection happens before activation. The M1 scan wrapper clears output tags and preserves fault PC/opcode/reason; the port must write those values to physical outputs. SCAN_OVERRUN is reserved for M4 deadline enforcement. Image/header errors use PC=65535 to mean no instruction location. The standalone VM mutates a working tag array; use the scan wrapper for transactional state and output fault handling.

Unknown opcodes and invalid operands are rejected even in unreachable code. Typed stack propagation and declared maximum depth apply to reachable instructions. The instruction budget counts HALT; a path containing ten instructions requires a budget of at least ten. Validation uses an 18,432-byte caller-owned workspace with a depth and a 64-bit type mask per code offset. It is separate from the VM's 64-cell execution stack.
