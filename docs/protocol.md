# Native engineering protocol proposal (R3)

Unimplemented design proposal, revised for the native architecture. Parser, encoder, and engineering CLI implementation belong to R3. Same bytes on UART and TCP. One host connection, one request outstanding, bounded buffers; no unsolicited frames. Multi-byte numbers are little-endian.

## Native payload contract

Transfer a versioned native package, not LLVM IR, an arbitrary `.o`, or a desktop
`.so`. Before READY, validate target/Thumb/float ABI, package bounds, state schema,
entry points, memory alignment/capacities, permitted imports and relocations,
and the selected integrity/authenticity policy. The exact package layout is an
R2 deliverable. CRC checks transport corruption and does not authorize code.

INFO must advertise target identity/features, native ABI/package versions,
permitted code/data/stack sizes and alignment, available slot states and
supported operations. The research call ABI is not itself a wire format.
The framing and command IDs below are proposals, not implemented compatibility
promises. Final response layouts require golden fixtures before R3 acceptance.

## Frame

```text
start:u8=0xA5 | length:u16 | command:u8 | payload:length-1 bytes | crc16:u16
```

Length counts command plus payload, 1..257, making the maximum frame 262 bytes. CRC-16/CCITT-FALSE covers length bytes, command, and payload (not start or CRC): polynomial `0x1021`, initial `0xFFFF`, no reflection, no final XOR; `123456789` → `0x29B1`.

Responses use `request_command | 0x80`. Every response payload starts with status:u8: OK=0, BAD_REQUEST=1, CRC_ERROR=2, BUSY=3, INVALID_IMAGE=4, NO_PROGRAM=5, NOT_WRITABLE=6, FAULT=7, UNSUPPORTED=8. No success-only response omits status. After a framing error, reset and search for start; after a rejected candidate, bounded replay of its remaining bytes preserves possible embedded starts. Reset a partially received frame after 100 ms without a new byte. Drop bad CRC frames rather than responding to an unreliable command; CRC_ERROR is reserved for valid-framed transfer content errors. Malformed lengths must not drive allocation.

## Commands

| ID | Command | Request after command byte | Planned success data after status |
| --- | --- | --- | --- |
| 0x01 | INFO | empty | protocol/image versions, capacities, slot states/generations, board identity |
| 0x02 | DOWNLOAD_BEGIN | total_bytes:u32 | transfer_id:u32; reserves inactive slot |
| 0x03 | DOWNLOAD_CHUNK | transfer_id:u32, offset:u32, bytes (1..240) | next_offset:u32 |
| 0x04 | DOWNLOAD_END | transfer_id:u32 | validated candidate generation:u32 |
| 0x05 | ACTIVATE | candidate_generation:u32 | accepted generation:u32; completion observed in status |
| 0x06 | ROLLBACK | empty | accepted generation:u32 |
| 0x07 | READ_TAGS | generation:u32, snapshot_scan:u64, first_index:u8, count:u8 | generation/scan sequence and bounded tag records |
| 0x08 | WRITE_TAG | generation:u32, index:u8, value:u32 | accepted; scan boundary applies it |
| 0x09 | GET_STATUS | empty | active generation, scan count, timing/jitter, overruns, fault and pending state |

Downloads are contiguous: offset must equal next_offset. An exact retransmission of the most recent chunk can be acknowledged idempotently; other duplicates/out-of-order chunks fail. DOWNLOAD_END validates the complete image and expected count. Abandoned transfers are discarded after a documented transfer timeout in R3. DOWNLOAD_BEGIN returns BUSY while an activation/migration owns the slot. Beginning a new download retires the old rollback image, exposed through INFO.

READ_TAGS paginates because 64 names cannot fit one frame. `snapshot_scan=0` starts a new enumeration (scan sequences start at 1); generation=0 accepts the captured active generation. Comms pins its owned snapshot for the entire enumeration, returning its generation and scan sequence on every page. Continuation requests must supply both returned identifiers. Release after the last page or 2 seconds of inactivity; stale identifiers produce BUSY and the host restarts. Values, types, names, scan count, and generation come from that one snapshot. Holding it cannot block the scan producer. WRITE_TAG rejects INPUT/OUTPUT and noncanonical BOOLs; it never writes directly into scan state. Full request queues return BUSY.

R3 must finalize exact response field layouts and width/unit definitions with cross-language golden frame fixtures before implementation. Timing values should be microseconds, signed jitter, and cumulative counters; they must not leak host struct layout. INFO's protocol version protects host/runtime compatibility.

## Connection and edits

`ACTIVATE` OK means queued, not executed. The CLI polls GET_STATUS to distinguish accepted, completed, rejected, or auto-rolled-back generations. ROLLBACK also executes only at a scan boundary. A transport timeout leaves outcome uncertain: reconcile status before retrying a mutation. The planned host transport uses loopback TCP port 6432; no listener exists yet. Framing and CRC are integrity checks, not authentication; remote access/authentication is outside v1.
