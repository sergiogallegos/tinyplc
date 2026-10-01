"""Prove host-only linking for both fixed native slots; this is not a packager."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def audit(path, base):
    data = path.read_bytes()
    assert data[:6] == b'\x7fELF\x01\x01'
    assert struct.unpack_from('<H', data, 16)[0] == 2  # ET_EXEC, not ET_REL/ET_DYN
    assert struct.unpack_from('<H', data, 18)[0] == 40
    entry = struct.unpack_from('<I', data, 24)[0]
    assert entry & 1  # Callable Thumb entry.
    offset = struct.unpack_from('<I', data, 32)[0]
    width, count = struct.unpack_from('<HH', data, 46)
    executable = []
    for i in range(count):
        h = struct.unpack_from('<10I', data, offset + i * width)
        assert not (h[1] in (4, 9) and h[5]), 'unresolved relocation section'
        if not (h[2] & 2) or not h[5]:
            continue
        assert not h[2] & 1 and h[1] != 8, 'writable or zero-fill payload'
        assert base <= h[3] and h[3] + h[5] <= base + 16384
        if h[2] & 4:
            executable.append((h[3], h[3] + h[5]))
    assert any(lo <= (entry & ~1) < hi for lo, hi in executable)
    return entry


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gcc-prefix', default='arm-none-eabi-')
    args = parser.parse_args()
    out = ROOT / 'build/placement'
    out.mkdir(parents=True, exist_ok=True)
    obj = ROOT / 'build/native/user_program.o'
    linker = ROOT / 'port/nucleo_f446re/native/program.ld'
    ld, assembler, objcopy = (args.gcc_prefix + x for x in ('ld', 'as', 'objcopy'))

    def link(source, dest, base):
        imports = subprocess.check_output([args.gcc_prefix + 'nm', '-u', str(source)], text=True)
        if imports.strip():
            return subprocess.CompletedProcess([], 1, '', 'imports forbidden: ' + imports)
        return subprocess.run([ld, '--no-undefined', '--fatal-warnings',
            f'--defsym=TINYPLC_CODE_BASE={base}', '-T', str(linker), str(source),
            '-o', str(dest)], capture_output=True, text=True)

    records = []
    for slot, base in [('A', 0x20010000), ('B', 0x20014000)]:
        elf, binary = out / f'program-{slot}.elf', out / f'program-{slot}.bin'
        result = link(obj, elf, base)
        assert result.returncode == 0, result.stderr
        entry = audit(elf, base)
        subprocess.run([objcopy, '-O', 'binary', str(elf), str(binary)], check=True)
        payload = binary.read_bytes()
        assert 0 < len(payload) <= 16384
        records.append(dict(slot=slot, base=hex(base), entry=hex(entry),
                            payload_bytes=len(payload), sha256=hashlib.sha256(payload).hexdigest()))
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory)
        prefix = '.syntax unified\n.cpu cortex-m4\n.thumb\n.text\n.global tinyplc_scan\n.thumb_func\ntinyplc_scan:\n'
        cases = {
            'import': (prefix + 'bl missing_service\nbx lr\n', 0x20010000, 'imports forbidden'),
            'weak-import': (prefix + 'bx lr\n.weak missing_service\n.word missing_service\n', 0x20010000, 'imports forbidden'),
            'data': (prefix + 'bx lr\n.data\n.word 1\n', 0x20010000, 'writable globals'),
            'overflow': (prefix + 'bx lr\n.space 16385\n', 0x20010000, 'will not fit'),
            'firmware-address': (prefix + 'bx lr\n', 0x08010000, 'unsupported program slot'),
        }
        for name, (text, base, reason) in cases.items():
            source, object_path = path / f'{name}.S', path / f'{name}.o'
            source.write_text(text)
            subprocess.run([assembler, '-mcpu=cortex-m4', '-mthumb', str(source), '-o', str(object_path)], check=True)
            result = link(object_path, path / 'bad.elf', base)
            assert result.returncode != 0 and reason in result.stderr, result.stderr
        # A real absolute self-reference must be fixed on the host for each slot.
        source, object_path = path / 'absolute.S', path / 'absolute.o'
        source.write_text(prefix + 'bx lr\n.balign 4\n.word tinyplc_scan\n')
        subprocess.run([assembler, '-mcpu=cortex-m4', '-mthumb', str(source), '-o', str(object_path)], check=True)
        for base in (0x20010000, 0x20014000):
            elf, binary = path / 'absolute.elf', path / 'absolute.bin'
            result = link(object_path, elf, base)
            assert result.returncode == 0, result.stderr
            audit(elf, base)
            subprocess.run([objcopy, '-O', 'binary', str(elf), str(binary)], check=True)
            assert struct.unpack_from('<I', binary.read_bytes(), 4)[0] == base | 1
    report = dict(programs=records, rejected=list(cases), absolute_fixups='host-resolved in both slots')
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    print('Fixed A/B placement and negative links passed. Raw payloads are NOT download packages.')


if __name__ == '__main__':
    main()
