# R3.1 native wire contract v1

This is tinyPLC's original educational contract for the F446 local-lab profile.
It freezes serialization. [R3.2](R3.2-report.md) implements portable package
validation/staging and a Rust encoder; [R3.3](engineering-transport.md) adds
the board serial endpoint and activation.
The source of numeric IDs, limits, widths and field order is
[`contract/wire.json`](../contract/wire.json). `make wire-generate` produces
[C constants](../contract/wire_generated.h), [Rust constants](../contract/src/generated.rs)
and [offset tables](wire-layouts.md). `make test-wire` rejects generated drift.
Do not copy a native C/Rust struct onto the wire. Decode little-endian fields
with bounds checks; C enums, padding and pointer widths are not serialized.

## Package v1

A package is exactly `80-byte header | payload | tag records`. There is no
optional section, trailing data, import table, relocation table or signature.
Maximum size is 19,024 bytes: 80 + 16,384 + 64 × 40. This is a **transfer size**,
not the code-slot reservation: only the payload belongs in the 16 KiB code
slot. Header/schema parsing and storage have a separate bounded [loader budget](native-loader.md);
do not copy a whole package into a code slot.

The header uses magic bytes `54 50 43 4e` (`TPCN`), format 1, native kind 1,
F446 target 1, native ABI 2 and runtime-contract revision 1. These target/ABI
IDs mean ARMv7E-M Thumb, little-endian, base AAPCS soft-float and the restrictions
in [native-abi.md](native-abi.md). Compatibility is exact equality in v1.
Unknown versions/kinds/targets/authentication IDs fail closed; no bytecode or
unsigned downgrade fallback. `auth=0` means unsigned lab and additionally
requires the firmware's own explicit opt-in. Flags and all reserved bytes
must be zero.

Placement and bounds are validated before any address calculation or copy:

- Header length is exactly 80 and declared total equals received length.
- Payload offset is exactly 80. Payload length is 4..16,384, divisible by four.
  The trusted packager includes any necessary zero alignment padding inside
  this length. Link base equals the reserved A or B slot, never a supplied
  arbitrary address.
- Text offset is relative to the payload. Text offset/length and entry offset
  are even; text length is at least two. The entire text interval fits inside
  the payload. The entry's first two bytes fit inside that text interval.
  The runtime derives `(link_base + entry_offset) | 1` only after checking.
  Constants/padding may exist outside text. This declaration does not prove
  that arbitrary native branches remain in text; MPU isolation is still needed.
- Tag offset equals `80 + payload_bytes`. Tag count is 1..64, record size 40,
  and `tags_offset + count × 40` equals total bytes exactly. Use subtraction
  checks or checked arithmetic, not unchecked offset-plus-length comparisons.
- Cell width is exactly four; requested worker stack is exactly 2,048 bytes.
  Neither value grants additional memory or proves native stack sufficiency.

A tag record is `name[32], type:u8, class:u8, binding:u16, reserved:u32`.
Names are 1..31 ASCII bytes matching `[A-Z_][A-Z0-9_]*`, followed by a NUL and
zero padding. Names are unique; declaration order is tag index and cell offset
is `index × 4`. Type IDs are BOOL=1, DINT=2; classes INPUT=1, OUTPUT=2, VAR=3.
Cold activation initializes all cells to zero; R4 healthy activation may migrate
compatible VAR cells under the [state contract](online-state.md). There are no pointer or nonzero-initializer
records. BOOL values are 0/1; DINT values are two's-complement 32-bit cells.

The board binding is independent of the tag's name. INPUT requires BOOL and
binding 1 (BTN/PC13, inverted). OUTPUT requires BOOL and binding 2 (LED/PA5,
safe FALSE). VAR requires binding 0 and permits BOOL or DINT. Each physical
binding may occur at most once. A schema need not use every binding; an
unbound physical output stays safe. Unsupported type/class/binding combinations
are rejected before READY. This profile does not support arbitrary pin numbers.

`schema_crc` is CRC-32/ISO-HDLC over the exact tag-record bytes. `package_crc`
is the same CRC over the entire package with bytes 64..67 treated as zero.
The schema CRC remains populated when calculating package CRC. Reflection,
polynomial, initial/final XOR and check values are in the contract; the check
for `123456789` is `0xcbf43926`. A fingerprint does not replace full schema
comparison. Neither CRC authenticates or proves the safety of native code.

## Supervisor dispatch descriptor

At input-region byte offset 256 (`0x20018100`), reserve 16 bytes:
`entry:u32, tag_count:u32, generation:u32, reserved:u32`. This is a firmware
memory ABI, **not a package field or writable engineering command**. The
supervisor alone publishes it while the worker is suspended, coordinated with
the selected slot's MPU mapping. Entry is a validated Thumb pointer, count is
1..64, generation nonzero, reserved zero. Inactive/disabled descriptor is all
zero and must never be invoked. The R3.3 firmware gateway consumes it; R2's earlier gateway used a static entry/count.

## Framing and errors

`A5 | length:u16 | command:u8 | payload | crc16:u16` has length 1..257,
counting command plus payload; total bytes are length + 5, at most 262.
CRC-16/CCITT-FALSE covers the two length bytes, command and payload, excluding
start and trailing CRC. Check value for `123456789` is `0x29b1`.

Responses use `command | 0x80`. Every success has status zero followed by the
exact response layout in [wire-layouts.md](wire-layouts.md). Every error contains
**only one status byte**, with no success fields. Wrong request widths, trailing
bytes, zero-length chunks or invalid argument encodings yield BAD_REQUEST.
Unknown commands yield UNSUPPORTED. Unsupported known operations do too.
Response-direction commands received by the device are dropped, preventing
response loops. CRC-bad frames are silently dropped: their command is untrusted.
CRC_ERROR is reserved for a valid-framed completed transfer with a bad package
CRC; other package validation failures yield INVALID_IMAGE.

Only one host request is outstanding. Frame timeout is 100 ms since the last
byte. After invalid framing, bounded replay/search of the rejected bytes must
preserve a possible embedded start; no received length drives allocation.
R3.3 implements UART stream parsing and bounded replay, with separate streaming
tests. The R3.1 fixture consumers still intentionally test complete frames only.

## Commands and exact tails

All fixed fields are generated in the layout tables. There are two variable tails:
DOWNLOAD_CHUNK adds 1..240 bytes after its eight-byte request prefix. READ_TAGS
adds exactly `count` 40-byte `tag_value` records after its 16-byte success prefix.
The latter replace the schema record's reserved u32 with the value u32.
No other request or response has a tail. READ_TAGS count is 1..5 in requests;
the returned count is the smaller of requested count and remaining tags.

INFO returns versions/profile, policy/capabilities, command mask, budgets,
transfer status and two 16-byte slot records in A/B order. Command-mask bit
`command_id - 1` advertises an implemented operation. Capability bits explicitly
advertise unsigned lab, online migration, rollback and queued VAR writes;
reserved bits are zero. A runtime need not implement every operation in v1.
Transfer ID/offset/remaining milliseconds are zero when no transfer exists.
Slot base/capacity are the fixed profile values; states distinguish EMPTY,
ACTIVE, RECEIVING, READY, PENDING and PREVIOUS. Generation is zero for EMPTY
and RECEIVING; all validated program states carry a nonzero generation.

DOWNLOAD_BEGIN reserves the inactive slot for a declared bounded package size
and returns transfer ID, base, code capacity and 30,000 ms timeout. It returns
BUSY if another transfer or activation owns the slot. It explicitly retires any PREVIOUS or READY
image there (READY is immutable until this new reservation). A transfer expires after 30,000 ms without an accepted chunk;
accepted exact duplicate chunks refresh expiry too. The host must reserve,
then link/select the matching slot package, and fit within that timeout.

Chunks are contiguous: offset must equal next offset and bytes must fit the
remaining declared total. An exact retransmission of the latest chunk only
is acknowledged without rewriting. Different bytes at that offset and any
other duplicate/out-of-order offset yield BAD_REQUEST without mutation.
Unknown/expired transfer IDs yield BAD_REQUEST. END requires the complete
count; validation failure releases the reservation. Success makes the slot
immutable READY and returns a fresh candidate generation. A repeated END is
not assumed idempotent: reconcile INFO after an uncertain response.

ACTIVATE names a READY generation. OK acknowledges a queued boundary request,
not execution. BUSY covers occupied queues/slots; stale or non-READY candidates
are BAD_REQUEST. R3 activation resets state to zero. R4 advertises migration and rollback through
CAP_ONLINE_MIGRATION/CAP_ROLLBACK; healthy activations migrate same-name/type
VARs, while faulted sources cold-start. ROLLBACK queues the retained PREVIOUS
generation, or returns NO_PROGRAM if there is none. A successful rollback
consumes that checkpoint; an accepted BEGIN retires it. Older firmware returns
UNSUPPORTED for ROLLBACK. Fault recovery
policy cannot be inferred from a package CRC or a pending flag.
[The state contract](online-state.md) specifies migration, one-shot rollback
and exact request outcomes. R4.2 implements it; R3 firmware does not advertise it.

GET_STATUS returns active generation (zero when absent), monotonically
increasing u64 scan sequence, execution state, latest activation outcome,
requested and pending generations, latched fault, last/max work time in µs,
signed release jitter in µs, and cumulative missed releases. Pending generation
is zero when none; requested generation persists with its last outcome until a
new request. Times round elapsed cycles upward to µs; jitter is actual minus
scheduled release, rounded away from zero and saturated to i32. Counters
saturate rather than wrap. Outcome ROLLED_BACK refers to the rejected request;
active generation identifies what actually runs. R3.3 implements these diagnostics; R3.4/R3.5 add coherent tag monitoring.
The fault field describes the current execution fault, not a recovered update
failure. R4 keeps those causes separate without changing this response.

GET_UPDATE_STATUS (command 10, INFO command-mask bit 9) returns the coherent
53-byte retained update record defined in [online-state.md](online-state.md).
It separates first-trial and recovery faults from current execution. Before any
accepted request its fields are zero; a new accepted ACTIVATE/ROLLBACK clears it,
while rejected requests and ordinary scans do not. The additive operation uses
protocol v1; no existing command encoding or native package field changes.

READ_TAGS `snapshot_scan=0, first_index=0` starts enumeration; generation zero
accepts the captured active generation, otherwise it must match. Continuations
supply the returned generation/scan pair and an in-range first index. A pinned
snapshot supplies names, types, bindings and values for every page. Release it
after the last page or 2,000 ms inactivity. Missing/stale snapshots yield BUSY;
no active program yields NO_PROGRAM. Holding it cannot block the scan producer.

WRITE_TAG is optional, VAR-only and generation checked. INPUT/OUTPUT yields
NOT_WRITABLE; bad index/value yields BAD_REQUEST; a full request queue yields
BUSY. Its success carries generation and `apply_after_scan`: a reservation to
apply immediately after that completed scan, before the next scan prepares
working state. Monitoring a later scan confirms the observed value, which
program logic may subsequently change. Activation and writes must not reserve
conflicting boundaries; return BUSY instead. Faulted execution rejects writes
with FAULT. No direct comms writes to live state are permitted.

Transfer IDs and generations are nonzero, never reused during one boot; refuse
new allocations on u32 exhaustion. All handles expire at reset/reconnection.
The host flushes transport input, obtains fresh INFO and abandons cached handles
before mutation. V1 has no boot nonce or cryptographic replay protection; it
assumes a direct local serial session and does not authorize remote transports.
After a timeout in that session, reconcile INFO/GET_STATUS before repeating a
mutation. There is no implicit acknowledgement of successful execution.

## Compatibility and test boundary

A format or protocol version changes when an existing byte layout/meaning
changes. Reserved fields remain zero until a versioned extension specifies
them. Runtime-contract revision changes when accepted native assumptions change.
Capability negotiation alone cannot redefine a field's encoding.

[Golden fixtures](../tests/wire/fixtures) cover both slot headers, canonical tags,
a dispatch descriptor, all nine request/success examples, an error and maximum
chunk. The tiny payload is hand-encoded Thumb `movs r0,#0; bx lr`, **not ST logic
and never flashed**. Independent C/Rust fixture consumers exercise byte readers,
CRCs and envelope ranges, including truncation/overflow cases. They deliberately
are not the production validator: target/ABI/schema checks, firmware policy, slot ownership and transactional
staging are implemented separately in R3.2, with streaming/activation in R3.3.
