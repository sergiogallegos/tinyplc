"""Explicit R3.5 lab-board acceptance: flash, edit/upload/activate/monitor,
stress concurrent scan/download/monitor traffic, and restore boot firmware.
Not part of host tests. Requires the connected NUCLEO-F446RE lab board.
"""

import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import time
from test_engineering_board import Serial

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", required=True)
    parser.add_argument("--openocd", default="openocd")
    parser.add_argument("--gcc-prefix", default="arm-none-eabi-")
    parser.add_argument("--clang", default="clang")
    parser.add_argument("--seconds", type=float, default=15)
    args = parser.parse_args()
    if args.seconds < 10:
        parser.error("at least 10 seconds of mixed traffic required")
    out = ROOT / "build/monitor-board"
    out.mkdir(parents=True, exist_ok=True)
    firmware = ROOT / "build/native/tinyplc-layout.elf"
    report = {
        "firmware_sha256": hashlib.sha256(firmware.read_bytes()).hexdigest(),
        "date": time.strftime("%Y-%m-%d"),
        "events": [],
    }

    def record(name, **data):
        event = dict(name=name, **data)
        report["events"].append(event)
        print(json.dumps(event), flush=True)
        (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")

    def cli(*cmd):
        result = subprocess.run(
            [str(ROOT / "target/debug/plctool"), args.device, *map(str, cmd)],
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert result.returncode == 0, result.stderr
        value = json.loads(result.stdout)
        record(
            "cli",
            command=[str(x).replace(str(ROOT) + "/", "") for x in cmd],
            result=value,
        )
        return value

    def ocd(name, script):
        path = out / (name + ".tcl")
        path.write_text("adapter speed 1000\n" + script)
        result = subprocess.run(
            [
                args.openocd,
                "-f",
                "interface/stlink.cfg",
                "-f",
                "target/stm32f4x.cfg",
                "-f",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=25,
        )
        log = result.stdout + result.stderr
        (out / (name + ".log")).write_text(log)
        assert result.returncode == 0, log
        return log

    def reset(name):
        ocd(name, "init\nreset run\nshutdown\n")
        time.sleep(0.3)

    symbols = {
        parts[2]: int(parts[0], 16)
        for line in (ROOT / "build/native/symbols.txt").read_text().splitlines()
        if len(parts := line.split()) == 3
    }

    def sample(name):
        fields = [
            "scan_count",
            "native_status",
            "assertion_latched",
            "scan_cycles_max",
            "scan_body_cycles_last",
            "scan_body_cycles_max",
            "period_cycles_min",
            "period_cycles_max",
            "release_jitter_max",
            "missed_releases",
            "uart_rx_errors",
            "uart_frames",
            "comms_stack_free_words",
            "stack_free_words",
            "worker_stack_free_words",
        ]
        # Halt only AFTER each measurement window; reset before the next window.
        # No debugger reads, breakpoints or halts occur during traffic measurement.
        log = ocd(
            name,
            "init\nhalt\n"
            + "".join(
                f'echo "DATA {key} [read_memory {symbols[key]} 32 1]"\n'
                for key in fields
            )
            + "resume\nshutdown\n",
        )
        values = {
            p[1]: int(p[2], 0)
            for line in log.splitlines()
            if line.startswith("DATA ") and len(p := line.split()) == 3
        }
        assert len(values) == len(fields), log
        record(name, values=values)
        assert (
            values["native_status"]
            == values["assertion_latched"]
            == values["missed_releases"]
            == values["uart_rx_errors"]
            == 0
        ), values
        assert 0 < values["scan_body_cycles_max"] < 160000, values
        assert (
            128000
            < values["period_cycles_min"]
            <= values["period_cycles_max"]
            < 192000
        ), values
        assert all(
            values[key] > 0
            for key in [
                "comms_stack_free_words",
                "stack_free_words",
                "worker_stack_free_words",
            ]
        ), values
        return values

    # A concrete source edit, built through the product Rust compiler/packager.
    edited = out / "edited.st"
    edited.write_text(
        "PROGRAM Edited\nVAR_INPUT BTN : BOOL; END_VAR\n"
        "VAR_OUTPUT LED : BOOL; END_VAR\nVAR N : DINT; END_VAR\n"
        "N := N + 7;\nLED := BTN;\nEND_PROGRAM\n"
    )
    maximum = out / "maximum.st"
    maximum.write_text(
        "PROGRAM Maximum\nVAR\n"
        + "".join(f"V{i:02d} : DINT;\n" for i in range(64))
        + "END_VAR\nV00 := V00 + 1;\n"
        + "".join(f"V{i:02d} := V00 + {i};\n" for i in range(1, 64))
        + "END_PROGRAM\n"
    )
    packages = {}
    for name, source in [
        ("normal", ROOT / "examples/button_led.st"),
        ("edited", edited),
        ("maximum", maximum),
    ]:
        for slot in ("A", "B"):
            dest = out / f"{name}-{slot}.tplc"
            subprocess.run(
                [
                    str(ROOT / "target/debug/plcpack"),
                    str(source),
                    "--slot",
                    slot,
                    "-o",
                    str(dest),
                    "--clang",
                    args.clang,
                    "--ld",
                    args.gcc_prefix + "ld",
                ],
                check=True,
            )
            packages[name, slot] = dest
    report["packages"] = {
        f"{name}-{slot}": {
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "bytes": path.stat().st_size,
        }
        for (name, slot), path in packages.items()
    }
    report["sources"] = {
        "edited": edited.read_text(),
        "maximum": maximum.read_text(),
    }

    def checked(serial, command, payload=b""):
        response = serial.request(command, payload)
        assert response[0] == 0, (command, response.hex())
        return response

    def status(serial):
        b = checked(serial, 9)
        assert len(b) == 49 and struct.unpack_from("<I", b, 25)[0] == 0, b.hex()
        return {
            "generation": struct.unpack_from("<I", b, 1)[0],
            "scan": struct.unpack_from("<Q", b, 5)[0],
            "misses": struct.unpack_from("<Q", b, 41)[0],
        }

    def page(serial, generation=0, scan=0, first=0):
        b = checked(serial, 7, struct.pack("<IQBB", generation, scan, first, 5))
        gen, seq, index, count, total = struct.unpack_from("<IQBBB", b, 1)
        assert (
            index == first
            and 1 <= count <= 5
            and count == min(5, total - first)
            and len(b) == 16 + 40 * count
        )
        if scan:
            assert (gen, seq) == (generation, scan)
        records = []
        for i in range(count):
            raw = b[16 + 40 * i : 56 + 40 * i]
            records.append(
                {
                    "name": raw[:32].split(b"\0")[0].decode("ascii"),
                    "type": raw[32],
                    "class": raw[33],
                    "value": struct.unpack_from("<i", raw, 36)[0],
                }
            )
        return {
            "generation": gen,
            "scan": seq,
            "first": first,
            "count": count,
            "total": total,
            "records": records,
        }

    def validate_maximum(p, base):
        assert p["total"] == 64
        for i, tag in enumerate(p["records"], p["first"]):
            assert tag == {
                "name": f"V{i:02d}",
                "type": 2,
                "class": 3,
                "value": base + i,
            }, tag

    def upload(serial, package, between=None):
        data = package.read_bytes()
        begin = checked(serial, 2, struct.pack("<I", len(data)))
        transfer = struct.unpack_from("<I", begin, 1)[0]
        for offset in range(0, len(data), 240):
            chunk = data[offset : offset + 240]
            ack = checked(
                serial, 3, struct.pack("<II", transfer, offset) + chunk
            )
            assert struct.unpack_from("<I", ack, 1)[0] == offset + len(chunk)
            if between:
                between()
        return struct.unpack_from(
            "<I", checked(serial, 4, struct.pack("<I", transfer)), 1
        )[0]

    def activate(serial, generation):
        checked(serial, 5, struct.pack("<I", generation))
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            s = status(serial)
            if s["generation"] == generation:
                return s
            time.sleep(0.01)
        raise AssertionError("activation timeout")

    try:
        ocd("flash", f"program {{{firmware}}} verify reset exit\n")
        time.sleep(0.3)
        assert cli("info")["commands"] & 0x15F == 0x15F
        boot = cli("monitor")
        assert [t["name"] for t in boot["tags"]] == ["BTN", "LED", "N"]
        assert boot["tags"][1]["value"] == (not boot["tags"][0]["value"])
        ready = cli("download", packages["edited", "B"])["ready_generation"]
        assert cli("status")["active_generation"] == boot["generation"]
        assert cli("activate", ready)["active_generation"] == ready
        edited_snapshot = cli("monitor")
        tags = {t["name"]: t["value"] for t in edited_snapshot["tags"]}
        assert (
            edited_snapshot["generation"] == ready
            and tags["LED"] == tags["BTN"]
            and tags["N"] > 0
            and tags["N"] % 7 == 0
        )
        record(
            "edit-build-upload-accept-monitor-pass",
            generation=ready,
            scan=edited_snapshot["scan"],
            tags=tags,
        )

        # Reset isolates each measurement window from previous debugger halts.
        reset("baseline-reset")
        time.sleep(3)
        sample("boot-baseline")
        reset("maximum-reset")
        ready = cli("download", packages["maximum", "B"])["ready_generation"]
        cli("activate", ready)
        cli("monitor")
        time.sleep(3)
        sample("maximum-baseline")
        reset("mixed-reset")
        ready = cli("download", packages["maximum", "B"])["ready_generation"]
        cli("activate", ready)
        serial = Serial(args.device)
        try:
            before = status(serial)
            started = time.monotonic()
            counts = {"downloads": 0, "pages": 0, "snapshots": 0}
            pinned = None
            base = None

            def monitor_page():
                nonlocal pinned, base
                if pinned is None:
                    p = page(serial)
                    base = p["records"][0]["value"]
                    counts["snapshots"] += 1
                else:
                    p = page(
                        serial,
                        pinned["generation"],
                        pinned["scan"],
                        pinned["first"] + pinned["count"],
                    )
                assert p["generation"] == ready
                validate_maximum(p, base)
                counts["pages"] += 1
                pinned = None if p["first"] + p["count"] == p["total"] else p

            while time.monotonic() - started < args.seconds:
                upload(serial, packages["maximum", "A"], monitor_page)
                counts["downloads"] += 1
            while pinned is not None:
                monitor_page()
            after = status(serial)
            elapsed = time.monotonic() - started
            assert (
                after["generation"] == ready
                and after["misses"] == before["misses"] == 0
            )
            assert after["scan"] - before["scan"] >= elapsed * 90
            record(
                "mixed-traffic-pass",
                duration_seconds=elapsed,
                before=before,
                after=after,
                **counts,
            )
        finally:
            serial.close()
        sample("mixed-traffic-timing")

        reset("lifetime-reset")
        ready = cli("download", packages["maximum", "B"])["ready_generation"]
        cli("activate", ready)
        serial = Serial(args.device)
        try:
            first = page(serial)
            base = first["records"][0]["value"]
            validate_maximum(first, base)
            # Keep the reader pinned while producer advances without monitor reads.
            time.sleep(0.25)
            running = status(serial)
            assert running["scan"] > first["scan"] + 15
            new = upload(serial, packages["normal", "A"])
            activate(serial, new)
            replacement = upload(serial, packages["edited", "B"])
            for index in range(5, 64, 5):
                validate_maximum(
                    page(serial, first["generation"], first["scan"], index),
                    base,
                )
            current = page(serial)
            assert current["generation"] == new and current["total"] == 3
            record(
                "stalled-reader-slot-reuse-pass",
                pinned_generation=first["generation"],
                pinned_scan=first["scan"],
                progress_scan=running["scan"],
                active_generation=new,
                replacement_generation=replacement,
            )
            activate(serial, replacement)
            # A 3-tag snapshot is released immediately; use the 64-tag image again.
            large = upload(serial, packages["maximum", "A"])
            activate(serial, large)
            stale = page(serial)
            time.sleep(2.1)
            assert (
                serial.request(
                    7,
                    struct.pack(
                        "<IQBB", stale["generation"], stale["scan"], 5, 5
                    ),
                )
                == b"\x03"
            )
            assert status(serial)["scan"] > stale["scan"] + 190
            record("snapshot-expiry-pass", generation=large)
        finally:
            serial.close()
        record("R3.5-pass")
    finally:
        reset("restore-normal")
        restored = cli("status")
        assert restored["active_generation"] == 1 and restored["fault"] == 0
        record("normal-boot-restored", status=restored)


if __name__ == "__main__":
    main()
