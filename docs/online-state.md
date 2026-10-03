# R4.1 — migration, trial and rollback contract

Decision recorded 2026-10-02. [R4.2](R4.2-report.md) implements and host-tests
this contract; [R4.3](R4.3-report.md) records board acceptance. Older R3 firmware
still cold-starts activations and rejects ROLLBACK; negotiate INFO capabilities.

The profile remains ABI 2, BOOL/DINT, 64 tags, one u32 cell per tag, two fixed
native-code slots, one engineering host and a 10 ms scheduled release. There
is no new language syntax, persistence, tag-write support or cold/warm selector.
All names below are canonical names from validated package metadata.

## Migration and initialization

An ACTIVATE request reserves a READY generation. At the next scan boundary,
before input sampling and candidate entry, the scan owner captures the latest
committed source state. Values are captured at application time, not when the
host receives its acknowledgement. Migration uses this captured state and
immutable source/target schemas.

| Target tag | Initial value before its first scan |
| --- | --- |
| VAR with an exact-name source VAR of the same type | Source committed u32 value |
| New or renamed VAR | Zero (`FALSE` or DINT 0) |
| Same name but different type or source class | Zero; no conversion or rejection solely for this difference |
| INPUT | Working/committed cell zero; input image freshly sampled by binding |
| OUTPUT | Zero; candidate code computes its first proposal |

Declaration order and index may change; offsets do not identify variables.
BOOL and DINT must match exactly. A schema CRC match is not a substitute for
metadata validation or permission checks. A valid BOOL source value is 0 or 1;
all u32 patterns are valid DINT values. A malformed trusted state/schema or
mismatched checkpoint identity fails closed before copying/entry; it is not
silently treated as a type conversion. If this check fails after request acceptance,
keep the current source selected, force outputs FALSE, latch BAD_STATE, clear
pending and complete the request as REJECTED. No candidate scan or automatic
recovery is attempted; the retained update record has no failed trial scan.
Names are already uppercase, unique,
zero-padded ASCII identifiers; no locale-dependent matching is performed.
Removed tags are ignored. No pointer, diagnostic, stack, input or output value
is migrated. The language has no declaration initializers; zero is the only
new-variable initializer in this profile.

An activation from a fault-latched source cold-initializes all target cells,
even same-name VARs. It creates no rollback checkpoint of that source. This
preserves R3's explicit recovery route and never automatically resumes a
program already faulted before the request. With a healthy source, migration
and rollback are always enabled when the R4 capabilities are advertised.
The existing ACTIVATE payload does not select modes.

Example: source `[N:VAR DINT=41, FLAG:VAR BOOL=1, LED:OUTPUT BOOL=1]`
and target `[FLAG:VAR BOOL, NEW:VAR DINT, N:VAR DINT, LED:OUTPUT BOOL]`
start the candidate with `[1, 0, 41, 0]`. If it executes `N := N + 7`, its
first successful commit contains `N=48`. Changing N to BOOL instead starts
it at FALSE. Changing FLAG from VAR to INPUT samples it from its binding
(unbound inputs are zero); it does not preserve the old TRUE.

## Scheduled boundary and first scan

One request may be reserved at a time. ACTIVATE acceptance pins the source
identity and candidate identity, including their slot indices/generations.
The request holds no unowned pointers. The scan owner rechecks these identities
before preparing the candidate. The entire preparation is part of scan timing.

1. After the prior scan has completed, enter the next scheduled release.
   Capture the healthy source's committed VAR cells and source descriptor as
   the rollback checkpoint. The source schema/code remain pinned in their slot.
2. Build a fresh target state: zero every cell, then copy eligible VARs.
   Destroy the suspended old worker context and construct a fresh candidate
   worker with the correct slot/MPU mapping and dispatch generation. Never
   preserve the old task stack or resume a frame from another generation.
3. Sample inputs for the target schema, zero unbound/non-input image cells,
   and freeze the image until the one candidate invocation finishes. Keep
   working INPUT cells zero. Set all target OUTPUT cells to zero before entry.
4. Execute one candidate scan under the existing guard. Validate result,
   canonical BOOL values, reserved INPUT cells, generation and elapsed time.
   Only an accepted result may commit target VAR/OUTPUT cells or drive outputs.
5. On success, publish the target snapshot and complete the request. Keep the
   healthy source checkpoint as PREVIOUS. On contained failure, follow the
   recovery rules below. Release reservations only at a completed transition.

There is one native invocation per scheduled release. Recovery does not add a
second invocation into a failed candidate's release. The scan sequence remains
monotonic across activations and rollbacks; it never resets with a generation.
Input/output bindings may change. Sample the target inputs by the target
schema and force unused physical outputs FALSE on commit. Until commit, the
prior physical output can remain applied; on a detected fault force FALSE.
Preserving VAR values does not promise unchanged physical output behavior.

The first-scan trial extends through the trusted scan body and release/deadline
check, including migration, context setup, publication and housekeeping. Keep
both slots reserved until this check completes. A late detected overrun can
occur after a physical output write; force FALSE and publish corrected fault
state. It cannot undo a pulse already emitted. Deadline recovery skips missed
releases using the existing scheduler policy; no catch-up burst is allowed.

After one fully successful trial, later faults latch normally. They do not
trigger automatic rollback. An explicit rollback may still use PREVIOUS.

## Checkpoint and slot ownership

The checkpoint contains a validity flag, exact slot/generation identity,
validated descriptor/count, and up to 64 saved cells in that source schema's
order. Save only VAR values; all saved INPUT/OUTPUT cells are zero. It represents
the source immediately before activation and never follows target updates.
The existing per-slot schema is immutable while the checkpoint is valid;
there is no third schema copy and no native-stack checkpoint.

| Phase | Slot use | Engineering mutations |
| --- | --- | --- |
| Idle, healthy source, candidate READY | Source ACTIVE; candidate READY | ACTIVATE may reserve candidate |
| Accepted activation | Source ACTIVE; target PENDING | BEGIN/ACTIVATE/ROLLBACK all BUSY |
| Candidate first scan | Target ACTIVE; source PREVIOUS if checkpoint valid, otherwise retired | All mutations BUSY through trial completion |
| Candidate accepted | Target ACTIVE; healthy source PREVIOUS | ROLLBACK may reserve PREVIOUS; BEGIN may retire it |
| Recovery queued/executing | Failing/returning contexts reserved by transaction | All mutations BUSY |
| Rollback completed or failed | Restored target ACTIVE; departing slot EMPTY | No further rollback checkpoint |

A transaction phase is required in addition to wire slot states. PREVIOUS
during a trial is reserved and is not available to BEGIN or ROLLBACK. Existing
checks for PENDING alone are insufficient. A no-checkpoint source may be
logically retired at installation, but neither slot becomes writable while the
transaction is in progress. READ_TAGS/GET_STATUS/INFO remain available.

A valid DOWNLOAD_BEGIN in idle phase can atomically retire PREVIOUS and its
checkpoint while reserving that exact slot. Rollback becomes unavailable at
BEGIN success, even if the transfer later expires or fails validation. A
rejected BEGIN must preserve the checkpoint. A simultaneous rollback reservation
and BEGIN must have one winner: the loser sees BUSY or NO_PROGRAM as appropriate
to the resulting state. Check/reserve/invalidate is one serialized ownership
operation, not separate checks around a preemptible copy.

No schema search, cell copy, CRC, task recreation or package copy belongs inside
a scan-blocking critical section. Use bounded index/identity transitions under
the existing board serialization, then copy only exclusively owned data.
The portable implementation must state its ownership contract; volatile fields
alone are not C-thread synchronization. R4.2 interleaving tests must exercise
the same transitions used by the board adapter.

The boot program has a complete retained descriptor/schema before its RAM
slot can be retired. R4 registers its entry/count/schema/bindings in the same
checkpointable representation as a downloaded image. R3 had copied its metadata
only for monitoring. Never dereference boot-exported constants after slot A reuse.

## Automatic recovery and explicit rollback

A recoverable failure is one for which the native guard has returned control
to a trusted supervisor and the source checkpoint remains valid. This includes
language faults, contained access/return faults, validated bad result/state,
and contained deadline aborts. Privileged corruption, invalid trusted metadata,
unrecoverable exception frames and watchdog resets do not authorize recovery.

On a contained candidate first-scan failure with a healthy checkpoint:

- Discard candidate working changes, force outputs FALSE, retain its generation,
  fault and diagnostic, and publish a failed candidate snapshot with its
  initialized committed VAR state and zero outputs.
- Queue restoration for the next scheduled release. Keep both slots reserved.
  Requested generation remains the rejected candidate; pending generation
  identifies the source being restored.
- Recreate a fresh worker for the checkpointed source. Restore its saved VARs,
  zero OUTPUT/INPUT state, resample inputs, and execute one scan. No reverse
  name matching from the candidate is performed.
- If that scan succeeds, mark the source ACTIVE/RUNNING, publish its new
  committed snapshot, record ROLLED_BACK for the rejected activation and clear
  pending. Retire the failed candidate slot to EMPTY, clear its generation and
  consume the checkpoint. There is no automatic retry of that candidate.
- If restoration fails, leave the restored source ACTIVE/FAULT with outputs
  FALSE, pending zero and outcome REJECTED. Retain both original and recovery
  fault causes. Consume the checkpoint and retire the candidate. Do not bounce
  between programs or attempt another automatic recovery.

Without a healthy checkpoint, a candidate failure stays ACTIVE/FAULT and
REJECTED with no pending recovery. A later successful explicit ACTIVATE can
cold-start another READY image. If reset occurs at any phase, RAM generations,
checkpoint and reservations are lost. Boot follows the existing R2 reset-fault
policy; there is no post-reset online rollback promise.

ROLLBACK reserves the retained PREVIOUS image and its saved state, even when
the current program is faulted. Its response names that target generation.
It restores saved pre-update VARs exactly, resamples INPUTs and starts OUTPUTs
at zero. Example: source N=41 was saved before activation, candidate later
reaches N=900; rollback of old code `N := N + 1` commits N=42 on its first scan,
not 901. This is restoration, not reverse migration.

Rollback is one-way and consumes the checkpoint. It does not save the departing
program as a new PREVIOUS, does not toggle images, and does not automatically
return to the departing program if the restored program fails. On explicit
rollback success, outcome is RUNNING for the requested rollback target; on
failure it is REJECTED with that target ACTIVE/FAULT. ROLLED_BACK is reserved
for automatic recovery of a rejected activation, preserving the v1 meaning.
A second rollback returns NO_PROGRAM until another healthy activation creates
a new checkpoint. Retired images need a new download/generation before reuse.

## Status and diagnostic compatibility

Package version 1, native ABI 2 and runtime contract 1 remain unchanged:
R4 uses the already defined state layout. Protocol v1 already reserves migration,
rollback and command capabilities. R4.2 advertises CAP_ONLINE_MIGRATION and
CAP_ROLLBACK only when both paths are implemented, tested and wired. ROLLBACK
command 6 retains its empty request and accepted-generation response.
Unknown or repeated ACTIVATE generations remain BAD_REQUEST; pending mutations
return BUSY. ROLLBACK without PREVIOUS returns NO_PROGRAM. Neither operation
has a general automatic transport retry. The CLI must reconcile actual
request outcome after timeout and report automatic recovery as activation
failure, even though the old program is running again.

GET_STATUS keeps its current field widths and meanings:

| Observation | Active generation | Execution/fault | Requested / pending | Outcome |
| --- | --- | --- | --- | --- |
| Accepted ACTIVATE C, source S still running | S | Existing source state | C / C | PENDING |
| First scan C succeeds | C | RUNNING / 0 | C / 0 | RUNNING |
| C fails, recovery to S queued | C | FAULT / candidate fault | C / S | PENDING |
| Recovery S succeeds | S | RUNNING / 0 | C / 0 | ROLLED_BACK |
| Recovery S fails | S | FAULT / recovery fault | C / 0 | REJECTED |
| C fails without checkpoint | C | FAULT / candidate fault | C / 0 | REJECTED |
| Explicit ROLLBACK S accepted | Departing generation | Existing state | S / S | PENDING |
| Explicit ROLLBACK S succeeds/fails | S | RUNNING / 0 or FAULT / restoration fault | S / 0 | RUNNING or REJECTED |

A status image is a coherent completed-scan observation with synchronized
accepted-request fields. INFO slot selection may advance before the next
completed-scan publication; cross-command responses are not an atomic session
snapshot. READ_TAGS retains the exact generation/scan of its owned publication,
even if the current status has advanced. A correction to a failed trial must
not mutate a reader-owned snapshot; publish a new owned image. Reusing a scan
ID for a correction does not revoke a snapshot already returned to a reader.

Do not put an old rejected fault in GET_STATUS's current fault field after
successful recovery. R4.2 adds the following read-only operation for the
separate retained update diagnostic. It adds a command; it does not redefine
any existing field. Its constants and golden fixtures are generated/checked alongside the original
commands. Command mask bit 9 advertises it.

**GET_UPDATE_STATUS (command 10)** has an empty request. Its success payload is
53 bytes, little endian, status included. Errors remain a single status byte.

| Offset | Width | Field |
| ---: | ---: | --- |
| 0 | u8 | status |
| 1 | u8 | request kind: 0 none, 1 ACTIVATE, 2 ROLLBACK |
| 2 | u8 | phase: 0 idle, 1 queued, 2 trial, 3 recovery queued, 4 recovery trial, 5 complete |
| 3 | u8 | outcome, existing outcome IDs |
| 4 | u8 | reserved zero |
| 5 | u32 | source generation at acceptance |
| 9 | u32 | requested target generation |
| 13 | u32 | generation of first failed trial, zero if none |
| 17 | u32 | first trial fault, zero if none |
| 21 | u32 | recovery trial fault, zero if none |
| 25 | u32 | first trial diagnostic line, zero when unavailable |
| 29 | u32 | first trial diagnostic column, zero when unavailable |
| 33 | u64 | first failed trial scan, zero if none |
| 41 | u32 | generation selected at completion, zero while pending |
| 45 | u64 | completion scan, zero while pending |

The record is cleared and assigned only when a new ACTIVATE/ROLLBACK is
accepted, not on rejected requests, INFO, BEGIN or ordinary subsequent scans.
It persists through automatic restoration, until a new accepted request or
reset. It is a coherent copied response owned by the scan/request machinery.
Before any request, all payload fields after status are zero. Phase is internal
transaction progress, not permission to reuse slots. Retained line/column are
untrusted bounded user numbers; this operation makes no source-map claim.
Recovery fault details beyond the numeric cause remain debugger diagnostics.

## Resource budget and acceptance cases

R3.5 static privileged RAM ends at 58,428 bytes of a 65,536-byte region. The
linker separately reserves 4,096 bytes for MSP, leaving **3,012 bytes** of
additional static headroom. The previously reported 7,108-byte raw gap includes
that stack and cannot all be allocated to state. Existing two code slots,
input/working buffers, worker stack and snapshot mailbox remain unchanged.

Budget at most 1,024 additional static bytes for R4's checkpoint, bounded
migration map, request/phase state and retained diagnostic combined. A 256-byte
saved-cell array plus compact scalar metadata fits this design; reuse the
existing active scan state and per-slot schema. Do not add another 2,560-byte
schema or full snapshot. This is a planning cap, not a measured implementation.
R4.2 must assert its object sizes, re-link with the existing MSP assertion,
inspect call-stack growth and measure the full body. R3.5's 4.054 ms observed
maximum is a baseline, not a guarantee that migration fits the deadline.
At most 64×64 name comparisons of at most 32 bytes is a bounded reference
matching algorithm; choose a map or faster search if target measurements require it.

Acceptance cases (execution evidence is in the R4.2/R4.3 reports):

1. Same-name/type VAR survives index reorder; additions, removals, renames,
   type/class changes and canonical BOOL/DINT boundary values obey the table.
2. Values changed after request acceptance but before application are migrated
   from the boundary state. Corrupt trusted values/identities fail closed.
3. New inputs use the new binding/frozen sample; output state starts zero,
   including unassigned outputs. No INPUT/OUTPUT is migrated or restored.
4. Successful trial preserves the old checkpoint unchanged over many scans;
   explicit rollback produces 42 in the 41/900 example and consumes PREVIOUS.
5. First-scan divide/access/deadline faults preserve old VARs and restore on a
   later release; faults after a successful trial do not auto-rollback.
6. Recovery failure leaves one faulted active program with no retry loop;
   activation from a faulted source cold-starts with no rollback eligibility.
7. BEGIN vs rollback, ACTIVATE vs BEGIN, pending/trial vs transfer expiry,
   stale generations, unsuccessful BEGIN and successful retirement obey the
   reservation rules. Lost mutation responses reconcile without duplicate work.
8. Slow readers retain complete snapshots through trial, restore and slot reuse;
   status fault/outcome and retained rejected cause remain distinct.
9. The firmware-linked boot program can be checkpointed/restored; later reuse
   of its code slot cannot leave dangling metadata references.
10. Host sanitizers/interleaving tests, target linker/stack checks and eventual
    R4.3 whole-body timing cover maximum tags, mixed traffic, contained faults,
    reset interruption and the fixed two-slot lifetime model.

R4.3 adds actual hardware migration/rollback, output and timing evidence.


## Implementation scheduling note

The board keeps a trial reserved through `xTaskDelayUntil`. At the following
release, it resolves that trial before preparing another generation or running
normal logic. This guarantees that a missed-release result cannot arrive after
rollback storage has been retired. Boundary resolution is measured in that new
release's body. A late failure discards trial VAR writes before publishing the
fault snapshot, while reservations remain held until boundary resolution.
The name/index map is built preemptibly by comms on reserved immutable schemas;
only its bounded 64-cell application and validation run in the scan task.
