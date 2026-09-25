# FMM3013 Align Conveyor - PLC Program Build Report

Build `de59e94e` · 09-25-2026 · generated from `data/` by `build/build_plc.py` · drawing FP010021 Rev A · **NOT FOR COMMISSIONING WITHOUT REVIEW**

## Result

- **Program:** `FMM3013`: 12 routines, 160 rungs, 135 tags, 20 alarms.
- **Gates:** 14 passed, 7 warnings, 0 errors.
- **Sequence tests:** 22 of 22 passed in the ladder simulator.
- **Test strength:** 12 of 12 deliberate bugs were caught by the tests.
- **Questions for the engineer:** 8, listed next. The program is built around each one, but each needs a decision before this machine is commissioned.

Files: `FMM3013_Program.L5X`, `FMM3013_HMI_Tags.csv`, `FMM3013_IO_Map.csv`, `FMM3013_Ladder.md`.

## Questions for the engineer

Found by auditing the job data against itself and against the O&M manual. None stops the build.

1. **F1.** Each of these relays is both a lamp-enable coil and a 'lamp is on' contact: CR3202 (out O:1/00, in I:0/02); CR3204 (out O:1/01, in I:0/03); CR3205 (out O:1/02, in I:0/04); CR3208 (out O:1/03, in I:0/12); CR3210 (out O:1/04, in I:0/13); CR3211 (out O:1/05, in I:0/14). If each is one relay, the input only echoes the PLC's own output and a lamp that fails to strike cannot be detected. Give the lamp-status relays their own tags, driven by each ballast's lamp-on output.
2. **F2.** M-CONV feedback is 'Encoder 1024 PPR' (a pulse device) but io.csv wires it as 4-20 mA analog AI:2/00 FT7300. The BOM carries a 5069-HSC2XOB4 high-speed counter with no points assigned. Either land the encoder on the HSC or specify a pulse-to-4-20 mA converter.
3. **F3.** M-RECIP feedback is 'Prox home' but no home input is in io.csv. The PLC cannot home or position the reciprocator carriage. Spare inputs I:0/06 and I:0/07 are free.
4. **F4.** M-FOCA / M-FOCB (focal lift screw jack) have only run-enable outputs. A lift must go up and down, so direction has to come from somewhere: a second drive input (needs 2 more outputs) or EtherNet/IP control of the PowerFlex 525 (sheets 024-026 say 'Speed ref EtherNet/IP'). The program computes FocalMoveUp / FocalMoveDown ready for either choice.
5. **F5.** Speed references are wired as 0-10 V analog outputs in io.csv, but sheets 024-026 say 'Speed ref EtherNet/IP'. Pick one; the program follows io.csv (analog).
6. **F6.** O&M 4.2: 'Confirm exhaust is running. Lamps will not strike without it.' No exhaust or airflow input exists in io.csv, so the PLC cannot enforce it. Add an airflow switch on spare I:0/06 and describe it with the word 'Exhaust'; the lamp strike permissive picks it up automatically on the next build.
7. **F7.** CR3113 (Safety Relay 2) is not monitored by the PLC. Only CR3112 is. The safety controller's own feedback loop may cover it; confirm on sheet 050.
8. **F8.** O&M 7.3 says each E-stop and door 'HMI annunciates', but the PLC only sees the safety controller's healthy output. It can report 'safety stop', not which device. Naming the device needs the GC-S1R's per-input status (network or extra inputs).

## Warnings

- **D3.** O:1/16 (SPARE16) is channel 16 but 5069-OB16 has 16 channels (0-15). The point does not exist on the hardware; sheet 072 and terminal TS1-10 show it anyway.
- **D6.** CR3202 is both DI I:0/02 'Upper Row Master Lamp Is On' and DO O:1/00 'Upper Row Master Lamp Enable'. PLC tags made unique as CR3202_I, CR3202_O.
- **D6.** CR3204 is both DI I:0/03 'Upper Row Slave 1 Lamp Is On' and DO O:1/01 'Upper Row Slave 1 Lamp Enable'. PLC tags made unique as CR3204_I, CR3204_O.
- **D6.** CR3205 is both DI I:0/04 'Upper Row Slave 2 Lamp Is On' and DO O:1/02 'Upper Row Slave 2 Lamp Enable'. PLC tags made unique as CR3205_I, CR3205_O.
- **D6.** CR3208 is both DI I:0/12 'Lower Row Master Lamp Is On' and DO O:1/03 'Lower Row Master Lamp Enable'. PLC tags made unique as CR3208_I, CR3208_O.
- **D6.** CR3210 is both DI I:0/13 'Lower Row Slave 1 Lamp Is On' and DO O:1/04 'Lower Row Slave 1 Lamp Enable'. PLC tags made unique as CR3210_I, CR3210_O.
- **D6.** CR3211 is both DI I:0/14 'Lower Row Slave 2 Lamp Is On' and DO O:1/05 'Lower Row Slave 2 Lamp Enable'. PLC tags made unique as CR3211_I, CR3211_O.

## What the program does

- The safety function is hardwired through the safety controller. The PLC only monitors it and never overrides it.
- After any safety stop, the operator presses the monitored reset and then re-initialises from the HMI before anything can run.
- Lamps strike from the HMI, one module per second. Each module must report lamp-is-on and each row its health, or an alarm is raised. After lamp off, a 5 minute cooldown blocks re-strike.
- Automatic needs: safety healthy, re-initialised, no alarms, no subsystem in manual, focal lift at its commanded position between the limits, lamps warmed up, and no unconfirmed part left in the machine.
- Auto start sounds the horn for 3 s before the conveyor and reciprocator move. Cycle stop keeps the conveyor running until the last part clears the exit photoeye.
- Parts are counted in at the entry photoeye and out at the exit photoeye. A part left inside after a safety stop must be cleared and confirmed on the HMI before automatic is allowed again.

## Program outline

| Routine | Rungs | Purpose |
|---|---:|---|
| `R00_Main` | 11 | Calls every routine once per scan, in order. |
| `R01_MapInputs` | 16 | Copy module inputs to named tags |
| `R02_Safety` | 7 | Safety status, re-initialise, reset lamp, flasher |
| `R03_Lamps` | 33 | UV lamp strike, cooldown, warm-up, intensity |
| `R04_Modes` | 17 | Automatic permissive, cycle start and cycle stop |
| `R05_Conveyor` | 8 | Conveyor drive run and speed |
| `R06_FocalLift` | 9 | Focal lift positioning, both screw jacks together |
| `R07_Recip` | 7 | Reciprocator run and speed |
| `R08_Parts` | 7 | Part tracking, jam detection, part-left check |
| `R09_Alarms` | 21 | Latching alarms and the Faulted summary |
| `R10_Indication` | 5 | Stack light and horn |
| `R99_MapOutputs` | 19 | Copy named tags to module outputs |

Every rung, with its comment, is in `FMM3013_Ladder.md`.

## Sequence tests

Each test runs the generated ladder in `build/ladder_sim.py` against a plant model of the machine. On every scan of every test the simulator also checks four invariants: nothing moves or lights without SafetyOK; at most one stack light is on; both focal screw jacks are commanded together; the horn and conveyor never run at the same time.

| Test | What it proves | Result |
|---|---|---|
| `test_auto_refused_when_focal_lift_not_in_position` | O&M 4.1: automatic needs the focal lift at its commanded position. | pass |
| `test_auto_refused_while_a_subsystem_is_in_manual` | O&M 4.1: automatic is refused while any subsystem is in manual. | pass |
| `test_auto_start_horn_three_seconds_before_motion` | O&M 4.2: the horn sounds 3 s before first motion, then conveyor and recip run, green on. | pass |
| `test_belt_not_moving_raises_alarm` | Conveyor commanded to run but the encoder shows no motion raises an alarm. | pass |
| `test_conveyor_jog_only_in_manual` | Jog runs the conveyor at jog speed in manual, and does nothing outside manual. | pass |
| `test_cooldown_blocks_restrike_for_five_minutes` | After lamps off, a re-strike is refused until the 5 minute cooldown ends. | pass |
| `test_cycle_stop_runs_until_the_last_part_clears` | O&M 4.3: cycle stop keeps the conveyor running until the last part clears the exit eye. | pass |
| `test_estop_while_running_drops_everything_and_needs_reinit` | O&M 4.4: E-stop drops lamps and drives at once; after release it needs reset + HMI re-init. | pass |
| `test_focal_jog_stops_at_high_limit` | In manual, jogging up stops at the high limit photoeye. | pass |
| `test_focal_lift_moves_down_with_both_jacks` | Going down, both screw jacks run together and stop at setpoint. | pass |
| `test_focal_lift_moves_to_setpoint_on_command_only` | The focal lift never moves on its own; on command it goes to setpoint and stops. | pass |
| `test_focal_lift_stuck_times_out` | A lift that is commanded but does not move faults after the move timeout. | pass |
| `test_focal_setpoint_beyond_limit_alarms` | A setpoint above the high limit stops at the photoeye and raises an alarm. | pass |
| `test_intensity_setpoint_scaled_to_volts` | Intensity 75 % gives 7.5 V; out-of-range entries are clamped to 0-10 V. | pass |
| `test_jam_stops_the_machine` | A part that never reaches the exit raises a jam alarm and automatic stops. | pass |
| `test_lamp_arc_lost_while_running_stops_auto` | A lamp that goes out in production raises 'arc lost' and automatic stops. | pass |
| `test_lamp_that_never_strikes_raises_its_alarm` | A module that never reports lamp-is-on raises its own strike alarm and blocks auto. | pass |
| `test_lamps_strike_one_per_second_in_order` | Lamps strike one module per second, in lamps.csv order, then warm up. | pass |
| `test_no_jog_during_safety_stop` | Manual jogs of every drive are dead while the safety circuit is open. | pass |
| `test_part_left_after_estop_must_be_confirmed` | O&M 4.4: a part left inside after a safety stop blocks automatic until cleared on the HMI. | pass |
| `test_power_up_is_safe_and_red` | Power up with the safety circuit not reset: nothing moves, red on, reset lamp flashes. | pass |
| `test_reset_clears_red_to_amber` | Monitored reset, then HMI reset: red clears, amber shows idle, reset lamp stops. | pass |

### Test strength

Each bug below was put into the program on purpose, one at a time. A test must fail for each.

| Deliberate bug | Tests that failed |
|---|---:|
| conveyor ignores safety | 1 |
| horn 1 s not 3 s | 1 |
| no cooldown lockout | 1 |
| auto allowed in manual | 1 |
| focal ignores high limit | 1 |
| jacks A/B not paired | 1 |
| cycle stop drops at once | 1 |
| no re-init after e-stop | 1 |
| strike all lamps at once | 2 |
| jam alarm never latches | 1 |
| green and amber together | 7 |
| part-left check skipped | 1 |

## Assumptions to confirm at commissioning

From `data/plc.yaml`. Change the value there and rebuild; do not edit the ladder.

| Setting | Value and note |
|---|---|
| `lamp_strike_timeout` | 10000 - ASSUMED - lamp-is-on must make within 10 s of enable |
| `lamp_strike_stagger` | 1000 - ASSUMED - one module per second to limit strike inrush |
| `lamp_warmup` | 60000 - ASSUMED - O&M says "allow the warm-up period", no figure given |
| `row_health_timeout` | 10000 - ASSUMED - row system-health relay must make within 10 s |
| `part_transit_max` | 30000 - ASSUMED - longest time between exits before a jam is declared |
| `focal_move_timeout` | 20000 - ASSUMED - longest focal lift move before a fault |
| `conveyor_motion_check` | 3000 - ASSUMED - belt feedback must show motion within 3 s of run |
| `focal_deadband_mm` | 1.0 - ASSUMED - focal lift "in position" band, +/- mm |
| `conveyor_min_feedback_pct` | 5.0 - ASSUMED - FT7300 below this while running = no motion |
| `jog_speed_pct` | 20.0 - ASSUMED - manual jog speed, percent of full speed |

## Loading it into Studio 5000

The L5X is a **program** import. It carries the program, its tags and routines; the controller and I/O modules are set up once by hand.

1. New project, controller **5069-L306ER**, named `FMM3013_PLC`.
2. Add the local 5069 modules in these slots:

   | Slot | Module | Use |
   |---:|---|---|
   | 1 | 5069-IB16 | DI per io.csv |
   | 2 | 5069-OB16 | DO per io.csv |
   | 3 | 5069-IF8 | AI per io.csv |
   | 4 | 5069-OF4 | AO per io.csv |
   | 5 | 5069-HSC2XOB4 | on the BOM (sheet 090), no points in io.csv - see F2 |

   If a module tag differs from the `module_channel` column in `FMM3013_IO_Map.csv`, only `R01_MapInputs` and `R99_MapOutputs` need to change.
3. In the Controller Organizer, right-click **MainTask**, choose **Add > Import Program**, pick `FMM3013_Program.L5X`.
4. Verify the controller. The program gates check tags, rung syntax and double coils the way Studio 5000's verify does, but only a real verify proves it. Then download to a **bench PLC or the emulator first**, never straight to the machine.
5. HMI tags for the PanelView are in `FMM3013_HMI_Tags.csv` (shortcut name `PLC`).

This L5X follows Rockwell's published L5X structure but has not yet been imported into a real Studio 5000. The first import is the acceptance test; report any import message back and the generator gets fixed, not the file.

## All checks

| Code | Level | Check |
|---|---|---|
| D3 | WARN | O:1/16 (SPARE16) is channel 16 but 5069-OB16 has 16 channels (0-15). The point does not exist on the hardware; sheet 072 and terminal TS1-10 show it anyway. |
| D5 | OK | GC-S1R -> GC_S1R (Logix tag names allow letters, digits, _) |
| D5 | OK | VFD-CONV -> VFD_CONV (Logix tag names allow letters, digits, _) |
| D5 | OK | VFD-FOCA -> VFD_FOCA (Logix tag names allow letters, digits, _) |
| D5 | OK | VFD-FOCB -> VFD_FOCB (Logix tag names allow letters, digits, _) |
| D5 | OK | VFD-RECIP -> VFD_RECIP (Logix tag names allow letters, digits, _) |
| D6 | WARN | CR3202 is both DI I:0/02 'Upper Row Master Lamp Is On' and DO O:1/00 'Upper Row Master Lamp Enable'. PLC tags made unique as CR3202_I, CR3202_O. |
| D6 | WARN | CR3204 is both DI I:0/03 'Upper Row Slave 1 Lamp Is On' and DO O:1/01 'Upper Row Slave 1 Lamp Enable'. PLC tags made unique as CR3204_I, CR3204_O. |
| D6 | WARN | CR3205 is both DI I:0/04 'Upper Row Slave 2 Lamp Is On' and DO O:1/02 'Upper Row Slave 2 Lamp Enable'. PLC tags made unique as CR3205_I, CR3205_O. |
| D6 | WARN | CR3208 is both DI I:0/12 'Lower Row Master Lamp Is On' and DO O:1/03 'Lower Row Master Lamp Enable'. PLC tags made unique as CR3208_I, CR3208_O. |
| D6 | WARN | CR3210 is both DI I:0/13 'Lower Row Slave 1 Lamp Is On' and DO O:1/04 'Lower Row Slave 1 Lamp Enable'. PLC tags made unique as CR3210_I, CR3210_O. |
| D6 | WARN | CR3211 is both DI I:0/14 'Lower Row Slave 2 Lamp Is On' and DO O:1/05 'Lower Row Slave 2 Lamp Enable'. PLC tags made unique as CR3211_I, CR3211_O. |
| F1 | FINDING | Each of these relays is both a lamp-enable coil and a 'lamp is on' contact: CR3202 (out O:1/00, in I:0/02); CR3204 (out O:1/01, in I:0/03); CR3205 (out O:1/02, in I:0/04); CR3208 (out O:1/03, in I:0/12); CR3210 (out O:1/04, in I:0/13); CR3211 (out O:1/05, in I:0/14). If each is one relay, the input only echoes the PLC's own output and a lamp that fails to strike cannot be detected. Give the lamp-status relays their own tags, driven by each ballast's lamp-on output. |
| F2 | FINDING | M-CONV feedback is 'Encoder 1024 PPR' (a pulse device) but io.csv wires it as 4-20 mA analog AI:2/00 FT7300. The BOM carries a 5069-HSC2XOB4 high-speed counter with no points assigned. Either land the encoder on the HSC or specify a pulse-to-4-20 mA converter. |
| F3 | FINDING | M-RECIP feedback is 'Prox home' but no home input is in io.csv. The PLC cannot home or position the reciprocator carriage. Spare inputs I:0/06 and I:0/07 are free. |
| F4 | FINDING | M-FOCA / M-FOCB (focal lift screw jack) have only run-enable outputs. A lift must go up and down, so direction has to come from somewhere: a second drive input (needs 2 more outputs) or EtherNet/IP control of the PowerFlex 525 (sheets 024-026 say 'Speed ref EtherNet/IP'). The program computes FocalMoveUp / FocalMoveDown ready for either choice. |
| F5 | FINDING | Speed references are wired as 0-10 V analog outputs in io.csv, but sheets 024-026 say 'Speed ref EtherNet/IP'. Pick one; the program follows io.csv (analog). |
| F6 | FINDING | O&M 4.2: 'Confirm exhaust is running. Lamps will not strike without it.' No exhaust or airflow input exists in io.csv, so the PLC cannot enforce it. Add an airflow switch on spare I:0/06 and describe it with the word 'Exhaust'; the lamp strike permissive picks it up automatically on the next build. |
| F7 | FINDING | CR3113 (Safety Relay 2) is not monitored by the PLC. Only CR3112 is. The safety controller's own feedback loop may cover it; confirm on sheet 050. |
| F8 | FINDING | O&M 7.3 says each E-stop and door 'HMI annunciates', but the PLC only sees the safety controller's healthy output. It can report 'safety stop', not which device. Naming the device needs the GC-S1R's per-input status (network or extra inputs). |
| P1 | OK | 160 rungs parse as Logix neutral text |
| P2 | OK | every tag the rungs use is defined |
| P3 | OK | no double coils (96 OTE targets, each written once) |
| P4 | OK | all 19 live outputs are driven by the logic |
| P5 | OK | all 16 live inputs are used by the logic |
| P6 | OK | all 11 routines are called exactly once from R00_Main |
| P7 | OK | all 35 live points map to their module channel (Local:1..4) |
| P8 | OK | all 16 timers have a preset above zero and one timer instruction each |
| P9 | OK | all 135 tag and 12 routine names are legal Logix names |

The safety function is not in this program. It is hardwired through the safety controller (sheet 050) and must be validated per O&M section 7.3 regardless of anything here.
