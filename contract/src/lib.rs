//! Wire constants and allocation-free primitives. No package loader or transport.
#![no_std]
pub mod generated;
mod primitives;
pub use primitives::*;
