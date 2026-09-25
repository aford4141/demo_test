"""Machine rules: FirstPass job data -> Logix ladder program.

This is the part an AI (or an engineer) writes and a human reviews. It turns
the sequence of operation in the O&M manual into rung templates. Every device
comes from data/: add a lamp to lamps.csv or a drive to drives.csv and the
program regenerates. gen_plc.py exports the result and the simulator in
ladder_sim.py proves it against test_plc_fmm3013.py.

Sequence of operation implemented (O&M section 4):
  * The safety function is hardwired through the safety controller. The PLC
    only monitors it and never overrides it.
  * After any safety stop, the operator presses the monitored reset and then
    re-initialises from the HMI before anything can run.
  * Lamps strike from the HMI, one module per second. Each module must report
    lamp-is-on and each row its health, or an alarm is raised. After lamp off,
    a 5 minute cooldown blocks re-strike.
  * Automatic needs: safety healthy, re-initialised, no alarms, no subsystem
    in manual, focal lift at its commanded position between the limits, lamps
    warmed up, and no unconfirmed part left in the machine.
  * Auto start sounds the horn for 3 s before the conveyor and reciprocator
    move. Cycle stop keeps the conveyor running until the last part clears the
    exit photoeye.
  * Parts are counted in at the entry photoeye and out at the exit photoeye.
    A part left inside after a safety stop must be cleared and confirmed on
    the HMI before automatic is allowed again.
"""
from dataclasses import dataclass, field

from plc_job import JobDataError

MAP_IN, MAP_OUT = "R01_MapInputs", "R99_MapOutputs"


@dataclass
class Tag:
    name: str
    datatype: str
    description: str
    role: str
    value: float = 0
    preset: int = 0
    io: object = None


@dataclass
class Rung:
    text: str
    comment: str = ""


@dataclass
class Routine:
    name: str
    description: str
    rungs: list = field(default_factory=list)

    def rung(self, text, comment=""):
        self.rungs.append(Rung(text, comment))


@dataclass
class Program:
    name: str
    controller: str
    main: str
    tags: dict
    routines: list
    alarms: list

    def routine(self, name):
        return next(r for r in self.routines if r.name == name)


class Builder:
    def __init__(self, job):
        self.job = job
        self.tags = {}
        self.routines = []
        self.alarms = []

    def tag(self, name, datatype="BOOL", desc="", role="INTERNAL", value=0, preset=0, io=None):
        if name in self.tags:
            raise JobDataError(f"tag {name} defined twice")
        self.tags[name] = Tag(name, datatype, desc, role, value, preset, io)
        return name

    def timer(self, name, ms, desc):
        return self.tag(name, "TIMER", desc, "TIMER", preset=max(int(ms), 1))

    def ton(self, name, kind="TON"):
        return f"{kind}({name},{self.tags[name].preset},0)"

    def routine(self, name, desc):
        r = Routine(name, desc)
        self.routines.append(r)
        return r

    def alarm(self, name, condition, desc):
        self.tag(name, "BOOL", desc, "ALARM")
        self.alarms.append((name, condition, desc))
        return name


def build_program(job):
    b = Builder(job)
    plc = job.plc
    _io_tags(b)
    _hmi_tags(b)

    main = b.routine("R00_Main", "Calls every routine once per scan, in order.")
    order = [
        (MAP_IN, "Copy module inputs to named tags", _map_inputs),
        ("R02_Safety", "Safety status, re-initialise, reset lamp, flasher", _safety),
        ("R03_Lamps", "UV lamp strike, cooldown, warm-up, intensity", _lamps),
        ("R04_Modes", "Automatic permissive, cycle start and cycle stop", _modes),
        ("R05_Conveyor", "Conveyor drive run and speed", _conveyor),
        ("R06_FocalLift", "Focal lift positioning, both screw jacks together", _focal_lift),
        ("R07_Recip", "Reciprocator run and speed", _recip),
        ("R08_Parts", "Part tracking, jam detection, part-left check", _parts),
        ("R09_Alarms", "Latching alarms and the Faulted summary", _alarms),
        ("R10_Indication", "Stack light and horn", _indication),
        (MAP_OUT, "Copy named tags to module outputs", _map_outputs),
    ]
    for name, desc, fn in order:
        r = b.routine(name, desc)
        fn(b, r)
        main.rung(f"JSR({name},0);", desc)

    return Program(plc["program"], plc["controller"], "R00_Main", b.tags, b.routines, b.alarms)


# --- tags -------------------------------------------------------------------

def _io_tags(b):
    for p in b.job.points():
        b.tag(p.tag, p.datatype, p.label(), p.kind, io=p)


def _hmi_tags(b):
    d = b.job.plc["hmi_defaults"]
    for name, desc in [
        ("HMI_ResetFaults", "HMI: reset alarms and re-initialise after a safety stop"),
        ("HMI_LampsOn", "HMI: strike lamps"),
        ("HMI_LampsOff", "HMI: lamps off (starts cooldown)"),
        ("HMI_AutoStart", "HMI: start automatic"),
        ("HMI_AutoStop", "HMI: cycle stop - runs until the last part clears"),
        ("HMI_PartsCleared", "HMI: operator confirms the machine is clear of parts"),
        ("HMI_FocalGoToSP", "HMI: move focal lift to its setpoint"),
        ("HMI_Manual_Lamps", "HMI: lamps in manual (maintenance)"),
        ("HMI_Manual_Conv", "HMI: conveyor in manual (maintenance)"),
        ("HMI_Manual_Focal", "HMI: focal lift in manual (maintenance)"),
        ("HMI_Manual_Recip", "HMI: reciprocator in manual (maintenance)"),
        ("HMI_JogConv", "HMI: jog conveyor (manual only, hold to run)"),
        ("HMI_JogRecip", "HMI: jog reciprocator (manual only, hold to run)"),
        ("HMI_FocalJogUp", "HMI: jog focal lift up (manual only, hold to run)"),
        ("HMI_FocalJogDown", "HMI: jog focal lift down (manual only, hold to run)"),
    ]:
        b.tag(name, "BOOL", desc, "HMI")
    for name, key, desc in [
        ("HMI_UpperIntensityPct", "upper_intensity_pct", "HMI: upper row lamp intensity, %"),
        ("HMI_LowerIntensityPct", "lower_intensity_pct", "HMI: lower row lamp intensity, %"),
        ("HMI_ConvSpeedPct", "conveyor_speed_pct", "HMI: conveyor speed in automatic, %"),
        ("HMI_RecipSpeedPct", "recip_speed_pct", "HMI: reciprocator speed in automatic, %"),
        ("HMI_FocalHeightSP", "focal_height_sp_mm", "HMI: focal lift height setpoint, mm"),
    ]:
        b.tag(name, "REAL", desc, "HMI", value=float(d[key]))


def _status(b, name, desc, datatype="BOOL"):
    return b.tag(name, datatype, desc, "STATUS")


# --- routines ---------------------------------------------------------------

def _map_inputs(b, r):
    for p in b.job.points("DI"):
        r.rung(f"XIC({p.path})OTE({p.tag});", p.label())
    for p in b.job.points("AI"):
        r.rung(f"MOV({p.path},{p.tag});", p.label())


def _map_outputs(b, r):
    for p in b.job.points("DO"):
        r.rung(f"XIC({p.tag})OTE({p.path});", p.label())
    for p in b.job.points("AO"):
        r.rung(f"MOV({p.tag},{p.path});", p.label())


def _safety(b, r):
    job = b.job
    healthy = job.need("DI", "safety controller healthy", "safety status").tag
    relay = job.need("DI", "safety relay .* monitor", "safety relay status").tag
    reset_lamp = job.need("DO", "reset lamp", "safety reset indicator").tag
    _status(b, "SafetyOK", "Safety system healthy (controller output on, safety relay picked up)")
    b.tag("SafetyOK_Prev", desc="SafetyOK last scan")
    _status(b, "SafetyLost", "One-scan pulse when the safety circuit drops")
    _status(b, "ReinitRequired", "A safety stop happened; re-initialise from the HMI")
    b.timer("FlashTmr", job.timer("flash_period"), "1 Hz flasher")
    b.tag("Flash", desc="Flasher output, on for the first half of each period")
    half = job.timer("flash_period") // 2

    r.rung(f"XIC({healthy})XIC({relay})OTE(SafetyOK);",
           "The safety function is hardwired through the safety controller (sheet 050). "
           "The PLC only watches it: healthy output on AND safety relay 1 picked up.")
    r.rung("XIO(SafetyOK)XIC(SafetyOK_Prev)OTE(SafetyLost);",
           "One-scan pulse when the safety circuit drops: E-stop, door opened or safety fault.")
    r.rung("[XIC(SafetyLost) ,XIC(ReinitRequired) [XIO(HMI_ResetFaults) ,XIO(SafetyOK)]]OTE(ReinitRequired);",
           "O&M 4.4: after a safety stop, press the monitored reset, then re-initialise from the HMI. "
           "Nothing runs until both are done.")
    r.rung("XIC(SafetyOK)OTE(SafetyOK_Prev);", "Remember SafetyOK for the edge above.")
    r.rung(f"XIO(FlashTmr.DN){b.ton('FlashTmr')};", "Free-running flasher timer.")
    r.rung(f"LES(FlashTmr.ACC,{half})OTE(Flash);", "Flash is on for the first half of each period.")
    r.rung(f"XIO(SafetyOK)XIC(Flash)OTE({reset_lamp});",
           "The illuminated reset button PB7015 flashes while the safety circuit needs a reset.")


def _lamps(b, r):
    job = b.job
    stagger = job.timer("lamp_strike_stagger")
    n = len(job.lamps)
    exhaust = job.find("DI", "exhaust")
    for name, desc in [("LampsCmd", "Lamps commanded on"),
                       ("CooldownActive", "Lamp cooldown running; re-strike blocked"),
                       ("AllLampsOn", "Every module reports lamp-is-on and every row is healthy"),
                       ("LampsReady", "Lamps on and warmed up")]:
        _status(b, name, desc)
    b.timer("CooldownTmr", job.timer("lamp_cooldown"), "Lamp cooldown after lamps off (O&M 4.3)")
    b.timer("StrikeSeqTmr", stagger * (n - 1), "Staggered strike sequence")
    b.timer("WarmUpTmr", job.timer("lamp_warmup"), "Lamp warm-up before automatic")

    permissive = "XIC(SafetyOK)XIO(ReinitRequired)"
    note = ""
    if exhaust is not None:
        permissive += f"XIC({exhaust.tag})"
        note = f" Exhaust must be proven ({exhaust.tag})."
    r.rung(f"[XIC(HMI_LampsOn)XIO(CooldownActive) ,XIC(LampsCmd)]{permissive}XIO(HMI_LampsOff)OTE(LampsCmd);",
           "Lamps on from the HMI. Refused during cooldown. Dropped by lamps-off or any safety stop "
           "(the safety contactor has already removed lamp power)." + note)
    r.rung(f"XIC(LampsCmd){b.ton('CooldownTmr', 'TOF')};",
           "Cooldown: the timer runs for 5 minutes after the lamps go off.")
    r.rung("XIC(CooldownTmr.DN)XIO(LampsCmd)OTE(CooldownActive);",
           "Do not re-strike a hot lamp (O&M 4.3). ASSUMED: medium-pressure lamps cannot hot-restrike; "
           "confirm against the LightHammer manual.")
    r.rung(f"XIC(LampsCmd){b.ton('StrikeSeqTmr')};",
           f"Strike sequence timer: one module every {stagger / 1000:g} s to limit inrush.")

    lamp_on = []
    for i, lamp in enumerate(job.lamps):
        key = f"{lamp['row']} Row {lamp['role']} Lamp"
        en = job.need("DO", f"^{key} Enable$", lamp["tag"]).tag
        on = job.need("DI", f"^{key} Is On$", lamp["tag"]).tag
        t = lamp["tag"].replace("-", "_")
        lamp_on.append(on)
        b.timer(f"{t}_StrikeTmr", job.timer("lamp_strike_timeout"), f"{lamp['tag']} strike watchdog")
        b.tag(f"{t}_WasOn", desc=f"{lamp['tag']} has reported lamp-is-on since it was enabled")
        desc = f"{lamp['tag']} {lamp['row']} {lamp['role']} ({lamp['model']}, {lamp['kw']} kW)"
        r.rung(f"XIC(LampsCmd)GEQ(StrikeSeqTmr.ACC,{i * stagger})OTE({en});",
               f"{desc}: enable at +{i * stagger / 1000:g} s.")
        r.rung(f"XIC({en})XIO({on}){b.ton(f'{t}_StrikeTmr')};",
               f"{lamp['tag']} strike watchdog: enabled but lamp-is-on not made.")
        r.rung(f"[XIC({on}) ,XIC({t}_WasOn)]XIC({en})OTE({t}_WasOn);",
               f"{lamp['tag']} remembers it was lit, so losing the arc can be told apart from never striking.")
        b.alarm(f"ALM_{t}_StrikeFail", f"XIC({t}_StrikeTmr.DN)", f"{lamp['tag']} failed to strike")
        b.alarm(f"ALM_{t}_LampLost", f"XIC({en})XIC({t}_WasOn)XIO({on})", f"{lamp['tag']} arc lost while enabled")

    healths = []
    for row in sorted({l["row"] for l in job.lamps}, key=lambda x: x != "Upper"):
        h = job.need("DI", f"^{row} Row System Health$", f"{row} row").tag
        healths.append(h)
        b.timer(f"{row}HealthTmr", job.timer("row_health_timeout"), f"{row} row health watchdog")
        r.rung(f"XIC(LampsCmd)XIO({h}){b.ton(f'{row}HealthTmr')};",
               f"{row} row system-health relay must make once the lamps are commanded on.")
        b.alarm(f"ALM_{row}RowHealth", f"XIC({row}HealthTmr.DN)", f"{row} row lamp system not healthy")

    r.rung("XIC(LampsCmd)" + "".join(f"XIC({x})" for x in lamp_on + healths) + "OTE(AllLampsOn);",
           "All modules lit and both rows healthy.")
    r.rung(f"XIC(AllLampsOn){b.ton('WarmUpTmr')};", "Warm-up before product (O&M 4.2 step 6).")
    r.rung("XIC(WarmUpTmr.DN)OTE(LampsReady);", "Lamps ready for automatic.")

    volts_per_pct = job.analog("ao_full_scale_volts") / 100.0
    for row in ("Upper", "Lower"):
        ao = job.find("AO", f"^{row} Row Lamp Intensity Setpoint$")
        if ao is None:
            continue
        sp = f"HMI_{row}IntensityPct"
        _clamp(r, sp, 0.0, 100.0)
        r.rung(f"MUL({sp},{volts_per_pct:g},{ao.tag});",
               f"{row} row intensity: 0-100 % -> 0-{job.analog('ao_full_scale_volts'):g} V on {ao.device_tag}. "
               "ASSUMED: the output channel is configured in volts.")


def _clamp(r, tag, lo, hi):
    r.rung(f"GRT({tag},{hi:.1f})MOV({hi:.1f},{tag});", f"Limit {tag} to {hi:g}.")
    r.rung(f"LES({tag},{lo:.1f})MOV({lo:.1f},{tag});", f"Limit {tag} to {lo:g}.")


def _modes(b, r):
    job = b.job
    hi = job.need("DI", "focal lift high limit", "focal lift").tag
    lo = job.need("DI", "focal lift low limit", "focal lift").tag
    pos = job.need("AI", "focal height position", "focal lift").tag
    for name, desc, dt in [
        ("AnyManual", "At least one subsystem is in manual", "BOOL"),
        ("FocalInPosition", "Focal lift at setpoint and between the limit photoeyes", "BOOL"),
        ("AutoPermissive", "All conditions for automatic are met", "BOOL"),
        ("AutoBlockReason", "Why automatic is refused: 0 none, 1 safety/re-init, 2 alarm, "
                            "3 subsystem in manual, 4 focal lift not in position, "
                            "5 lamps not ready, 6 part left in machine", "DINT"),
        ("AutoRequest", "Automatic requested (horn warning, then running)", "BOOL"),
        ("AutoRunning", "Automatic running - conveyor and reciprocator moving", "BOOL"),
        ("CycleStopping", "Cycle stop requested; running until the last part exits", "BOOL"),
    ]:
        _status(b, name, desc, dt)
    b.tag("FocalError", "REAL", "Focal height minus setpoint, mm")
    b.tag("P_FocalDeadband", "REAL", "Focal in-position band, mm", "PARAM", value=job.analog("focal_deadband_mm"))
    b.tag("P_FocalDeadbandNeg", "REAL", "Negative of P_FocalDeadband")
    b.tag("CycleStopDone", desc="Cycle stop finished: machine empty")
    b.timer("HornPrewarnTmr", job.timer("horn_prewarn"), "Horn before first motion (O&M 4.2 step 7)")

    r.rung("[XIC(HMI_Manual_Lamps) ,XIC(HMI_Manual_Conv) ,XIC(HMI_Manual_Focal) ,XIC(HMI_Manual_Recip)]OTE(AnyManual);",
           "Automatic is refused while any subsystem is in manual (O&M 4.1).")
    r.rung(f"SUB({pos},HMI_FocalHeightSP,FocalError);", "Focal position error.")
    r.rung("MUL(P_FocalDeadband,-1.0,P_FocalDeadbandNeg);", "Lower edge of the in-position band.")
    r.rung(f"LIM(P_FocalDeadbandNeg,FocalError,P_FocalDeadband)XIO({hi})XIO({lo})OTE(FocalInPosition);",
           "O&M 4.1 condition 3: focal lift at its commanded position, between the high and low limit photoeyes.")
    r.rung("XIC(SafetyOK)XIO(ReinitRequired)XIO(Faulted)XIO(AnyManual)XIC(FocalInPosition)"
           "XIC(LampsReady)XIO(PartsCheckRequired)OTE(AutoPermissive);",
           "Everything automatic needs (O&M 4.1 plus lamps warmed up and no part left in the machine).")
    r.rung("MOV(0,AutoBlockReason);", "Reason codes for the HMI, lowest priority first; the last true one wins.")
    r.rung("XIO(LampsReady)MOV(5,AutoBlockReason);", "5: lamps not lit and warmed up.")
    r.rung("XIO(FocalInPosition)MOV(4,AutoBlockReason);", "4: focal lift not at its setpoint.")
    r.rung("XIC(PartsCheckRequired)MOV(6,AutoBlockReason);", "6: a part may be left in the machine.")
    r.rung("XIC(AnyManual)MOV(3,AutoBlockReason);", "3: a subsystem is in manual; the HMI shows which.")
    r.rung("XIC(Faulted)MOV(2,AutoBlockReason);", "2: an alarm is active.")
    r.rung("[XIO(SafetyOK) ,XIC(ReinitRequired)]MOV(1,AutoBlockReason);", "1: safety stop or not re-initialised.")
    r.rung("[XIC(HMI_AutoStop)XIC(AutoRequest) ,XIC(CycleStopping)XIC(AutoRequest)]OTE(CycleStopping);",
           "Cycle stop (O&M 4.3): stop taking product, keep running until the last part clears.")
    r.rung("XIC(CycleStopping)EQU(PartsInMachine,0)OTE(CycleStopDone);", "Machine is empty.")
    r.rung("[XIC(HMI_AutoStart)XIO(CycleStopping) ,XIC(AutoRequest)]XIC(AutoPermissive)XIO(CycleStopDone)OTE(AutoRequest);",
           "Automatic request. Drops on cycle stop completion or the moment any permissive is lost.")
    r.rung(f"XIC(AutoRequest){b.ton('HornPrewarnTmr')};", "Horn sounds before first motion.")
    r.rung("XIC(AutoRequest)XIC(HornPrewarnTmr.DN)OTE(AutoRunning);", "Motion allowed after the horn.")


def _drive(b, r, word, jog, manual, speed_sp, run_note):
    job = b.job
    d = next(x for x in job.drives if x["motor"].split()[0] == word)
    en = next(p for p in job.points("DO") if p.tag == "VFD_" + d["tag"].split("-", 1)[1]).tag
    r.rung(f"[XIC(AutoRunning) ,XIC({manual})XIC({jog})XIO(AutoRequest)]XIC(SafetyOK)XIO(ReinitRequired)OTE({en});",
           f"{d['tag']} {d['motor']} ({d['vfd_model']}) run enable, sheet 072. {run_note}")
    ao = job.find("AO", f"{word} speed reference")
    if ao is None:
        return en
    cmd = b.tag(f"{word}SpeedCmdPct", "REAL", f"{d['motor']} speed command, %")
    if "P_JogSpeedPct" not in b.tags:
        b.tag("P_JogSpeedPct", "REAL", "Manual jog speed, %", "PARAM", value=job.analog("jog_speed_pct"))
    _clamp(r, speed_sp, 0.0, 100.0)
    r.rung(f"XIC(AutoRunning)MOV({speed_sp},{cmd});", "Automatic speed from the HMI recipe.")
    r.rung(f"XIO(AutoRunning)MOV(P_JogSpeedPct,{cmd});", "Jog speed in manual.")
    r.rung(f"XIO({en})MOV(0.0,{cmd});", "Zero reference when not running.")
    vpp = job.analog("ao_full_scale_volts") / 100.0
    r.rung(f"MUL({cmd},{vpp:g},{ao.tag});",
           f"Speed reference {ao.device_tag}: 0-100 % -> 0-{job.analog('ao_full_scale_volts'):g} V.")
    return en


def _conveyor(b, r):
    job = b.job
    en = _drive(b, r, "Conveyor", "HMI_JogConv", "HMI_Manual_Conv", "HMI_ConvSpeedPct",
                "Runs in automatic, or jogs in manual.")
    fb = job.find("AI", "conveyor.*feedback")
    if fb is not None:
        b.tag("P_ConvMinFeedbackPct", "REAL", "Belt feedback below this while running = no motion",
              "PARAM", value=job.analog("conveyor_min_feedback_pct"))
        b.timer("ConvMotionTmr", job.timer("conveyor_motion_check"), "Conveyor motion watchdog")
        r.rung(f"XIC({en})LES({fb.tag},P_ConvMinFeedbackPct){b.ton('ConvMotionTmr')};",
               f"Belt must show motion on {fb.device_tag} once running. ASSUMED: the channel is scaled 0-100 % speed.")
        b.alarm("ALM_ConvNoMotion", "XIC(ConvMotionTmr.DN)", "Conveyor commanded to run but the belt is not moving")


def _focal_lift(b, r):
    job = b.job
    hi = job.need("DI", "focal lift high limit", "focal lift").tag
    lo = job.need("DI", "focal lift low limit", "focal lift").tag
    enables = [p.tag for p in job.points("DO") if p.tag.startswith("VFD_FOC")]
    for name, desc in [("FocalPositioning", "Focal lift moving to its setpoint"),
                       ("FocalMoveUp", "Focal lift direction command: up. Map to the drive once F4 is decided"),
                       ("FocalMoveDown", "Focal lift direction command: down. Map to the drive once F4 is decided"),
                       ("FocalFault", "A focal lift alarm is active")]:
        _status(b, name, desc)
    b.tag("FocalAutoUp", desc="Positioning needs to go up")
    b.tag("FocalAutoDown", desc="Positioning needs to go down")
    b.timer("FocalMoveTmr", job.timer("focal_move_timeout"), "Focal lift move watchdog")

    r.rung("[XIC(HMI_FocalGoToSP) ,XIC(FocalPositioning)]XIC(SafetyOK)XIO(ReinitRequired)XIO(HMI_Manual_Focal)"
           "XIO(FocalInPosition)XIO(FocalFault)XIO(AutoRequest)OTE(FocalPositioning);",
           "Move to setpoint only on an HMI command, never on its own: no unexpected motion.")
    r.rung("XIC(FocalPositioning)LES(FocalError,P_FocalDeadbandNeg)OTE(FocalAutoUp);", "Below setpoint: go up.")
    r.rung("XIC(FocalPositioning)GRT(FocalError,P_FocalDeadband)OTE(FocalAutoDown);", "Above setpoint: go down.")
    r.rung(f"[XIC(FocalAutoUp) ,XIC(HMI_Manual_Focal)XIC(HMI_FocalJogUp)XIO(HMI_FocalJogDown)]XIO({hi})"
           "XIC(SafetyOK)XIO(ReinitRequired)XIO(FocalFault)OTE(FocalMoveUp);",
           "Up: stops at the high limit photoeye.")
    r.rung(f"[XIC(FocalAutoDown) ,XIC(HMI_Manual_Focal)XIC(HMI_FocalJogDown)XIO(HMI_FocalJogUp)]XIO({lo})"
           "XIC(SafetyOK)XIO(ReinitRequired)XIO(FocalFault)OTE(FocalMoveDown);",
           "Down: stops at the low limit photoeye.")
    for en in enables:
        r.rung(f"[XIC(FocalMoveUp) ,XIC(FocalMoveDown)]OTE({en});",
               f"{en}: both screw jacks always run together so the lamp carriage stays level.")
    r.rung(f"[XIC(FocalMoveUp) ,XIC(FocalMoveDown)]{b.ton('FocalMoveTmr')};", "Move watchdog.")
    b.alarm("ALM_FocalTimeout", "XIC(FocalMoveTmr.DN)", "Focal lift did not reach position in time")
    b.alarm("ALM_FocalLimitSensors", f"XIC({hi})XIC({lo})", "Both focal limit photoeyes on at once: sensor fault")
    b.alarm("ALM_FocalSetpointRange", f"[XIC(FocalAutoUp)XIC({hi}) ,XIC(FocalAutoDown)XIC({lo})]",
            "Focal setpoint is beyond a limit photoeye")
    r.rung("[XIC(ALM_FocalTimeout) ,XIC(ALM_FocalLimitSensors) ,XIC(ALM_FocalSetpointRange)]OTE(FocalFault);",
           "Any focal lift alarm stops the lift.")


def _recip(b, r):
    _drive(b, r, "Reciprocator", "HMI_JogRecip", "HMI_Manual_Recip", "HMI_RecipSpeedPct",
           "Traverses the lamp carriage while automatic runs, or jogs in manual.")


def _parts(b, r):
    job = b.job
    pe_in = job.need("DI", "incoming part photoeye", "part tracking").tag
    pe_out = job.need("DI", "outgoing part photoeye", "part tracking").tag
    _status(b, "PartsInMachine", "Parts between the entry and exit photoeyes", "DINT")
    _status(b, "PartsCheckRequired", "A part may be left inside after a safety stop; confirm on the HMI")
    for name in ("PartInOns", "PartOutOns", "PartInEdge", "PartOutEdge"):
        b.tag(name)
    b.timer("JamTmr", job.timer("part_transit_max"), "Time since the last part left while parts are inside")

    r.rung(f"XIC({pe_in})ONS(PartInOns)OTE(PartInEdge);", "A part arrives at the entry photoeye.")
    r.rung(f"XIC({pe_out})ONS(PartOutOns)OTE(PartOutEdge);", "A part leaves at the exit photoeye.")
    r.rung("XIC(PartInEdge)ADD(PartsInMachine,1,PartsInMachine);", "Count in.")
    r.rung("XIC(PartOutEdge)GRT(PartsInMachine,0)SUB(PartsInMachine,1,PartsInMachine);", "Count out.")
    r.rung(f"GRT(PartsInMachine,0)XIC(AutoRunning)XIO(PartOutEdge){b.ton('JamTmr')};",
           "Jam watchdog: restarts every time a part leaves.")
    b.alarm("ALM_Jam", "XIC(JamTmr.DN)", "Part jam: nothing has left the machine in time")
    r.rung("XIC(SafetyLost)GRT(PartsInMachine,0)OTL(PartsCheckRequired);",
           "O&M 4.4: a part left in the machine must be cleared manually before automatic.")
    r.rung("XIC(HMI_PartsCleared)XIO(AutoRequest)[MOV(0,PartsInMachine) ,OTU(PartsCheckRequired)];",
           "Operator confirms the machine is clear.")


def _alarms(b, r):
    _status(b, "Faulted", "At least one alarm is active or unacknowledged")
    b.alarm("ALM_SafetyStop", "XIO(SafetyOK)", "Safety stop: E-stop pressed, door open or safety fault")
    for name, cond, desc in b.alarms:
        r.rung(f"[{cond} ,XIC({name})XIO(HMI_ResetFaults)]OTE({name});",
               f"{desc}. Latches until the cause clears and Reset is pressed.")
    r.rung("[" + " ,".join(f"XIC({a[0]})" for a in b.alarms) + "]OTE(Faulted);", "Any alarm.")


def _indication(b, r):
    job = b.job
    red = job.need("DO", "stack light red", "indication").tag
    amber = job.need("DO", "stack light amber", "indication").tag
    green = job.need("DO", "stack light green", "indication").tag
    horn = job.need("DO", "horn", "indication").tag
    b.tag("Attention", desc="Waiting on something: warm-up, cooldown, part check or horn warning")
    r.rung(f"[XIC(Faulted) ,XIC(ReinitRequired)]OTE({red});", "Red: faulted or safety stop.")
    r.rung("[XIC(CooldownActive) ,XIC(LampsCmd)XIO(LampsReady) ,XIC(PartsCheckRequired) ,XIC(AutoRequest)XIO(AutoRunning)]"
           "OTE(Attention);", "Conditions that make amber flash.")
    r.rung(f"XIO({red})XIO(AutoRunning)[XIO(Attention) ,XIC(Flash)]OTE({amber});",
           "Amber: stopped. Steady when idle, flashing while waiting on something.")
    r.rung(f"XIO({red})XIC(AutoRunning)OTE({green});", "Green: running in automatic.")
    r.rung(f"XIC(AutoRequest)XIO(AutoRunning)OTE({horn});", "Horn: the 3 s warning before first motion.")
