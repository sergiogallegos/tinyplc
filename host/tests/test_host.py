import json
import os
from pathlib import Path
import random
import struct
import subprocess
import sys
import tempfile
import unittest

from tinyplc.compiler import CompileError, compile_source, lex
from tinyplc.image import ImageError, crc, disassemble, load_profile, read_image
from tinyplc.reference import run

ROOT = Path(__file__).resolve().parents[2]
PROFILE = load_profile()
RUNNER = Path(os.environ.get("TINYPLC_VM_RUNNER", ROOT / "build/sim/vm-runner"))


def source(body, declarations="VAR x : DINT; y : DINT; b : BOOL; END_VAR"):
    return f"PROGRAM Main\n{declarations}\n{body}\nEND_PROGRAM"


def raw_image(code, maximum=0, descriptors=b""):
    data = bytearray(
        struct.pack(
            "<4s6H2I",
            b"TPLC",
            1,
            24,
            len(code),
            len(descriptors) // 36,
            maximum,
            0,
            24 + len(descriptors) + len(code),
            0,
        )
    )
    data.extend(descriptors + code)
    struct.pack_into("<I", data, 20, crc(data))
    return bytes(data)


def descriptor(name="X", type_=2, kind=3):
    return struct.pack("<BBH32s", type_, kind, 0, name.encode())


class CompilerTests(unittest.TestCase):
    def test_golden_not(self):
        data = compile_source(
            source(
                "LED := NOT BTN;",
                "VAR_INPUT BTN : BOOL; END_VAR\nVAR_OUTPUT LED : BOOL; END_VAR",
            ),
            PROFILE,
        )
        # Fixed whole-image fixture, including CRC, rather than rebuilding it with production helpers.
        self.assertEqual(
            data.hex(),
            "54504c43010018000600020001000000660000007b78e0de"
            "0101000042544e0000000000000000000000000000000000000000000000000000000000"
            "010200004c45440000000000000000000000000000000000000000000000000000000000"
            "0200230301ff",
        )
        self.assertEqual(
            disassemble(data, PROFILE),
            "TPLC v1 tags=2 code=6 max_stack=1\ntag 0: INPUT BTN : BOOL\n"
            "tag 1: OUTPUT LED : BOOL\n0000  LOAD 0 (BTN)\n0002  NOT\n0003  STORE 1 (LED)\n0005  HALT\n",
        )

    def test_button_golden_and_scans(self):
        data = compile_source(
            (ROOT / "examples/button_led.st").read_text(), PROFILE
        )
        image = read_image(data, PROFILE)
        self.assertEqual(
            image.code.hex(),
            "020041130002020102010000001003024013000200230301ff",
        )
        self.assertEqual(image.max_stack, 2)
        values = [0, 0, 0]
        for pressed in [0, 1, 1, 0, 0]:
            values[0] = pressed
            result = run(data, PROFILE, values)
            self.assertEqual(result.fault, 0)
            values = list(result.values)
        self.assertEqual(values, [0, 1, 2])

    def test_precedence_associativity(self):
        data = compile_source(
            source(
                "x := 20 - 6 / 2 * 3 - 1; y := - - +2; b := TRUE OR FALSE XOR TRUE AND NOT FALSE;"
            ),
            PROFILE,
        )
        self.assertEqual(run(data, PROFILE).values, (10, 2, 1))
        data = compile_source(
            source("b := 1 + 2 * 3 = 7 AND 9 > 8; x := 20 / 3 / 2;"), PROFILE
        )
        self.assertEqual(run(data, PROFILE).values, (3, 0, 1))
        data = compile_source(source("b := TRUE = FALSE = FALSE;"), PROFILE)
        self.assertEqual(run(data, PROFILE).values[-1], 1)

    def test_conditions_and_empty_blocks(self):
        body = "IF x = 0 THEN IF b THEN ELSE y := 1; END_IF; ELSIF x = 1 THEN y := 2; ELSIF x = 2 THEN y := 3; ELSE y := 4; END_IF; IF FALSE THEN END_IF;"
        data = compile_source(source(body), PROFILE)
        for value, expected in [(0, 1), (1, 2), (2, 3), (3, 4)]:
            self.assertEqual(
                run(data, PROFILE, [value, 0, 0]).values[1], expected
            )
        self.assertEqual(
            run(compile_source(source("", ""), PROFILE), PROFILE).values, ()
        )

    def test_case_comments_and_positions(self):
        data = compile_source(
            "program main\n(* comment\nsecond *)var x : dint; end_var\nx := 1; end_program",
            PROFILE,
        )
        self.assertEqual(read_image(data, PROFILE).tags[0].name, "X")
        token = lex("(* a\nb *)\n  missing")[0]
        self.assertEqual((token.line, token.column), (3, 3))
        with self.assertRaisesRegex(CompileError, r"^3:3: unknown tag MISSING"):
            compile_source(
                "PROGRAM Main\nVAR x : DINT; END_VAR\n  missing := 1;\nEND_PROGRAM",
                PROFILE,
            )

    def test_errors(self):
        cases = [
            (source("x := TRUE;"), "assignment type"),
            (source("b := 1 AND 2;"), "operand type"),
            (source("b := TRUE < FALSE;"), "operand type"),
            (source("b := TRUE = 1;"), "operand type"),
            (source("x := NOT 1;"), "operand type"),
            (source("b := +TRUE;"), "operand type"),
            (source("IF x THEN END_IF;"), "condition"),
            (source("x := missing;"), "unknown tag"),
            (source("BTN := FALSE;", "VAR_INPUT BTN : BOOL; END_VAR"), "input"),
            (source("", "VAR x : BOOL; X : DINT; END_VAR"), "duplicate"),
            (source("", "VAR_INPUT LED : BOOL; END_VAR"), "I/O"),
            (source("", "VAR_OUTPUT LED : DINT; END_VAR"), "I/O"),
            (source("", "VAR_INPUT OTHER : BOOL; END_VAR"), "I/O"),
            (source("x := 2147483648;"), "out of range"),
            (source("x := -2147483649;"), "out of range"),
            (source("x := " + "9" * 5000 + ";"), "out of range"),
            (source("x := 1"), "expected ;"),
            (source("IF TRUE THEN x := 1;"), "expected END_IF"),
            (source("WHILE TRUE DO END_WHILE;"), "expected :="),
            (source("x := 1.5;"), "unexpected character"),
            (source("x := 1;") + " junk", "expected EOF"),
            ("PROGRAM Main (* missing", "unterminated"),
            ("PROGRAM Main (* (* *) END_PROGRAM", "nested comments"),
            (
                source("", "VAR " + "a" * 32 + ": BOOL; END_VAR"),
                "31 characters",
            ),
            (source("", "VAR café : BOOL; END_VAR"), "unexpected character"),
            (source("", "VAR x : REAL; END_VAR"), "BOOL or DINT"),
        ]
        for text, message in cases:
            with self.subTest(message=message, source=text[:100]):
                with self.assertRaisesRegex(CompileError, message):
                    compile_source(text, PROFILE)

    def test_limits_and_long_expressions(self):
        declarations = (
            "VAR " + "".join(f"v{i}: DINT;" for i in range(64)) + "END_VAR"
        )
        self.assertEqual(
            len(
                read_image(
                    compile_source(source("", declarations), PROFILE), PROFILE
                ).tags
            ),
            64,
        )
        with self.assertRaisesRegex(CompileError, "tag capacity"):
            compile_source(
                source(
                    "", declarations.replace("END_VAR", "extra: DINT; END_VAR")
                ),
                PROFILE,
            )
        for text, message in [
            (source("x := 1;" * 300), "capacity"),
            (source("x := " + "(" * 70 + "1" + ")" * 70 + ";"), "nesting"),
            (source("IF TRUE THEN " * 70 + "END_IF;" * 70), "nesting"),
            (" " * (1024 * 1024 + 1), "1 MiB"),
            (source("x := " + "+".join(["1"] * 2000) + ";"), "capacity"),
        ]:
            with self.assertRaisesRegex(CompileError, message):
                compile_source(text, PROFILE)
        data = compile_source(
            source("x := " + "+".join(["1"] * 200) + ";"), PROFILE
        )
        self.assertEqual(run(data, PROFILE).values[0], 200)
        exact = source("x := 1;" * 255 + "x := x + x;")
        self.assertEqual(
            len(read_image(compile_source(exact, PROFILE), PROFILE).code), 2048
        )
        with self.assertRaisesRegex(CompileError, "capacity"):
            compile_source(exact.replace("x + x", "x + -x"), PROFILE)

    def test_arithmetic_edges_and_eager_logic(self):
        cases = [
            ("2147483647 + 1", 0x80000000),
            ("-2147483648 / -1", 0x80000000),
            ("-7 / 3", 0xFFFFFFFE),
            ("7 / -3", 0xFFFFFFFE),
            ("-7 / -3", 2),
            ("- -2147483648", 0x80000000),
            ("65536 * 65536", 0),
            ("-2147483648 - 1", 0x7FFFFFFF),
        ]
        for expression, expected in cases:
            self.assertEqual(
                run(
                    compile_source(source(f"x := {expression};"), PROFILE),
                    PROFILE,
                ).values[0],
                expected,
            )
        result = run(
            compile_source(
                source("x := 7; b := FALSE AND (1 / 0 = 0);"), PROFILE
            ),
            PROFILE,
        )
        self.assertEqual(
            (result.fault, result.values[0], result.opcode), (5, 7, 0x13)
        )

    def test_cli(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            st, image = directory / "test.st", directory / "test.tplc"
            st.write_text(source("x := 4;"))
            command = [sys.executable, "-m", "tinyplc"]
            compiled = subprocess.run(
                command + [str(st), "-o", str(image)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            listing = subprocess.run(
                command + ["-d", str(image)], capture_output=True, text=True
            )
            self.assertEqual(listing.returncode, 0, listing.stderr)
            self.assertIn("PUSH_CONST DINT 4", listing.stdout)
            before = image.read_bytes()
            st.write_text(source("x := TRUE;"))
            rejected = subprocess.run(
                command + [str(st), "-o", str(image)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(rejected.returncode, 1)
            self.assertIn("assignment type mismatch", rejected.stderr)
            self.assertNotIn("Traceback", rejected.stderr)
            self.assertEqual(image.read_bytes(), before)
            invalid_profile = directory / "invalid.json"
            invalid_profile.write_text("[]")
            for arguments in (
                [str(st), "--board", str(invalid_profile)],
                ["-d", str(image), "-o", str(image)],
                [str(directory / "missing.st")],
            ):
                failure = subprocess.run(
                    command + arguments, capture_output=True, text=True
                )
                self.assertEqual(failure.returncode, 1)
                self.assertNotIn("Traceback", failure.stderr)
            self.assertEqual(image.read_bytes(), before)

    def test_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "board.json"
            path.write_text(
                json.dumps({"inputs": {"sensor": {"type": "DINT"}}})
            )
            profile = load_profile(path)
            data = compile_source(
                source("", "VAR_INPUT SENSOR : DINT; END_VAR"), profile
            )
            self.assertEqual(read_image(data, profile).tags[0].type, 2)
            with self.assertRaises(ImageError):
                read_image(data, PROFILE)
            path.write_text(
                '{"inputs":{"a":{"type":"BOOL"},"A":{"type":"DINT"}}}'
            )
            with self.assertRaisesRegex(ValueError, "duplicate"):
                load_profile(path)


class DifferentialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not RUNNER.is_file():
            raise RuntimeError(
                "build vm-runner first (make test), or set TINYPLC_VM_RUNNER"
            )
        cls.directory = tempfile.TemporaryDirectory()
        cls.path = Path(cls.directory.name) / "program.tplc"

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def native(self, data, values=(), budget=4096):
        self.path.write_bytes(data)
        process = subprocess.run(
            [str(RUNNER), str(self.path), str(budget), *map(str, values)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(process.returncode, 0, process.stderr)
        return json.loads(process.stdout)

    def compare(self, data, values=None, budget=4096):
        python = run(data, PROFILE, values, budget)
        native = self.native(data, values or (), budget)
        self.assertTrue(native["accepted"])
        self.assertEqual(
            (native["values"], native["fault"], native["pc"], native["opcode"]),
            (list(python.values), python.fault, python.pc, python.opcode),
        )
        return python

    def test_opcodes_and_faults(self):
        bodies = [
            "x := x + y; x := x - y; x := x * y; x := x / y; x := -x; b := NOT b;",
            "b := b AND TRUE; b := b OR FALSE; b := b XOR TRUE; b := b = FALSE; b := b <> TRUE;",
            "b := x = y; b := x <> y; b := x < y; b := x > y; b := x <= y; b := x >= y;",
            "IF b THEN x := 8; ELSIF x = 0 THEN x := 9; ELSE x := 10; END_IF;",
            "x := 42; y := 1 / 0;",
            "x := -2147483648 / -1;",
        ]
        seen = set()
        for body in bodies:
            data = compile_source(source(body), PROFILE)
            seen.update(i.op for i in read_image(data, PROFILE).instructions)
            for values in (
                [0, 0, 0],
                [0x80000000, 0xFFFFFFFF, 1],
                [0x7FFFFFFF, 3, 0],
            ):
                self.compare(data, values)
            for budget in (0, 1, 2, 5, 20):
                self.compare(data, [1, 2, 1], budget)
        from tinyplc.image import NAMES

        self.assertEqual(seen, set(NAMES))
        data = compile_source(source("x := 1;"), PROFILE)
        self.assertEqual(self.compare(data, budget=2).fault, 6)
        self.assertEqual(self.compare(data, budget=3).fault, 0)
        self.assertEqual(self.compare(data, [0, 0, 2]).fault, 8)
        # Exercise the image/VM stack boundary independently of parser nesting.
        full_stack = raw_image(
            bytes.fromhex("010201000000") * 64 + b"\x03\x00" * 64 + b"\xff",
            64,
            descriptor(),
        )
        self.assertEqual(self.compare(full_stack).values, (1,))

    def test_compiled_button_scans(self):
        data = compile_source(
            (ROOT / "examples/button_led.st").read_text(), PROFILE
        )
        values = [0, 0, 0]
        for pressed in (0, 1, 1, 0, 0):
            values[0] = pressed
            values = list(self.compare(data, values).values)
        self.assertEqual(values, [0, 1, 2])

    def test_random_typed_asts(self):
        rng = random.Random(0x4D32)
        edges = [0, 1, -1, -2147483648, 2147483647, 65536, -7, 3]

        # Test-owned AST generator/evaluator also checks compilation, independently
        # of both bytecode interpreters. Each node carries its result type.
        def generate(type_, depth):
            if depth == 0 or rng.random() < 0.3:
                if rng.random() < 0.4:
                    return (
                        "name",
                        type_,
                        rng.choice(["x", "y"]) if type_ == 2 else "b",
                    )
                return (
                    "literal",
                    type_,
                    rng.choice(edges) if type_ == 2 else rng.randrange(2),
                )
            if rng.random() < 0.2:
                return (
                    "unary",
                    type_,
                    "-" if type_ == 2 else "NOT",
                    generate(type_, depth - 1),
                )
            if type_ == 2:
                op, operand = rng.choice(["+", "-", "*", "/"]), 2
            else:
                op = rng.choice(
                    ["AND", "OR", "XOR", "=", "<>", "<", ">", "<=", ">="]
                )
                operand = (
                    1
                    if op in ("AND", "OR", "XOR")
                    else rng.choice([1, 2])
                    if op in ("=", "<>")
                    else 2
                )
            return (
                "binary",
                type_,
                op,
                generate(operand, depth - 1),
                generate(operand, depth - 1),
            )

        def render(node):
            kind, type_, value, *children = node
            if kind == "name":
                return value
            if kind == "literal":
                return (
                    str(value) if type_ == 2 else "TRUE" if value else "FALSE"
                )
            if kind == "unary":
                return f"({value} {render(children[0])})"
            return f"({render(children[0])} {value} {render(children[1])})"

        def signed_cell(value):
            return (value + 2**31) % 2**32 - 2**31

        def evaluate(node, state):
            kind, type_, op, *children = node
            if kind == "name":
                return state[op]
            if kind == "literal":
                return op & 0xFFFFFFFF
            a = evaluate(children[0], state)
            if kind == "unary":
                return (-a if op == "-" else int(not a)) & 0xFFFFFFFF
            b = evaluate(children[1], state)
            sa, sb = signed_cell(a), signed_cell(b)
            if op == "/":
                if sb == 0:
                    raise ZeroDivisionError
                return (
                    int(abs(sa) // abs(sb))
                    * (-1 if (sa < 0) != (sb < 0) else 1)
                ) & 0xFFFFFFFF
            return {
                "+": lambda: a + b,
                "-": lambda: a - b,
                "*": lambda: a * b,
                "AND": lambda: a & b,
                "OR": lambda: a | b,
                "XOR": lambda: a ^ b,
                "=": lambda: a == b,
                "<>": lambda: a != b,
                "<": lambda: sa < sb,
                ">": lambda: sa > sb,
                "<=": lambda: sa <= sb,
                ">=": lambda: sa >= sb,
            }[op]() & 0xFFFFFFFF

        for case in range(200):
            condition, first, second, boolean = (
                generate(1, 3),
                generate(2, 3),
                generate(2, 3),
                generate(1, 3),
            )
            text = source(
                f"IF {render(condition)} THEN x := {render(first)}; ELSE y := {render(second)}; END_IF; b := {render(boolean)};"
            )
            data = compile_source(text, PROFILE)
            values = [
                rng.choice(edges) & 0xFFFFFFFF,
                rng.getrandbits(32),
                rng.randrange(2),
            ]
            for scan in range(3):
                with self.subTest(
                    seed="0x4d32", case=case, scan=scan, source=text
                ):
                    state = dict(zip(("x", "y", "b"), values))
                    fault = 0
                    try:
                        if evaluate(condition, state):
                            state["x"] = evaluate(first, state)
                        else:
                            state["y"] = evaluate(second, state)
                        state["b"] = evaluate(boolean, state)
                    except ZeroDivisionError:
                        fault = 5
                    result = self.compare(data, values)
                    self.assertEqual(result.fault, fault)
                    self.assertEqual(result.values, tuple(state.values()))
                    values = list(result.values)

    def test_malformed_images(self):
        push_bool = bytes.fromhex("010100000000")
        push_dint = bytes.fromhex("010201000000")
        invalid = [
            b"",
            b"TPLC",
            raw_image(b"\x00"),
            raw_image(b"\x01"),
            raw_image(b"\x02\x00\xff"),
            raw_image(b"\x03\x00\xff", descriptors=descriptor("BTN", 1, 1)),
            raw_image(b"\x40\x00\x00\xff"),
            raw_image(b"\x40\x02\x00\xff"),
            raw_image(b"\x40\xff\xff\xff"),
            raw_image(push_bool + b"\xff", 1),
            raw_image(b"\x10\xff"),
            raw_image(push_bool + b"\x14\xff", 1),
            raw_image(push_dint + b"\x41\x09\x00\xff", 1),
            raw_image(push_bool + b"\x23", 1),
            raw_image(b"\xff", 1),
            raw_image(b"\xff\x99"),
            raw_image(b"\xff", descriptors=descriptor("lower")),
            raw_image(b"\xff", descriptors=descriptor() * 2),
            raw_image(b"\xff", descriptors=descriptor("OTHER", 1, 1)),
            raw_image(b"\xff", descriptors=descriptor(type_=9)),
            raw_image(bytes.fromhex("010102000000ff"), 1),
            raw_image(push_dint * 65 + b"\xff", 64),
            # JZ path arrives empty; fallthrough path arrives with a DINT.
            raw_image(push_bool + b"\x41\x0f\x00" + push_dint + b"\xff", 1),
            raw_image(push_bool + push_dint + b"\x30\xff", 2),
        ]
        valid = compile_source(source("x := x + 1;"), PROFILE)
        for offset in (0, 4, 6, 8, 10, 12, 14, 16, 20, 26, 28):
            changed = bytearray(valid)
            changed[offset] ^= 0x80
            if offset != 20:
                struct.pack_into("<I", changed, 20, crc(changed))
            invalid.append(bytes(changed))
        invalid.extend([valid[:-1], valid + b"\0"])
        for data in invalid:
            with self.subTest(image=data.hex()[:100]):
                with self.assertRaises(ImageError):
                    read_image(data, PROFILE)
                self.assertFalse(self.native(data)["accepted"])

    def test_seeded_image_mutations(self):
        rng = random.Random(0xC0DE)
        original = compile_source(
            source("IF b THEN x := x + 1; ELSE y := -y; END_IF;"), PROFILE
        )
        for case in range(200):
            mutated = bytearray(original)
            for _ in range(rng.randint(1, 3)):
                mutated[rng.randrange(len(mutated))] ^= rng.randrange(1, 256)
            if case % 2:
                struct.pack_into("<I", mutated, 20, crc(mutated))
            try:
                read_image(mutated, PROFILE)
                accepted = True
            except ImageError:
                accepted = False
            with self.subTest(seed="0xc0de", case=case):
                self.assertEqual(self.native(mutated)["accepted"], accepted)
                if accepted:
                    self.compare(mutated)


if __name__ == "__main__":
    unittest.main()
