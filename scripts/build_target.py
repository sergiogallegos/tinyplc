"""Build the R2.3 scaffold from an explicitly supplied verified kernel archive."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]


def run(args):
    subprocess.run(list(map(str, args)), check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kernel-archive', required=True, type=Path)
    parser.add_argument('--gcc-prefix', default='arm-none-eabi-')
    parser.add_argument('--source', type=Path, default=ROOT / 'examples/button_led.st')
    parser.add_argument('--probe', type=int, choices=range(1, 19), help='test-only adversarial image')
    args = parser.parse_args()
    lock = json.loads((ROOT / 'config/target-lock.json').read_text())
    if hashlib.sha256(args.kernel_archive.read_bytes()).hexdigest() != lock['freertos']['archive_sha256']:
        parser.error('kernel archive SHA-256 mismatch')
    gcc = args.gcc_prefix + 'gcc'
    version = subprocess.check_output([gcc, '-dumpfullversion'], text=True).strip()
    if version != lock['tools']['arm-none-eabi-gcc']:
        parser.error(f'expected GCC {lock["tools"]["arm-none-eabi-gcc"]}, got {version}')
    out = ROOT / 'build/native'
    out.mkdir(parents=True, exist_ok=True)
    upstream = out / 'upstream'
    upstream.mkdir(exist_ok=True)
    with tarfile.open(args.kernel_archive) as archive:
        top = archive.getmembers()[0].name.split('/')[0]
        archive.extractall(upstream, filter='data')
    kernel = upstream / top
    port = kernel / lock['freertos']['port']
    # Keep upstream pristine. Exactly one targeted permission change in a copy.
    original = (port / 'port.c').read_text()
    old = 'portMPU_REGION_ATTRIBUTE_REG = ( portMPU_REGION_READ_WRITE | portMPU_REGION_EXECUTE_NEVER )'
    new = 'portMPU_REGION_ATTRIBUTE_REG = ( portMPU_REGION_PRIVILEGED_READ_WRITE | portMPU_REGION_EXECUTE_NEVER )'
    if original.count(old) != 1:
        parser.error('unexpected upstream peripheral mapping; review patch')
    patched = out / 'port_hardened.c'
    patched.write_text(original.replace(old, new))
    (out / 'FreeRTOS-LICENSE.md').write_bytes((kernel / 'LICENSE.md').read_bytes())
    local = ROOT / 'port/nucleo_f446re/native'
    sources = [kernel / x for x in ['tasks.c', 'queue.c', 'list.c']]
    sources += [patched, port / 'mpu_wrappers_v2_asm.c', kernel / 'portable/Common/mpu_wrappers_v2.c']
    sources += [local / x for x in ['startup.c', 'main.c', 'memory.c']]
    sources += [ROOT / 'runtime/src/scan.c', local / 'guard.c', local / 'gateway.S']
    sources += [ROOT / 'runtime/src' / x for x in ['package.c', 'loader.c', 'engineering.c', 'snapshot.c', 'update.c']]
    sources += [local / 'engineering_board.c']
    flags = lock['runtime_cflags'] + ['-fno-builtin', '-fstack-usage', '-Wall', '-Wextra', '-Werror']
    includes = ['-I', local, '-I', kernel / 'include', '-I', port, '-I', ROOT / 'runtime/include', '-I', ROOT / 'contract']
    # ABI 2 ST code is a separate LLVM-produced object placed in executable RAM.
    plcc = ROOT / 'target/debug/plcc'
    clang = os.environ.get('CLANG', 'clang')
    ll = out / 'user_program.ll'
    user_obj = out / 'user_program.o'
    if args.probe:
        run([gcc, '-mcpu=cortex-m4', '-mthumb', f'-DPROBE={args.probe}', '-c',
             ROOT / 'tests/target/probes.S', '-o', user_obj])
    else:
        run([plcc, args.source, '--abi', '2', '-o', ll])
        run([clang, *lock['user_flags'], '-Wno-override-module', '-c', ll, '-o', user_obj])
    imports = subprocess.check_output([args.gcc_prefix + 'nm', '-u', user_obj], text=True)
    if imports.strip():
        raise RuntimeError(f'user code must have no imports: {imports}')
    objects = [user_obj]
    for index, source in enumerate(sources):
        obj = out / f'{index}_{source.stem}.o'
        extra = ['-Wno-unused-parameter'] if source.name == 'mpu_wrappers_v2_asm.c' else []
        run([gcc, *flags, *extra, *includes, '-c', source, '-o', obj])
        objects.append(obj)
    elf = out / 'tinyplc-layout.elf'
    run([gcc, *lock['runtime_cflags'], '-nostdlib', *objects, '-lgcc',
         '-T', local / 'memory.ld', '-Wl,--gc-sections', f'-Wl,-Map={out / "tinyplc-layout.map"}',
         '-Wl,--print-memory-usage', '-Wl,-z,noexecstack', '-o', elf])
    run([args.gcc_prefix + 'size', elf])
    undefined = subprocess.check_output([args.gcc_prefix + 'nm', '-u', elf], text=True)
    if undefined.strip():
        raise RuntimeError(f'unresolved symbols: {undefined}')
    symbols = subprocess.check_output([args.gcc_prefix + 'nm', '-n', elf], text=True)
    (out / 'symbols.txt').write_text(symbols)
    print(f'Built {elf}; no board flashing or execution performed.')


if __name__ == '__main__':
    main()
