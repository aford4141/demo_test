"""Load a FirstPass job (data/) and turn its I/O list into PLC tags.

Nothing here decides machine behaviour; that is plc_rules.py. This module
answers "what hardware and I/O does the job have, and is that data sound
enough to write a program against?"
"""
from dataclasses import dataclass, field
from pathlib import Path
import csv
import re

import yaml

ROOT = Path(__file__).resolve().parent.parent

# What the generator knows about each I/O module. The path is the Logix module
# tag for one channel; slot is the local-bus slot (controller is slot 0).
MODULES = {
    "5069-IB16": ("DI", 16, "Local:{slot}:I.Pt{ch:02d}.Data", "BOOL"),
    "5069-OB16": ("DO", 16, "Local:{slot}:O.Pt{ch:02d}.Data", "BOOL"),
    "5069-IF8":  ("AI", 8,  "Local:{slot}:I.Ch{ch:02d}.Data", "REAL"),
    "5069-OF4":  ("AO", 4,  "Local:{slot}:O.Ch{ch:02d}.Data", "REAL"),
}
ADDRESS = re.compile(r"^(I|O|AI|AO):(\d+)/(\d+)$")
KIND_OF_PREFIX = {"I": "DI", "O": "DO", "AI": "AI", "AO": "AO"}
SUFFIX_OF_KIND = {"DI": "_I", "DO": "_O", "AI": "_AI", "AO": "_AO"}

ERROR, WARN, FINDING, OK = "ERROR", "WARN", "FINDING", "OK"


@dataclass
class Check:
    code: str
    level: str
    message: str


@dataclass
class IoPoint:
    address: str
    kind: str
    module: str
    module_index: int
    channel: int
    device_tag: str
    description: str
    device: str
    wire: str
    terminal: str
    panel: str
    sheet: str
    spare: bool
    tag: str = ""
    slot: int = 0
    path: str = ""

    @property
    def datatype(self):
        return "BOOL" if self.kind in ("DI", "DO") else "REAL"

    def label(self):
        return (f"{self.address} {self.device_tag} {self.description} - "
                f"wire {self.wire}, {self.terminal}, +{self.panel}, sheet {self.sheet}")


@dataclass
class Job:
    root: Path
    project: dict
    plc: dict
    io: list
    drives: list
    lamps: list
    safety: list
    checks: list = field(default_factory=list)

    def check(self, code, level, message):
        self.checks.append(Check(code, level, message))

    def points(self, kind=None, spare=False):
        return [p for p in self.io
                if (kind is None or p.kind == kind) and p.spare == spare]

    def find(self, kind, pattern):
        """The one live point of `kind` whose description matches `pattern`,
        or None. More than one match is a data error."""
        rx = re.compile(pattern, re.I)
        hits = [p for p in self.points(kind) if rx.search(p.description)]
        if len(hits) > 1:
            raise JobDataError(f"'{pattern}' matches {len(hits)} {kind} points: "
                               + ", ".join(p.address for p in hits))
        return hits[0] if hits else None

    def need(self, kind, pattern, why):
        p = self.find(kind, pattern)
        if p is None:
            raise JobDataError(f"no {kind} point matching '{pattern}' in io.csv ({why})")
        return p

    def timer(self, name):
        return int(self.plc["timers_ms"][name])

    def analog(self, name):
        return float(self.plc["analog"][name])


class JobDataError(ValueError):
    pass


def logix_name(raw):
    """Device tag -> legal Logix tag name. Letters, digits and single
    underscores; must not start with a digit."""
    name = re.sub(r"[^A-Za-z0-9_]", "_", raw.strip())
    name = re.sub(r"_+", "_", name).strip("_")
    if not name or name[0].isdigit():
        name = "T_" + name
    return name


def _rows(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return [{k.strip(): (v or "").strip() for k, v in r.items()}
                for r in csv.DictReader(f)]


def load_job(root=ROOT):
    root = Path(root)
    data = root / "data"
    job = Job(
        root=root,
        project=yaml.safe_load((data / "project.yaml").read_text()),
        plc=yaml.safe_load((data / "plc.yaml").read_text()),
        io=[], drives=_rows(data / "drives.csv"), lamps=_rows(data / "lamps.csv"),
        safety=_rows(data / "safety.csv"),
    )
    _load_io(job, _rows(data / "io.csv"))
    return job


def _load_io(job, rows):
    offset = int(job.plc["io"]["local_slot_offset"])
    seen = {}
    for r in rows:
        addr = r["point"]
        m = ADDRESS.match(addr)
        if not m:
            job.check("D1", ERROR, f"{addr}: not a valid I/O address")
            continue
        kind = KIND_OF_PREFIX[m.group(1)]
        index, ch = int(m.group(2)), int(m.group(3))
        spare = r["tag"].upper().startswith("SPARE")
        p = IoPoint(addr, kind, r["module"], index, ch, r["tag"], r["description"],
                    r["device"], r["wire"], r["terminal"], r["panel"], r["sheet"], spare)
        if addr in seen:
            job.check("D4", ERROR, f"{addr} is listed twice ({seen[addr]} and {p.device_tag})")
            continue
        seen[addr] = p.device_tag

        mod = MODULES.get(p.module)
        if mod is None:
            job.check("D2", ERROR, f"{addr}: module {p.module} is not in the module catalog")
            continue
        mkind, channels, path, _ = mod
        if r["type"] != kind or mkind != kind:
            job.check("D7", ERROR, f"{addr}: type {r['type']} on {p.module} does not match the address")
            continue
        p.slot = index + offset
        if ch >= channels:
            level = WARN if spare else ERROR
            job.check("D3", level,
                      f"{addr} ({p.device_tag}) is channel {ch} but {p.module} has "
                      f"{channels} channels (0-{channels - 1}). The point does not exist on "
                      f"the hardware; sheet {p.sheet} and terminal {p.terminal} show it anyway.")
            p.spare = True  # never map a channel that does not exist
            p.tag = logix_name(p.device_tag)
            job.io.append(p)
            continue
        p.path = path.format(slot=p.slot, ch=ch)
        job.io.append(p)

    _name_tags(job)


def _name_tags(job):
    by_name = {}
    for p in job.points():
        by_name.setdefault(logix_name(p.device_tag), []).append(p)
    for name, pts in sorted(by_name.items()):
        if len(pts) == 1:
            pts[0].tag = name
            if name != pts[0].device_tag:
                job.check("D5", OK, f"{pts[0].device_tag} -> {name} (Logix tag names allow letters, digits, _)")
            continue
        kinds = [p.kind for p in pts]
        if len(set(kinds)) != len(kinds):
            job.check("D6", ERROR, f"tag {name} is used by {len(pts)} points of the same type: "
                      + ", ".join(p.address for p in pts))
        for p in pts:
            p.tag = name + SUFFIX_OF_KIND[p.kind]
        job.check("D6", WARN,
                  f"{name} is both " + " and ".join(f"{p.kind} {p.address} '{p.description}'" for p in pts)
                  + ". PLC tags made unique as " + ", ".join(p.tag for p in pts) + ".")
    for p in job.points(spare=True):
        p.tag = p.tag or logix_name(p.device_tag)


def audit(job):
    """Cross-checks between the data files and against what the O&M manual
    promises. These do not stop the build; they are questions for the engineer."""
    # Lamps: every module needs an enable output and a lamp-is-on input,
    # every row a system-health input.
    for lamp in job.lamps:
        key = f"{lamp['row']} Row {lamp['role']} Lamp"
        for kind, what in (("DO", "Enable"), ("DI", "Is On")):
            if job.find(kind, f"^{key} {what}$") is None:
                job.check("D8", ERROR, f"lamp {lamp['tag']} has no {kind} '{key} {what}' in io.csv")
    for row in sorted({l["row"] for l in job.lamps}):
        if job.find("DI", f"^{row} Row System Health$") is None:
            job.check("D8", ERROR, f"{row} row has no 'System Health' input in io.csv")

    # Lamp enable and lamp-is-on on the same relay tag reads the relay back.
    outs = {p.device_tag: p.address for p in job.points("DO")}
    shared = [f"{p.device_tag} (out {outs[p.device_tag]}, in {p.address})" for p in job.points("DI")
              if p.device_tag in outs and "Lamp Is On" in p.description]
    if shared:
        job.check("F1", FINDING,
                  f"Each of these relays is both a lamp-enable coil and a 'lamp is on' contact: "
                  f"{'; '.join(shared)}. If each is one relay, the input only echoes the PLC's own "
                  f"output and a lamp that fails to strike cannot be detected. Give the lamp-status "
                  f"relays their own tags, driven by each ballast's lamp-on output.")

    # Drives: run enable must exist; feedback promised in drives.csv must be wired.
    reported = set()
    for d in job.drives:
        short = d["tag"].split("-", 1)[1]
        if not any(p.tag == f"VFD_{short}" for p in job.points("DO")):
            job.check("D9", ERROR, f"drive {d['tag']} has no run-enable output VFD-{short} in io.csv")
        fb = d["feedback"].lower()
        word = d["motor"].split()[0]
        if fb.startswith("encoder"):
            ai = job.find("AI", f"{word}.*encoder")
            if ai is not None:
                job.check("F2", FINDING,
                          f"{d['tag']} feedback is '{d['feedback']}' (a pulse device) but io.csv wires it "
                          f"as 4-20 mA analog {ai.address} {ai.device_tag}. The BOM carries a "
                          f"5069-HSC2XOB4 high-speed counter with no points assigned. Either land the "
                          f"encoder on the HSC or specify a pulse-to-4-20 mA converter.")
        if "home" in fb and job.find("DI", f"{word}.*home") is None:
            job.check("F3", FINDING,
                      f"{d['tag']} feedback is '{d['feedback']}' but no home input is in io.csv. "
                      f"The PLC cannot home or position the {d['motor'].lower()}. "
                      f"Spare inputs I:0/06 and I:0/07 are free.")
        if "limit" in fb and word not in reported and job.find("DO", f"{word}.*(reverse|direction|down)") is None:
            reported.add(word)
            axis = [x["tag"] for x in job.drives if x["motor"].split()[0] == word]
            job.check("F4", FINDING,
                      f"{' / '.join(axis)} ({d['motor'].rsplit(' ', 1)[0].lower()}) have only run-enable "
                      f"outputs. A lift must go up and "
                      f"down, so direction has to come from somewhere: a second drive input "
                      f"(needs 2 more outputs) or EtherNet/IP control of the PowerFlex 525 (sheets "
                      f"024-026 say 'Speed ref EtherNet/IP'). The program computes FocalMoveUp / "
                      f"FocalMoveDown ready for either choice.")
    if job.find("AO", "conveyor speed") is not None:
        job.check("F5", FINDING,
                  "Speed references are wired as 0-10 V analog outputs in io.csv, but sheets 024-026 "
                  "say 'Speed ref EtherNet/IP'. Pick one; the program follows io.csv (analog).")

    # Exhaust: O&M 4.2 says lamps will not strike without it.
    if any("exhaust" in l["cooling"].lower() for l in job.lamps) and job.find("DI", "exhaust") is None:
        job.check("F6", FINDING,
                  "O&M 4.2: 'Confirm exhaust is running. Lamps will not strike without it.' No exhaust "
                  "or airflow input exists in io.csv, so the PLC cannot enforce it. Add an airflow "
                  "switch on spare I:0/06 and describe it with the word 'Exhaust'; the lamp strike "
                  "permissive picks it up automatically on the next build.")

    # Safety: the PLC must see the safety system's state.
    tags = {p.device_tag for p in job.points("DI")}
    for s in job.safety:
        if s["type"] == "controller" and s["tag"] not in tags:
            job.check("D10", ERROR, f"safety controller {s['tag']} status is not wired to the PLC")
        if s["type"] == "relay" and s["tag"] not in tags:
            job.check("F7", FINDING,
                      f"{s['tag']} ({s['description']}) is not monitored by the PLC. Only "
                      + ", ".join(x["tag"] for x in job.safety if x["type"] == "relay" and x["tag"] in tags)
                      + " is. The safety controller's own feedback loop may cover it; confirm on sheet 050.")
    job.check("F8", FINDING,
              "O&M 7.3 says each E-stop and door 'HMI annunciates', but the PLC only sees the safety "
              "controller's healthy output. It can report 'safety stop', not which device. Naming the "
              "device needs the GC-S1R's per-input status (network or extra inputs).")
    return job
