"""Program gates: checks on the generated ladder before anything is exported.

Data gates (bad addresses, tag collisions, missing points) live in plc_job.py.
These check the program itself. An ERROR stops the build.
"""
import re
from collections import Counter

from plc_job import Check, ERROR, WARN, OK
from plc_rules import MAP_IN, MAP_OUT
from rll import SUPPORTED, WRITES, READS, RungSyntaxError, base_tag, instructions, is_literal, parse_rung

LOGIX_NAME = re.compile(r"^[A-Za-z_](?:[A-Za-z0-9]|_(?!_))*$")


def verify_program(program, job):
    checks = []

    def add(code, level, msg):
        checks.append(Check(code, level, msg))

    parsed = {}
    for r in program.routines:
        for n, g in enumerate(r.rungs):
            try:
                parsed[(r.name, n)] = parse_rung(g.text)
            except RungSyntaxError as e:
                add("P1", ERROR, f"{r.name} rung {n}: {e}")
    if any(c.level == ERROR for c in checks):
        return checks
    add("P1", OK, f"{len(parsed)} rungs parse as Logix neutral text")

    routines = {r.name for r in program.routines}
    writes, reads, coils, timers, calls = Counter(), Counter(), Counter(), Counter(), Counter()
    for (rname, n), rung in parsed.items():
        for i in instructions(rung):
            where = f"{rname} rung {n}"
            if i.op not in SUPPORTED:
                add("P2", ERROR, f"{where}: instruction {i.op} is not supported by the gates/simulator")
                continue
            if i.op == "JSR":
                calls[i.args[0]] += 1
                if i.args[0] not in routines:
                    add("P6", ERROR, f"{where}: JSR to missing routine {i.args[0]}")
                continue
            for arg in i.args:
                if is_literal(arg):
                    continue
                tag = base_tag(arg)
                if tag.startswith("Local:"):
                    if rname not in (MAP_IN, MAP_OUT):
                        add("P7", ERROR, f"{where}: module path {arg} used outside the I/O mapping routines")
                    continue
                if tag not in program.tags:
                    add("P2", ERROR, f"{where}: tag {arg} is not defined")
            w = WRITES.get(i.op)
            if w is not None and rname not in (MAP_OUT,):
                writes[base_tag(i.args[w])] += 1
            if rname != MAP_IN:
                for k in READS[i.op]:
                    if not is_literal(i.args[k]):
                        reads[base_tag(i.args[k])] += 1
            if i.op == "OTE":
                coils[i.args[0]] += 1
            if i.op in ("TON", "TOF"):
                timers[i.args[0]] += 1
                if int(float(i.args[1])) <= 0:
                    add("P8", ERROR, f"{where}: timer {i.args[0]} has preset {i.args[1]}")
    if not any(c.code == "P2" for c in checks):
        add("P2", OK, "every tag the rungs use is defined")

    doubles = [t for t, k in coils.items() if k > 1]
    for t in doubles:
        add("P3", ERROR, f"double coil: {t} is written by {coils[t]} OTE instructions")
    if not doubles:
        add("P3", OK, f"no double coils ({len(coils)} OTE targets, each written once)")

    for t, k in timers.items():
        if k > 1:
            add("P8", ERROR, f"timer {t} is driven by {k} timer instructions")
    if not any(c.code == "P8" for c in checks):
        add("P8", OK, f"all {len(timers)} timers have a preset above zero and one timer instruction each")

    undriven = [p for p in job.points("DO") + job.points("AO") if writes[p.tag] == 0]
    for p in undriven:
        add("P4", ERROR, f"output {p.address} {p.tag} ({p.description}) is never driven by the logic")
    if not undriven:
        add("P4", OK, f"all {len(job.points('DO')) + len(job.points('AO'))} live outputs are driven by the logic")

    unread = [p for p in job.points("DI") + job.points("AI") if reads[p.tag] == 0]
    for p in unread:
        add("P5", WARN, f"input {p.address} {p.tag} ({p.description}) is wired but never used by the logic")
    if not unread:
        add("P5", OK, f"all {len(job.points('DI')) + len(job.points('AI'))} live inputs are used by the logic")

    main_calls = [r for r in routines if r != program.main]
    for r in main_calls:
        if calls[r] != 1:
            add("P6", ERROR, f"routine {r} is called {calls[r]} times (expected once)")
    if all(calls[r] == 1 for r in main_calls):
        add("P6", OK, f"all {len(main_calls)} routines are called exactly once from {program.main}")

    mapped_in = {i.args[-1] for rung in (parsed[(MAP_IN, n)] for n in range(len(program.routine(MAP_IN).rungs)))
                 for i in instructions(rung)}
    mapped_out = {i.args[0] for rung in (parsed[(MAP_OUT, n)] for n in range(len(program.routine(MAP_OUT).rungs)))
                  for i in instructions(rung)}
    missing = [p for p in job.points("DI") + job.points("AI") if p.tag not in mapped_in]
    missing += [p for p in job.points("DO") + job.points("AO") if p.tag not in mapped_out]
    for p in missing:
        add("P7", ERROR, f"{p.address} {p.tag} has no module mapping rung")
    paths = Counter(p.path for p in job.points())
    for path, k in paths.items():
        if k > 1:
            add("P7", ERROR, f"module channel {path} is mapped {k} times")
    if not missing:
        add("P7", OK, f"all {len(job.points())} live points map to their module channel "
                      f"(Local:{min(p.slot for p in job.io)}..{max(p.slot for p in job.io)})")

    bad = [n for n in list(program.tags) + list(routines) if not LOGIX_NAME.match(n) or len(n) > 40]
    for n in bad:
        add("P9", ERROR, f"'{n}' is not a legal Logix name (letters, digits, single _, max 40)")
    if not bad:
        add("P9", OK, f"all {len(program.tags)} tag and {len(routines)} routine names are legal Logix names")
    return checks
