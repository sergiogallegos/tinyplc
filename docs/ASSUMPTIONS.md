# Assumptions and decisions

Recorded before M0 code, 2026-09-30. These are design commitments unless a later milestone explicitly revises them.

- Work stops for a report after each milestone. M0 establishes the repository, learning guide, host scaffold, and standalone board blink target. PLC behavior starts in M1; TCP starts in M3; FreeRTOS starts in M4.
- This is an educational and research project, unsuitable for real machinery or safety functions.
- Target: NUCLEO-F446RE with factory solder bridges. LD2 uses PA5, B1 uses PC13, and ST-LINK VCP connects USART2 PA2/PA3. Configure 115200 8N1 in firmware; this baud rate is our choice, not a fixed board property.
- The requested BTN inversion is retained in the profile. UM1724 confirms PC13 but does not specify button polarity in its prose. Check the physical board revision against its schematic and verify released/pressed levels before M4 acceptance.
- Use C11, CMake + GNU Arm Embedded + OpenOCD. M0 blink uses direct registers and the reset-default 16 MHz HSI clock, without a HAL. No package is installed automatically or globally.
- Required future dependencies are only FreeRTOS-Kernel, pytest for tests, and optional pyserial for serial transport. Their inclusion will be reviewed at the relevant milestone; standard-library Python provides compiler and TCP transport. No dependency is fetched by the default build.
- Program code is at most 2048 bytes per slot, with at most 64 tags, a 64-value VM stack, and a default 4096-instruction scan budget. Names are ASCII identifiers, at most 31 bytes, case-insensitive and stored canonically in uppercase.
- BOOL is canonical 0/1. DINT arithmetic wraps modulo 2^32 using unsigned C operations; signed division truncates toward zero. INT32_MIN / -1 wraps to INT32_MIN; division by zero faults. No implicit BOOL/DINT conversion.
- Inputs are read-only in ST. Outputs and internal VARs may be assigned in ST; protocol writes affect internal VARs only and are applied by the scan owner at a boundary.
- No loops, calls, retention, or hardware debounce in v1. BTN counts may reflect contact bounce. Internal VAR values persist between scans but reset at power loss.
- The scan owns active program state. Comms stages bytes in the inactive slot and sends bounded requests; slot states prevent modifying a rollback image or a pending image. Publication and ownership need C11 atomics, not volatile alone.
- A failed first scan forces outputs FALSE immediately and schedules automatic rollback. A later scan restores old execution; recovery semantics will be tested in M5. Ordinary faults latch until explicit recovery; comms stays available.
- macOS is a functional simulator, not evidence of microcontroller timing. A detected usbmodem device is not proof of the board identity or a passed hardware test.
- Bytecode and wire formats below are proposed v1 contracts until M1/M3 tests lock them down. Documentation must distinguish implemented behavior from planned behavior.
- MIT applies to project code; future third-party code retains its own license.

## M1 implementation decisions

- The validator uses a caller-owned fixed workspace, with one depth and a 64-bit type mask per code offset. It is allocated statically in the simulator/tests, not on the scan stack. This keeps forward-control-flow validation bounded without storing a full stack at every instruction.
- The core receives an explicit list of permitted I/O bindings; it never reads JSON or assumes STM32 pin names. The host/port supply the same profile semantics.
- M1 provides a single-producer comms/scan activation mailbox. Download/image validation occurs while the inactive slot is reserved; the scan owns tag values and commits swaps only through an explicit boundary call. Migration and rollback are deferred to M5; M1 activation starts new values at zero.
- A scan fault latches execution off until a valid activation. A diagnostic record remains available after recovery. M1's scan wrapper handles VM faults transactionally; hardware deadline/output handling is added by the port in M4.
