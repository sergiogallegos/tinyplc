"""Golden bytes are checked in, never regenerated during tests.

The C/Rust consumers intentionally check framing and package ranges/CRCs only.
They are not substitutes for R3.2's target/schema/ownership validator.
"""
import binascii
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
import zlib
ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / 'tests/wire/fixtures'


class Wire(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.temp.name)
        cls.c = cls.out / 'c-probe'
        cls.rust = cls.out / 'rust-probe'
        subprocess.run([os.environ.get('CLANG', 'clang'), '-std=c11', '-Wall', '-Wextra', '-Werror',
                        '-fsanitize=address,undefined', '-Icontract', 'tests/wire/probe.c', '-o', str(cls.c)], cwd=ROOT, check=True)
        subprocess.run(['rustc', '--edition=2021', '-Dwarnings', 'tests/wire/probe.rs', '-o', str(cls.rust)], cwd=ROOT, check=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def consumers(self, mode, blob, valid):
        path = self.out / 'input.bin'
        path.write_bytes(blob)
        for exe in (self.c, self.rust):
            result = subprocess.run([str(exe), mode, str(path)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0 if valid else 1, result.stderr)
            if valid:
                self.assertEqual(result.stdout, f'{zlib.crc32(blob):08x}\n')

    def test_generated_files(self):
        subprocess.run(['python3', 'scripts/generate_wire.py', '--check'], cwd=ROOT, check=True)

    def test_dispatch(self):
        b = bytes.fromhex((FIX / 'dispatch.hex').read_text())
        self.assertEqual(struct.unpack('<4I', b), (0x20010001, 3, 9, 0))
        self.consumers('dispatch', b, True)
        for at, value in [(0, 0x20010000), (0, 0x08010001), (4, 0), (4, 65), (8, 0), (12, 1)]:
            bad = bytearray(b)
            struct.pack_into('<I', bad, at, value)
            self.consumers('dispatch', bad, False)
        self.consumers('dispatch', b[:-1], False)

    def test_package_goldens(self):
        for name, base in [('a', 0x20010000), ('b', 0x20014000)]:
            b = bytes.fromhex((FIX / f'package-{name}.hex').read_text())
            self.assertEqual(len(b), 204)
            self.assertEqual(b[:4], b'TPCN')
            self.assertEqual(struct.unpack_from('<I', b, 24)[0], base)
            self.assertEqual(b[80:84], bytes.fromhex('00207047'))
            self.assertEqual(b[84:88], b'BTN\0')
            self.assertEqual(struct.unpack_from('<I', b, 60)[0], zlib.crc32(b[84:]))
            self.assertEqual(struct.unpack_from('<I', b, 64)[0], zlib.crc32(b[:64]+bytes(4)+b[68:]))
            self.consumers('package', b, True)

    def test_package_ranges(self):
        original = bytes.fromhex((FIX / 'package-a.hex').read_text())
        for at, value in [(8, 203), (28, 0xffffffff), (32, 0xffffffff), (32, 0),
                          (32, 3), (36, 0xfffffffe), (40, 0), (40, 0xfffffffe),
                          (44, 1), (44, 4), (48, 80), (48, 0xffffffff)]:
            b = bytearray(original)
            struct.pack_into('<I', b, at, value)
            struct.pack_into('<I', b, 64, 0)
            struct.pack_into('<I', b, 64, zlib.crc32(b))
            self.consumers('package', b, False)
        for at, value in [(52, 0), (52, 65), (54, 39)]:
            b = bytearray(original)
            struct.pack_into('<H', b, at, value)
            struct.pack_into('<I', b, 64, 0)
            struct.pack_into('<I', b, 64, zlib.crc32(b))
            self.consumers('package', b, False)
        for size in (0, 1, 63, 79, 80, 83, 203):
            self.consumers('package', original[:size], False)
        self.consumers('package', original+b'\0', False)
        damaged = bytearray(original)
        damaged[-1] ^= 1
        self.consumers('package', damaged, False)

    def test_frames_and_response_widths(self):
        # Independent explicit struct formats cross-check the source layouts.
        requests = ['<', '<I', '<II', '<I', '<I', '<', '<IQBB', '<IBI', '<', '<']
        responses = ['<B6H3I4H4I16s16s', '<B4I', '<BI', '<BI', '<BI', '<BI', '<BIQBBB', '<BIQ', '<BIQBBH5IiQ', '<5B7IQIQ']
        spec = json.loads((ROOT / 'contract/wire.json').read_text())
        widths = {'u8': 1, 'u16': 2, 'u32': 4, 'i32': 4, 'u64': 8}
        for i, command in enumerate(spec['commands'].values()):
            for direction, formats in [('request', requests), ('response', responses)]:
                fields = spec['layouts'][command[direction]]
                size = sum(widths[k] if k in widths else int(k) for _, k in fields)
                self.assertEqual(size, struct.calcsize(formats[i]))
        for entry in json.loads((FIX / 'frames.json').read_text()):
            b = bytes.fromhex(entry['hex'])
            self.assertEqual(b[0], 0xa5)
            self.assertEqual(b[3], entry['command'])
            self.assertEqual(b[4:-2].hex(), entry['payload'])
            self.assertEqual(struct.unpack_from('<H', b, 1)[0], len(b)-5)
            self.assertEqual(struct.unpack_from('<H', b, len(b)-2)[0], binascii.crc_hqx(b[1:-2], 0xffff))
            self.consumers('frame', b, True)
            if entry['name'].startswith('command-'):
                index = (entry['command'] & 0x7f)-1
                response = bool(entry['command'] & 0x80)
                expected = struct.calcsize(responses[index] if response else requests[index])
                if index == 2 and not response: expected += 4
                if index == 6 and response: expected += 3*40
                self.assertEqual(len(b)-6, expected)
        normal = bytes.fromhex('a5010001')
        normal += struct.pack('<H', binascii.crc_hqx(normal[1:], 0xffff))
        for size in range(len(normal)):
            self.consumers('frame', normal[:size], False)
        for bad in [normal+b'\0', bytes([0])+normal[1:], normal[:-1]+bytes([normal[-1]^1]),
                    bytes.fromhex('a50000010000'), bytes.fromhex('a5ffff010000')]:
            self.consumers('frame', bad, False)
        # Maximum framing length, separate from command-specific chunk limit.
        body = struct.pack('<HB', 257, 0x7f) + bytes(256)
        self.consumers('frame', b'\xa5'+body+struct.pack('<H', binascii.crc_hqx(body, 0xffff)), True)
        self.consumers('frame', bytes(263), False)


if __name__ == '__main__':
    unittest.main()
