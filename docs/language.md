# Structured Text research subset (R1)

One source file contains `PROGRAM name`, zero or more declaration blocks,
statements, and `END_PROGRAM`, with no trailing tokens. Keywords and ASCII
identifiers are case-insensitive. Identifiers match `[A-Za-z_][A-Za-z_0-9]*`
and are at most 31 characters; keywords are reserved. `(* ... *)` comments
may span lines but do not nest. Diagnostics use one-based line and column.

Declarations are `name : BOOL;` or `name : DINT;` inside `VAR_INPUT`,
`VAR_OUTPUT`, or `VAR` blocks terminated by `END_VAR`. Multiple blocks are
allowed; duplicate names (including case variants) are rejected. No declaration
initializers, comma-separated names, or implicit conversions are supported.
All values initially equal zero. I/O declarations must match the selected
board profile's name, direction, and type. Inputs cannot be assigned.

Statements are `name := expression;` and
`IF expression THEN ... {ELSIF expression THEN ...} [ELSE ...] END_IF;`.
Conditions must be BOOL. Empty bodies and nested IFs are allowed. There are
no loops, calls, timers, or standalone empty statements.

Operator precedence, from lowest to highest:

| Operators | Associativity / operand types |
| --- | --- |
| OR | left / BOOL |
| XOR | left / BOOL |
| AND | left / BOOL |
| = <> | left / matching BOOL or DINT |
| < > <= >= | left / DINT |
| + - | left / DINT |
| * / | left / DINT |
| unary +, unary -, NOT | right / DINT, DINT, BOOL |
| literals, names, `(expression)` | parentheses override precedence |

Comparison results are BOOL; chained comparisons follow the table and must
still type-check. Logic evaluates both operands, even if the left value alone
determines the result. Decimal DINT literals range from 0 through 2147483647;
the immediately negated literal `-2147483648` is also accepted. Larger literal
magnitudes are errors. TRUE and FALSE are BOOL literals. Unary plus checks
DINT type and emits no instruction. Unary minus wraps, including on the
minimum DINT. Arithmetic wraps modulo 2^32; signed division truncates toward
zero, minimum DINT divided by -1 wraps, and division by zero faults at runtime.

The Rust compiler preserves declaration order as tag order and evaluates
expressions left to right. It emits LLVM IR with forward control flow and a
transactional scan entry point; see [the call ABI](../compiler/README.md).
Limits are 64 tags, 1 MiB source, 65,536 tokens, 4,096 expression nodes,
4,096 statements, and 64 levels of parser nesting. These bound compiler
resources; they are not a measured MCU execution-time guarantee.

Successful scans commit outputs and internal variables. Division faults clear
output cells and preserve previous internal values; the C supervisor must
apply the physical output policy. Inputs remain read-only. The current CLI
uses built-in logical BTN/LED bindings; the library accepts explicit bindings.

The historical M2 compiler implements these source semantics with different
backend limits: 2,048 bytecode bytes and 64 stack cells. Its standalone reference
interpreter exposes partial working values on faults; the differential tests
normalize those values to the R1 transactional ABI. See [M2](M2-report.md) and
[historical bytecode](bytecode.md). This is an explicitly small ST subset,
not full IEC 61131-3 conformance.
