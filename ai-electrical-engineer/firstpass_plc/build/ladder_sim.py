"""A small Logix ladder simulator: run the generated program with no PLC.

It executes the same rung text that goes into the L5X, scan after scan, with
Logix semantics for the instructions the rules use. A plant model (a Python
function called every scan) stands in for the machine: it reads outputs and
writes inputs, so a whole sequence of operation can be tested in seconds.

Not a Studio 5000 emulator: no tasks, no I/O update timing, no faults. It
answers one question: does this ladder logic do what the sequence says?
"""
from rll import Branch, instructions, is_literal, parse_rung

DEFAULTS = {"BOOL": False, "DINT": 0, "REAL": 0.0}


class Timer:
    __slots__ = ("PRE", "ACC", "EN", "TT", "DN")

    def __init__(self, preset):
        self.PRE, self.ACC, self.EN, self.TT, self.DN = preset, 0, False, False, False


class Sim:
    def __init__(self, program, skip_routines=(), plant=None):
        self.program = program
        self.skip = set(skip_routines)
        self.plant = plant
        self.time_ms = 0.0
        self.dt_ms = 10.0
        self.watchers = []
        self.tags = {}
        for t in program.tags.values():
            if t.datatype == "TIMER":
                self.tags[t.name] = Timer(t.preset)
            else:
                self.tags[t.name] = type(DEFAULTS[t.datatype])(t.value)
        self.types = {t.name: t.datatype for t in program.tags.values()}
        self.routines = {r.name: [parse_rung(g.text) for g in r.rungs] for r in program.routines}

    # --- public ------------------------------------------------------------

    def __getitem__(self, name):
        return self._read(name)

    def __setitem__(self, name, value):
        self._write(name, value)

    def scan(self):
        if self.plant:
            self.plant(self, self.dt_ms / 1000.0)
        self._run(self.program.main)
        self.time_ms += self.dt_ms
        for w in self.watchers:
            w(self)

    def run(self, seconds, dt=0.01):
        self.dt_ms = dt * 1000.0
        for _ in range(max(1, round(seconds / dt))):
            self.scan()

    def run_until(self, condition, timeout, dt=0.01):
        """Scan until condition(sim) is true; return seconds taken or raise."""
        self.dt_ms = dt * 1000.0
        start = self.time_ms
        while not condition(self):
            if self.time_ms - start > timeout * 1000.0:
                raise TimeoutError(f"condition not met within {timeout} s")
            self.scan()
        return (self.time_ms - start) / 1000.0

    # --- execution ---------------------------------------------------------

    def _run(self, routine):
        if routine in self.skip:
            return
        for rung in self.routines[routine]:
            self._series(rung, True)

    def _series(self, elems, rin):
        for e in elems:
            rin = self._branch(e, rin) if isinstance(e, Branch) else self._instr(e, rin)
        return rin

    def _branch(self, b, rin):
        out = False
        for leg in b.legs:
            leg_out = self._series(leg, rin)
            out = out or leg_out
        return out

    def _instr(self, i, rin):
        op, a = i.op, i.args
        if op == "XIC":
            return rin and bool(self._read(a[0]))
        if op == "XIO":
            return rin and not self._read(a[0])
        if op in ("GRT", "GEQ", "LES", "LEQ", "EQU", "NEQ"):
            x, y = self._read(a[0]), self._read(a[1])
            return rin and {"GRT": x > y, "GEQ": x >= y, "LES": x < y,
                            "LEQ": x <= y, "EQU": x == y, "NEQ": x != y}[op]
        if op == "LIM":
            lo, x, hi = (self._read(v) for v in a)
            return rin and lo <= x <= hi
        if op == "OTE":
            self._write(a[0], rin)
            return rin
        if op == "OTL":
            if rin:
                self._write(a[0], True)
            return rin
        if op == "OTU":
            if rin:
                self._write(a[0], False)
            return rin
        if op == "ONS":
            out = rin and not self._read(a[0])
            self._write(a[0], rin)
            return out
        if op in ("TON", "TOF"):
            t = self.tags[a[0]]
            t.PRE = int(float(a[1]))
            (self._ton if op == "TON" else self._tof)(t, rin)
            return rin
        if op == "MOV":
            if rin:
                self._write(a[1], self._read(a[0]))
            return rin
        if op in ("ADD", "SUB", "MUL", "DIV"):
            if rin:
                x, y = self._read(a[0]), self._read(a[1])
                self._write(a[2], {"ADD": x + y, "SUB": x - y, "MUL": x * y,
                                   "DIV": x / y if y else 0}[op])
            return rin
        if op == "JSR":
            if rin:
                self._run(a[0])
            return rin
        if op == "NOP":
            return rin
        raise NotImplementedError(f"simulator does not support {op}")

    def _ton(self, t, rin):
        if not rin:
            t.EN = t.TT = t.DN = False
            t.ACC = 0
            return
        t.EN = True
        if t.ACC < t.PRE:
            t.ACC = min(t.PRE, t.ACC + int(round(self.dt_ms)))
        t.DN = t.ACC >= t.PRE
        t.TT = not t.DN

    def _tof(self, t, rin):
        if rin:
            t.EN = t.DN = True
            t.TT = False
            t.ACC = 0
            return
        t.EN = False
        if t.DN:
            t.ACC = min(t.PRE, t.ACC + int(round(self.dt_ms)))
            if t.ACC >= t.PRE:
                t.DN = t.TT = False
            else:
                t.TT = True

    # --- tags --------------------------------------------------------------

    def _read(self, arg):
        if is_literal(arg):
            return float(arg) if any(c in arg for c in ".eE") else int(arg)
        name, _, member = arg.partition(".")
        if name not in self.tags:
            raise KeyError(f"unknown tag {arg}")
        v = self.tags[name]
        return getattr(v, member) if member else v

    def _write(self, arg, value):
        name, _, member = arg.partition(".")
        if name not in self.tags:
            raise KeyError(f"unknown tag {arg}")
        if member:
            setattr(self.tags[name], member, value)
            return
        dt = self.types[name]
        if dt == "BOOL":
            value = bool(value)
        elif dt == "DINT":
            value = int(round(value))
        elif dt == "REAL":
            value = float(value)
        self.tags[name] = value


def used_instructions(program):
    return sorted({i.op for r in program.routines for g in r.rungs
                   for i in instructions(parse_rung(g.text))})
