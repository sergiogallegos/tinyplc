# plctool — local serial engineering CLI

Build with `cargo build --workspace --locked --offline`. Uses only the project's
contract crate, Rust std and the system `stty` command. No third-party Rust crates.

```sh
plctool DEVICE info
plctool DEVICE status
plctool DEVICE monitor
plctool DEVICE update-status
plctool DEVICE rollback
plctool DEVICE download PACKAGE.tplc
plctool DEVICE activate GENERATION
```

Use `./target/debug/plctool` from the repository. DEVICE is the board's callout
port, for example `/dev/cu.usbmodem2103`. Only one host/session may use it.
The board firmware must already be installed by ST-LINK. INFO validates the
contract and reports numeric slot states. Download checks the local file CRC
and placement, reserves the inactive slot and transfers contiguous chunks.
It stops at READY; ACTIVATE is separate and confirms the observed outcome.

Read commands and successful operations print JSON. Device/transport errors
return nonzero. An activation fault may print its status JSON then return
nonzero. Transfer IDs and generations expire on reset; they are not durable
program identities. Do not retry an uncertain activation blindly. Only exact
chunk retries are automatic; INFO/GET_STATUS reconcile other timeouts.

See [transport/ownership](../docs/engineering-transport.md),
[wire contract](../docs/wire-format.md), [packager](../packager/README.md) and
[hardware evidence](../docs/R3.3-report.md). Writes and network access are not implemented.

`monitor` prints one complete coherent snapshot as JSON, with generation, scan,
and up to 64 named tags. BOOL values are JSON booleans; DINT values are signed
integers; TIME values are nonnegative milliseconds. TON records include Q/ET
and internal state, with the shared clock input. It reads pages of at most five tags from one owned snapshot and rejects
inconsistent pages. The board releases the enumeration after its last page or
2 seconds of inactivity. On expiry, run `monitor` again to start a new snapshot.
See [R3.4 ownership and validation](../docs/R3.4-report.md) and
[R3.5 board workflow/timing evidence](../docs/R3.5-report.md).


R4-capable firmware migrates exact-name/same-type internal VARs on healthy
activation. New/incompatible variables and outputs start zero; inputs are
resampled. A faulted source cold-starts the candidate. `rollback` restores the
saved pre-update VAR state and consumes the checkpoint. Starting another
download retires that checkpoint even if the transfer later fails.

A failed first-scan trial can automatically restore the old program. `activate`
then prints the observed status and returns nonzero, even if the old generation
is running successfully. `update-status` reports the rejected generation,
first fault, recovery fault and completion scan. A later fault after a successful
trial latches normally; explicit rollback may still recover the saved program.
See [R4 implementation](../docs/R4.2-report.md) and
[board evidence](../docs/R4.3-report.md). The CLI supports older R3 firmware;
its missing rollback/update-status operations remain unavailable.

R5.1 adds [TON/TIME](../docs/ton.md). Timer instances restart on activation,
rollback, and failed-trial recovery; scalar TIME VARs follow normal migration.
