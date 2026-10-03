import json
import os
from pathlib import Path
import pty
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class Engineering(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.temp.name)
        cc = os.environ.get("CLANG", "clang")
        for name, source in [
            ("unit", "engineering_test.c"),
            ("simulator", "simulator.c"),
            ("snapshot", "snapshot_test.c"),
            ("update", "update_test.c"),
            ("update-thread", "update_thread_test.c"),
        ]:
            subprocess.run(
                [
                    cc,
                    "-std=c11",
                    "-pthread",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    "-fsanitize=address,undefined",
                    "-Icontract",
                    "-Iruntime/include",
                    "runtime/src/scan.c",
                    "runtime/src/package.c",
                    "runtime/src/loader.c",
                    "runtime/src/engineering.c",
                    "runtime/src/snapshot.c",
                    "runtime/src/update.c",
                    f"tests/engineering/{source}",
                    "-o",
                    str(cls.out / name),
                ],
                cwd=ROOT,
                check=True,
            )

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_update_concurrency(self):
        subprocess.run(
            [str(self.out / "update-thread")], check=True, timeout=20
        )

    def test_update_transactions(self):
        subprocess.run([str(self.out / "update")], check=True)

    def test_snapshot_ownership(self):
        subprocess.run([str(self.out / "snapshot")], check=True)

    def test_parser_and_commands(self):
        subprocess.run([str(self.out / "unit")], check=True)

    def test_posix_cli_and_lost_chunk_ack(self):
        master, slave = pty.openpty()
        device = os.ttyname(slave)
        process = subprocess.Popen(
            [str(self.out / "simulator")],
            stdin=master,
            stdout=master,
            stderr=subprocess.PIPE,
            env={**os.environ, "DROP_CHUNK_ACK": "1"},
        )

        def cli(*args):
            result = subprocess.run(
                [str(ROOT / "target/debug/plctool"), device, *map(str, args)],
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout)

        try:
            info = cli("info")
            self.assertEqual(info["slots"][0]["generation"], 1)
            package = self.out / "b.tplc"
            package.write_bytes(
                bytes.fromhex(
                    (ROOT / "tests/wire/fixtures/package-b.hex").read_text()
                )
            )
            ready = cli("download", package)
            self.assertEqual(ready["ready_generation"], 2)
            self.assertEqual(cli("status")["active_generation"], 1)
            self.assertEqual(cli("activate", 2)["active_generation"], 2)
            info = cli("info")
            self.assertEqual(info["slots"][1]["state"], 1)
            snapshot = cli("monitor")
            self.assertEqual(snapshot["generation"], 2)
            self.assertEqual(len(snapshot["tags"]), 64)
            self.assertIs(snapshot["tags"][0]["value"], True)
            self.assertEqual(snapshot["tags"][-1]["name"], "TAG63")
            self.assertEqual(snapshot["tags"][-1]["value"], -37)
            # Wrong-base preflight must fail before reserving or retiring a slot.
            result = subprocess.run(
                [
                    str(ROOT / "target/debug/plctool"),
                    device,
                    "download",
                    str(package),
                ],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(cli("info")["transfer_id"], 0)
        finally:
            process.terminate()
            process.wait(timeout=5)
            os.close(master)
            os.close(slave)
            errors = process.stderr.read().decode()
            process.stderr.close()
            self.assertNotIn("ERROR: AddressSanitizer", errors)


if __name__ == "__main__":
    unittest.main()
