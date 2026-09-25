# Machine Reference — American Ultraviolet FMM3013 "Align Conveyor"

Decoded from the as-built electrical drawing package in
`source_drawings/FMM3013_Align_Conveyor_Electrical_Drawings_B009981.pdf`
(31 sheets, schematic file B009981, version D, as-built 08-24-2026,
engineer C. Pleasant, American Ultraviolet, Lebanon, IN).

This machine is the **quality target** for the drawing pipeline: our generated
packages should look and read like this one.

Not to be confused with the **FirstPass FMM3013** (drawing FP010021, 5069-L306ER with 5069
I/O, in Google Drive under *Panel Business / FMM3013 Package*). That is the business's own
re-engineered design, and the PLC program builder in `firstpass_plc/` is built from its data.

## 1. What the machine is

A UV-curing conveyor: parts ride a conveyor belt under two rows of high-power UV
lamp modules ("Light Hammer" modules). The machine has four electrical enclosures
(EC1–EC4), an HMI touchscreen, a safety system, and a PLC coordinating everything.

## 2. Nameplate / service entrance

| Item | Value |
|---|---|
| Supply | 230 VAC, 3-phase, 50/60 Hz |
| Full load amps | 115 FLA |
| Power | 27 kVA |
| Largest single load | 15 A |
| Main disconnect | CB2001, 150 A breaker disconnect, 2 AWG feeders |
| Serial format | 2606201001 (first serial; sequential) |

Drawing conventions stated on sheet 002: contacts drawn in normal (non-actuated)
position; wire markers at both ends of every wire; ferrules on all wire ends.

## 3. Ethernet network (sheet 010)

All devices on 192.168.1.x / 255.255.255.0, star topology through an Ethernet switch:

| Device | Tag | IP |
|---|---|---|
| PLC processor (CompactLogix, with end cap) | -PLC1002 | 192.168.1.100 |
| Safety controller + safety relay expansion | — | 192.168.1.101 |
| VFD 1 (PowerFlex 525) | — | 192.168.1.10 |
| VFD 2 (PowerFlex 525) | — | 192.168.1.11 |
| Enclosure HMI | -PLC3001 | 192.168.1.20 |
| Ethernet switch | -PLC3006 | (unmanaged) |
| Computer access port (RJ45 on panel) | — | plug in here to program |

## 4. PLC rack (Allen-Bradley CompactLogix, 1769 Compact I/O)

| Slot/Module | Catalog | Function | Sheet |
|---|---|---|---|
| Processor | CompactLogix (1769-L3xER class) | EtherNet/IP CPU | 010 |
| Module 01 | 1769-IQ16 | 16-pt 24 VDC inputs (tag PLC7100) | 070 |
| Module 02 | 1769-OB8 | 8-pt 24 VDC sourcing outputs (PLC7101) | 071 |
| Module 03 | 1769-OB8 | 8-pt outputs, second card | 072 |
| Module 04 | 1769-HSC | High-speed counter (PLC7301) | 073 |
| Module 05 | 1769-IF4XOF2 | 4-ch analog in / 2-ch analog out (PLC7401) | 074–075 |

### Digital inputs (sheet 070, module 1769-IQ16)

| Point | Signal |
|---|---|
| I/00 | Incoming part photoeye (PRS7001) |
| I/01 | Outgoing part photoeye (PRS7002) |
| I/02 | Upper row master "lamp is on" relay (CR3202) |
| I/03 | Upper row slave 1 lamp on (CR3204) |
| I/04 | Upper row slave 2 lamp on (CR3205) |
| I/05 | Upper row master system health relay (CR3201) |
| I/08 | Safety relay 1 + 2 status (CR3112, CR3113 in series) |
| I/09 | Safety controller relay (GC-S1R) |
| I/10 | Focal lift high limit photoeye (PRS7012) |
| I/11 | Focal lift low limit photoeye (PRS7013) |
| I/12 | Lower row master lamp on (CR3208) |
| I/13 | Lower row slave 1 lamp on (CR3210) |
| I/14 | Lower row slave 2 lamp on (CR3211) |
| I/15 | Lower row master system health (CR3207) |

### Digital outputs (sheet 071, first 1769-OB8)

| Point | Signal |
|---|---|
| OUT 2 | Conveyor ON contactor (CR7104 → contactor EOB1088) |
| OUT 3 | Stack light RED relay (CR7105) |
| OUT 4 | Stack light YELLOW relay (CR7108) |
| OUT 5 | Stack light GREEN relay (CR7109) |
| OUT 7 | "Control power on" pilot light (LT7102) |

### High-speed counter (sheet 073, 1769-HSC)

- Channel B0: conveyor motor tach (PRS7303) — belt speed feedback
- Channel A1: focal motor tach 1 (PRS7307)
- Channel B1: focal motor tach 2 (PRS7309)
- Shielded cable required for all tach signals.

### Analog (sheet 074, 1769-IF4XOF2)

- IN 0: DRST-UN signal conditioner (DV7401)
- IN 1: Upper row UV intensity monitor (SEN7404 + UV sensor DV7405, 0–10 V)
- IN 2: Lower row UV intensity monitor (SEN7504 + UV sensor DV7505, 0–10 V)
- OUT 0: speed/level reference sent to drive circuit (to sheet 24xx area)

## 5. Drives and motion

| Drive | Type | Load |
|---|---|---|
| 2 × PowerFlex 525, 5 HP, 230 V (EIB1017) | AC VFD, on EtherNet/IP | Focal drive motors |
| 2 × KBIC-240DS boards (EEB1053) with signal isolator (EXB1176) and tuning resistors | DC SCR drive | Conveyor + recip drive |
| Contactors: 3 × 9 A (EOB1088), 1 × 12 A (EOB1092), overloads (E3B1104) | Motor switching | |

## 6. Safety system

- Safety controller with safety relay expansion unit (networked, 192.168.1.101)
- Keyence safety switch wiring (sheet 050) — guard/door interlocks
- Two safety relays (CR3112/CR3113) monitored by the PLC
- Warning labels: arc flash (NFPA 70E), hazardous voltage, UV light hazard

## 7. Sheet index (the shape of a professional package)

001 Title · 002 Electrical info + labels · 003 Table of contents ·
004 Machine overview · 010 Ethernet network · 020 Incoming power ·
021 DC power supplies · 022–023 Light Hammer modules rows 1–2 ·
024 Conveyor DC drive · 025 Focal drive · 026 Recip drive ·
030–031 DC control wiring · 032/034 PLC input/output interface wiring ·
033 Stack light interfacing · 050 Safety switch wiring ·
051 LightHammer master/slave · 070 PLC inputs · 071–072 PLC outputs ·
073 High-speed counter · 074–075 Analog I/O · 090–093 Panel layouts EC1–EC4
(with BOMs) · 100 Terminal strip details · 900–903 Panel dimensions

**Numbering system worth copying:** sheet 070's wires are 70xx; line numbers on each
sheet map to wire numbers (line 7104 → wire 71041); cross-references say exactly
where a wire continues ("from (3416)", "to (7300)"). This is what makes a package
traceable, and it is easy to generate from data.

## 8. Vendor part number glossary (AUV internal prefixes)

AUV uses internal part numbers (EYB=breakers, EOB=contactors, EUB=terminal/dist
blocks, EEB=drive/safety boards, EXB=electronic modules, E3B=relays/overloads,
E4B=sensors/cables, HXB/HBB=hardware). A real parts database should map these
styles of internal numbers to manufacturer catalog numbers — that is next-steps
item 3 in the pass-off report.
