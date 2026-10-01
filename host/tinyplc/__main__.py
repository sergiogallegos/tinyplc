"""plcc: compile ST or disassemble a validated image."""
import argparse
from pathlib import Path
import sys
from .compiler import compile_source
from .image import DEFAULT_PROFILE, disassemble, load_profile


def main(argv=None):
    parser = argparse.ArgumentParser(prog='plcc')
    parser.add_argument('source', type=Path, help='ST source (or image with --disassemble)')
    parser.add_argument('-o', '--output', type=Path)
    parser.add_argument('--board', type=Path, default=DEFAULT_PROFILE)
    parser.add_argument('-d', '--disassemble', action='store_true')
    args = parser.parse_args(argv)
    try:
        if args.output and args.output.resolve() == args.source.resolve():
            raise ValueError('output must differ from source')
        profile = load_profile(args.board)
        if args.disassemble:
            listing = disassemble(args.source.read_bytes(), profile)
            if args.output:
                args.output.write_text(listing)
            else:
                print(listing, end='')
        else:
            output = args.output or args.source.with_suffix('.tplc')
            if output.resolve() == args.source.resolve():
                raise ValueError('output must differ from source')
            data = compile_source(args.source.read_text(encoding='utf-8'), profile)
            output.write_bytes(data)
            print(f'{output}: {len(data)} bytes')
    except (OSError, ValueError) as error:
        print(f'{args.source}: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
