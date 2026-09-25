# FirstPass PLC Program Builder

Generates the PLC program for a FirstPass job from the same `data/` files that
generate its drawings and O&M manual. It tests the program in a ladder simulator
before handing over a Studio 5000 import file. The first job is the **FMM3013
Align Conveyor**.

This is step 7 of the FirstPass Builder roadmap ("L5X export... Studio 5000
imports L5X natively"). It follows FirstPass rules: one data source, nothing typed
twice, deterministic Python, and gates that stop the build.

## Run it

```
python3 build/build_plc.py            # gates, generate, test, report  (~15 s)
python3 build/build_plc.py --mutate   # also prove the tests can fail  (~3 min)
python3 build/test_plc_fmm3013.py     # just the sequence tests
```

Needs Python 3.9+ and PyYAML (`pip3 install pyyaml`), the same as FirstPass.
Nothing else, and no PLC.

## What comes out (`plc/`)

| File | What it is |
|---|---|
| `FMM3013_PLC_Report.md` | **Start here.** Result, questions for the engineer, tests, assumptions, how to load it into Studio 5000 |
| `FMM3013_Program.L5X` | The program, for Studio 5000: *Add > Import Program* |
| `FMM3013_Ladder.md` | Every rung with its comment, readable without Studio 5000 |
| `FMM3013_IO_Map.csv` | Every I/O point: address, module channel, PLC tag, wire, terminal, sheet |
| `FMM3013_HMI_Tags.csv` | Tags the PanelView reads and writes |

## How it works

```
data/ (io.csv, lamps.csv, drives.csv, safety.csv, project.yaml, plc.yaml)
   |
   |  plc_job.py      load the job, turn io.csv into Logix tags, data gates, audit
   v
   |  plc_rules.py    the sequence of operation, as rung templates  <- the AI-written part
   v
   |  verify_plc.py   program gates: syntax, undefined tags, double coils,
   |                  undriven outputs, unused inputs, I/O mapping, names
   v
   |  ladder_sim.py   run the ladder scan by scan against a plant model
   |  test_plc_fmm3013.py   22 tests, one per piece of the O&M sequence
   |  mutate_plc.py   plant 12 deliberate bugs; the tests must catch every one
   v
   gen_plc.py        L5X + ladder listing + I/O map + HMI tags  ->  plc/
```

**Where the AI fits.** An AI wrote `plc_rules.py` by reading the O&M manual and
the drawings, and it audits the data (`plc_job.audit`). The generator itself is
plain, deterministic code: the same data always gives the same program. That
matches the FirstPass roadmap: "the LLM's job stays reading, auditing, and
building the rules."

**Change the machine by changing data, never the ladder.** A new lamp in
`lamps.csv`, a drive in `drives.csv`, or a timer in `plc.yaml` means you rebuild.
If a rule is wrong, fix `plc_rules.py` and add a test that would have caught it.

## What the FMM3013 test run found

The audit turned up 8 design questions in the FMM3013 data and 1 hardware error.
All of them are in the report. The most important:

- **O:1/16 does not exist.** `io.csv` lists 17 outputs on a 16-point 5069-OB16
  (sheets 071-072, terminal TS1-10). It's a spare, but the drawing shows a wire
  landing on a point that is not there.
- **Six relays are both output and input.** CR3202, CR3204, CR3205, CR3208,
  CR3210 and CR3211 are each the lamp-enable coil *and* the "lamp is on" contact.
  If each is one relay, the PLC reads back its own output and can never see a
  lamp fail to strike.
- **No exhaust interlock input.** The O&M says lamps must not strike without
  exhaust, but no input exists. Put an airflow switch on spare I:0/06 and describe
  it as "Exhaust"; the rules pick it up on the next build (tested).
- **The focal lift has no direction.** There's only a run enable per screw jack.
  It needs two more outputs, or EtherNet/IP drive control.
- **Encoder and HSC mismatch.** The conveyor's 1024 PPR encoder is listed as a
  4-20 mA analog input while the HSC module on the BOM has nothing on it.

## Status and limits

- **Tested in simulation only.** The L5X has not yet been imported into a real
  Studio 5000. The first import is the acceptance test. Report any import message
  back so the generator gets fixed, not the file.
- **5069 module tag paths** (`Local:1:I.Pt00.Data`, `Local:3:I.Ch00.Data`) are the
  standard 5069 format. If a firmware's paths differ, only the two mapping routines
  change.
- **The safety function is not in this program.** It is hardwired through the
  Keyence GC-S1R (sheet 050). The PLC only monitors it. Validate per O&M 7.3.
- **Archetype.** The rules are written for the UV conveyor family: lamp rows,
  conveyor, focal lift, reciprocator. FMM3020/3021/3050/3060 should reuse most of
  them; each new archetype needs its own rules and tests.

## Using it with the FirstPass package in Google Drive

The FirstPass Builder lives in Drive at *Panel Business / FMM3013 Package*
(`data/`, `build/`). To run this against the live data there, copy the `.py` files
from `build/` here into that `build/` folder, and `data/plc.yaml` into `data/`. Then
run `python3 build/build_plc.py`. `data/` here is a copy of that folder's
`io.csv`, `drives.csv`, `lamps.csv`, `safety.csv` and `project.yaml` as of
08-28-2026.
