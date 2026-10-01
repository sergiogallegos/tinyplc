"""Independent v1 image decoder, validator and human-readable disassembler."""
from dataclasses import dataclass
import json
from pathlib import Path
import re
import struct
import zlib

NAMES = {1: 'PUSH_CONST', 2: 'LOAD', 3: 'STORE', 0x10: 'ADD', 0x11: 'SUB',
         0x12: 'MUL', 0x13: 'DIV', 0x14: 'NEG', 0x20: 'AND', 0x21: 'OR',
         0x22: 'XOR', 0x23: 'NOT', 0x30: 'EQ', 0x31: 'NE', 0x32: 'LT',
         0x33: 'GT', 0x34: 'LE', 0x35: 'GE', 0x40: 'JMP', 0x41: 'JZ', 0xff: 'HALT'}
TYPES = {1: 'BOOL', 2: 'DINT'}
KINDS = {1: 'INPUT', 2: 'OUTPUT', 3: 'VAR'}
IDENTIFIER = re.compile(r'[A-Z_][A-Z_0-9]{0,30}\Z')
DEFAULT_PROFILE = Path(__file__).resolve().parents[2] / 'boards/nucleo_f446re.json'


class ImageError(ValueError):
    pass


@dataclass(frozen=True)
class Tag:
    name: str
    type: int
    kind: int


@dataclass(frozen=True)
class Instruction:
    pc: int
    op: int
    size: int
    args: tuple


@dataclass(frozen=True)
class Image:
    tags: tuple
    code: bytes
    max_stack: int
    instructions: tuple


def load_profile(path=DEFAULT_PROFILE):
    data = json.loads(Path(path).read_text())
    if not isinstance(data, dict):
        raise ValueError('board profile must be an object')
    result = {}
    for section, kind in (('inputs', 1), ('outputs', 2)):
        bindings = data.get(section, {})
        if not isinstance(bindings, dict):
            raise ValueError(f'profile {section} must be an object')
        for name, metadata in bindings.items():
            canonical = name.upper()
            if not IDENTIFIER.fullmatch(canonical) or not name.isascii():
                raise ValueError(f'invalid profile name {name!r}')
            if not isinstance(metadata, dict) or metadata.get('type') not in ('BOOL', 'DINT'):
                raise ValueError(f'invalid profile type for {name}')
            if any(key[1] == canonical for key in result):
                raise ValueError(f'duplicate profile name {name}')
            result[kind, canonical] = 1 if metadata['type'] == 'BOOL' else 2
    return result


def signed(value):
    return value if value < 0x80000000 else value - 0x100000000


def crc(image):
    return zlib.crc32(image[:20] + b'\0' * 4 + image[24:])


def build_image(tags, code, maximum, profile):
    size = 24 + 36 * len(tags) + len(code)
    data = bytearray(struct.pack('<4s6H2I', b'TPLC', 1, 24, len(code), len(tags), maximum, 0, size, 0))
    for tag in tags:
        data.extend(struct.pack('<BBH32s', tag.type, tag.kind, 0, tag.name.encode('ascii')))
    data.extend(code)
    struct.pack_into('<I', data, 20, crc(data))
    result = bytes(data)
    read_image(result, profile)
    return result


def read_image(data, profile):
    def require(condition, message):
        if not condition:
            raise ImageError(message)

    require(24 <= len(data) <= 4376, 'image size')
    magic, version, header, length, count, maximum, flags, size, checksum = struct.unpack_from('<4s6H2I', data)
    require(magic == b'TPLC' and version == 1 and header == 24 and flags == 0,
            'invalid header')
    require(0 < length <= 2048 and count <= 64 and maximum <= 64 and
            size == len(data) == 24 + 36 * count + length, 'invalid lengths/capacities')
    require(checksum == crc(data), 'CRC32 mismatch')
    tags = []
    for index in range(count):
        type_, kind, reserved, raw = struct.unpack_from('<BBH32s', data, 24 + 36 * index)
        require(type_ in TYPES and kind in KINDS and reserved == 0, 'invalid tag descriptor')
        name, separator, padding = raw.partition(b'\0')
        require(bool(separator) and not any(padding), 'invalid name padding')
        try:
            name = name.decode('ascii')
        except UnicodeDecodeError as error:
            raise ImageError('non-ASCII tag name') from error
        require(IDENTIFIER.fullmatch(name) is not None, 'invalid tag name')
        require(all(tag.name != name for tag in tags), 'duplicate tag name')
        require(kind == 3 or profile.get((kind, name)) == type_, 'unsupported I/O binding')
        tags.append(Tag(name, type_, kind))
    code = bytes(data[24 + count * 36:])
    instructions, pc = {}, 0
    while pc < length:
        op = code[pc]
        require(op in NAMES, f'{pc}: unknown opcode')
        width = 6 if op == 1 else 2 if op in (2, 3) else 3 if op in (0x40, 0x41) else 1
        require(pc + width <= length, f'{pc}: truncated operand')
        args = ()
        if op == 1:
            args = struct.unpack_from('<BI', code, pc + 1)
            require(args[0] in TYPES and (args[0] != 1 or args[1] <= 1), f'{pc}: invalid constant')
        elif op in (2, 3):
            args = (code[pc + 1],)
            require(args[0] < count, f'{pc}: tag out of range')
            require(op != 3 or tags[args[0]].kind != 1, f'{pc}: STORE to input')
        elif op in (0x40, 0x41):
            args = (struct.unpack_from('<H', code, pc + 1)[0],)
            require(pc < args[0] < length, f'{pc}: jump must be forward and within code')
        instructions[pc] = Instruction(pc, op, width, args)
        pc += width
    states, computed, halt = {0: ()}, 0, False
    for pc, instruction in instructions.items():
        op, args = instruction.op, instruction.args
        if op in (0x40, 0x41):
            require(args[0] in instructions, f'{pc}: jump into operand')
        if pc not in states:
            continue
        stack = list(states[pc])

        def pop(expected=None):
            require(bool(stack), f'{pc}: stack underflow')
            actual = stack.pop()
            require(expected is None or actual == expected, f'{pc}: operand type mismatch')
            return actual

        if op == 1:
            stack.append(args[0])
        elif op == 2:
            stack.append(tags[args[0]].type)
        elif op == 3:
            pop(tags[args[0]].type)
        elif op == 0x41:
            pop(1)
        elif op in (0x14, 0x23):
            stack.append(pop(2 if op == 0x14 else 1))
        elif op not in (0x40, 0xff):
            expected = 1 if op in (0x20, 0x21, 0x22) else None if op in (0x30, 0x31) else 2
            actual = pop(expected)
            pop(actual)
            stack.append(1 if op >= 0x20 else 2)
        require(len(stack) <= 64, f'{pc}: stack overflow')
        computed = max(computed, len(stack))
        if op == 0xff:
            require(not stack, f'{pc}: nonempty HALT')
            halt = True
            continue
        successors = [args[0]] if op == 0x40 else [pc + instruction.size]
        if op == 0x41:
            successors.append(args[0])
        for successor in successors:
            require(successor in instructions, f'{pc}: fallthrough outside code')
            state = tuple(stack)
            require(successor not in states or states[successor] == state, f'{pc}: stack merge mismatch')
            states[successor] = state
    require(halt and computed == maximum, 'HALT or declared stack mismatch')
    return Image(tuple(tags), code, maximum, tuple(instructions.values()))


def disassemble(data, profile):
    image = read_image(data, profile)
    lines = [f'TPLC v1 tags={len(image.tags)} code={len(image.code)} max_stack={image.max_stack}']
    for index, tag in enumerate(image.tags):
        lines.append(f'tag {index}: {KINDS[tag.kind]} {tag.name} : {TYPES[tag.type]}')
    for instruction in image.instructions:
        op, args = instruction.op, instruction.args
        suffix = ''
        if op == 1:
            suffix = f' {TYPES[args[0]]} {signed(args[1]) if args[0] == 2 else args[1]}'
        elif op in (2, 3):
            suffix = f' {args[0]} ({image.tags[args[0]].name})'
        elif args:
            suffix = f' {args[0]:04d}'
        lines.append(f'{instruction.pc:04d}  {NAMES[op]}{suffix}')
    return '\n'.join(lines) + '\n'
