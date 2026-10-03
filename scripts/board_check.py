"""Emit an OpenOCD board-test script. Does not access or flash hardware itself."""

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--flash", action="store_true", help="include programming the built ELF"
    )
    parser.add_argument(
        "--observe",
        action="store_true",
        help="sample the running program without reset",
    )
    parser.add_argument(
        "--expect-fault",
        action="store_true",
        help="expect the division-fault fixture",
    )
    args = parser.parse_args()
    if args.observe and args.flash:
        parser.error("--observe and --flash are mutually exclusive")
    out = ROOT / "build/native"
    symbols = {}
    for line in (out / "symbols.txt").read_text().splitlines():
        parts = line.split()
        if len(parts) == 3:
            symbols[parts[2]] = int(parts[0], 16)
    fields = [
        "assertion_latched",
        "scan_count",
        "stack_free_words",
        "native_status",
        "native_count",
        "native_output",
        "scan_cycles_max",
        "input_raw",
        "input_pressed",
        "input_transitions",
        "period_cycles_min",
        "period_cycles_max",
        "release_jitter_max",
        "missed_releases",
    ]
    reads = "\n".join(
        f"    set {name} [lindex [read_memory 0x{symbols[name]:08x} 32 1] 0]"
        for name in fields
    )
    image = out / "tinyplc-layout.elf"
    if any(c in str(image) for c in "{}\\\n"):
        raise ValueError("unsupported Tcl path characters")
    program = f"program {{{image}}} verify reset" if args.flash else "resume"
    text = (
        """# Generated from this build's symbols; no hardcoded variable addresses.
proc require {condition message} {
    if {![uplevel 1 [list expr $condition]]} { error $message }
}
adapter speed 1000
init
reset halt
set id [lindex [read_memory 0xE0042000 32 1] 0]
set flash_kib [lindex [read_memory 0x1FFF7A22 16 1] 0]
require {($id & 0xfff) == 0x421 && $flash_kib == 512} "Expected F446, 512 KiB"
echo "BOARD id=$id flash_kib=$flash_kib"
"""
        + program
        + """
set previous 0
for {set sample 0} {$sample < 2} {incr sample} {
    sleep 1000
    halt
"""
        + reads
        + """
    require {$assertion_latched == 0} "Assertion failure"
    require {$scan_count > $previous && $native_status == EXPECTED_STATUS} "No scan progress"
    require {$stack_free_words > 0 && $stack_free_words <= 512} "Stack failure"
    require {$scan_cycles_max > 0 && $scan_cycles_max < 160000} "Scan timing failure"
    require {$missed_releases == 0} "Missed scan release"
    require {$period_cycles_min > 128000 && $period_cycles_max < 192000} "Scan period outside observation window"
    set odr [lindex [read_memory 0x40020014 32 1] 0]
    require {(($odr >> 5) & 1) == $native_output} "GPIO output mismatch"
    EXPECTED_OUTPUT
    echo "SAMPLE scans=$scan_count status=$native_status n=$native_count led=$native_output raw=$input_raw pressed=$input_pressed transitions=$input_transitions stack_free=$stack_free_words scan_cycles_max=$scan_cycles_max period_min=$period_cycles_min period_max=$period_cycles_max jitter_max=$release_jitter_max missed=$missed_releases"
    set previous $scan_count
    set mpu [lindex [read_memory 0xE000ED94 32 1] 0]
    require {($mpu & 1) == 1} "MPU disabled"
    mww 0xE000ED98 4
    set peripheral [lindex [read_memory 0xE000EDA0 32 1] 0]
    require {(($peripheral >> 24) & 7) == 1 && ($peripheral & 0x10000000)} "Peripheral region not privileged/XN"
    echo "MPU enabled=$mpu peripheral_rasr=$peripheral"
    resume
}
echo "TINYPLC_BOARD_CHECK_PASS"
shutdown
"""
    )
    if args.observe:
        text = text.replace("reset halt", "halt")
    text = text.replace("EXPECTED_STATUS", "5" if args.expect_fault else "0")
    check = (
        'require {$native_count == 0 && $native_output == 0} "Fault committed state"'
        if args.expect_fault
        else 'require {$native_output == !$input_pressed && $input_pressed == !$input_raw} "ST GPIO mapping mismatch"'
    )
    text = text.replace("EXPECTED_OUTPUT", check)
    path = out / "board-check.tcl"
    path.write_text(text)
    print(path)


if __name__ == "__main__":
    main()
