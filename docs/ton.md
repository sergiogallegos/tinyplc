# TON on-delay timer (R5.1)

The first requested R5 extension is a reusable on-delay timer. It compiles to
native instructions and uses the existing transactional scan state; it adds
no runtime imports, heap allocation, tasks, or new memory regions.

```iecst
PROGRAM DelayedButton
VAR_INPUT BTN : BOOL; END_VAR
VAR_OUTPUT LED : BOOL; END_VAR
VAR Delay : TON; END_VAR
Delay(IN := BTN, PT := T#500ms);
LED := Delay.Q;
END_PROGRAM
```

Build with `plcc --abi 2`, or package
[examples/ton_led.st](../examples/ton_led.st) with `plcpack` as usual. The
research ABI 1 and historical Python/bytecode compiler do not support TON.

## Language and behavior

Declare a TON instance in `VAR`, then invoke `instance(IN := bool, PT := time);`.
Both named arguments are required exactly once, in either order. Read the
outputs as `instance.Q` (BOOL) and `instance.ET` (TIME). Members are read-only;
instance assignment, other members, optional parameters, positional arguments,
and output association (`Q => ...`) are outside this subset. Instances cannot
be I/O declarations and have names of at most 20 characters. Identifiers
beginning `__` are now reserved for compiler-generated cells.

TIME is a distinct type containing a nonnegative integer number of milliseconds,
0..2,147,483,647. Literals use `T#` or `TIME#` followed by one integer and one
unit: `ms`, `s`, `m`, or `h`, case-insensitively. For example, `T#500ms` and
`TIME#2s` are valid. Negative, fractional, compound, and overflowing literals
are rejected. TIME supports assignment and matching-type comparisons, including
ordered comparisons; arithmetic and implicit conversion from DINT are rejected.
TIME variables start at zero. Invalid native TIME state returns fault 9 with
the declaration's source position; the supervisor also rejects invalid
successful candidate TIME cells before committing.

On each invocation:

- `IN=FALSE` resets Q, ET, active state, and accumulated elapsed time to zero.
- The first `IN=TRUE` invocation starts at elapsed zero. `PT=T#0ms` makes Q
  true immediately; otherwise Q stays false until elapsed time reaches PT.
- While IN remains true, elapsed time accumulates between invocations. ET is
  capped at the current PT; Q is true exactly when elapsed is at least PT.
- PT is evaluated on every call. Lowering it can complete the timer immediately;
  raising it can make Q false again. Internal elapsed time continues beyond PT,
  saturating at the largest TIME value, so changing PT does not lose elapsed time.
- A skipped invocation retains all timer outputs/state. On the next invocation,
  elapsed includes the skipped interval if the previously observed IN was true.
  Input changes that are never passed to an invocation cannot reset the timer.
- Calls share the scan's frozen clock. Calling one instance twice in a scan
  does not double-count time. Calls execute in source order and can reset/restart
  the same instance with different arguments. Instances otherwise evolve independently.

The basic IN/PT/Q/ET interface and reset/delay behavior follow the
[Fernhill TON documentation](https://www.fernhillsoftware.com/help/iec-61131/common-elements/standard-function-blocks/on-delay-timer.html).
The literal subset, dynamic-PT behavior, skipped calls, limits, and update policy
above are explicit tinyplc choices, not a claim of full IEC conformance.

## Clock and storage contract

The compiler appends one shared INPUT DINT cell `__CLOCK_MS`, binding 3. The
supervisor samples the 32-bit FreeRTOS tick at input acquisition, alongside
physical inputs; the board build asserts a 1,000 Hz tick rate. Native code reads
that frozen cell without privileged service calls. Its DINT bit pattern is an
unsigned modulo-2^32 millisecond timestamp, not a user-visible TIME duration.
Host callers must supply an equivalent monotonically advancing clock themselves.

Elapsed subtraction tolerates timestamp wrap. The gap between successive calls
of an active timer must be less than 2^32 milliseconds (about 49.7 days).
The maximum preset is about 24.9 days. Time resolution is 1 ms; Q changes only
when the program invokes the timer. The 10 ms release period, RTOS timing, and
board oscillator limit observed timing accuracy. This is not a precision clock
or a hard real-time timing certification.

Each declaration expands in place to five cells, all class TIMER=4 and binding 0:

| Suffix in `__T_<INSTANCE>_<SUFFIX>` | Type | Meaning |
| --- | --- | --- |
| Q | BOOL=1 | Delayed output |
| ET | TIME=3 | Elapsed capped at current PT |
| RUN | BOOL=1 | Last invocation's IN |
| LAST | DINT=2 | Last sampled unsigned timestamp bits |
| AGE | TIME=3 | Saturating accumulated elapsed |

Only Q and ET have source-level aliases. The monitor exposes these scalar
records and the clock; TIME values are numeric milliseconds. Five cells per
timer and one shared clock count against the existing 64-cell bound. At most
12 timers fit, leaving three cells for other declarations. No separate
privileged timer storage or changes to the 2 KiB worker stack are needed.

Native ABI 2's four-argument call shape and package/record widths stay unchanged.
New type/class/binding IDs extend the accepted schema. Older firmware rejects
these unsupported IDs before READY, rather than running a timer with an absent
clock or migrating its state as ordinary VARs. Existing BOOL/DINT packages and
golden wire fixtures remain valid on the extended runtime. INFO's existing
capability bits are unchanged; they do not advertise TON support. Use the R5.1
firmware for TON packages.

## Scan and update transactions

Timer cells persist across successful ordinary scans, with the same all-or-none
commit as scalar state. A failed scan discards timer changes along with other
candidate changes; the supervisor latches the fault and clears physical outputs.

All timer cells reset to zero before the first scan after activation, explicit
rollback, automatic failed-trial recovery, and device reset. They are neither
migrated nor stored as rollback checkpoint state, even if instance names and
layouts match. Fresh clock sampling and the first call determine the new timing
origin. A timer with true IN restarts its full delay. Ordinary TIME VARs use
existing same-name/same-type migration and checkpoint restoration rules.
This deliberately avoids carrying stale timer timestamps across program changes.

Acceptance and resource measurements: [R5.1 report](R5.1-report.md).
