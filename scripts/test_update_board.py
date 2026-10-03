"""Explicit R4.3 lab-board test: flash, migrate, rollback and inject native faults.
Restores the normal boot program in finally. Not part of host-only tests.
"""

import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import time
import zlib
from test_engineering_board import Serial

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--device", required=True)
    ap.add_argument("--openocd", default="openocd")
    ap.add_argument("--gcc-prefix", default="arm-none-eabi-")
    ap.add_argument("--clang", default="clang")
    args = ap.parse_args()
    out = ROOT / "build/update-board"
    out.mkdir(parents=True, exist_ok=True)
    firmware = ROOT / "build/native/tinyplc-layout.elf"
    report = {
        "date": time.strftime("%Y-%m-%d"),
        "firmware_sha256": hashlib.sha256(firmware.read_bytes()).hexdigest(),
        "events": [],
    }

    def record(name, **data):
        e = dict(name=name, **data)
        report["events"].append(e)
        print(json.dumps(e), flush=True)
        (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")

    def cli(*cmd, fail=False):
        result = subprocess.run(
            [str(ROOT / "target/debug/plctool"), args.device, *map(str, cmd)],
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert (result.returncode != 0) == fail, (
            cmd,
            result.stdout,
            result.stderr,
        )
        data = json.loads(result.stdout) if result.stdout.strip() else None
        if data and "last_scan_us" in data:
            assert data["last_scan_us"] <= data["max_scan_us"], data
        record(
            "cli",
            command=[str(x).replace(str(ROOT) + "/", "") for x in cmd],
            code=result.returncode,
            result=data,
            error=result.stderr.strip(),
        )
        return data

    def ocd(name, script):
        p = out / (name + ".tcl")
        p.write_text("adapter speed 1000\n" + script)
        result = subprocess.run(
            [
                args.openocd,
                "-f",
                "interface/stlink.cfg",
                "-f",
                "target/stm32f4x.cfg",
                "-f",
                str(p),
            ],
            capture_output=True,
            text=True,
            timeout=25,
        )
        log = result.stdout + result.stderr
        (out / (name + ".log")).write_text(log)
        assert not result.returncode, log
        return log

    def reset(name):
        ocd(name, "init\nreset run\nshutdown\n")
        time.sleep(0.3)

    sources = {
        "source": """PROGRAM Source
VAR_INPUT BTN : BOOL; END_VAR
VAR_OUTPUT LED : BOOL; END_VAR
VAR N : DINT; FLAG : BOOL; END_VAR
IF N = 0 THEN N := 41; ELSE N := N + 1; END_IF;
FLAG := TRUE;
LED := NOT BTN;
END_PROGRAM
""",
        "edit": """PROGRAM Edited
VAR FLAG : DINT; NEW : DINT; N : DINT; END_VAR
VAR_OUTPUT LED : BOOL; END_VAR
VAR_INPUT BTN : BOOL; END_VAR
N := N + 7;
NEW := NEW + 3;
END_PROGRAM
""",
        "fault": """PROGRAM Fault
VAR_INPUT BTN : BOOL; END_VAR
VAR_OUTPUT LED : BOOL; END_VAR
VAR N : DINT; ZERO : DINT; END_VAR
N := N + 1000;
LED := TRUE;
N := N / ZERO;
END_PROGRAM
""",
        "restore-fault": """PROGRAM RestoreFault
VAR_OUTPUT LED : BOOL; END_VAR
VAR RESTORE_COUNT : DINT; ZERO : DINT; END_VAR
IF RESTORE_COUNT > 0 AND NOT LED THEN RESTORE_COUNT := RESTORE_COUNT / ZERO; END_IF;
RESTORE_COUNT := RESTORE_COUNT + 1;
LED := TRUE;
END_PROGRAM
""",
        "late": """PROGRAM Late
VAR N : DINT; END_VAR
N := N + 1;
IF N >= 10 THEN N := N / 0; END_IF;
END_PROGRAM
""",
    }
    wide_names = [f"LONG_COMMON_PREFIX_{i:02d}" for i in range(64)]
    sources["wide-source"] = (
        "PROGRAM Wide\nVAR\n"
        + "".join(f"{n} : DINT;\n" for n in wide_names)
        + "END_VAR\n"
        + wide_names[0]
        + " := "
        + wide_names[0]
        + " + 1;\n"
        + "".join(
            f"{n} := {wide_names[0]} + {i};\n"
            for i, n in enumerate(wide_names[1:], 1)
        )
        + "END_PROGRAM\n"
    )
    sources["wide-edit"] = (
        "PROGRAM WideEdit\nVAR\n"
        + "".join(f"{n} : DINT;\n" for n in reversed(wide_names))
        + "END_VAR\n"
        + "".join(f"{n} := {n} + 7;\n" for n in wide_names)
        + "END_PROGRAM\n"
    )
    packages = {}
    for name, source in sources.items():
        path = out / (name + ".st")
        path.write_text(source)
        for slot in ("A", "B"):
            dest = out / f"{name}-{slot}.tplc"
            subprocess.run(
                [
                    str(ROOT / "target/debug/plcpack"),
                    str(path),
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
    golden = bytes.fromhex(
        (ROOT / "tests/wire/fixtures/package-a.hex").read_text()
    )
    for probe in (3, 8, 9):
        for slot, base in [("A", 0x20010000), ("B", 0x20014000)]:
            obj = out / f"probe-{probe}-{slot}.o"
            elf = obj.with_suffix(".elf")
            binary = obj.with_suffix(".bin")
            subprocess.run(
                [
                    args.gcc_prefix + "gcc",
                    "-mcpu=cortex-m4",
                    "-mthumb",
                    f"-DPROBE={probe}",
                    "-DFIRST_SCAN_FAULT",
                    "-c",
                    str(ROOT / "tests/target/probes.S"),
                    "-o",
                    str(obj),
                ],
                check=True,
            )
            subprocess.run(
                [
                    args.gcc_prefix + "ld",
                    f"--defsym=TINYPLC_CODE_BASE={base}",
                    "-T",
                    str(ROOT / "port/nucleo_f446re/native/program.ld"),
                    str(obj),
                    "-o",
                    str(elf),
                ],
                check=True,
            )
            subprocess.run(
                [
                    args.gcc_prefix + "objcopy",
                    "-O",
                    "binary",
                    str(elf),
                    str(binary),
                ],
                check=True,
            )
            eb = elf.read_bytes()
            sh = struct.unpack_from("<I", eb, 32)[0]
            n = struct.unpack_from("<H", eb, 48)[0]
            sections = [
                struct.unpack_from("<10I", eb, sh + i * 40) for i in range(n)
            ]
            text = next(s for s in sections if s[2] & 4 and s[5])
            payload = binary.read_bytes()
            payload += bytes((-len(payload)) % 4)
            b = bytearray(golden[:80]) + payload + golden[84:]
            for at, value in [
                (8, len(b)),
                (24, base),
                (32, len(payload)),
                (36, text[3] - base),
                (40, text[5]),
                (44, (struct.unpack_from("<I", eb, 24)[0] & ~1) - base),
                (48, 80 + len(payload)),
                (64, 0),
            ]:
                struct.pack_into("<I", b, at, value)
            struct.pack_into("<I", b, 64, zlib.crc32(b))
            dest = out / f"probe-{probe}-{slot}.tplc"
            dest.write_bytes(b)
            packages[f"probe-{probe}", slot] = dest
    report["sources"] = sources
    report["packages"] = {
        f"{name}-{slot}": hashlib.sha256(p.read_bytes()).hexdigest()
        for (name, slot), p in packages.items()
    }

    def download(name, slot):
        return cli("download", packages[name, slot])["ready_generation"]

    def monitor():
        m = cli("monitor")
        return m, {t["name"]: t["value"] for t in m["tags"]}

    symbols = {
        p[2]: int(p[0], 16)
        for line in (ROOT / "build/native/symbols.txt").read_text().splitlines()
        if len(p := line.split()) == 3
    }

    def sample(name):
        fields = [
            "scan_count",
            "native_status",
            "assertion_latched",
            "scan_body_cycles_max",
            "missed_releases",
            "uart_rx_errors",
            "stack_free_words",
            "worker_stack_free_words",
            "comms_stack_free_words",
        ]
        log = ocd(
            name,
            "init\nhalt\n"
            + "".join(
                f'echo "DATA {k} [read_memory {symbols[k]} 32 1]"\n'
                for k in fields
            )
            + "resume\nshutdown\n",
        )
        values = {
            p[1]: int(p[2], 0)
            for line in log.splitlines()
            if line.startswith("DATA ") and len(p := line.split()) == 3
        }
        assert len(values) == len(fields)
        record(name, values=values)
        assert values["assertion_latched"] == values["uart_rx_errors"] == 0
        return values

    try:
        ocd("flash", f"program {{{firmware}}} verify reset exit\n")
        time.sleep(0.3)
        info = cli("info")
        assert info["capabilities"] == 7 and info["commands"] == 0x37F
        assert cli("update-status")["kind"] == 0
        # Actual product CLI path, with exact arithmetic across global scan IDs.
        source = download("source", "B")
        cli("activate", source)
        source_first = cli("update-status")["completed_scan"]
        m, v = monitor()
        assert v["N"] == 41 + m["scan"] - source_first and v["FLAG"] is True
        edited = download("edit", "A")
        cli("activate", edited)
        edit_first = cli("update-status")["completed_scan"]
        checkpoint = 41 + edit_first - 1 - source_first
        m, v = monitor()
        steps = m["scan"] - edit_first + 1
        assert (
            v["N"] == checkpoint + 7 * steps
            and v["NEW"] == 3 * steps
            and v["FLAG"] == 0
            and v["LED"] is False
        ), (m, checkpoint, steps)
        cli("rollback")
        rollback_first = cli("update-status")["completed_scan"]
        m, v = monitor()
        assert (
            m["generation"] == source
            and v["N"] == checkpoint + 1 + m["scan"] - rollback_first
        )
        cli("rollback", fail=True)
        record(
            "migration-explicit-rollback-pass",
            source_generation=source,
            target_generation=edited,
            source_first_scan=source_first,
            target_first_scan=edit_first,
            checkpoint_n=checkpoint,
            rollback_first_scan=rollback_first,
            observed=m,
        )
        # Failed trial must discard N+1000 and recover saved old VARs once.
        before, values = monitor()
        bad = download("fault", "A")
        result = cli("activate", bad, fail=True)
        assert (
            result["active_generation"] == source
            and result["outcome"] == 4
            and result["fault"] == 0
        )
        diag = cli("update-status")
        assert (
            diag["first_fault"] == 5
            and diag["failed_generation"] == bad
            and diag["recovery_fault"] == 0
        )
        assert diag["completed_scan"] == diag["failed_scan"] + 1
        m, v = monitor()
        assert v["N"] == values["N"] + m["scan"] - before["scan"] - 1
        assert cli("info")["slots"][0]["state"] == 0
        record("language-fault-auto-rollback-pass", diagnostic=diag, observed=m)
        # Starting BEGIN retires checkpoint even when its transfer is rejected.
        edited = download("edit", "A")
        cli("activate", edited)
        serial = Serial(args.device)
        try:
            assert serial.request(2, struct.pack("<I", 0)) == b"\x01"
            assert serial.request(6)[0] == 0  # Invalid BEGIN kept checkpoint.
            deadline = time.monotonic() + 2
            while time.monotonic() < deadline:
                st = serial.request(9)
                if struct.unpack_from("<I", st, 21)[0] == 0:
                    break
            else:
                raise AssertionError("rollback did not complete")
        finally:
            serial.close()
        edited = download("edit", "A")
        cli("activate", edited)
        serial = Serial(args.device)
        try:
            begin = serial.request(2, struct.pack("<I", len(golden)))
            assert begin[0] == 0
            tid = struct.unpack_from("<I", begin, 1)[0]
            corrupt = bytearray(golden)
            corrupt[80] ^= 1
            assert (
                serial.request(3, struct.pack("<II", tid, 0) + corrupt)[0] == 0
            )
            assert (
                serial.request(4, struct.pack("<I", tid)) == b"\x04"
            )  # Wrong slot A package reserved B.
            assert serial.request(6) == b"\x05"
        finally:
            serial.close()
        record("begin-retirement-pass")
        timing = sample("migration-timing")
        assert (
            timing["scan_body_cycles_max"] < 160000
            and timing["missed_releases"] == 0
        )
        reset("wide-reset")
        wide = download("wide-source", "B")
        cli("activate", wide)
        before, values = monitor()
        edit = download("wide-edit", "A")
        cli("activate", edit)
        first = cli("update-status")["completed_scan"]
        saved = values[wide_names[0]] + first - 1 - before["scan"]
        m, v = monitor()
        base = saved + 7 * (m["scan"] - first + 1)
        assert [v[n] for n in wide_names] == [base + i for i in range(64)]
        cli("rollback")
        restored = cli("update-status")["completed_scan"]
        m, v = monitor()
        base = saved + 1 + m["scan"] - restored
        assert [v[n] for n in wide_names] == [base + i for i in range(64)]
        record(
            "maximum-reordered-migration-pass",
            checkpoint_base=saved,
            trial_scan=first,
            restore_scan=restored,
            observed=m,
        )
        timing = sample("maximum-migration-timing")
        assert (
            timing["scan_body_cycles_max"] < 160000
            and timing["missed_releases"] == 0
        )
        # Boot descriptor is rollback-capable. Access/deadline faults recover;
        # invalid exception stack forces reset and cannot preserve RAM checkpoint.
        for probe, fault in [(3, 259), (8, 258), (9, 261)]:
            reset(f"probe-{probe}-reset")
            bad = download(f"probe-{probe}", "B")
            cli("activate", bad, fail=True)
            if probe == 9:
                time.sleep(0.7)
                st = cli("status")
                assert st["active_generation"] == 1 and st["fault"] == 261
                assert cli("update-status")["kind"] == 0
                record("watchdog-reset-discards-checkpoint-pass", status=st)
                # Explicit activation from a faulted source creates no fallback.
                bad = download("fault", "B")
                st = cli("activate", bad, fail=True)
                assert (
                    st["active_generation"] == bad
                    and st["fault"] == 5
                    and st["outcome"] == 3
                )
                cli("rollback", fail=True)
                record("faulted-source-cold-start-pass", status=st)
            else:
                st = cli("status")
                diag = cli("update-status")
                assert (
                    st["active_generation"] == 1
                    and st["fault"] == 0
                    and st["outcome"] == 4
                )
                assert (
                    diag["first_fault"] == fault and diag["recovery_fault"] == 0
                )
                m, v = monitor()
                assert v["LED"] == (not v["BTN"])
                record(
                    f"probe-{probe}-auto-rollback-pass",
                    status=st,
                    diagnostic=diag,
                )
        # Outputs start zero on restoration. This source deliberately faults
        # only when saved nonzero VAR state meets that reset output image.
        for automatic in (True, False):
            reset(
                "recovery-failure-reset"
                if automatic
                else "rollback-failure-reset"
            )
            old = download("restore-fault", "B")
            cli("activate", old)
            old_first = cli("update-status")["completed_scan"]
            target = download("fault" if automatic else "edit", "A")
            cli("activate", target, fail=automatic)
            if automatic:
                diag = cli("update-status")
                checkpoint = diag["failed_scan"] - old_first
                assert (
                    diag["first_fault"] == 5
                    and diag["recovery_fault"] == 5
                    and diag["failed_generation"] == target
                )
            else:
                checkpoint = cli("update-status")["completed_scan"] - old_first
                cli("rollback", fail=True)
                diag = cli("update-status")
                assert (
                    diag["kind"] == 2
                    and diag["first_fault"] == 5
                    and diag["recovery_fault"] == 0
                )
            st = cli("status")
            m, v = monitor()
            assert (
                st["active_generation"] == old
                and st["fault"] == 5
                and st["outcome"] == 3
                and st["pending_generation"] == 0
            )
            assert v["RESTORE_COUNT"] == checkpoint and v["LED"] is False
            assert cli("info")["slots"][0]["state"] == 0
            cli("rollback", fail=True)
            record(
                "automatic-recovery-failure-pass"
                if automatic
                else "explicit-rollback-failure-pass",
                diagnostic=diag,
                observed=m,
            )
        # Failure after a successful first scan must stay latched, not auto-revert.
        reset("later-fault-reset")
        late = download("late", "B")
        cli("activate", late)
        time.sleep(0.2)
        st = cli("status")
        assert (
            st["active_generation"] == late
            and st["fault"] == 5
            and st["outcome"] == 2
        )
        cli("rollback")
        assert cli("status")["active_generation"] == 1
        record("later-fault-explicit-recovery-pass")
        record("R4-board-pass")
    finally:
        reset("restore-normal")
        st = cli("status")
        assert st["active_generation"] == 1 and st["fault"] == 0
        record("normal-boot-restored", status=st)


if __name__ == "__main__":
    main()
