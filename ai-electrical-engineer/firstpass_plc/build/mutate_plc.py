"""Test the tests: break the generated FMM3013 program on purpose, one bug at a
time, and confirm the scenario tests catch every one.

    python3 build/mutate_plc.py

A bug the tests miss means a test is missing, not that the program is right.
"""
import copy
import io
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import test_plc_fmm3013 as T  # noqa: E402

# (bug, routine, rung text to find, replacement)

MUTANTS = [
    ("conveyor ignores safety", "R05_Conveyor", "XIC(SafetyOK)XIO(ReinitRequired)OTE(VFD_CONV)", "XIO(ReinitRequired)OTE(VFD_CONV)"),
    ("horn 1 s not 3 s", "R04_Modes", "TON(HornPrewarnTmr,3000,0)", "TON(HornPrewarnTmr,1000,0)"),
    ("no cooldown lockout", "R03_Lamps", "XIC(HMI_LampsOn)XIO(CooldownActive)", "XIC(HMI_LampsOn)"),
    ("auto allowed in manual", "R04_Modes", "XIO(AnyManual)XIC(FocalInPosition)", "XIC(FocalInPosition)"),
    ("focal ignores high limit", "R06_FocalLift", "XIO(PRS7012)XIC(SafetyOK)", "XIC(SafetyOK)"),
    ("jacks A/B not paired", "R06_FocalLift", "[XIC(FocalMoveUp) ,XIC(FocalMoveDown)]OTE(VFD_FOCB)", "XIC(FocalMoveUp)OTE(VFD_FOCB)"),
    ("cycle stop drops at once", "R04_Modes", "XIC(CycleStopping)EQU(PartsInMachine,0)OTE(CycleStopDone)", "XIC(CycleStopping)OTE(CycleStopDone)"),
    ("no re-init after e-stop", "R02_Safety", "[XIC(SafetyLost) ,XIC(ReinitRequired)", "[XIC(ReinitRequired)"),
    ("strike all lamps at once", "R03_Lamps", "GEQ(StrikeSeqTmr.ACC,4000)", "GEQ(StrikeSeqTmr.ACC,0)"),
    ("jam alarm never latches", "R09_Alarms", "[XIC(JamTmr.DN) ,", "[XIO(JamTmr.DN)XIC(JamTmr.DN) ,"),
    ("green and amber together", "R10_Indication", "XIO(LT7109)XIO(AutoRunning)[XIO(Attention)", "XIO(LT7109)[XIO(Attention)"),
    ("part-left check skipped", "R04_Modes", "XIC(LampsReady)XIO(PartsCheckRequired)OTE(AutoPermissive)", "XIC(LampsReady)OTE(AutoPermissive)"),
]


def run():
    """Return [(bug, failing test count)] for every deliberate bug."""
    original = T.PROGRAM
    results = []
    try:
        for name, routine, old, new in MUTANTS:
            prog = copy.deepcopy(original)
            hits = [g for g in prog.routine(routine).rungs if old in g.text]
            if len(hits) != 1:
                raise RuntimeError(f"mutant '{name}': expected 1 rung containing {old!r}, found {len(hits)}")
            hits[0].text = hits[0].text.replace(old, new)
            T.PROGRAM = prog
            res = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(
                unittest.defaultTestLoader.loadTestsFromTestCase(T.FMM3013))
            results.append((name, len(res.failures) + len(res.errors)))
    finally:
        T.PROGRAM = original
    return results


if __name__ == "__main__":
    results = run()
    for name, bad in results:
        print(f"{'CAUGHT' if bad else 'MISSED'}  {name:28s} {bad} failing test(s)")
    caught = sum(1 for _, bad in results if bad)
    print(f"\n{caught}/{len(results)} deliberate bugs caught")
    sys.exit(0 if caught == len(results) else 1)
