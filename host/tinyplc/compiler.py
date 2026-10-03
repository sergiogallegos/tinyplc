"""Positioned lexer, recursive-descent AST parser, type checker and emitter."""

from dataclasses import dataclass
import re
from .image import Tag, build_image

KEYWORDS = set(
    "PROGRAM END_PROGRAM VAR_INPUT VAR_OUTPUT VAR END_VAR BOOL DINT IF THEN ELSIF ELSE END_IF TRUE FALSE AND OR XOR NOT".split()
)
PRECEDENCE = {
    "OR": 1,
    "XOR": 2,
    "AND": 3,
    "=": 4,
    "<>": 4,
    "<": 5,
    ">": 5,
    "<=": 5,
    ">=": 5,
    "+": 6,
    "-": 6,
    "*": 7,
    "/": 7,
}
OPS = {
    "+": 0x10,
    "-": 0x11,
    "*": 0x12,
    "/": 0x13,
    "AND": 0x20,
    "OR": 0x21,
    "XOR": 0x22,
    "=": 0x30,
    "<>": 0x31,
    "<": 0x32,
    ">": 0x33,
    "<=": 0x34,
    ">=": 0x35,
}
TOKEN_PATTERN = re.compile(
    r"[A-Za-z_][A-Za-z_0-9]*|[0-9]+|:=|<>|<=|>=|[;:()+*/=<>-]"
)


class CompileError(ValueError):
    def __init__(self, token, message):
        self.line, self.column = token.line, token.column
        super().__init__(f"{self.line}:{self.column}: {message}")


@dataclass(frozen=True)
class Token:
    kind: str
    text: str
    line: int
    column: int


def lex(source):
    tokens = []
    pos, line, column = 0, 1, 1
    if len(source) > 1024 * 1024:
        raise CompileError(Token("", "", 1, 1), "source exceeds 1 MiB")
    while pos < len(source):
        start = Token("", "", line, column)
        if source.startswith("(*", pos):
            end = source.find("*)", pos + 2)
            if end < 0:
                raise CompileError(start, "unterminated comment")
            fragment = source[pos : end + 2]
            if "(*" in fragment[2:]:
                raise CompileError(start, "nested comments are unsupported")
        elif source[pos] in " \t\r\n":
            fragment = source[pos]
        else:
            match = TOKEN_PATTERN.match(source, pos)
            if not match:
                raise CompileError(
                    start, f"unexpected character {source[pos]!r}"
                )
            fragment = match.group()
            text = fragment.upper()
            if text[0] in "ABCDEFGHIJKLMNOPQRSTUVWXYZ_":
                if len(text) > 31:
                    raise CompileError(
                        start, "identifier exceeds 31 characters"
                    )
                kind = text if text in KEYWORDS else "IDENT"
            elif text.isdecimal():
                kind = "NUMBER"
            else:
                kind = text
            tokens.append(Token(kind, text, line, column))
        lines = fragment.split("\n")
        if len(lines) > 1:
            line += len(lines) - 1
            column = len(lines[-1]) + 1
        else:
            column += len(fragment)
        pos += len(fragment)
    tokens.append(Token("EOF", "", line, column))
    return tokens


@dataclass(frozen=True)
class Expr:
    token: Token
    kind: str
    value: object
    children: tuple = ()


@dataclass(frozen=True)
class Assign:
    name: Token
    expression: Expr


@dataclass(frozen=True)
class Conditional:
    branches: tuple
    otherwise: tuple


@dataclass(frozen=True)
class Program:
    name: Token
    declarations: tuple
    statements: tuple


class Parser:
    def __init__(self, source):
        self.tokens = lex(source)
        self.index = 0

    @property
    def current(self):
        return self.tokens[self.index]

    def take(self, kind=None):
        token = self.current
        if kind is not None and token.kind != kind:
            raise CompileError(
                token, f"expected {kind}, found {token.text or 'end of file'}"
            )
        self.index += 1
        return token

    def accept(self, kind):
        if self.current.kind == kind:
            return self.take()
        return None

    def check_depth(self, depth):
        if depth > 64:
            raise CompileError(self.current, "nesting exceeds 64 levels")

    def parse(self):
        self.take("PROGRAM")
        name = self.take("IDENT")
        declarations = []
        while self.current.kind in ("VAR_INPUT", "VAR_OUTPUT", "VAR"):
            kind = {"VAR_INPUT": 1, "VAR_OUTPUT": 2, "VAR": 3}[self.take().kind]
            while self.current.kind != "END_VAR":
                token = self.take("IDENT")
                self.take(":")
                type_token = self.take()
                if type_token.kind not in ("BOOL", "DINT"):
                    raise CompileError(type_token, "expected BOOL or DINT")
                self.take(";")
                declarations.append(
                    (token, 1 if type_token.kind == "BOOL" else 2, kind)
                )
            self.take("END_VAR")
        body = self.statements(0)
        self.take("END_PROGRAM")
        self.take("EOF")
        return Program(name, tuple(declarations), body)

    def statements(self, depth):
        self.check_depth(depth)
        result = []
        while self.current.kind not in (
            "ELSIF",
            "ELSE",
            "END_IF",
            "END_PROGRAM",
            "EOF",
        ):
            if self.accept("IF"):
                branches = []
                while True:
                    condition = self.expression()
                    self.take("THEN")
                    branches.append((condition, self.statements(depth + 1)))
                    if not self.accept("ELSIF"):
                        break
                otherwise = (
                    self.statements(depth + 1) if self.accept("ELSE") else ()
                )
                self.take("END_IF")
                self.take(";")
                result.append(Conditional(tuple(branches), otherwise))
            else:
                name = self.take("IDENT")
                self.take(":=")
                expression = self.expression()
                self.take(";")
                result.append(Assign(name, expression))
        return tuple(result)

    def expression(self, minimum=1, depth=0):
        self.check_depth(depth)
        token = self.take()
        if token.kind in ("+", "-", "NOT"):
            # The sole literal exception permits the signed minimum directly.
            if (
                token.kind == "-"
                and self.current.kind == "NUMBER"
                and self.current.text.lstrip("0") == "2147483648"
            ):
                self.take()
                left = Expr(token, "DINT", -2147483648)
            else:
                left = Expr(
                    token, "unary", token.kind, (self.expression(8, depth + 1),)
                )
        elif token.kind == "(":
            left = self.expression(1, depth + 1)
            self.take(")")
        elif token.kind == "NUMBER":
            digits = token.text.lstrip("0") or "0"
            if len(digits) > 10 or int(digits) > 2147483647:
                raise CompileError(token, "DINT literal out of range")
            left = Expr(token, "DINT", int(digits))
        elif token.kind in ("TRUE", "FALSE"):
            left = Expr(token, "BOOL", int(token.kind == "TRUE"))
        elif token.kind == "IDENT":
            left = Expr(token, "name", token.text)
        else:
            raise CompileError(token, "expected expression")
        while PRECEDENCE.get(self.current.kind, 0) >= minimum:
            operator = self.take()
            right = self.expression(PRECEDENCE[operator.kind] + 1, depth + 1)
            left = Expr(operator, "binary", operator.kind, (left, right))
        return left


class Compiler:
    def __init__(self, profile):
        self.profile = profile
        self.tags, self.symbols = [], {}
        self.code = bytearray()
        self.depth = self.maximum = 0

    def emit(self, op, operand=b"", delta=0, token=None):
        self.code.append(op)
        self.code.extend(operand)
        self.depth += delta
        self.maximum = max(self.maximum, self.depth)
        if len(self.code) > 2048 or self.maximum > 64:
            raise CompileError(
                token or self.location, "bytecode or stack capacity exceeded"
            )

    def expression(self, root):
        # Iterative postorder handles long left-associative expressions safely.
        pending, types = [(root, False)], []
        while pending:
            node, visited = pending.pop()
            if not visited and node.children:
                pending.append((node, True))
                pending.extend(
                    (child, False) for child in reversed(node.children)
                )
                continue
            if node.kind in ("BOOL", "DINT"):
                type_ = 1 if node.kind == "BOOL" else 2
                self.emit(
                    1,
                    bytes([type_])
                    + (node.value & 0xFFFFFFFF).to_bytes(4, "little"),
                    1,
                    node.token,
                )
            elif node.kind == "name":
                if node.value not in self.symbols:
                    raise CompileError(node.token, f"unknown tag {node.value}")
                index = self.symbols[node.value]
                type_ = self.tags[index].type
                self.emit(2, bytes([index]), 1, node.token)
            elif node.kind == "unary":
                type_ = types.pop()
                expected = 1 if node.value == "NOT" else 2
                if type_ != expected:
                    raise CompileError(
                        node.token, f"{node.value} operand type mismatch"
                    )
                if node.value != "+":
                    self.emit(
                        0x23 if node.value == "NOT" else 0x14, token=node.token
                    )
            else:
                right, left = types.pop(), types.pop()
                expected = 1 if node.value in ("AND", "OR", "XOR") else 2
                if left != right or (
                    node.value not in ("=", "<>") and left != expected
                ):
                    raise CompileError(
                        node.token, f"{node.value} operand type mismatch"
                    )
                type_ = (
                    1
                    if node.value in ("=", "<>", "<", ">", "<=", ">=")
                    else left
                )
                self.emit(OPS[node.value], delta=-1, token=node.token)
            types.append(type_)
        return types.pop()

    def jump(self, op):
        offset = len(self.code) + 1
        self.emit(op, b"\0\0", -1 if op == 0x41 else 0)
        return offset

    def patch(self, offset):
        self.code[offset : offset + 2] = len(self.code).to_bytes(2, "little")

    def statements(self, statements):
        for statement in statements:
            if isinstance(statement, Assign):
                self.location = statement.name
                index = self.symbols.get(statement.name.text)
                if index is None:
                    raise CompileError(
                        statement.name, f"unknown tag {statement.name.text}"
                    )
                tag = self.tags[index]
                if tag.kind == 1:
                    raise CompileError(statement.name, "cannot assign to input")
                if self.expression(statement.expression) != tag.type:
                    raise CompileError(
                        statement.name, "assignment type mismatch"
                    )
                self.emit(3, bytes([index]), -1)
            else:
                ends = []
                for condition, body in statement.branches:
                    self.location = condition.token
                    if self.expression(condition) != 1:
                        raise CompileError(
                            condition.token, "IF condition must be BOOL"
                        )
                    skip = self.jump(0x41)
                    self.statements(body)
                    ends.append(self.jump(0x40))
                    self.patch(skip)
                self.statements(statement.otherwise)
                for end in ends:
                    self.patch(end)

    def compile(self, program):
        self.location = program.name
        for token, type_, kind in program.declarations:
            if token.text in self.symbols:
                raise CompileError(token, f"duplicate tag {token.text}")
            if len(self.tags) == 64:
                raise CompileError(token, "tag capacity exceeded")
            tag = Tag(token.text, type_, kind)
            if kind != 3 and self.profile.get((kind, token.text)) != type_:
                raise CompileError(
                    token, f"unsupported I/O binding {token.text}"
                )
            self.symbols[token.text] = len(self.tags)
            self.tags.append(tag)
        self.statements(program.statements)
        self.emit(0xFF)
        return build_image(self.tags, self.code, self.maximum, self.profile)


def compile_source(source, profile):
    return Compiler(profile).compile(Parser(source).parse())
