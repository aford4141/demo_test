# FMM3013 Align Conveyor - ladder listing

Program `FMM3013`, 12 routines, 160 rungs, 135 tags. Generated from data/ by build/gen_plc.py; this is the same rung text that is in the L5X.

## R00_Main

Calls every routine once per scan, in order.

**0.** Copy module inputs to named tags

```
JSR(R01_MapInputs,0);
```

**1.** Safety status, re-initialise, reset lamp, flasher

```
JSR(R02_Safety,0);
```

**2.** UV lamp strike, cooldown, warm-up, intensity

```
JSR(R03_Lamps,0);
```

**3.** Automatic permissive, cycle start and cycle stop

```
JSR(R04_Modes,0);
```

**4.** Conveyor drive run and speed

```
JSR(R05_Conveyor,0);
```

**5.** Focal lift positioning, both screw jacks together

```
JSR(R06_FocalLift,0);
```

**6.** Reciprocator run and speed

```
JSR(R07_Recip,0);
```

**7.** Part tracking, jam detection, part-left check

```
JSR(R08_Parts,0);
```

**8.** Latching alarms and the Faulted summary

```
JSR(R09_Alarms,0);
```

**9.** Stack light and horn

```
JSR(R10_Indication,0);
```

**10.** Copy named tags to module outputs

```
JSR(R99_MapOutputs,0);
```

## R01_MapInputs

Copy module inputs to named tags

**0.** I:0/00 PRS7001 Incoming Part Photoeye - wire 70011, TS1-1, +EC1, sheet 070

```
XIC(Local:1:I.Pt00.Data)OTE(PRS7001);
```

**1.** I:0/01 PRS7002 Outgoing Part Photoeye - wire 70021, TS1-2, +EC1, sheet 070

```
XIC(Local:1:I.Pt01.Data)OTE(PRS7002);
```

**2.** I:0/02 CR3202 Upper Row Master Lamp Is On - wire 70031, TS2-1, +EC2, sheet 070

```
XIC(Local:1:I.Pt02.Data)OTE(CR3202_I);
```

**3.** I:0/03 CR3204 Upper Row Slave 1 Lamp Is On - wire 70041, TS2-2, +EC2, sheet 070

```
XIC(Local:1:I.Pt03.Data)OTE(CR3204_I);
```

**4.** I:0/04 CR3205 Upper Row Slave 2 Lamp Is On - wire 70051, TS2-3, +EC2, sheet 070

```
XIC(Local:1:I.Pt04.Data)OTE(CR3205_I);
```

**5.** I:0/05 CR3201 Upper Row System Health - wire 70061, TS2-4, +EC2, sheet 070

```
XIC(Local:1:I.Pt05.Data)OTE(CR3201);
```

**6.** I:0/08 CR3112 Safety Relay 1 Monitor - wire 70091, TS4-1, +EC4, sheet 070

```
XIC(Local:1:I.Pt08.Data)OTE(CR3112);
```

**7.** I:0/09 GC-S1R Safety Controller Healthy - wire 70101, TS4-2, +EC4, sheet 070

```
XIC(Local:1:I.Pt09.Data)OTE(GC_S1R);
```

**8.** I:0/10 PRS7012 Focal Lift High Limit Photoeye - wire 70111, TS4-3, +EC4, sheet 070

```
XIC(Local:1:I.Pt10.Data)OTE(PRS7012);
```

**9.** I:0/11 PRS7013 Focal Lift Low Limit Photoeye - wire 70121, TS4-4, +EC4, sheet 070

```
XIC(Local:1:I.Pt11.Data)OTE(PRS7013);
```

**10.** I:0/12 CR3208 Lower Row Master Lamp Is On - wire 70131, TS3-1, +EC3, sheet 070

```
XIC(Local:1:I.Pt12.Data)OTE(CR3208_I);
```

**11.** I:0/13 CR3210 Lower Row Slave 1 Lamp Is On - wire 70141, TS3-2, +EC3, sheet 070

```
XIC(Local:1:I.Pt13.Data)OTE(CR3210_I);
```

**12.** I:0/14 CR3211 Lower Row Slave 2 Lamp Is On - wire 70151, TS3-3, +EC3, sheet 070

```
XIC(Local:1:I.Pt14.Data)OTE(CR3211_I);
```

**13.** I:0/15 CR3207 Lower Row System Health - wire 70161, TS3-4, +EC3, sheet 070

```
XIC(Local:1:I.Pt15.Data)OTE(CR3207);
```

**14.** AI:2/00 FT7300 Conveyor Encoder Feedback - wire 73011, TS1-11, +EC1, sheet 073

```
MOV(Local:3:I.Ch00.Data,FT7300);
```

**15.** AI:2/01 PT7301 Focal Height Position - wire 73021, TS4-10, +EC4, sheet 073

```
MOV(Local:3:I.Ch01.Data,PT7301);
```

## R02_Safety

Safety status, re-initialise, reset lamp, flasher

**0.** The safety function is hardwired through the safety controller (sheet 050). The PLC only watches it: healthy output on AND safety relay 1 picked up.

```
XIC(GC_S1R)XIC(CR3112)OTE(SafetyOK);
```

**1.** One-scan pulse when the safety circuit drops: E-stop, door opened or safety fault.

```
XIO(SafetyOK)XIC(SafetyOK_Prev)OTE(SafetyLost);
```

**2.** O&M 4.4: after a safety stop, press the monitored reset, then re-initialise from the HMI. Nothing runs until both are done.

```
[XIC(SafetyLost) ,XIC(ReinitRequired) [XIO(HMI_ResetFaults) ,XIO(SafetyOK)]]OTE(ReinitRequired);
```

**3.** Remember SafetyOK for the edge above.

```
XIC(SafetyOK)OTE(SafetyOK_Prev);
```

**4.** Free-running flasher timer.

```
XIO(FlashTmr.DN)TON(FlashTmr,1000,0);
```

**5.** Flash is on for the first half of each period.

```
LES(FlashTmr.ACC,500)OTE(Flash);
```

**6.** The illuminated reset button PB7015 flashes while the safety circuit needs a reset.

```
XIO(SafetyOK)XIC(Flash)OTE(CR3115);
```

## R03_Lamps

UV lamp strike, cooldown, warm-up, intensity

**0.** Lamps on from the HMI. Refused during cooldown. Dropped by lamps-off or any safety stop (the safety contactor has already removed lamp power).

```
[XIC(HMI_LampsOn)XIO(CooldownActive) ,XIC(LampsCmd)]XIC(SafetyOK)XIO(ReinitRequired)XIO(HMI_LampsOff)OTE(LampsCmd);
```

**1.** Cooldown: the timer runs for 5 minutes after the lamps go off.

```
XIC(LampsCmd)TOF(CooldownTmr,300000,0);
```

**2.** Do not re-strike a hot lamp (O&M 4.3). ASSUMED: medium-pressure lamps cannot hot-restrike; confirm against the LightHammer manual.

```
XIC(CooldownTmr.DN)XIO(LampsCmd)OTE(CooldownActive);
```

**3.** Strike sequence timer: one module every 1 s to limit inrush.

```
XIC(LampsCmd)TON(StrikeSeqTmr,5000,0);
```

**4.** UV1-1 Upper Master (LightHammer 10 Mk II, 6.0 kW): enable at +0 s.

```
XIC(LampsCmd)GEQ(StrikeSeqTmr.ACC,0)OTE(CR3202_O);
```

**5.** UV1-1 strike watchdog: enabled but lamp-is-on not made.

```
XIC(CR3202_O)XIO(CR3202_I)TON(UV1_1_StrikeTmr,10000,0);
```

**6.** UV1-1 remembers it was lit, so losing the arc can be told apart from never striking.

```
[XIC(CR3202_I) ,XIC(UV1_1_WasOn)]XIC(CR3202_O)OTE(UV1_1_WasOn);
```

**7.** UV1-2 Upper Slave 1 (LightHammer 10 Mk II, 6.0 kW): enable at +1 s.

```
XIC(LampsCmd)GEQ(StrikeSeqTmr.ACC,1000)OTE(CR3204_O);
```

**8.** UV1-2 strike watchdog: enabled but lamp-is-on not made.

```
XIC(CR3204_O)XIO(CR3204_I)TON(UV1_2_StrikeTmr,10000,0);
```

**9.** UV1-2 remembers it was lit, so losing the arc can be told apart from never striking.

```
[XIC(CR3204_I) ,XIC(UV1_2_WasOn)]XIC(CR3204_O)OTE(UV1_2_WasOn);
```

**10.** UV1-3 Upper Slave 2 (LightHammer 10 Mk II, 6.0 kW): enable at +2 s.

```
XIC(LampsCmd)GEQ(StrikeSeqTmr.ACC,2000)OTE(CR3205_O);
```

**11.** UV1-3 strike watchdog: enabled but lamp-is-on not made.

```
XIC(CR3205_O)XIO(CR3205_I)TON(UV1_3_StrikeTmr,10000,0);
```

**12.** UV1-3 remembers it was lit, so losing the arc can be told apart from never striking.

```
[XIC(CR3205_I) ,XIC(UV1_3_WasOn)]XIC(CR3205_O)OTE(UV1_3_WasOn);
```

**13.** UV2-1 Lower Master (LightHammer 10 Mk II, 6.0 kW): enable at +3 s.

```
XIC(LampsCmd)GEQ(StrikeSeqTmr.ACC,3000)OTE(CR3208_O);
```

**14.** UV2-1 strike watchdog: enabled but lamp-is-on not made.

```
XIC(CR3208_O)XIO(CR3208_I)TON(UV2_1_StrikeTmr,10000,0);
```

**15.** UV2-1 remembers it was lit, so losing the arc can be told apart from never striking.

```
[XIC(CR3208_I) ,XIC(UV2_1_WasOn)]XIC(CR3208_O)OTE(UV2_1_WasOn);
```

**16.** UV2-2 Lower Slave 1 (LightHammer 10 Mk II, 6.0 kW): enable at +4 s.

```
XIC(LampsCmd)GEQ(StrikeSeqTmr.ACC,4000)OTE(CR3210_O);
```

**17.** UV2-2 strike watchdog: enabled but lamp-is-on not made.

```
XIC(CR3210_O)XIO(CR3210_I)TON(UV2_2_StrikeTmr,10000,0);
```

**18.** UV2-2 remembers it was lit, so losing the arc can be told apart from never striking.

```
[XIC(CR3210_I) ,XIC(UV2_2_WasOn)]XIC(CR3210_O)OTE(UV2_2_WasOn);
```

**19.** UV2-3 Lower Slave 2 (LightHammer 10 Mk II, 6.0 kW): enable at +5 s.

```
XIC(LampsCmd)GEQ(StrikeSeqTmr.ACC,5000)OTE(CR3211_O);
```

**20.** UV2-3 strike watchdog: enabled but lamp-is-on not made.

```
XIC(CR3211_O)XIO(CR3211_I)TON(UV2_3_StrikeTmr,10000,0);
```

**21.** UV2-3 remembers it was lit, so losing the arc can be told apart from never striking.

```
[XIC(CR3211_I) ,XIC(UV2_3_WasOn)]XIC(CR3211_O)OTE(UV2_3_WasOn);
```

**22.** Upper row system-health relay must make once the lamps are commanded on.

```
XIC(LampsCmd)XIO(CR3201)TON(UpperHealthTmr,10000,0);
```

**23.** Lower row system-health relay must make once the lamps are commanded on.

```
XIC(LampsCmd)XIO(CR3207)TON(LowerHealthTmr,10000,0);
```

**24.** All modules lit and both rows healthy.

```
XIC(LampsCmd)XIC(CR3202_I)XIC(CR3204_I)XIC(CR3205_I)XIC(CR3208_I)XIC(CR3210_I)XIC(CR3211_I)XIC(CR3201)XIC(CR3207)OTE(AllLampsOn);
```

**25.** Warm-up before product (O&M 4.2 step 6).

```
XIC(AllLampsOn)TON(WarmUpTmr,60000,0);
```

**26.** Lamps ready for automatic.

```
XIC(WarmUpTmr.DN)OTE(LampsReady);
```

**27.** Limit HMI_UpperIntensityPct to 100.

```
GRT(HMI_UpperIntensityPct,100.0)MOV(100.0,HMI_UpperIntensityPct);
```

**28.** Limit HMI_UpperIntensityPct to 0.

```
LES(HMI_UpperIntensityPct,0.0)MOV(0.0,HMI_UpperIntensityPct);
```

**29.** Upper row intensity: 0-100 % -> 0-10 V on SC7401. ASSUMED: the output channel is configured in volts.

```
MUL(HMI_UpperIntensityPct,0.1,SC7401);
```

**30.** Limit HMI_LowerIntensityPct to 100.

```
GRT(HMI_LowerIntensityPct,100.0)MOV(100.0,HMI_LowerIntensityPct);
```

**31.** Limit HMI_LowerIntensityPct to 0.

```
LES(HMI_LowerIntensityPct,0.0)MOV(0.0,HMI_LowerIntensityPct);
```

**32.** Lower row intensity: 0-100 % -> 0-10 V on SC7402. ASSUMED: the output channel is configured in volts.

```
MUL(HMI_LowerIntensityPct,0.1,SC7402);
```

## R04_Modes

Automatic permissive, cycle start and cycle stop

**0.** Automatic is refused while any subsystem is in manual (O&M 4.1).

```
[XIC(HMI_Manual_Lamps) ,XIC(HMI_Manual_Conv) ,XIC(HMI_Manual_Focal) ,XIC(HMI_Manual_Recip)]OTE(AnyManual);
```

**1.** Focal position error.

```
SUB(PT7301,HMI_FocalHeightSP,FocalError);
```

**2.** Lower edge of the in-position band.

```
MUL(P_FocalDeadband,-1.0,P_FocalDeadbandNeg);
```

**3.** O&M 4.1 condition 3: focal lift at its commanded position, between the high and low limit photoeyes.

```
LIM(P_FocalDeadbandNeg,FocalError,P_FocalDeadband)XIO(PRS7012)XIO(PRS7013)OTE(FocalInPosition);
```

**4.** Everything automatic needs (O&M 4.1 plus lamps warmed up and no part left in the machine).

```
XIC(SafetyOK)XIO(ReinitRequired)XIO(Faulted)XIO(AnyManual)XIC(FocalInPosition)XIC(LampsReady)XIO(PartsCheckRequired)OTE(AutoPermissive);
```

**5.** Reason codes for the HMI, lowest priority first; the last true one wins.

```
MOV(0,AutoBlockReason);
```

**6.** 5: lamps not lit and warmed up.

```
XIO(LampsReady)MOV(5,AutoBlockReason);
```

**7.** 4: focal lift not at its setpoint.

```
XIO(FocalInPosition)MOV(4,AutoBlockReason);
```

**8.** 6: a part may be left in the machine.

```
XIC(PartsCheckRequired)MOV(6,AutoBlockReason);
```

**9.** 3: a subsystem is in manual; the HMI shows which.

```
XIC(AnyManual)MOV(3,AutoBlockReason);
```

**10.** 2: an alarm is active.

```
XIC(Faulted)MOV(2,AutoBlockReason);
```

**11.** 1: safety stop or not re-initialised.

```
[XIO(SafetyOK) ,XIC(ReinitRequired)]MOV(1,AutoBlockReason);
```

**12.** Cycle stop (O&M 4.3): stop taking product, keep running until the last part clears.

```
[XIC(HMI_AutoStop)XIC(AutoRequest) ,XIC(CycleStopping)XIC(AutoRequest)]OTE(CycleStopping);
```

**13.** Machine is empty.

```
XIC(CycleStopping)EQU(PartsInMachine,0)OTE(CycleStopDone);
```

**14.** Automatic request. Drops on cycle stop completion or the moment any permissive is lost.

```
[XIC(HMI_AutoStart)XIO(CycleStopping) ,XIC(AutoRequest)]XIC(AutoPermissive)XIO(CycleStopDone)OTE(AutoRequest);
```

**15.** Horn sounds before first motion.

```
XIC(AutoRequest)TON(HornPrewarnTmr,3000,0);
```

**16.** Motion allowed after the horn.

```
XIC(AutoRequest)XIC(HornPrewarnTmr.DN)OTE(AutoRunning);
```

## R05_Conveyor

Conveyor drive run and speed

**0.** M-CONV Conveyor belt drive (PowerFlex 525 25B-B012N104) run enable, sheet 072. Runs in automatic, or jogs in manual.

```
[XIC(AutoRunning) ,XIC(HMI_Manual_Conv)XIC(HMI_JogConv)XIO(AutoRequest)]XIC(SafetyOK)XIO(ReinitRequired)OTE(VFD_CONV);
```

**1.** Limit HMI_ConvSpeedPct to 100.

```
GRT(HMI_ConvSpeedPct,100.0)MOV(100.0,HMI_ConvSpeedPct);
```

**2.** Limit HMI_ConvSpeedPct to 0.

```
LES(HMI_ConvSpeedPct,0.0)MOV(0.0,HMI_ConvSpeedPct);
```

**3.** Automatic speed from the HMI recipe.

```
XIC(AutoRunning)MOV(HMI_ConvSpeedPct,ConveyorSpeedCmdPct);
```

**4.** Jog speed in manual.

```
XIO(AutoRunning)MOV(P_JogSpeedPct,ConveyorSpeedCmdPct);
```

**5.** Zero reference when not running.

```
XIO(VFD_CONV)MOV(0.0,ConveyorSpeedCmdPct);
```

**6.** Speed reference SC7403: 0-100 % -> 0-10 V.

```
MUL(ConveyorSpeedCmdPct,0.1,SC7403);
```

**7.** Belt must show motion on FT7300 once running. ASSUMED: the channel is scaled 0-100 % speed.

```
XIC(VFD_CONV)LES(FT7300,P_ConvMinFeedbackPct)TON(ConvMotionTmr,3000,0);
```

## R06_FocalLift

Focal lift positioning, both screw jacks together

**0.** Move to setpoint only on an HMI command, never on its own: no unexpected motion.

```
[XIC(HMI_FocalGoToSP) ,XIC(FocalPositioning)]XIC(SafetyOK)XIO(ReinitRequired)XIO(HMI_Manual_Focal)XIO(FocalInPosition)XIO(FocalFault)XIO(AutoRequest)OTE(FocalPositioning);
```

**1.** Below setpoint: go up.

```
XIC(FocalPositioning)LES(FocalError,P_FocalDeadbandNeg)OTE(FocalAutoUp);
```

**2.** Above setpoint: go down.

```
XIC(FocalPositioning)GRT(FocalError,P_FocalDeadband)OTE(FocalAutoDown);
```

**3.** Up: stops at the high limit photoeye.

```
[XIC(FocalAutoUp) ,XIC(HMI_Manual_Focal)XIC(HMI_FocalJogUp)XIO(HMI_FocalJogDown)]XIO(PRS7012)XIC(SafetyOK)XIO(ReinitRequired)XIO(FocalFault)OTE(FocalMoveUp);
```

**4.** Down: stops at the low limit photoeye.

```
[XIC(FocalAutoDown) ,XIC(HMI_Manual_Focal)XIC(HMI_FocalJogDown)XIO(HMI_FocalJogUp)]XIO(PRS7013)XIC(SafetyOK)XIO(ReinitRequired)XIO(FocalFault)OTE(FocalMoveDown);
```

**5.** VFD_FOCA: both screw jacks always run together so the lamp carriage stays level.

```
[XIC(FocalMoveUp) ,XIC(FocalMoveDown)]OTE(VFD_FOCA);
```

**6.** VFD_FOCB: both screw jacks always run together so the lamp carriage stays level.

```
[XIC(FocalMoveUp) ,XIC(FocalMoveDown)]OTE(VFD_FOCB);
```

**7.** Move watchdog.

```
[XIC(FocalMoveUp) ,XIC(FocalMoveDown)]TON(FocalMoveTmr,20000,0);
```

**8.** Any focal lift alarm stops the lift.

```
[XIC(ALM_FocalTimeout) ,XIC(ALM_FocalLimitSensors) ,XIC(ALM_FocalSetpointRange)]OTE(FocalFault);
```

## R07_Recip

Reciprocator run and speed

**0.** M-RECIP Reciprocator carriage (PowerFlex 525 25B-B8P0N104) run enable, sheet 072. Traverses the lamp carriage while automatic runs, or jogs in manual.

```
[XIC(AutoRunning) ,XIC(HMI_Manual_Recip)XIC(HMI_JogRecip)XIO(AutoRequest)]XIC(SafetyOK)XIO(ReinitRequired)OTE(VFD_RECIP);
```

**1.** Limit HMI_RecipSpeedPct to 100.

```
GRT(HMI_RecipSpeedPct,100.0)MOV(100.0,HMI_RecipSpeedPct);
```

**2.** Limit HMI_RecipSpeedPct to 0.

```
LES(HMI_RecipSpeedPct,0.0)MOV(0.0,HMI_RecipSpeedPct);
```

**3.** Automatic speed from the HMI recipe.

```
XIC(AutoRunning)MOV(HMI_RecipSpeedPct,ReciprocatorSpeedCmdPct);
```

**4.** Jog speed in manual.

```
XIO(AutoRunning)MOV(P_JogSpeedPct,ReciprocatorSpeedCmdPct);
```

**5.** Zero reference when not running.

```
XIO(VFD_RECIP)MOV(0.0,ReciprocatorSpeedCmdPct);
```

**6.** Speed reference SC7404: 0-100 % -> 0-10 V.

```
MUL(ReciprocatorSpeedCmdPct,0.1,SC7404);
```

## R08_Parts

Part tracking, jam detection, part-left check

**0.** A part arrives at the entry photoeye.

```
XIC(PRS7001)ONS(PartInOns)OTE(PartInEdge);
```

**1.** A part leaves at the exit photoeye.

```
XIC(PRS7002)ONS(PartOutOns)OTE(PartOutEdge);
```

**2.** Count in.

```
XIC(PartInEdge)ADD(PartsInMachine,1,PartsInMachine);
```

**3.** Count out.

```
XIC(PartOutEdge)GRT(PartsInMachine,0)SUB(PartsInMachine,1,PartsInMachine);
```

**4.** Jam watchdog: restarts every time a part leaves.

```
GRT(PartsInMachine,0)XIC(AutoRunning)XIO(PartOutEdge)TON(JamTmr,30000,0);
```

**5.** O&M 4.4: a part left in the machine must be cleared manually before automatic.

```
XIC(SafetyLost)GRT(PartsInMachine,0)OTL(PartsCheckRequired);
```

**6.** Operator confirms the machine is clear.

```
XIC(HMI_PartsCleared)XIO(AutoRequest)[MOV(0,PartsInMachine) ,OTU(PartsCheckRequired)];
```

## R09_Alarms

Latching alarms and the Faulted summary

**0.** UV1-1 failed to strike. Latches until the cause clears and Reset is pressed.

```
[XIC(UV1_1_StrikeTmr.DN) ,XIC(ALM_UV1_1_StrikeFail)XIO(HMI_ResetFaults)]OTE(ALM_UV1_1_StrikeFail);
```

**1.** UV1-1 arc lost while enabled. Latches until the cause clears and Reset is pressed.

```
[XIC(CR3202_O)XIC(UV1_1_WasOn)XIO(CR3202_I) ,XIC(ALM_UV1_1_LampLost)XIO(HMI_ResetFaults)]OTE(ALM_UV1_1_LampLost);
```

**2.** UV1-2 failed to strike. Latches until the cause clears and Reset is pressed.

```
[XIC(UV1_2_StrikeTmr.DN) ,XIC(ALM_UV1_2_StrikeFail)XIO(HMI_ResetFaults)]OTE(ALM_UV1_2_StrikeFail);
```

**3.** UV1-2 arc lost while enabled. Latches until the cause clears and Reset is pressed.

```
[XIC(CR3204_O)XIC(UV1_2_WasOn)XIO(CR3204_I) ,XIC(ALM_UV1_2_LampLost)XIO(HMI_ResetFaults)]OTE(ALM_UV1_2_LampLost);
```

**4.** UV1-3 failed to strike. Latches until the cause clears and Reset is pressed.

```
[XIC(UV1_3_StrikeTmr.DN) ,XIC(ALM_UV1_3_StrikeFail)XIO(HMI_ResetFaults)]OTE(ALM_UV1_3_StrikeFail);
```

**5.** UV1-3 arc lost while enabled. Latches until the cause clears and Reset is pressed.

```
[XIC(CR3205_O)XIC(UV1_3_WasOn)XIO(CR3205_I) ,XIC(ALM_UV1_3_LampLost)XIO(HMI_ResetFaults)]OTE(ALM_UV1_3_LampLost);
```

**6.** UV2-1 failed to strike. Latches until the cause clears and Reset is pressed.

```
[XIC(UV2_1_StrikeTmr.DN) ,XIC(ALM_UV2_1_StrikeFail)XIO(HMI_ResetFaults)]OTE(ALM_UV2_1_StrikeFail);
```

**7.** UV2-1 arc lost while enabled. Latches until the cause clears and Reset is pressed.

```
[XIC(CR3208_O)XIC(UV2_1_WasOn)XIO(CR3208_I) ,XIC(ALM_UV2_1_LampLost)XIO(HMI_ResetFaults)]OTE(ALM_UV2_1_LampLost);
```

**8.** UV2-2 failed to strike. Latches until the cause clears and Reset is pressed.

```
[XIC(UV2_2_StrikeTmr.DN) ,XIC(ALM_UV2_2_StrikeFail)XIO(HMI_ResetFaults)]OTE(ALM_UV2_2_StrikeFail);
```

**9.** UV2-2 arc lost while enabled. Latches until the cause clears and Reset is pressed.

```
[XIC(CR3210_O)XIC(UV2_2_WasOn)XIO(CR3210_I) ,XIC(ALM_UV2_2_LampLost)XIO(HMI_ResetFaults)]OTE(ALM_UV2_2_LampLost);
```

**10.** UV2-3 failed to strike. Latches until the cause clears and Reset is pressed.

```
[XIC(UV2_3_StrikeTmr.DN) ,XIC(ALM_UV2_3_StrikeFail)XIO(HMI_ResetFaults)]OTE(ALM_UV2_3_StrikeFail);
```

**11.** UV2-3 arc lost while enabled. Latches until the cause clears and Reset is pressed.

```
[XIC(CR3211_O)XIC(UV2_3_WasOn)XIO(CR3211_I) ,XIC(ALM_UV2_3_LampLost)XIO(HMI_ResetFaults)]OTE(ALM_UV2_3_LampLost);
```

**12.** Upper row lamp system not healthy. Latches until the cause clears and Reset is pressed.

```
[XIC(UpperHealthTmr.DN) ,XIC(ALM_UpperRowHealth)XIO(HMI_ResetFaults)]OTE(ALM_UpperRowHealth);
```

**13.** Lower row lamp system not healthy. Latches until the cause clears and Reset is pressed.

```
[XIC(LowerHealthTmr.DN) ,XIC(ALM_LowerRowHealth)XIO(HMI_ResetFaults)]OTE(ALM_LowerRowHealth);
```

**14.** Conveyor commanded to run but the belt is not moving. Latches until the cause clears and Reset is pressed.

```
[XIC(ConvMotionTmr.DN) ,XIC(ALM_ConvNoMotion)XIO(HMI_ResetFaults)]OTE(ALM_ConvNoMotion);
```

**15.** Focal lift did not reach position in time. Latches until the cause clears and Reset is pressed.

```
[XIC(FocalMoveTmr.DN) ,XIC(ALM_FocalTimeout)XIO(HMI_ResetFaults)]OTE(ALM_FocalTimeout);
```

**16.** Both focal limit photoeyes on at once: sensor fault. Latches until the cause clears and Reset is pressed.

```
[XIC(PRS7012)XIC(PRS7013) ,XIC(ALM_FocalLimitSensors)XIO(HMI_ResetFaults)]OTE(ALM_FocalLimitSensors);
```

**17.** Focal setpoint is beyond a limit photoeye. Latches until the cause clears and Reset is pressed.

```
[[XIC(FocalAutoUp)XIC(PRS7012) ,XIC(FocalAutoDown)XIC(PRS7013)] ,XIC(ALM_FocalSetpointRange)XIO(HMI_ResetFaults)]OTE(ALM_FocalSetpointRange);
```

**18.** Part jam: nothing has left the machine in time. Latches until the cause clears and Reset is pressed.

```
[XIC(JamTmr.DN) ,XIC(ALM_Jam)XIO(HMI_ResetFaults)]OTE(ALM_Jam);
```

**19.** Safety stop: E-stop pressed, door open or safety fault. Latches until the cause clears and Reset is pressed.

```
[XIO(SafetyOK) ,XIC(ALM_SafetyStop)XIO(HMI_ResetFaults)]OTE(ALM_SafetyStop);
```

**20.** Any alarm.

```
[XIC(ALM_UV1_1_StrikeFail) ,XIC(ALM_UV1_1_LampLost) ,XIC(ALM_UV1_2_StrikeFail) ,XIC(ALM_UV1_2_LampLost) ,XIC(ALM_UV1_3_StrikeFail) ,XIC(ALM_UV1_3_LampLost) ,XIC(ALM_UV2_1_StrikeFail) ,XIC(ALM_UV2_1_LampLost) ,XIC(ALM_UV2_2_StrikeFail) ,XIC(ALM_UV2_2_LampLost) ,XIC(ALM_UV2_3_StrikeFail) ,XIC(ALM_UV2_3_LampLost) ,XIC(ALM_UpperRowHealth) ,XIC(ALM_LowerRowHealth) ,XIC(ALM_ConvNoMotion) ,XIC(ALM_FocalTimeout) ,XIC(ALM_FocalLimitSensors) ,XIC(ALM_FocalSetpointRange) ,XIC(ALM_Jam) ,XIC(ALM_SafetyStop)]OTE(Faulted);
```

## R10_Indication

Stack light and horn

**0.** Red: faulted or safety stop.

```
[XIC(Faulted) ,XIC(ReinitRequired)]OTE(LT7109);
```

**1.** Conditions that make amber flash.

```
[XIC(CooldownActive) ,XIC(LampsCmd)XIO(LampsReady) ,XIC(PartsCheckRequired) ,XIC(AutoRequest)XIO(AutoRunning)]OTE(Attention);
```

**2.** Amber: stopped. Steady when idle, flashing while waiting on something.

```
XIO(LT7109)XIO(AutoRunning)[XIO(Attention) ,XIC(Flash)]OTE(LT7108);
```

**3.** Green: running in automatic.

```
XIO(LT7109)XIC(AutoRunning)OTE(LT7107);
```

**4.** Horn: the 3 s warning before first motion.

```
XIC(AutoRequest)XIO(AutoRunning)OTE(HN7110);
```

## R99_MapOutputs

Copy named tags to module outputs

**0.** O:1/00 CR3202 Upper Row Master Lamp Enable - wire 71011, TS2-5, +EC2, sheet 071

```
XIC(CR3202_O)OTE(Local:2:O.Pt00.Data);
```

**1.** O:1/01 CR3204 Upper Row Slave 1 Lamp Enable - wire 71021, TS2-6, +EC2, sheet 071

```
XIC(CR3204_O)OTE(Local:2:O.Pt01.Data);
```

**2.** O:1/02 CR3205 Upper Row Slave 2 Lamp Enable - wire 71031, TS2-7, +EC2, sheet 071

```
XIC(CR3205_O)OTE(Local:2:O.Pt02.Data);
```

**3.** O:1/03 CR3208 Lower Row Master Lamp Enable - wire 71041, TS3-5, +EC3, sheet 071

```
XIC(CR3208_O)OTE(Local:2:O.Pt03.Data);
```

**4.** O:1/04 CR3210 Lower Row Slave 1 Lamp Enable - wire 71051, TS3-6, +EC3, sheet 071

```
XIC(CR3210_O)OTE(Local:2:O.Pt04.Data);
```

**5.** O:1/05 CR3211 Lower Row Slave 2 Lamp Enable - wire 71061, TS3-7, +EC3, sheet 071

```
XIC(CR3211_O)OTE(Local:2:O.Pt05.Data);
```

**6.** O:1/06 LT7107 Stack Light Green - Running - wire 71071, TS1-5, +EC1, sheet 071

```
XIC(LT7107)OTE(Local:2:O.Pt06.Data);
```

**7.** O:1/07 LT7108 Stack Light Amber - Warning - wire 71081, TS1-6, +EC1, sheet 071

```
XIC(LT7108)OTE(Local:2:O.Pt07.Data);
```

**8.** O:1/08 LT7109 Stack Light Red - Faulted - wire 71091, TS1-7, +EC1, sheet 071

```
XIC(LT7109)OTE(Local:2:O.Pt08.Data);
```

**9.** O:1/09 HN7110 Warning Horn - wire 71101, TS1-8, +EC1, sheet 071

```
XIC(HN7110)OTE(Local:2:O.Pt09.Data);
```

**10.** O:1/10 VFD-CONV Conveyor Drive Run Enable - wire 72011, TS4-5, +EC4, sheet 072

```
XIC(VFD_CONV)OTE(Local:2:O.Pt10.Data);
```

**11.** O:1/11 VFD-FOCA Focal Lift A Run Enable - wire 72021, TS4-6, +EC4, sheet 072

```
XIC(VFD_FOCA)OTE(Local:2:O.Pt11.Data);
```

**12.** O:1/12 VFD-FOCB Focal Lift B Run Enable - wire 72031, TS4-7, +EC4, sheet 072

```
XIC(VFD_FOCB)OTE(Local:2:O.Pt12.Data);
```

**13.** O:1/13 VFD-RECIP Reciprocator Run Enable - wire 72041, TS4-8, +EC4, sheet 072

```
XIC(VFD_RECIP)OTE(Local:2:O.Pt13.Data);
```

**14.** O:1/14 CR3115 Safety Circuit Reset Lamp - wire 72051, TS4-9, +EC4, sheet 072

```
XIC(CR3115)OTE(Local:2:O.Pt14.Data);
```

**15.** AO:3/00 SC7401 Upper Row Lamp Intensity Setpoint - wire 74011, TS2-8, +EC2, sheet 074

```
MOV(SC7401,Local:4:O.Ch00.Data);
```

**16.** AO:3/01 SC7402 Lower Row Lamp Intensity Setpoint - wire 74021, TS3-8, +EC3, sheet 074

```
MOV(SC7402,Local:4:O.Ch01.Data);
```

**17.** AO:3/02 SC7403 Conveyor Speed Reference - wire 74031, TS4-11, +EC4, sheet 074

```
MOV(SC7403,Local:4:O.Ch02.Data);
```

**18.** AO:3/03 SC7404 Reciprocator Speed Reference - wire 74041, TS4-12, +EC4, sheet 074

```
MOV(SC7404,Local:4:O.Ch03.Data);
```
