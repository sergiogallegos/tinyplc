"""Cross-language contract fixtures; no MCU execution or compiler ABI 2 claim."""

import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
CLANG = os.environ.get("CLANG", "clang")


def command(args):
    result = subprocess.run(
        list(map(str, args)), capture_output=True, text=True, timeout=60
    )
    if result.returncode:
        raise AssertionError(f"{args}\n{result.stdout}\n{result.stderr}")


class NativeContractTests(unittest.TestCase):
    def test_c_caller_and_llvm_entry(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            common = [
                CLANG,
                "-std=c11",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-Wno-override-module",
                "-I",
                ROOT / "runtime/include",
            ]
            for level in ("-O0", "-O2"):
                executable = out / ("abi" + level)
                command(
                    [
                        *common,
                        level,
                        ROOT / "tests/abi/caller.c",
                        ROOT / "tests/abi/entry.ll",
                        "-o",
                        executable,
                    ]
                )
                command([executable])
            for source in ("caller.c", "entry.ll"):
                obj = out / (source + ".o")
                flags = (
                    common
                    if source.endswith(".c")
                    else [CLANG, "-Werror", "-Wno-override-module"]
                )
                command(
                    [
                        *flags,
                        "--target=thumbv7em-none-eabi",
                        "-mcpu=cortex-m4",
                        "-mthumb",
                        "-mfloat-abi=soft",
                        "-ffreestanding",
                        "-O2",
                        "-c",
                        ROOT / "tests/abi" / source,
                        "-o",
                        obj,
                    ]
                )
                data = obj.read_bytes()
                self.assertEqual(
                    data[:6], b"\x7fELF\x01\x01"
                )  # ELF32 little-endian
                self.assertEqual(
                    int.from_bytes(data[18:20], "little"), 40
                )  # EM_ARM


if __name__ == "__main__":
    unittest.main()
