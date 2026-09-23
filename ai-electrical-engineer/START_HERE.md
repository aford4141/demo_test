# START HERE — AI Electrical Engineer Project

**Owner:** Alan Ford (aford4141@gmail.com)
**Last updated:** September 23, 2026
**Status:** Planning / early build

## What this folder is

This is the shared knowledge base for building an **AI electrical engineer** for Alan's
panel business. Any person or AI assistant (LLM) picking up this project should read this
folder first. Everything here is written to stand alone — you do not need any prior chat
history to understand it.

## The mission, in one paragraph

Alan wants an AI system that works like the best electrical engineer he's ever had:
it takes a machine description and produces complete, professional electrical drawing
packages (schematics, panel layouts, BOMs, wire lists) with almost no manual effort —
the same quality as the real-world example package in `source_drawings/`. Alongside
that, Alan is learning PLC programming so the business can also deliver working PLC
programs, not just drawings.

## Reading order

| File | What it tells you |
|---|---|
| `START_HERE.md` | This file. Orientation. |
| `01_pass_off_report.md` | Full pass-off report: everything learned and decided so far, and what to do next. |
| `02_machine_reference_FMM3013.md` | Decoded reference for the example machine (American Ultraviolet FMM3013 "Align Conveyor") — specs, network map, PLC I/O map, parts. |
| `03_llm_and_hardware_plan.md` | Can a local LLM do this job? Model sizes, Mac/PC hardware tiers, and the recommended setup. |
| `04_plc_software_guide.md` | Exactly what software to download for PLC programming, and a free learning path. |
| `05_drawing_pipeline_plan.md` | The architecture for generating drawings automatically (the "brain + drafter" pipeline) and next build steps. |
| `source_drawings/` | The real as-built drawing package (31 sheets, PDF) used as the quality target. |

## Key decisions already made (do not re-litigate without Alan)

1. **Architecture:** The LLM is the *engineer's brain* (decides circuits, sizes wire,
   assigns I/O, outputs structured data). Deterministic code is the *drafter* (renders
   DXF/PDF sheets from templates). No LLM draws schematics directly as images.
2. **Brains:** A frontier hosted model (Claude) is the engineer for now. Local models
   are optional helpers, not the engineer. See `03_llm_and_hardware_plan.md`.
3. **PLC platform for the example machine:** Allen-Bradley CompactLogix →
   Studio 5000 Logix Designer. Free learning starts with a simulator first.
   See `04_plc_software_guide.md`.

## Open items

- The drawing **templates** ("Brad files") were started in a separate chat and are not
  yet in this folder. **Next assistant: ask Alan for them and add them here** under a
  `templates/` subfolder so everything lives in one place.
- The Panel Business folder on Google Drive already holds a **library of real drawing
  packages** (FMM3013 Package, FMM3020, FMM3021, FMM3050, FMM3060, FPJ-0001 through
  FPJ-0003). Only FMM3013 has been decoded so far — the others are additional
  reference material and future decode targets.
- Nothing from the drawing pipeline is built yet — `05_drawing_pipeline_plan.md` has
  the first concrete build step.

## Where this lives

- Google Drive: `Panel Business / AI Electrical Engineer /` (working copy Alan uses)
- GitHub: `aford4141/demo_test`, folder `ai-electrical-engineer/` (version-controlled copy)

If you update one copy, mirror the change to the other and bump the
"Last updated" date above.
