"""FMM3013 sequence-of-operation tests, run against the generated ladder.

Each test drives the simulated machine through a piece of the O&M manual and
checks what the PLC does. Invariants (safety, stack light, focal jacks) are
checked on every scan of every test, not just at the end.

    python3 build/test_plc_fmm3013.py
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ladder_sim import Sim  # noqa: E402
from plc_job import audit, load_job  # noqa: E402
from plc_rules import MAP_IN, MAP_OUT, build_program  # noqa: E402

# (lamp, enable output, lamp-is-on input, row health input) from io.csv / lamps.csv
LAMPS = [("UV1-1", "CR3202_O", "CR3202_I", "CR3201"), ("UV1-2", "CR3204_O", "CR3204_I", "CR3201"),
         ("UV1-3", "CR3205_O", "CR3205_I", "CR3201"), ("UV2-1", "CR3208_O", "CR3208_I", "CR3207"),
         ("UV2-2", "CR3210_O", "CR3210_I", "CR3207"), ("UV2-3", "CR3211_O", "CR3211_I", "CR3207")]
DRIVES = ["VFD_CONV", "VFD_FOCA", "VFD_FOCB", "VFD_RECIP"]
LIGHTS = ["LT7109", "LT7108", "LT7107"]  # red, amber, green

JOB = audit(load_job())
PROGRAM = build_program(JOB)


class Plant:
    """Stands in for the FMM3013 hardware."""

    def __init__(self):
        self.safety = False            # safety controller healthy + safety relay 1 picked up
        self.strike_s = 2.0            # time for a module to report lamp-is-on
        self.dead_lamps = set()        # modules that never strike
        self.lamp_age = {lamp: 0.0 for lamp, *_ in LAMPS}
        self.belt_ok = True
        self.pos = 100.0               # focal height, mm
        self.focal_speed = 10.0        # mm/s
        self.focal_stuck = False
        self.high_limit, self.low_limit = 200.0, 20.0
        self.parts = []                # leading edge of each part on the belt, mm
        self.part_len, self.pe_in, self.pe_out, self.belt_end = 100.0, 150.0, 1200.0, 1400.0
        self.jammed = False

    def __call__(self, sim, dt):
        sim["GC_S1R"] = self.safety
        sim["CR3112"] = self.safety
        for lamp, en, on, _ in LAMPS:
            lit = sim[en] and self.safety and lamp not in self.dead_lamps
            self.lamp_age[lamp] = self.lamp_age[lamp] + dt if lit else 0.0
            sim[on] = self.lamp_age[lamp] >= self.strike_s
        sim["CR3201"] = sim["CR3207"] = self.safety

        belt = 0.0
        if sim["VFD_CONV"] and self.safety and self.belt_ok:
            belt = sim["SC7403"] * 10.0            # 0-10 V -> 0-100 %
        sim["FT7300"] = belt
        if not self.jammed:
            self.parts = [x + belt * 5.0 * dt for x in self.parts]   # 100 % = 500 mm/s
        self.parts = [x for x in self.parts if x - self.part_len < self.belt_end]
        sim["PRS7001"] = any(x - self.part_len <= self.pe_in <= x for x in self.parts)
        sim["PRS7002"] = any(x - self.part_len <= self.pe_out <= x for x in self.parts)

        if sim["VFD_FOCA"] and sim["VFD_FOCB"] and self.safety and not self.focal_stuck:
            step = self.focal_speed * dt
            self.pos += step if sim["FocalMoveUp"] else -step if sim["FocalMoveDown"] else 0.0
        sim["PT7301"] = self.pos
        sim["PRS7012"] = self.pos >= self.high_limit
        sim["PRS7013"] = self.pos <= self.low_limit

    def load_part(self):
        self.parts.append(0.0)


class FMM3013(unittest.TestCase):

    def setUp(self):
        self.plant = Plant()
        self.sim = Sim(PROGRAM, skip_routines=(MAP_IN, MAP_OUT), plant=self.plant)
        self.sim.watchers.append(self.invariants)

    def invariants(self, sim):
        if not sim["SafetyOK"]:
            live = [t for t in DRIVES + [en for _, en, _, _ in LAMPS] if sim[t]]
            assert not live, f"t={sim.time_ms / 1000:.2f}s safety not OK but {live} on"
        lit = [t for t in LIGHTS if sim[t]]
        assert len(lit) <= 1, f"t={sim.time_ms / 1000:.2f}s more than one stack light on: {lit}"
        assert sim["VFD_FOCA"] == sim["VFD_FOCB"], "focal screw jacks commanded differently"
        assert not (sim["HN7110"] and sim["VFD_CONV"]), "horn and conveyor motion at the same time"

    # --- helpers -------------------------------------------------------------

    def press(self, tag, hold=0.1):
        self.sim[tag] = True
        self.sim.run(hold)
        self.sim[tag] = False
        self.sim.run(0.05)

    def safety_reset(self):
        self.plant.safety = True
        self.sim.run(0.1)
        self.press("HMI_ResetFaults")

    def lamps_ready(self):
        self.press("HMI_LampsOn")
        self.sim.run_until(lambda s: s["LampsReady"], timeout=120, dt=0.05)

    def ready_for_auto(self):
        self.safety_reset()
        self.plant.pos = self.sim["HMI_FocalHeightSP"]
        self.lamps_ready()
        self.assertTrue(self.sim["AutoPermissive"], f"reason {self.sim['AutoBlockReason']}")

    def start_auto(self):
        self.press("HMI_AutoStart")
        self.sim.run_until(lambda s: s["AutoRunning"], timeout=5)

    # --- power up and safety ------------------------------------------------

    def test_power_up_is_safe_and_red(self):
        """Power up with the safety circuit not reset: nothing moves, red on, reset lamp flashes."""
        states = set()
        for _ in range(20):
            self.sim.run(0.1)
            states.add(self.sim["CR3115"])
        self.assertEqual(states, {True, False}, "reset lamp should flash")
        self.assertTrue(self.sim["LT7109"])
        self.assertFalse(any(self.sim[t] for t in DRIVES))
        self.assertEqual(self.sim["AutoBlockReason"], 1)

    def test_reset_clears_red_to_amber(self):
        """Monitored reset, then HMI reset: red clears, amber shows idle, reset lamp stops."""
        self.sim.run(0.5)                    # powered up, safety circuit not yet reset
        self.plant.safety = True
        self.sim.run(0.2)
        self.assertTrue(self.sim["SafetyOK"])
        self.assertTrue(self.sim["LT7109"], "alarm latched until acknowledged")
        self.press("HMI_ResetFaults")
        self.assertFalse(self.sim["LT7109"])
        self.assertTrue(self.sim["LT7108"])
        self.assertFalse(self.sim["CR3115"])

    # --- lamps ----------------------------------------------------------------

    def test_lamps_strike_one_per_second_in_order(self):
        """Lamps strike one module per second, in lamps.csv order, then warm up."""
        self.safety_reset()
        on_at = {}

        def record(sim):
            for lamp, en, _, _ in LAMPS:
                if sim[en] and lamp not in on_at:
                    on_at[lamp] = sim.time_ms / 1000.0
        self.sim.watchers.append(record)
        self.press("HMI_LampsOn")
        self.sim.run_until(lambda s: len(on_at) == len(LAMPS), timeout=10)
        times = [on_at[lamp] for lamp, *_ in LAMPS]
        self.assertEqual(times, sorted(times))
        gaps = [round(b - a, 2) for a, b in zip(times, times[1:])]
        self.assertTrue(all(abs(g - 1.0) <= 0.02 for g in gaps), gaps)
        self.assertFalse(self.sim["LampsReady"], "warm-up not finished yet")
        self.sim.run_until(lambda s: s["LampsReady"], timeout=120, dt=0.05)

    def test_lamp_that_never_strikes_raises_its_alarm(self):
        """A module that never reports lamp-is-on raises its own strike alarm and blocks auto."""
        self.plant.dead_lamps.add("UV2-2")
        self.safety_reset()
        self.press("HMI_LampsOn")
        self.sim.run(13, dt=0.05)            # UV2-2 is enabled at +4 s; its watchdog is 10 s
        self.assertFalse(self.sim["ALM_UV2_2_StrikeFail"], "not before the 10 s watchdog")
        self.sim.run(2, dt=0.05)
        self.assertTrue(self.sim["ALM_UV2_2_StrikeFail"])
        self.assertFalse(self.sim["ALM_UV2_1_StrikeFail"])
        self.assertTrue(self.sim["LT7109"])
        self.assertFalse(self.sim["LampsReady"])

    def test_lamp_arc_lost_while_running_stops_auto(self):
        """A lamp that goes out in production raises 'arc lost' and automatic stops."""
        self.ready_for_auto()
        self.start_auto()
        self.plant.dead_lamps.add("UV1-3")
        self.sim.run(0.2)
        self.assertTrue(self.sim["ALM_UV1_3_LampLost"])
        self.assertFalse(self.sim["AutoRunning"])
        self.assertFalse(self.sim["VFD_CONV"])

    def test_cooldown_blocks_restrike_for_five_minutes(self):
        """After lamps off, a re-strike is refused until the 5 minute cooldown ends."""
        self.safety_reset()
        self.lamps_ready()
        self.press("HMI_LampsOff")
        self.assertTrue(self.sim["CooldownActive"])
        self.sim.run(60, dt=0.1)
        self.press("HMI_LampsOn")
        self.assertFalse(self.sim["LampsCmd"], "re-strike during cooldown must be refused")
        self.sim.run(241, dt=0.1)
        self.assertFalse(self.sim["CooldownActive"])
        self.press("HMI_LampsOn")
        self.assertTrue(self.sim["LampsCmd"])

    def test_intensity_setpoint_scaled_to_volts(self):
        """Intensity 75 % gives 7.5 V; out-of-range entries are clamped to 0-10 V."""
        self.sim["HMI_UpperIntensityPct"] = 75.0
        self.sim["HMI_LowerIntensityPct"] = 150.0
        self.sim.run(0.05)
        self.assertAlmostEqual(self.sim["SC7401"], 7.5)
        self.assertAlmostEqual(self.sim["SC7402"], 10.0)
        self.sim["HMI_UpperIntensityPct"] = -5.0
        self.sim.run(0.05)
        self.assertAlmostEqual(self.sim["SC7401"], 0.0)

    # --- automatic ------------------------------------------------------------

    def test_auto_refused_while_a_subsystem_is_in_manual(self):
        """O&M 4.1: automatic is refused while any subsystem is in manual."""
        self.ready_for_auto()
        self.sim["HMI_Manual_Recip"] = True
        self.press("HMI_AutoStart")
        self.sim.run(4)
        self.assertFalse(self.sim["AutoRunning"])
        self.assertEqual(self.sim["AutoBlockReason"], 3)

    def test_auto_refused_when_focal_lift_not_in_position(self):
        """O&M 4.1: automatic needs the focal lift at its commanded position."""
        self.safety_reset()
        self.plant.pos = self.sim["HMI_FocalHeightSP"] + 25.0
        self.lamps_ready()
        self.press("HMI_AutoStart")
        self.sim.run(4)
        self.assertFalse(self.sim["AutoRunning"])
        self.assertEqual(self.sim["AutoBlockReason"], 4)

    def test_auto_start_horn_three_seconds_before_motion(self):
        """O&M 4.2: the horn sounds 3 s before first motion, then conveyor and recip run, green on."""
        self.ready_for_auto()
        self.press("HMI_AutoStart")
        self.assertTrue(self.sim["HN7110"])
        self.sim.run(2.7)
        self.assertTrue(self.sim["HN7110"])
        self.assertFalse(self.sim["VFD_CONV"] or self.sim["VFD_RECIP"])
        self.sim.run(0.3)
        self.assertFalse(self.sim["HN7110"])
        self.assertTrue(self.sim["VFD_CONV"] and self.sim["VFD_RECIP"])
        self.assertTrue(self.sim["LT7107"])
        self.assertAlmostEqual(self.sim["SC7403"], 5.0)   # 50 % recipe speed -> 5 V

    def test_estop_while_running_drops_everything_and_needs_reinit(self):
        """O&M 4.4: E-stop drops lamps and drives at once; after release it needs reset + HMI re-init."""
        self.ready_for_auto()
        self.start_auto()
        self.plant.safety = False
        self.sim.run(0.02)
        for t in DRIVES + [en for _, en, _, _ in LAMPS]:
            self.assertFalse(self.sim[t], t)
        self.assertTrue(self.sim["LT7109"])
        self.plant.safety = True
        self.sim.run(1)
        self.assertTrue(self.sim["ReinitRequired"])
        self.press("HMI_LampsOn")
        self.assertFalse(self.sim["LampsCmd"], "nothing runs before re-init")
        self.press("HMI_ResetFaults")
        self.assertFalse(self.sim["ReinitRequired"])
        self.assertTrue(self.sim["CooldownActive"], "lamps were on: cooldown before re-strike")

    # --- parts ----------------------------------------------------------------

    def test_cycle_stop_runs_until_the_last_part_clears(self):
        """O&M 4.3: cycle stop keeps the conveyor running until the last part clears the exit eye."""
        self.ready_for_auto()
        self.start_auto()
        self.plant.load_part()
        self.sim.run_until(lambda s: s["PartsInMachine"] == 1, timeout=5)
        self.press("HMI_AutoStop")
        self.assertTrue(self.sim["VFD_CONV"], "must keep running with a part inside")
        took = self.sim.run_until(lambda s: not s["VFD_CONV"], timeout=20)
        self.assertEqual(self.sim["PartsInMachine"], 0)
        self.assertGreater(took, 3.0)
        self.assertFalse(self.sim["AutoRunning"])

    def test_part_left_after_estop_must_be_confirmed(self):
        """O&M 4.4: a part left inside after a safety stop blocks automatic until cleared on the HMI."""
        self.ready_for_auto()
        self.start_auto()
        self.plant.load_part()
        self.sim.run_until(lambda s: s["PartsInMachine"] == 1, timeout=5)
        self.plant.safety = False
        self.sim.run(0.1)
        self.assertTrue(self.sim["PartsCheckRequired"])
        self.plant.safety = True
        self.plant.parts.clear()
        self.sim.run(0.1)
        self.press("HMI_ResetFaults")
        self.sim.run(300, dt=0.1)          # cooldown
        self.lamps_ready()
        self.assertEqual(self.sim["AutoBlockReason"], 6)
        self.assertFalse(self.sim["AutoPermissive"])
        self.press("HMI_AutoStart")
        self.sim.run(4)
        self.assertFalse(self.sim["AutoRunning"], "must not start before the operator confirms")
        self.press("HMI_PartsCleared")
        self.assertEqual(self.sim["PartsInMachine"], 0)
        self.assertTrue(self.sim["AutoPermissive"])

    def test_jam_stops_the_machine(self):
        """A part that never reaches the exit raises a jam alarm and automatic stops."""
        self.ready_for_auto()
        self.start_auto()
        self.plant.load_part()
        self.sim.run_until(lambda s: s["PartsInMachine"] == 1, timeout=5)
        self.plant.jammed = True
        self.sim.run(31, dt=0.05)
        self.assertTrue(self.sim["ALM_Jam"])
        self.assertFalse(self.sim["AutoRunning"])
        self.assertFalse(self.sim["VFD_CONV"])

    def test_belt_not_moving_raises_alarm(self):
        """Conveyor commanded to run but the encoder shows no motion raises an alarm."""
        self.ready_for_auto()
        self.plant.belt_ok = False
        self.start_auto()
        self.sim.run(3.5)
        self.assertTrue(self.sim["ALM_ConvNoMotion"])
        self.assertFalse(self.sim["VFD_CONV"])

    # --- focal lift -----------------------------------------------------------

    def test_focal_lift_moves_to_setpoint_on_command_only(self):
        """The focal lift never moves on its own; on command it goes to setpoint and stops."""
        self.safety_reset()
        self.sim["HMI_FocalHeightSP"] = 130.0
        self.sim.run(2)
        self.assertFalse(self.sim["VFD_FOCA"], "no motion without a command")
        self.press("HMI_FocalGoToSP")
        self.assertTrue(self.sim["FocalMoveUp"])
        self.sim.run_until(lambda s: s["FocalInPosition"], timeout=10)
        self.sim.run(0.1)
        self.assertFalse(self.sim["VFD_FOCA"])
        self.assertAlmostEqual(self.plant.pos, 130.0, delta=1.0)

    def test_focal_lift_moves_down_with_both_jacks(self):
        """Going down, both screw jacks run together and stop at setpoint."""
        self.safety_reset()
        self.sim["HMI_FocalHeightSP"] = 60.0
        self.press("HMI_FocalGoToSP")
        self.assertTrue(self.sim["FocalMoveDown"])
        self.assertTrue(self.sim["VFD_FOCA"] and self.sim["VFD_FOCB"])
        self.sim.run_until(lambda s: s["FocalInPosition"], timeout=10)
        self.sim.run(0.1)
        self.assertFalse(self.sim["VFD_FOCA"] or self.sim["VFD_FOCB"])
        self.assertAlmostEqual(self.plant.pos, 60.0, delta=1.0)

    def test_focal_jog_stops_at_high_limit(self):
        """In manual, jogging up stops at the high limit photoeye."""
        self.safety_reset()
        self.plant.pos = 190.0
        self.sim["HMI_Manual_Focal"] = True
        self.sim["HMI_FocalJogUp"] = True
        self.sim.run(3)
        self.assertTrue(self.sim["PRS7012"])
        self.assertFalse(self.sim["VFD_FOCA"])
        self.assertLess(self.plant.pos, 201.0)

    def test_focal_setpoint_beyond_limit_alarms(self):
        """A setpoint above the high limit stops at the photoeye and raises an alarm."""
        self.safety_reset()
        self.plant.pos = 190.0
        self.sim["HMI_FocalHeightSP"] = 250.0
        self.press("HMI_FocalGoToSP")
        self.sim.run(3)
        self.assertTrue(self.sim["ALM_FocalSetpointRange"])
        self.assertFalse(self.sim["VFD_FOCA"])

    def test_focal_lift_stuck_times_out(self):
        """A lift that is commanded but does not move faults after the move timeout."""
        self.safety_reset()
        self.plant.focal_stuck = True
        self.sim["HMI_FocalHeightSP"] = 150.0
        self.press("HMI_FocalGoToSP")
        self.sim.run(21, dt=0.05)
        self.assertTrue(self.sim["ALM_FocalTimeout"])
        self.assertFalse(self.sim["VFD_FOCA"] or self.sim["VFD_FOCB"])

    # --- manual ---------------------------------------------------------------

    def test_conveyor_jog_only_in_manual(self):
        """Jog runs the conveyor at jog speed in manual, and does nothing outside manual."""
        self.safety_reset()
        self.sim["HMI_JogConv"] = True
        self.sim.run(0.2)
        self.assertFalse(self.sim["VFD_CONV"])
        self.sim["HMI_Manual_Conv"] = True
        self.sim.run(0.2)
        self.assertTrue(self.sim["VFD_CONV"])
        self.assertAlmostEqual(self.sim["SC7403"], 2.0)   # 20 % jog -> 2 V
        self.sim["HMI_JogConv"] = False
        self.sim.run(0.1)
        self.assertFalse(self.sim["VFD_CONV"])

    def test_no_jog_during_safety_stop(self):
        """Manual jogs of every drive are dead while the safety circuit is open."""
        for flag in ("HMI_Manual_Conv", "HMI_Manual_Recip", "HMI_Manual_Focal",
                     "HMI_JogConv", "HMI_JogRecip", "HMI_FocalJogUp"):
            self.sim[flag] = True
        self.sim.run(1)
        self.assertFalse(any(self.sim[t] for t in DRIVES))


if __name__ == "__main__":
    unittest.main(verbosity=2)
