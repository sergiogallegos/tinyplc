"""Verify R2.3 ELF boundaries and prove linker rejection of overflowing input data."""

import argparse
from pathlib import Path
import struct
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gcc-prefix", default="arm-none-eabi-")
    args = parser.parse_args()
    out = ROOT / "build/native"
    data = (out / "tinyplc-layout.elf").read_bytes()
    assert data[:6] == b"\x7fELF\x01\x01"
    assert struct.unpack_from("<H", data, 18)[0] == 40
    offset = struct.unpack_from("<I", data, 32)[0]
    width, count, names_index = struct.unpack_from("<HHH", data, 46)
    headers = [
        struct.unpack_from("<10I", data, offset + i * width)
        for i in range(count)
    ]
    names_header = headers[names_index]
    names = data[names_header[4] : names_header[4] + names_header[5]]
    sections = {names[h[0] :].split(b"\0")[0].decode(): h for h in headers}
    ranges = {
        ".isr_vector": (0x08000000, 0x08010000),
        ".text": (0x08000000, 0x08010000),
        ".syscalls": (0x08010000, 0x08011000),
        ".gateway": (0x08010000, 0x08011000),
        ".data": (0x20000000, 0x2000F000),
        ".bss": (0x20000000, 0x2000F000),
        ".retained": (0x20000000, 0x2000F000),
        ".user_program": (0x20010000, 0x20014000),
        ".code_b": (0x20014000, 0x20018000),
        ".inputs": (0x20018000, 0x20018200),
        ".working": (0x20018200, 0x20018400),
        ".user_stack": (0x20018800, 0x20019000),
    }
    for name, (start, end) in ranges.items():
        h = sections[name]
        assert start <= h[3] and h[3] + h[5] <= end, name
        print(f"{name}: address=0x{h[3]:08x}, bytes={h[5]}")
    assert sections[".user_program"][2] & 4  # SHF_EXECINSTR
    for name in [".inputs", ".working", ".user_stack", ".bss", ".retained"]:
        assert not sections[name][2] & 4, name
    # Vector entries must reference the actual linked FreeRTOS handlers.
    syms = {}
    for line in (out / "symbols.txt").read_text().splitlines():
        parts = line.split()
        if len(parts) == 3:
            syms[parts[2]] = int(parts[0], 16)
    h = sections[".isr_vector"]
    vectors = struct.unpack_from("<55I", data, h[4])
    assert vectors[0] == 0x20010000
    for index, name in [
        (1, "Reset_Handler"),
        (11, "plc_svc_handler"),
        (14, "xPortPendSVHandler"),
        (15, "xPortSysTickHandler"),
        (44, "plc_timer_handler"),
        (54, "plc_uart_handler"),
        (3, "plc_fault_handler"),
        (4, "plc_fault_handler"),
        (5, "plc_fault_handler"),
        (6, "plc_fault_handler"),
    ]:
        assert vectors[index] == syms[name] | 1, name
    assert syms["tinyplc_scan"] == 0x20010000
    for name in ["plc_worker", "plc_return_svc", "plc_abort_loop"]:
        assert 0x08010000 <= syms[name] < 0x08011000, name
    assert 0x20000000 <= syms["scan_stack"] < 0x2000F000
    assert syms["worker_stack"] == 0x20018800
    assert 0x20010000 <= syms["tinyplc_scan"] < 0x20014000
    assert 0x20010000 <= syms["tinyplc_abi_version"] < 0x20014000
    # An additional kept input cell exceeds the fixed 512-byte MPU reservation.
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory)
        source = path / "overflow.c"
        source.write_text(
            '__attribute__((section(".inputs"),used)) unsigned overflow;\n'
        )
        obj = path / "overflow.o"
        gcc = args.gcc_prefix + "gcc"
        subprocess.run(
            [
                gcc,
                "-mcpu=cortex-m4",
                "-mthumb",
                "-c",
                str(source),
                "-o",
                str(obj),
            ],
            check=True,
        )
        objects = [
            str(out / name)
            for name in [
                "0_tasks.o",
                "1_queue.o",
                "2_list.o",
                "3_port_hardened.o",
                "4_mpu_wrappers_v2_asm.o",
                "5_mpu_wrappers_v2.o",
                "6_startup.o",
                "7_main.o",
                "8_memory.o",
                "9_scan.o",
                "10_guard.o",
                "11_gateway.o",
                "12_package.o",
                "13_loader.o",
                "14_engineering.o",
                "15_engineering_board.o",
                "user_program.o",
            ]
        ]
        result = subprocess.run(
            [
                gcc,
                "-mcpu=cortex-m4",
                "-mthumb",
                "-mfpu=fpv4-sp-d16",
                "-mfloat-abi=softfp",
                "-nostdlib",
                *objects,
                str(obj),
                "-lgcc",
                "-Wl,--gc-sections",
                "-Wl,-z,noexecstack",
                "-T",
                str(ROOT / "port/nucleo_f446re/native/memory.ld"),
                "-o",
                str(path / "bad.elf"),
            ],
            capture_output=True,
            text=True,
        )
        assert (
            result.returncode != 0 and "input region overflow" in result.stderr
        ), result.stderr
    print(
        "ELF boundaries, vectors, RAM entry and negative overflow link passed."
    )


if __name__ == "__main__":
    main()
