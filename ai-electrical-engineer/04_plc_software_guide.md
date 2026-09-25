# PLC Software Guide — What to download and how to learn

**Goal:** be able to write real PLC programs, eventually for machines like the
FMM3013 (Allen-Bradley CompactLogix).

## 1. Software for THIS machine (Allen-Bradley CompactLogix)

The FMM3013's PLC is an Allen-Bradley CompactLogix with 1769 Compact I/O. Only one
program can program it:

| Software | Maker | Cost | Runs on | Purpose |
|---|---|---|---|---|
| **Studio 5000 Logix Designer** | Rockwell Automation | ~$1,500–4,000 (edition-dependent) | Windows only | Writes/edits CompactLogix programs. Version installed must support the controller's firmware revision. |
| **FactoryTalk Linx / RSLinx Classic Lite** | Rockwell | Free | Windows | The communication driver — how the laptop finds and connects to the PLC. |

**Connecting to the machine:** plug into the labeled "Computer Access Port" RJ45 on
the panel, set the laptop to a static IP on 192.168.1.x (e.g. 192.168.1.50,
mask 255.255.255.0), and the PLC is at **192.168.1.100**. To *edit* the existing
program you also need the original project file (.ACD) from the builder, or an
upload from the controller if it isn't locked.

**Mac reality check:** none of this runs on macOS. A Windows VM (Parallels) on a
Mac sometimes works but is officially unsupported and flaky. The practical, proven
answer used by working controls engineers: **a cheap used Windows laptop (~$300)
dedicated to PLC work.**

## 2. Free learning path (start tonight, no hardware needed)

Do these in order. Each step is free until step 3's small PLC purchase.

### Step 1 — Do-more Designer (free, has a built-in simulator)
- From AutomationDirect. Download, install on any Windows machine.
- Includes a **software PLC simulator** — you can write ladder logic and watch it
  run with zero hardware.
- First exercises: (1) start/stop motor seal-in circuit, (2) on-delay timer,
  (3) parts counter from a photoeye input. These three patterns are 80% of real
  machine code.

### Step 2 — Connected Components Workbench (free, Rockwell)
- Rockwell's free software for their Micro800 PLC line.
- Gets you fluent in the Allen-Bradley way of doing things (tags, instructions,
  organization), which transfers directly to Studio 5000.

### Step 3 — A real small PLC (~$200–350)
- Buy an Allen-Bradley **Micro820** (programs with the free CCW from step 2).
- Wire real buttons, a relay, a stack light. Physical wiring + programming
  together is where it clicks.

### Step 4 — Studio 5000 (paid, when there's real CompactLogix work)
- Buy when a paying job needs it, not before. Mini edition is the cheapest entry.

## 3. Alternatives worth knowing about

| Software | Cost | Why it matters |
|---|---|---|
| OpenPLC | Free, open source | IEC 61131-3 ladder logic; runtime runs on a Raspberry Pi — cheapest possible physical trainer. |
| CODESYS | Free IDE | The European/industrial standard IDE; many PLC brands are CODESYS-based. Good second ecosystem to know. |
| Click PLC software (AutomationDirect) | Free | Pairs with $100-ish Click PLCs — cheapest real PLC hardware path. |

## 4. Safety rule (non-negotiable)

The FMM3013 is 230 V, 115 A UV equipment with arc-flash labeling. **Never
experiment on a live production machine.** Learn on simulators and bench PLCs;
touch real machines only de-energized or with someone qualified, following
lockout/tagout and NFPA 70E practices.
