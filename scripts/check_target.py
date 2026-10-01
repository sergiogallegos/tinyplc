"""Offline R2.2 provenance/tool checks. Never downloads or installs anything."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, help='verify the complete upstream archive')
    parser.add_argument('--source', type=Path, help='verify reviewed files in an extracted tree')
    parser.add_argument('--tools', choices=['host', 'target', 'all'])
    args = parser.parse_args()
    if not (args.archive or args.source or args.tools):
        parser.error('choose --archive, --source, or --tools')
    lock = json.loads((ROOT / 'config/target-lock.json').read_text())
    failures = []

    def check_file(path, expected):
        try:
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            if actual != expected:
                failures.append(f'{path}: SHA-256 mismatch')
            else:
                print(f'OK {path}')
        except OSError as exc:
            failures.append(str(exc))

    if args.archive:
        check_file(args.archive, lock['freertos']['archive_sha256'])
    if args.source:
        for name, checksum in lock['freertos']['reviewed_files_sha256'].items():
            check_file(args.source / name, checksum)
        print('Source check covers reviewed files only; archive check covers all bytes.')
    if args.tools:
        target = {'arm-none-eabi-gcc', 'openocd'}
        for tool, version in lock['tools'].items():
            if args.tools == 'host' and tool in target:
                continue
            if args.tools == 'target' and tool not in target:
                continue
            executable = shutil.which(tool)
            if not executable:
                failures.append(f'{tool}: missing (selected version {version})')
                continue
            try:
                result = subprocess.run([executable, '--version'], capture_output=True,
                                        text=True, timeout=10)
                output = result.stdout + result.stderr
                if result.returncode or not re.search(r'(?<![\d.])' + re.escape(version) + r'(?![\d.])', output):
                    failures.append(f'{tool}: expected version {version}')
                else:
                    print(f'OK {tool} {version}: {executable}')
            except (OSError, subprocess.TimeoutExpired) as exc:
                failures.append(f'{tool}: {exc}')
    for failure in failures:
        print(f'FAIL {failure}')
    return bool(failures)


if __name__ == '__main__':
    raise SystemExit(main())
