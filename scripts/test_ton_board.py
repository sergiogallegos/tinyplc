"""Explicit TON lab-board acceptance. Flash current firmware; restore boot in finally."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
SOURCE = """PROGRAM TimerExercise
VAR_OUTPUT LED: BOOL; END_VAR
VAR N: DINT; Delay: TON; END_VAR
N := N + 1;
Delay(IN := N < 100 OR N >= 130, PT := T#500ms);
LED := Delay.Q;
END_PROGRAM
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", required=True)
    parser.add_argument("--gcc-prefix", default="arm-none-eabi-")
    parser.add_argument("--clang", default="clang")
    parser.add_argument("--openocd", default="openocd")
    args = parser.parse_args()
    out = ROOT / "build/ton-board"
    out.mkdir(parents=True, exist_ok=True)
    firmware = ROOT / "build/native/tinyplc-layout.elf"
    report = {
        "date": time.strftime("%Y-%m-%d"),
        "source": SOURCE,
        "firmware_sha256": hashlib.sha256(firmware.read_bytes()).hexdigest(),
        "events": [],
    }

    def record(name, **data):
        event = dict(name=name, **data)
        report["events"].append(event)
        print(json.dumps(event), flush=True)
        (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")

    def cli(*args):
        result = subprocess.run(
            [
                str(ROOT / "target/debug/plctool"),
                options.device,
                *map(str, args),
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert result.returncode == 0, (args, result.stdout, result.stderr)
        data = json.loads(result.stdout)
        record(
            "cli",
            command=[str(a).replace(str(ROOT) + "/", "") for a in args],
            result=data,
        )
        return data

    options = args

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
            timeout=30,
        )
        log = result.stdout + result.stderr
        (out / (name + ".log")).write_text(log)
        assert result.returncode == 0, log
        return log

    source = out / "exercise.st"
    source.write_text(SOURCE)
    packages = {}
    for slot in ("A", "B"):
        dest = out / f"exercise-{slot}.tplc"
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
        packages[slot] = dest
    names = [f"TIMER_INSTANCE_{i:02d}" for i in range(12)]
    wide_source = (
        "PROGRAM FullTimers VAR_OUTPUT LED: BOOL; END_VAR VAR N: DINT; PT: TIME; "
        + "".join(f"{name}: TON;" for name in names)
        + " END_VAR PT := T#10s; N := N + 1; "
        + "".join(f"{name}(IN := TRUE, PT := PT);" for name in names)
        + f" LED := {names[-1]}.Q; END_PROGRAM"
    )
    wide = out / "wide.st"
    wide.write_text(wide_source)
    wide_package = out / "wide-A.tplc"
    subprocess.run(
        [
            str(ROOT / "target/debug/plcpack"),
            str(wide),
            "--slot",
            "A",
            "-o",
            str(wide_package),
            "--clang",
            args.clang,
            "--ld",
            args.gcc_prefix + "ld",
        ],
        check=True,
    )
    report["wide_source"] = wide_source
    report["wide_package_sha256"] = hashlib.sha256(
        wide_package.read_bytes()
    ).hexdigest()
    report["package_sha256"] = {
        slot: hashlib.sha256(p.read_bytes()).hexdigest()
        for slot, p in packages.items()
    }

    def monitor():
        m = cli("monitor")
        return m, {t["name"]: t["value"] for t in m["tags"]}

    try:
        ocd("flash", f"program {{{firmware}}} verify reset exit\n")
        time.sleep(0.3)
        generation = cli("download", packages["B"])["ready_generation"]
        cli("activate", generation)
        stages = set()
        origins = {}
        previous = None
        end = time.monotonic() + 2.6
        while time.monotonic() < end:
            m, v = monitor()
            n, et, q, now = (
                v["N"],
                v["__T_DELAY_ET"],
                v["LED"],
                v["__CLOCK_MS"] & 0xFFFFFFFF,
            )
            assert m["generation"] == generation and q == v["__T_DELAY_Q"]
            enabled = n < 100 or n >= 130
            assert v["__T_DELAY_RUN"] == enabled
            if not enabled:
                assert et == 0 and q is False
                stages.add("reset")
            else:
                phase = 0 if n < 100 else 1
                stages.add(f"{phase}-done" if q else f"{phase}-waiting")
                assert q == (et == 500) and 0 <= et <= 500
                if et < 500:
                    origin = (now - et) & 0xFFFFFFFF
                    if phase in origins:
                        assert origin == origins[phase]
                    origins[phase] = origin
                if phase in origins:
                    assert et == min((now - origins[phase]) & 0xFFFFFFFF, 500)
            if previous:
                assert m["scan"] > previous
            previous = m["scan"]
            time.sleep(0.025)
        assert stages == {
            "0-waiting",
            "0-done",
            "reset",
            "1-waiting",
            "1-done",
        }, stages
        record(
            "ton-timing-reset-rearm-pass",
            stages=sorted(stages),
            clock_origins=origins,
        )
        # Same-name timer state must restart, while N is migrated.
        _, before = monitor()
        edited = cli("download", packages["A"])["ready_generation"]
        cli("activate", edited)
        m, after = monitor()
        assert m["generation"] == edited and after["N"] > before["N"]
        assert after["LED"] is False and 0 <= after["__T_DELAY_ET"] < 500, after
        time.sleep(0.6)
        _, ready = monitor()
        assert ready["LED"] is True and ready["__T_DELAY_ET"] == 500
        cli("rollback")
        m, restored = monitor()
        assert m["generation"] == generation and restored["N"] < ready["N"]
        assert restored["LED"] is False and restored["__T_DELAY_ET"] < 500, (
            restored
        )
        record(
            "timer-restart-migration-rollback-pass",
            before=before,
            after=after,
            restored=restored,
        )
        time.sleep(0.3)
        wide_generation = cli("download", wide_package)["ready_generation"]
        cli("activate", wide_generation)
        m, values = monitor()
        assert m["generation"] == wide_generation and len(m["tags"]) == 64
        for name in names:
            assert values[f"__T_{name}_ET"] == values[f"__T_{names[0]}_ET"]
        assert values["LED"] is False
        record("twelve-timers-64-cells-pass", generation=wide_generation)
        status = cli("status")
        assert status["fault"] == 0, status
        symbols = {
            p[2]: int(p[0], 16)
            for line in (ROOT / "build/native/symbols.txt")
            .read_text()
            .splitlines()
            if len(p := line.split()) == 3
        }
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
            "measurement",
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
        assert (
            values["native_status"]
            == values["assertion_latched"]
            == values["missed_releases"]
            == values["uart_rx_errors"]
            == 0
        ), values
        record("measurement", values=values)
        report["passed"] = True
    finally:
        ocd("restore-boot", "init\nreset run\nshutdown\n")
        time.sleep(0.3)
        record("restored-boot", status=cli("status"))


if __name__ == "__main__":
    main()
