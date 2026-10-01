"""Independent Python execution of validated bytecode, using integer cells."""
from dataclasses import dataclass
from .image import read_image, signed


@dataclass(frozen=True)
class Result:
    values: tuple
    fault: int
    pc: int
    opcode: int


def run(data, profile, values=None, budget=4096):
    image = read_image(data, profile)
    cells = list(values) if values is not None else [0] * len(image.tags)
    if len(cells) != len(image.tags) or any(not isinstance(v, int) or not 0 <= v <= 0xffffffff for v in cells):
        raise ValueError('values must contain one u32 cell per tag')
    if not isinstance(budget, int) or not 0 <= budget <= 0xffffffff:
        raise ValueError('budget must be u32')
    for tag, value in zip(image.tags, cells):
        if tag.type == 1 and value > 1:
            return Result(tuple(cells), 8, 65535, 0)
    instructions = {i.pc: i for i in image.instructions}
    stack, pc = [], 0
    for _ in range(budget):
        instruction = instructions[pc]
        op, args = instruction.op, instruction.args
        next_pc = pc + instruction.size
        if op == 1:
            stack.append(args[1])
        elif op == 2:
            stack.append(cells[args[0]])
        elif op == 3:
            cells[args[0]] = stack.pop()
        elif op == 0x14:
            stack.append(-stack.pop() & 0xffffffff)
        elif op == 0x23:
            stack.append(int(not stack.pop()))
        elif op == 0x40:
            next_pc = args[0]
        elif op == 0x41:
            if not stack.pop():
                next_pc = args[0]
        elif op == 0xff:
            return Result(tuple(cells), 0, pc, op)
        else:
            b, a = stack.pop(), stack.pop()
            if op == 0x10:
                value = a + b
            elif op == 0x11:
                value = a - b
            elif op == 0x12:
                value = a * b
            elif op == 0x13:
                if b == 0:
                    return Result(tuple(cells), 5, pc, op)
                sa, sb = signed(a), signed(b)
                value = abs(sa) // abs(sb)
                if (sa < 0) != (sb < 0):
                    value = -value
            elif op == 0x20:
                value = a & b
            elif op == 0x21:
                value = a | b
            elif op == 0x22:
                value = a ^ b
            elif op == 0x30:
                value = int(a == b)
            elif op == 0x31:
                value = int(a != b)
            elif op == 0x32:
                value = int(signed(a) < signed(b))
            elif op == 0x33:
                value = int(signed(a) > signed(b))
            elif op == 0x34:
                value = int(signed(a) <= signed(b))
            elif op == 0x35:
                value = int(signed(a) >= signed(b))
            stack.append(value & 0xffffffff)
        pc = next_pc
    return Result(tuple(cells), 6, pc, instructions[pc].op)
