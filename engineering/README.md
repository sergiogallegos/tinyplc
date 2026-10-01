# plctool — local serial engineering CLI

Build with `cargo build --workspace --locked --offline`. Uses only the project's
contract crate, Rust std and the system `stty` command. No third-party Rust crates.

```sh
plctool DEVICE info
plctool DEVICE status
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
[hardware evidence](../docs/R3.3-report.md). Tag snapshots, writes, rollback and
network access are not implemented.
