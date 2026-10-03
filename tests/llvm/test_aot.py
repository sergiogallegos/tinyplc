"""Verify emitted IR and execute AOT host code at O0/O2 against both bytecode VMs."""

import ctypes
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "host"))
from tinyplc.compiler import compile_source
from tinyplc.image import load_profile, read_image
from tinyplc.reference import run

PROFILE = load_profile()
PLCC = Path(os.environ.get("TINYPLC_PLCC", ROOT / "target/debug/plcc"))
VM = Path(os.environ.get("TINYPLC_VM_RUNNER", ROOT / "build/sim/vm-runner"))
CLANG = os.environ.get("CLANG", "clang")
LLVM_AS = os.environ.get("LLVM_AS", "llvm-as")
OPT = os.environ.get("LLVM_OPT", "opt")


def command(args):
    result = subprocess.run(
        list(map(str, args)), capture_output=True, text=True, timeout=60
    )
    if result.returncode:
        raise AssertionError(f"{args}\n{result.stdout}\n{result.stderr}")
    return result


def source(body):
    return f"PROGRAM Main\nVAR_INPUT BTN: BOOL; END_VAR\nVAR_OUTPUT LED: BOOL; END_VAR\nVAR x: DINT; y: DINT; b: BOOL; END_VAR\n{body}\nEND_PROGRAM"


class Diagnostic(ctypes.Structure):
    _fields_ = [("line", ctypes.c_uint32), ("column", ctypes.c_uint32)]


class AotTests(unittest.TestCase):
    abi = 1

    @classmethod
    def setUpClass(cls):
        for tool in (PLCC, VM, CLANG, LLVM_AS, OPT):
            if not (Path(tool).is_file() or shutil.which(str(tool))):
                raise RuntimeError(
                    f"missing {tool}; run make test-llvm with installed Rust and LLVM"
                )
        cls.temp = tempfile.TemporaryDirectory()
        cls.path = Path(cls.temp.name)
        cls.sources = [
            (ROOT / "examples/button_led.st").read_text(),
            "PROGRAM Empty END_PROGRAM",
            source(
                "x := 20 - 6 / 2 * 3 - 1; y := - - +2; b := TRUE OR FALSE XOR TRUE AND NOT FALSE; LED := b;"
            ),
            source("x := 2147483647 + 1; y := -2147483648 / -1; LED := x = y;"),
            source("x := -7 / 3; y := 7 / -3; b := x = y;"),
            source(
                "x := 65536 * 65536; y := -2147483648 - 1; b := - -2147483648 < 0;"
            ),
            source("x := 42; LED := TRUE; y := 1 / 0;"),
            source("x := 7; b := FALSE AND (1 / 0 = 0);"),
            source(
                "IF x = 0 THEN IF b THEN ELSE y := 1; END_IF; ELSIF x = 1 THEN y := 2; ELSIF x = 2 THEN y := 3; ELSE y := 4; END_IF; IF FALSE THEN END_IF; LED := BTN;"
            ),
        ]
        rng = random.Random(0x52555354)

        def expression(ty, depth):
            if not depth or rng.random() < 0.3:
                return (
                    rng.choice(
                        [
                            "x",
                            "y",
                            "0",
                            "1",
                            "-1",
                            "-2147483648",
                            "2147483647",
                            "65536",
                            "-7",
                        ]
                    )
                    if ty == 2
                    else rng.choice(["b", "BTN", "TRUE", "FALSE"])
                )
            if rng.random() < 0.2:
                return (
                    f"({'-' if ty == 2 else 'NOT'} {expression(ty, depth - 1)})"
                )
            op = (
                rng.choice(["+", "-", "*", "/"])
                if ty == 2
                else rng.choice(
                    ["AND", "OR", "XOR", "=", "<>", "<", ">", "<=", ">="]
                )
            )
            operand = (
                2
                if ty == 2 or op in ("<", ">", "<=", ">=")
                else rng.choice([1, 2])
                if op in ("=", "<>")
                else 1
            )
            return f"({expression(operand, depth - 1)} {op} {expression(operand, depth - 1)})"

        for _ in range(100):
            cls.sources.append(
                source(
                    f"IF {expression(1, 3)} THEN x := {expression(2, 3)}; ELSE y := {expression(2, 3)}; END_IF; b := {expression(1, 3)}; LED := b XOR BTN;"
                )
            )
        cls.images, cls.irs = [], []
        for index, text in enumerate(cls.sources):
            st, ll = cls.path / "source.st", cls.path / "source.ll"
            st.write_text(text)
            command([PLCC, st, "-o", ll, "--abi", cls.abi])
            cls.irs.append(ll.read_text())
            cls.images.append(compile_source(text, PROFILE))
        module = cls.path / "combined.ll"
        module.write_text(
            "\n".join(
                ir.replace("tinyplc_", f"p{i}_") for i, ir in enumerate(cls.irs)
            )
        )
        command([LLVM_AS, module, "-o", cls.path / "combined.bc"])
        command(
            [OPT, "-passes=verify", "-disable-output", cls.path / "combined.bc"]
        )
        cls.libraries = []
        for level in (0, 2):
            library = cls.path / f"programs{level}.dylib"
            command(
                [
                    CLANG,
                    f"-O{level}",
                    "-dynamiclib" if sys.platform == "darwin" else "-shared",
                    "-fPIC",
                    module,
                    "-o",
                    library,
                ]
            )
            cls.libraries.append(ctypes.CDLL(str(library)))
        # Cross-codegen smoke check only: no claim of linked/loaded MCU execution.
        arm = cls.path / "programs.arm.o"
        command(
            [
                CLANG,
                "--target=thumbv7em-none-eabi",
                "-mcpu=cortex-m4",
                "-mthumb",
                "-mfloat-abi=soft",
                "-ffreestanding",
                "-O2",
                "-c",
                module,
                "-o",
                arm,
            ]
        )
        data = arm.read_bytes()
        if (
            data[:4] != b"\x7fELF"
            or int.from_bytes(data[18:20], "little") != 40
        ):
            raise AssertionError("expected ELF ARM object")

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def native(self, library, index, values, count=None):
        cells = (ctypes.c_uint32 * max(1, len(values)))(*values)
        diagnostic = Diagnostic(999, 999)
        function = getattr(library, f"p{index}_scan")
        function.argtypes = [
            ctypes.POINTER(ctypes.c_uint32),
            ctypes.c_uint32,
            ctypes.POINTER(Diagnostic),
        ]
        function.restype = ctypes.c_uint32
        fault = function(
            cells,
            len(values) if count is None else count,
            ctypes.byref(diagnostic),
        )
        return (
            fault,
            tuple(cells)[: len(values)],
            (diagnostic.line, diagnostic.column),
        )

    def test_reference_agreement(self):
        rng = random.Random(0x414F54)
        for index, image in enumerate(self.images):
            tags = read_image(image, PROFILE).tags
            values = [
                rng.randrange(2) if t.type == 1 else rng.getrandbits(32)
                for t in tags
            ]
            for scan in range(3):
                with self.subTest(program=index, scan=scan):
                    result = run(image, PROFILE, values)
                    binary = self.path / "reference.tplc"
                    binary.write_bytes(image)
                    actual_c = json.loads(
                        command([VM, binary, 4096, *values]).stdout
                    )
                    self.assertEqual(
                        (actual_c["fault"], actual_c["values"]),
                        (result.fault, list(result.values)),
                    )
                    expected = (
                        tuple(
                            0 if tag.kind == 2 else old
                            for tag, old in zip(tags, values)
                        )
                        if result.fault
                        else result.values
                    )
                    for library in self.libraries:
                        fault, observed, diagnostic = self.native(
                            library, index, values
                        )
                        self.assertEqual(
                            (fault, observed), (result.fault, expected)
                        )
                        if fault == 0:
                            self.assertEqual(diagnostic, (0, 0))
                        else:
                            self.assertGreater(diagnostic[0], 0)
                            self.assertGreater(diagnostic[1], 0)
                    values = list(expected)

    def test_tag_metadata(self):
        for index, image in enumerate(self.images):
            tags = read_image(image, PROFILE).tags
            lib = self.libraries[1]
            self.assertEqual(
                ctypes.c_uint32.in_dll(lib, f"p{index}_abi_version").value,
                self.abi,
            )
            self.assertEqual(
                ctypes.c_uint32.in_dll(lib, f"p{index}_tag_count").value,
                len(tags),
            )
            names = ((ctypes.c_char * 32) * len(tags)).in_dll(
                lib, f"p{index}_tag_names"
            )
            types = (ctypes.c_uint8 * len(tags)).in_dll(
                lib, f"p{index}_tag_types"
            )
            classes = (ctypes.c_uint8 * len(tags)).in_dll(
                lib, f"p{index}_tag_classes"
            )
            self.assertEqual(
                [bytes(n).split(b"\0")[0].decode() for n in names],
                [t.name for t in tags],
            )
            self.assertEqual(list(types), [t.type for t in tags])
            self.assertEqual(list(classes), [t.kind for t in tags])

    def test_button_scans_and_invalid_arguments(self):
        for library in self.libraries:
            values = [0, 0, 0]
            for pressed in (0, 1, 1, 0, 0):
                values[0] = pressed
                fault, values, diagnostic = self.native(library, 0, values)
                self.assertEqual((fault, diagnostic), (0, (0, 0)))
                values = list(values)
            self.assertEqual(values, [0, 1, 2])
            self.assertEqual(
                self.native(library, 0, [1, 1, 12], count=2),
                (4, (1, 1, 12), (0, 0)),
            )
            fault, values, diagnostic = self.native(library, 0, [2, 1, 12])
            self.assertEqual((fault, values), (8, (2, 0, 12)))
            self.assertGreater(diagnostic[0], 0)

    def test_fault_position_and_transaction(self):
        text = self.sources[6]
        line = next(
            (i, line)
            for i, line in enumerate(text.splitlines(), 1)
            if " / " in line
        )
        expected = (line[0], line[1].index("/") + 1)
        for library in self.libraries:
            self.assertEqual(
                self.native(library, 6, [0, 1, 9, 11, 0]),
                (5, (0, 0, 9, 11, 0), expected),
            )

    def test_cli_rejects_without_overwriting(self):
        st, ll = self.path / "bad.st", self.path / "existing.ll"
        st.write_text(source("x := TRUE;"))
        ll.write_text("keep me")
        process = subprocess.run(
            [PLCC, st, "-o", ll], capture_output=True, text=True
        )
        self.assertNotEqual(process.returncode, 0)
        self.assertIn("assignment type mismatch", process.stderr)
        self.assertEqual(ll.read_text(), "keep me")
        for arguments in (
            [],
            ["--bad"],
            [str(st), "-o"],
            [str(st), "-o", str(st)],
            [str(st), "--abi"],
            [str(st), "--abi", "3"],
        ):
            self.assertNotEqual(
                subprocess.run(
                    [PLCC, *arguments], capture_output=True
                ).returncode,
                0,
            )


class NativeV2Tests(AotTests):
    abi = 2

    def raw(self, library, index, inputs, working, count):
        inp = (ctypes.c_uint32 * max(1, len(inputs)))(*inputs)
        work = (ctypes.c_uint32 * max(1, len(working)))(*working)
        diagnostic = Diagnostic(999, 999)
        function = getattr(library, f"p{index}_scan")
        function.argtypes = [
            ctypes.POINTER(ctypes.c_uint32),
            ctypes.POINTER(ctypes.c_uint32),
            ctypes.c_uint32,
            ctypes.POINTER(Diagnostic),
        ]
        function.restype = ctypes.c_uint32
        status = function(inp, work, count, ctypes.byref(diagnostic))
        self.assertEqual(tuple(inp)[: len(inputs)], tuple(inputs))
        return (
            status,
            tuple(work)[: len(working)],
            (diagnostic.line, diagnostic.column),
        )

    def native(self, library, index, values, count=None):
        tags = read_image(self.images[index], PROFILE).tags
        inputs = [v if t.kind == 1 else 0 for t, v in zip(tags, values)]
        working = [0 if t.kind == 1 else v for t, v in zip(tags, values)]
        status, candidate, diagnostic = self.raw(
            library,
            index,
            inputs,
            working,
            len(values) if count is None else count,
        )
        self.assertTrue(
            all(v == 0 for t, v in zip(tags, candidate) if t.kind == 1)
        )
        # Model only the specified supervisor commit/discard policy for comparison.
        if status == 4:
            observed = tuple(values)
        elif status:
            observed = tuple(
                0 if t.kind == 2 else v for t, v in zip(tags, values)
            )
        else:
            observed = tuple(
                v if t.kind == 1 else c
                for t, v, c in zip(tags, values, candidate)
            )
        return status, observed, diagnostic

    def test_separate_bases_and_exact_count(self):
        for library in self.libraries:
            # Non-input cells in the input buffer must not be used as old state.
            status, work, diag = self.raw(library, 0, [1, 99, 99], [0, 0, 7], 3)
            self.assertEqual((status, work, diag), (0, (0, 0, 8), (0, 0)))
            self.assertEqual(
                self.raw(library, 0, [1, 0, 0], [0, 1, 7], 4),
                (4, (0, 1, 7), (0, 0)),
            )
            # Fault outputs are candidate memory, not physical output policy.
            status, work, _ = self.raw(library, 0, [2, 0, 0], [0, 1, 7], 3)
            self.assertEqual((status, work), (8, (0, 1, 7)))


if __name__ == "__main__":
    unittest.main()
