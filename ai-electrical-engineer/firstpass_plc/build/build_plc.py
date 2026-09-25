#!/usr/bin/env python3
"""Build the PLC program for the job in data/.

    python3 build/build_plc.py            gates, generate, test, report
    python3 build/build_plc.py --mutate   also prove the tests catch deliberate bugs (~3 min)

Same rule as build_all.py: verify first. If a gate fails or a test fails,
nothing is exported - a program that cannot pass its own checks does not get
an L5X.
"""
from datetime import date
import hashlib
import io
import sys
import unittest

from plc_job import ROOT, ERROR, WARN, FINDING, OK, JobDataError, audit, load_job
from plc_rules import build_program
import plc_rules
import gen_plc
import verify_plc

OUT = ROOT / "plc"


def fingerprint():
    h = hashlib.sha256()
    for f in sorted((ROOT / "data").glob("*")) + sorted((ROOT / "build").glob("*.py")):
        h.update(f.name.encode())
        h.update(f.read_bytes())
    return h.hexdigest()[:8]


def run_tests():
    import test_plc_fmm3013 as T
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(T.FMM3013)
    cases = [(t.id(), t._testMethodName, (t._testMethodDoc or "").strip().splitlines()[0]) for t in suite]
    res = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
    failed = {t.id(): tb for t, tb in res.failures + res.errors}
    return [(name, doc, tid not in failed, failed.get(tid, "")) for tid, name, doc in cases]


def main(argv):
    print("Loading job data")
    try:
        job = audit(load_job())
    except JobDataError as e:
        print(f"  ERROR {e}")
        return 1
    errors = [c for c in job.checks if c.level == ERROR]
    _print_checks(job.checks)
    if errors:
        print(f"\n{len(errors)} data error(s). Nothing built.")
        return 1

    print("\nBuilding program")
    try:
        program = build_program(job)
    except JobDataError as e:
        print(f"  ERROR {e}\n\nNothing built.")
        return 1
    rungs = sum(len(r.rungs) for r in program.routines)
    print(f"  {len(program.routines)} routines, {rungs} rungs, {len(program.tags)} tags, {len(program.alarms)} alarms")

    print("\nVerifying program")
    pchecks = verify_plc.verify_program(program, job)
    _print_checks(pchecks)
    if any(c.level == ERROR for c in pchecks):
        print("\nProgram gate failed. Nothing built.")
        return 1

    print("\nRunning sequence tests")
    tests = run_tests()
    passed = sum(1 for t in tests if t[2])
    print(f"  {passed}/{len(tests)} passed")
    for name, _, ok, tb in tests:
        if not ok:
            print(f"  FAIL {name}\n{tb}")
    if passed != len(tests):
        print("\nTests failed. Nothing built.")
        return 1

    mutants = None
    if "--mutate" in argv:
        print("\nTesting the tests (deliberate bugs)")
        import mutate_plc
        mutants = mutate_plc.run()
        for name, bad in mutants:
            print(f"  {'caught' if bad else 'MISSED'}  {name}")
        if not all(bad for _, bad in mutants):
            print("\nA deliberate bug went undetected: a test is missing. Nothing built.")
            return 1

    files = gen_plc.write_all(program, job, OUT)
    report = OUT / f"{job.project['project']}_PLC_Report.md"
    report.write_text(_report(job, program, pchecks, tests, mutants, files, fingerprint()), encoding="utf-8")
    print("\nWritten")
    for f in list(files.values()) + [report]:
        print(f"  {f.relative_to(ROOT)}")
    findings = [c for c in job.checks if c.level == FINDING]
    print(f"\nProgram built. {len(findings)} question(s) for the engineer in the report.")
    return 0


def _bullets(text):
    """Docstring bullets ('* ...' with wrapped continuation lines) -> Markdown list."""
    items = []
    for line in text.strip().splitlines():
        line = line.strip()
        if line.startswith("* "):
            items.append(line[2:])
        elif line and items:
            items[-1] += " " + line
    return "\n".join(f"- {i}" for i in items)


def _print_checks(checks):
    for c in checks:
        if c.level != OK:
            print(f"  {c.level:7s} {c.code:4s} {c.message}")
    n_ok = sum(1 for c in checks if c.level == OK)
    if n_ok:
        print(f"  {n_ok} check(s) OK")


def _report(job, program, pchecks, tests, mutants, files, fp):
    p = job.project
    findings = sorted((c for c in job.checks if c.level == FINDING), key=lambda c: int(c.code[1:]))
    warns = [c for c in job.checks + pchecks if c.level == WARN]
    passed = sum(1 for t in tests if t[2])
    rungs = sum(len(r.rungs) for r in program.routines)
    modules = sorted({(pt.slot, pt.module) for pt in job.io})
    assumed = [ln.split("#", 1) for ln in (ROOT / "data" / "plc.yaml").read_text().splitlines()
               if "ASSUMED" in ln and ":" in ln.split("#", 1)[0]]
    seq = _bullets(plc_rules.__doc__.split("Sequence of operation implemented", 1)[1].split(":", 1)[1])

    out = [
        f"# {p['project']} {p['title']} - PLC Program Build Report",
        "",
        f"Build `{fp}` · {date.today():%m-%d-%Y} · generated from `data/` by `build/build_plc.py` · "
        f"drawing {p['drawing']} Rev {p['revision']} · **NOT FOR COMMISSIONING WITHOUT REVIEW**",
        "",
        "## Result",
        "",
        f"- **Program:** `{program.name}`: {len(program.routines)} routines, {rungs} rungs, "
        f"{len(program.tags)} tags, {len(program.alarms)} alarms.",
        f"- **Gates:** {sum(1 for c in job.checks + pchecks if c.level == OK)} passed, {len(warns)} warnings, 0 errors.",
        f"- **Sequence tests:** {passed} of {len(tests)} passed in the ladder simulator.",
        ("- **Test strength:** " + (f"{sum(1 for _, b in mutants if b)} of {len(mutants)} deliberate bugs were "
                                    "caught by the tests." if mutants else
                                    "not measured this build (`python3 build/build_plc.py --mutate`).")),
        f"- **Questions for the engineer:** {len(findings)}, listed next. The program is built around each "
        "one, but each needs a decision before this machine is commissioned.",
        "",
        "Files: " + ", ".join(f"`{f.name}`" for f in files.values()) + ".",
        "",
        "## Questions for the engineer",
        "",
        "Found by auditing the job data against itself and against the O&M manual. None stops the build.",
        "",
    ]
    for n, c in enumerate(findings, 1):
        out.append(f"{n}. **{c.code}.** {c.message}")
    out += ["", "## Warnings", ""]
    out += [f"- **{c.code}.** {c.message}" for c in warns] or ["None."]
    out += ["", "## What the program does", "", seq, "",
            "## Program outline", "", "| Routine | Rungs | Purpose |", "|---|---:|---|"]
    out += [f"| `{r.name}` | {len(r.rungs)} | {r.description} |" for r in program.routines]
    out += ["", f"Every rung, with its comment, is in `{files['ladder'].name}`.", "",
            "## Sequence tests", "",
            "Each test runs the generated ladder in `build/ladder_sim.py` against a plant model of the "
            "machine. On every scan of every test the simulator also checks four invariants: nothing "
            "moves or lights without SafetyOK; at most one stack light is on; both focal screw jacks are "
            "commanded together; the horn and conveyor never run at the same time.", "",
            "| Test | What it proves | Result |", "|---|---|---|"]
    out += [f"| `{name}` | {doc} | {'pass' if ok else '**FAIL**'} |" for name, doc, ok, _ in tests]
    if mutants:
        out += ["", "### Test strength", "",
                "Each bug below was put into the program on purpose, one at a time. A test must fail for each.", "",
                "| Deliberate bug | Tests that failed |", "|---|---:|"]
        out += [f"| {name} | {bad} |" for name, bad in mutants]
    out += ["", "## Assumptions to confirm at commissioning", "",
            "From `data/plc.yaml`. Change the value there and rebuild; do not edit the ladder.", "",
            "| Setting | Value and note |", "|---|---|"]
    out += [f"| `{k.split(':')[0].strip()}` | {k.split(':', 1)[1].strip()} - {v.strip()} |" for k, v in assumed]
    out += ["", "## Loading it into Studio 5000", "",
            "The L5X is a **program** import. It carries the program, its tags and routines; the "
            "controller and I/O modules are set up once by hand.", "",
            f"1. New project, controller **{p['control']['plc'].split()[-1]}**, named `{program.controller}`.",
            "2. Add the local 5069 modules in these slots:", "",
            "   | Slot | Module | Use |", "   |---:|---|---|"]
    out += [f"   | {s} | {m} | {', '.join(sorted({pt.kind for pt in job.io if pt.module == m}))} per io.csv |"
            for s, m in modules]
    out += [f"   | {max(s for s, _ in modules) + 1} | 5069-HSC2XOB4 | on the BOM (sheet 090), no points in io.csv - see F2 |",
            "",
            "   If a module tag differs from the `module_channel` column in "
            f"`{files['io'].name}`, only `R01_MapInputs` and `R99_MapOutputs` need to change.",
            f"3. In the Controller Organizer, right-click **MainTask**, choose **Add > Import Program**, "
            f"pick `{files['l5x'].name}`.",
            "4. Verify the controller. The program gates check tags, rung syntax and double coils the way "
            "Studio 5000's verify does, but only a real verify proves it. Then download to a **bench PLC "
            "or the emulator first**, never straight to the machine.",
            f"5. HMI tags for the PanelView are in `{files['hmi'].name}` (shortcut name `PLC`).",
            "",
            "This L5X follows Rockwell's published L5X structure but has not yet been imported into a real "
            "Studio 5000. The first import is the acceptance test; report any import message back and the "
            "generator gets fixed, not the file.",
            "",
            "## All checks", "", "| Code | Level | Check |", "|---|---|---|"]
    order = {"D": 0, "F": 1, "P": 2}
    out += [f"| {c.code} | {c.level} | {c.message} |"
            for c in sorted(job.checks + pchecks, key=lambda c: (order[c.code[0]], int(c.code[1:])))]
    out += ["", "The safety function is not in this program. It is hardwired through the safety controller "
            "(sheet 050) and must be validated per O&M section 7.3 regardless of anything here.", ""]
    return "\n".join(out)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
