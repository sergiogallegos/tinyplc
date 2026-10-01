"""Build adversarial fixtures and emit an explicit OpenOCD test; never flashes.

Each fixture is tested on the user's authorized lab board when they separately
run OpenOCD. The script always restores the normal image after test success or
failure. All evidence is local build output until reviewed into docs/evidence.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[1]
CASES = [
    ('priv-write', 1, 259), ('input-write', 2, 259), ('code-write', 3, 259),
    ('gpio-write', 4, 259), ('priv-read', 5, 259), ('execute-data', 6, 259),
    ('kernel-svc', 7, 260), ('infinite', 8, 258), ('stack-reset', 9, 261),
    ('mask-interrupts', 10, 258), ('user-fpu', 11, 259), ('forged-return', 12, 260),
    ('stack-guard', 13, 259), ('execute-kernel', 14, 259),
    ('scheduler-svc', 15, 260), ('stack-outside-reset', 16, 261),
    ('stacking-reset', 17, 261), ('st-divide', None, 5), ('gateway-write', 18, 259), ('normal', None, 0),
]
FIELDS = ['scan_count', 'native_status', 'native_count', 'native_output',
          'assertion_latched', 'guard_entries', 'guard_returns', 'guard_control',
          'guard_boot_fault', 'guard_reset_flags', 'guard_fault_cfsr',
          'guard_fault_address', 'guard_fault_pc', 'guard_fault_sp', 'guard_fault_exc',
          'guard_fault_control', 'guard_fault_cycles',
          'guard_safe_cycles', 'guard_deadlines', 'guard_last_elapsed',
          'scan_cycles_max', 'missed_releases', 'stack_free_words', 'worker_stack_free_words']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kernel-archive', type=Path, required=True)
    parser.add_argument('--gcc-prefix', default='arm-none-eabi-')
    parser.add_argument('--case', action='append', choices=[x[0] for x in CASES],
                        help='run selected case(s), always ending with normal firmware')
    args = parser.parse_args()
    out = ROOT / 'build/isolation'
    out.mkdir(parents=True, exist_ok=True)
    manifest = []
    selected = [x for x in CASES if not args.case or x[0] in args.case or x[0] == 'normal']
    for name, probe, status in selected:
        command = [sys.executable, str(ROOT / 'scripts/build_target.py'),
                   '--kernel-archive', str(args.kernel_archive), '--gcc-prefix', args.gcc_prefix]
        if probe:
            command += ['--probe', str(probe)]
        elif name == 'st-divide':
            command += ['--source', str(ROOT / 'tests/scan/fault.st')]
        with (out / f'{name}-build.log').open('w') as log:
            subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
        image = out / f'{name}.elf'
        shutil.copyfile(ROOT / 'build/native/tinyplc-layout.elf', image)
        syms = {}
        for line in (ROOT / 'build/native/symbols.txt').read_text().splitlines():
            fields = line.split()
            if len(fields) == 3:
                syms[fields[2]] = int(fields[0], 16)
        manifest.append(dict(name=name, probe=probe, status=status, image=str(image),
                             sha256=hashlib.sha256(image.read_bytes()).hexdigest(),
                             symbols={field: syms[field] for field in FIELDS}))
        print(f'Built {name}', flush=True)
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    script = '''proc require {condition message} {
    if {![uplevel 1 [list expr $condition]]} { error $message }
}
adapter speed 1000
init
reset halt
set id [lindex [read_memory 0xE0042000 32 1] 0]
set flash_kib [lindex [read_memory 0x1FFF7A22 16 1] 0]
require {($id & 0xfff) == 0x421 && $flash_kib == 512} "Wrong board"
echo "BOARD id=$id flash_kib=$flash_kib"
set outcome [catch {
'''
    for entry in manifest:
        image = entry['image']
        if any(c in image for c in '{}\\\n'):
            raise ValueError('unsupported Tcl path')
        script += f'echo "CASE {entry["name"]} sha256={entry["sha256"]}"\n'
        script += f'program {{{image}}} verify\nreset halt\nresume\nsleep 15\nhalt\n'
        symbols = entry['symbols']
        if entry['probe']:
            script += f'set before [lindex [read_memory 0x{symbols["native_count"]:08x} 32 1] 0]\n'
            script += 'set before_odr [lindex [read_memory 0x40020014 32 1] 0]\n'
            script += 'require {$before > 0 && $before <= 3 && ($before_odr & 32)} "Fixture did not start with output ON"\n'
            script += 'echo "BEFORE n=$before output_on=1"\n'
        script += 'resume\nsleep 1200\nhalt\n'
        for field, address in symbols.items():
            script += f'set {field} [lindex [read_memory 0x{address:08x} 32 1] 0]\n'
        script += 'echo "OBSERVED ' + entry['name'] + ' ' + ' '.join(f'{f}=${f}' for f in FIELDS) + '"\n'
        script += f'require {{$native_status == {entry["status"]} && $scan_count > 10 && $assertion_latched == 0}} "Wrong outcome"\n'
        script += 'set odr [lindex [read_memory 0x40020014 32 1] 0]\n'
        if entry['status']:
            expected_n = 0 if entry['status'] in (5, 261) else 3
            script += f'require {{$native_output == 0 && !($odr & 32) && $native_count == {expected_n}}} "Fault state/output mismatch"\n'
            if entry['status'] == 5:
                script += 'require {$guard_entries == 1 && $guard_returns == 1 && $guard_control == 1} "ST arithmetic fault did not return through gateway"\n'
            elif entry['status'] == 261:
                script += 'require {$guard_boot_fault == 261 && ($guard_reset_flags & 0x20000000) && $guard_fault_sp != 0} "Missing watchdog/stack reset evidence"\n'
                if entry['name'] == 'stacking-reset':
                    script += 'require {$guard_fault_cfsr & 0x3838} "Hardware stacking fault not recorded"\n'
            else:
                script += 'require {$guard_entries == 4 && $guard_returns == 3 && $guard_control == 1} "User execution/gateway count mismatch"\n'
                script += 'require {(($guard_safe_cycles - $guard_fault_cycles) & 0xffffffff) < 512} "Unexpected ISR output response"\n'
                if entry['status'] == 258:
                    script += 'require {$guard_deadlines == 1 && $guard_last_elapsed >= 160000 && $guard_last_elapsed < 161600} "Deadline IRQ evidence missing"\n'
                elif entry['status'] == 259:
                    script += 'require {$guard_fault_cfsr != 0} "CPU fault evidence missing"\n'
        else:
            script += 'require {$guard_entries == $guard_returns && $guard_returns > 10 && $guard_control == 1 && $missed_releases == 0} "Normal isolated execution mismatch"\n'
            script += 'require {(($odr >> 5) & 1) == $native_output} "GPIO mismatch"\n'
        script += 'echo "RESULT ' + entry['name'] + ' ' + ' '.join(f'{f}=${f}' for f in FIELDS) + '"\n'
        script += 'resume\n'
    normal = manifest[-1]['image']
    script += f'''}} error_text]
# Restore usable firmware even if an assertion failed partway through the matrix.
program {{{normal}}} verify reset
if {{$outcome}} {{ echo "ISOLATION_FAIL $error_text"; shutdown error }}
echo "TINYPLC_ISOLATION_PASS"
shutdown
'''
    (out / 'run.tcl').write_text(script)
    print(f'Prepared {out / "run.tcl"}; hardware has not been accessed.')


if __name__ == '__main__':
    main()
