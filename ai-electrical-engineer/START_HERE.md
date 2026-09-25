# START HERE — AI Electrical Engineer Project

**Owner:** A. Ford (aford4141@gmail.com)
**Last updated:** September 25, 2026
**Status:** Drawing generator (FirstPass Builder) working; PLC program builder working in simulation

## What this folder is

This is the shared knowledge base for building an **AI electrical engineer** for the
panel business. Any person or AI assistant (LLM) picking up this project should read this
folder first. Everything here is written to stand alone — you do not need any prior chat
history to understand it.

## The mission, in one paragraph

Build an AI system that works like the best electrical engineer the owner has ever had.
It takes a machine description and produces complete, professional electrical drawing
packages (schematics, panel layouts, BOMs, wire lists) and working PLC programs, with
almost no manual effort. The quality bar is a real as-built package from the industry
(`source_drawings/`).

## Reading order

| File | What it tells you |
|---|---|
| `START_HERE.md` | This file. Orientation. |
| `01_pass_off_report.md` | Pass-off report: everything learned and decided so far, and what to do next. |
| `02_machine_reference_FMM3013.md` | The American Ultraviolet FMM3013 as-built drawings, decoded: specs, network, PLC I/O map, parts. |
| `03_llm_and_hardware_plan.md` | Can a local LLM do this job? Model sizes, Mac/PC hardware tiers, and the recommended setup. |
| `04_plc_software_guide.md` | What software to download for PLC programming, and a free learning path. |
| `05_drawing_pipeline_plan.md` | The "brain + drafter" architecture for drawings, and where the FirstPass Builder fits. |
| `firstpass_plc/README.md` | **The PLC program builder:** job data in, tested Studio 5000 program out. First job: FMM3013. |
| `firstpass_plc/plc/FMM3013_PLC_Report.md` | The FMM3013 program build report: results, tests, and 8 design questions for the engineer. |
| `source_drawings/` | The AUV as-built FMM3013 drawing package (31-sheet scan). |

## Two FMM3013 designs — do not mix them up

1. **AUV as-built** (`source_drawings/`, decoded in `02_...`): American Ultraviolet schematic
   B009981, CompactLogix with **1769** I/O. This is the reference: what a real, built machine looks like.
2. **FirstPass FMM3013** (Google Drive, *Panel Business / FMM3013 Package*): the business's own
   re-engineered design for customer Cardinal IG, drawing FP010021 Rev A, CompactLogix
   **5069-L306ER** with 5069 I/O. Its `data/` folder is the single source of truth, and the
   drawings, O&M manual, cost model and now the PLC program are all generated from it.

## Key decisions already made (do not re-litigate without the owner)

1. **Architecture:** The LLM is the engineer's brain. It reads, audits and writes the rules.
   Deterministic Python renders everything: drawings, manuals, PLC programs. No LLM draws
   schematics or types ladder by hand.
2. **One data source per job.** Everything is generated from the job's `data/` folder.
   Nothing is typed twice. Gates stop a build that fails its own checks.
3. **Brains:** A frontier hosted model (Claude) is the engineer for now. Local models are
   optional helpers. See `03_llm_and_hardware_plan.md`.
4. **PLC platform:** Allen-Bradley CompactLogix, programmed in Studio 5000 Logix Designer
   (Windows). The program builder emits L5X files that Studio 5000 imports.

## Where things live

| What | Where |
|---|---|
| FirstPass Builder (drawings, O&M manual, costing) | Google Drive: *Panel Business / FMM3013 Package* (`data/`, `build/`, `reference/`, `MANIFEST.txt`) |
| FirstPass roadmap | Google Drive: *FirstPass Builder Roadmap.pdf* |
| This knowledge base + PLC builder (working copy) | Google Drive: *Panel Business / AI Electrical Engineer* |
| This knowledge base + PLC builder (version-controlled) | GitHub `aford4141/demo_test`, folder `ai-electrical-engineer/` |

If you update one copy, mirror the change to the other and bump "Last updated" above.

## Open items

- **Answer the 8 design questions** in `firstpass_plc/plc/FMM3013_PLC_Report.md`: six relays
  that are both input and output, no exhaust interlock input, a focal lift with no direction
  output, an encoder on an analog input, and others. Fix them in the FirstPass `data/` so the
  drawings, manual and program all change together.
- **First Studio 5000 import** of `FMM3013_Program.L5X`, on a bench PLC or the emulator. This is
  the acceptance test for the L5X format.
- The other drawing packages in Drive (FMM3020, 3021, 3050, 3060, FPJ-0001 through 0003) are
  future jobs for the same builders.
