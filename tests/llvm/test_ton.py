"""Execute real emitted TON machine code with a deterministic millisecond clock."""
import ctypes as c
import random
import sys
import tempfile
import unittest
from pathlib import Path
from test_aot import command, ROOT, PLCC, CLANG, LLVM_AS, OPT, Diagnostic

SOURCE = '''PROGRAM Timers
VAR_INPUT BTN: BOOL; END_VAR
VAR_OUTPUT LED: BOOL; END_VAR
VAR delay: TON; other: TON; pt: TIME; skip: BOOL; twice: BOOL; fail: BOOL; n: DINT; END_VAR
IF NOT skip THEN
    delay(IN := BTN, PT := pt);
    IF twice THEN delay(IN := BTN, PT := pt); END_IF;
END_IF;
other(IN := NOT BTN, PT := T#25ms);
LED := delay.Q;
IF fail THEN n := n / 0; END_IF;
END_PROGRAM
'''

class TonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.path = Path(cls.temp.name)
        st, ll = cls.path/'ton.st', cls.path/'ton.ll'
        st.write_text(SOURCE)
        command([PLCC, st, '--abi', 2, '-o', ll])
        command([LLVM_AS, ll, '-o', cls.path/'ton.bc'])
        command([OPT, '-passes=verify', '-disable-output', cls.path/'ton.bc'])
        cls.libraries = []
        for level in (0, 2):
            lib = cls.path/f'ton{level}.dylib'
            command([CLANG, f'-O{level}', '-dynamiclib' if sys.platform == 'darwin' else '-shared', '-fPIC', ll, '-o', lib])
            cls.libraries.append(c.CDLL(str(lib)))
        command([CLANG, '--target=thumbv7em-none-eabi', '-mcpu=cortex-m4', '-mthumb', '-mfloat-abi=soft', '-ffreestanding', '-O2', '-c', ll, '-o', cls.path/'ton.o'])

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def state(self, lib):
        count = c.c_uint32.in_dll(lib, 'tinyplc_tag_count').value
        names = ((c.c_char * 32) * count).in_dll(lib, 'tinyplc_tag_names')
        indices = {bytes(n).split(b'\0')[0].decode(): i for i, n in enumerate(names)}
        inputs, cells = (c.c_uint32 * count)(), (c.c_uint32 * count)()
        function = lib.tinyplc_scan
        function.argtypes = [c.POINTER(c.c_uint32), c.POINTER(c.c_uint32), c.c_uint32, c.POINTER(Diagnostic)]
        function.restype = c.c_uint32
        def scan(now, enabled, pt, *, skip=False, twice=False, fail=False, expected_fault=0):
            inputs[indices['BTN']] = enabled
            inputs[indices['__CLOCK_MS']] = now & 0xffffffff
            for name, value in [('PT', pt), ('SKIP', skip), ('TWICE', twice), ('FAIL', fail)]:
                cells[indices[name]] = value
            before = tuple(cells)
            frozen = tuple(inputs)
            diag = Diagnostic()
            fault = function(inputs, cells, count, c.byref(diag))
            self.assertEqual(fault, expected_fault)
            self.assertEqual(tuple(inputs), frozen)
            self.assertEqual(cells[indices['__CLOCK_MS']], 0)
            if fault:
                self.assertEqual(tuple(cells), before)
                self.assertGreater(diag.line, 0)
            return {name: cells[i] for name, i in indices.items()}
        return scan

    def test_edges_jitter_reset_zero_and_wrap(self):
        for lib in self.libraries:
            scan = self.state(lib)
            for now, enabled, pt, q, et in [
                (100, 0, 50, 0, 0), (113, 1, 50, 0, 0),
                (124, 1, 50, 0, 11), (162, 1, 50, 0, 49),
                (163, 1, 50, 1, 50), (190, 1, 50, 1, 50),
                (191, 0, 50, 0, 0), (192, 1, 0, 1, 0),
                (193, 0, 0, 0, 0), (0xfffffff0, 1, 50, 0, 0),
                (0x10000000a, 1, 50, 0, 26), (0x100000022, 1, 50, 1, 50),
            ]:
                result = scan(now, enabled, pt)
                self.assertEqual((result['LED'], result['__T_DELAY_ET']), (q, et))

    def test_conditional_calls_presets_multiple_instances_and_atomic_fault(self):
        for lib in self.libraries:
            scan = self.state(lib)
            scan(100, 1, 100)
            r = scan(150, 1, 100, twice=True)
            self.assertEqual(r['__T_DELAY_ET'], 50)  # same frozen time, no double counting
            r = scan(200, 1, 100, skip=True)
            self.assertEqual(r['__T_DELAY_ET'], 50)  # skipped invocation retains outputs
            r = scan(201, 1, 200)
            self.assertEqual((r['LED'], r['__T_DELAY_ET']), (0, 101))
            r = scan(202, 1, 50)
            self.assertEqual((r['LED'], r['__T_DELAY_ET']), (1, 50))
            r = scan(203, 1, 150)
            self.assertEqual((r['LED'], r['__T_DELAY_ET']), (0, 103))
            scan(250, 1, 150, fail=True, expected_fault=5)
            r = scan(251, 1, 150)
            self.assertEqual((r['LED'], r['__T_DELAY_ET']), (1, 150))
            scan(260, 0, 150)
            r = scan(285, 0, 150)
            self.assertEqual((r['__T_DELAY_Q'], r['__T_OTHER_Q'], r['__T_OTHER_ET']), (0, 1, 25))
            scan(300, 1, 0x80000000, expected_fault=9)

    def test_saturation_and_seeded_elapsed_reference(self):
        for lib in self.libraries:
            scan = self.state(lib)
            scan(0, 1, 0x7fffffff)
            r = scan(0x80000000, 1, 0x7fffffff)
            self.assertEqual((r['LED'], r['__T_DELAY_ET']), (1, 0x7fffffff))
            r = scan(0xffffffff, 1, 0x7fffffff)
            self.assertEqual(r['__T_DELAY_AGE'], 0x7fffffff)
            rng = random.Random(73)
            now, start, running, q, et = 0xffffff00, 0, False, 0, 0
            scan(now, 0, 100)
            for _ in range(1000):
                now += rng.randrange(1, 25)
                enabled, skip, pt = rng.random() > .04, rng.random() < .1, rng.randrange(300)
                if not skip:
                    if enabled and not running: start = now
                    age = min(now-start, 0x7fffffff) if enabled else 0
                    et, q, running = min(age, pt), int(enabled and age >= pt), enabled
                r = scan(now, enabled, pt, skip=skip, twice=True)
                self.assertEqual((r['LED'], r['__T_DELAY_ET']), (q, et))
