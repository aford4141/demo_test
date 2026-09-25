"""Parse Logix ladder rungs written in Rockwell "neutral text".

    XIC(Start)[XIO(Stop) ,XIC(Seal)]OTE(Motor);

This is the same text Studio 5000 shows for a rung and stores inside an L5X
file, so one parser serves the simulator, the verification gates and the
exporter. A rung is a series of elements. An element is an instruction or a
branch; a branch is a list of legs and each leg is itself a series.
"""
from dataclasses import dataclass
import re

IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
NUMBER = re.compile(r"^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$")

# Which operand an instruction writes, and which it only reads. Used by the
# gates (double coils, undriven outputs, unread inputs) and the simulator.
CONDITIONS = {"XIC", "XIO", "GRT", "GEQ", "LES", "LEQ", "EQU", "NEQ", "LIM"}
WRITES = {"OTE": 0, "OTL": 0, "OTU": 0, "ONS": 0, "TON": 0, "TOF": 0,
          "MOV": 1, "ADD": 2, "SUB": 2, "MUL": 2, "DIV": 2}
READS = {"XIC": (0,), "XIO": (0,), "GRT": (0, 1), "GEQ": (0, 1), "LES": (0, 1),
         "LEQ": (0, 1), "EQU": (0, 1), "NEQ": (0, 1), "LIM": (0, 1, 2),
         "MOV": (0,), "ADD": (0, 1), "SUB": (0, 1), "MUL": (0, 1), "DIV": (0, 1),
         "ONS": (0,), "TON": (0,), "TOF": (0,), "OTE": (), "OTL": (), "OTU": (),
         "JSR": (), "NOP": ()}
SUPPORTED = set(READS)


class RungSyntaxError(ValueError):
    pass


@dataclass
class Instr:
    op: str
    args: list


@dataclass
class Branch:
    legs: list


def parse_rung(text):
    """Return the rung as a list of Instr / Branch elements."""
    s = text.strip()
    if not s.endswith(";"):
        raise RungSyntaxError(f"rung must end with ';': {text!r}")
    p = _Parser(s[:-1])
    series = p.series(closers="")
    p.skip_ws()
    if p.i != len(p.s):
        raise RungSyntaxError(f"unexpected {p.s[p.i]!r} at {p.i} in {text!r}")
    return series


class _Parser:
    def __init__(self, s):
        self.s, self.i = s, 0

    def skip_ws(self):
        while self.i < len(self.s) and self.s[self.i].isspace():
            self.i += 1

    def series(self, closers):
        out = []
        while True:
            self.skip_ws()
            if self.i >= len(self.s) or self.s[self.i] in closers:
                return out
            if self.s[self.i] == "[":
                out.append(self.branch())
            else:
                out.append(self.instr())

    def branch(self):
        self.i += 1  # '['
        legs = [self.series(closers=",]")]
        while True:
            self.skip_ws()
            if self.i >= len(self.s):
                raise RungSyntaxError(f"unclosed branch in {self.s!r}")
            c = self.s[self.i]
            self.i += 1
            if c == "]":
                return Branch(legs)
            legs.append(self.series(closers=",]"))

    def instr(self):
        m = IDENT.match(self.s, self.i)
        if not m:
            raise RungSyntaxError(f"expected instruction at {self.i} in {self.s!r}")
        op = m.group(0)
        self.i = m.end()
        if self.i >= len(self.s) or self.s[self.i] != "(":
            raise RungSyntaxError(f"{op} needs '(' in {self.s!r}")
        self.i += 1
        args, depth, start = [], 0, self.i
        while self.i < len(self.s):
            c = self.s[self.i]
            if c in "([":
                depth += 1
            elif c == "]":
                depth -= 1
            elif c == ")":
                if depth == 0:
                    tail = self.s[start:self.i].strip()
                    if tail or args:
                        args.append(tail)
                    self.i += 1
                    return Instr(op, args)
                depth -= 1
            elif c == "," and depth == 0:
                args.append(self.s[start:self.i].strip())
                start = self.i + 1
            self.i += 1
        raise RungSyntaxError(f"unclosed '(' after {op} in {self.s!r}")


def instructions(series):
    """Every Instr in a parsed rung, depth first, in execution order."""
    for e in series:
        if isinstance(e, Branch):
            for leg in e.legs:
                yield from instructions(leg)
        else:
            yield e


def is_literal(arg):
    return bool(NUMBER.match(arg))


def base_tag(arg):
    """'Timer.DN' -> 'Timer'. Module paths such as 'Local:1:I.Pt00.Data' are
    returned whole; they belong to the I/O tree, not the program."""
    if arg.startswith("Local:"):
        return arg
    return arg.split(".", 1)[0].split("[", 1)[0]
