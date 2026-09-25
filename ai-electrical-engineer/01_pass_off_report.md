# Pass-Off Report — AI Electrical Engineer Project

**Date:** September 23, 2026 (updated September 25, 2026 — see section 7)
**Prepared for:** A. Ford (the owner) and any AI assistant continuing this work
**Read `START_HERE.md` first for orientation.**

---

## 1. What this project is trying to do

Build an AI-driven system for the panel business that can:

1. **Produce complete electrical drawing packages** (title sheets, power distribution,
   control wiring, PLC I/O sheets, panel layouts with BOMs, terminal strip details)
   at the quality of a professional controls house — with minimal manual effort.
2. **Program PLCs** — starting with the owner learning the tools, working toward the
   business delivering real PLC programs.

The quality target is a real as-built package: American Ultraviolet's **FMM3013
"Align Conveyor"** (31 sheets, in `source_drawings/`). It was analyzed sheet by sheet
and decoded in `02_machine_reference_FMM3013.md`.

## 2. What was done in this session

- Read all 31 sheets of the FMM3013 electrical package and extracted the machine's
  full electrical story: 230 V 3-phase 115 FLA service, two rows of UV "Light Hammer"
  lamp modules, PowerFlex 525 VFDs, a DC conveyor drive, a safety controller, an HMI,
  and an Allen-Bradley CompactLogix PLC with 1769-series I/O on an EtherNet/IP network.
- Answered the core question: **can a local LLM on a Mac Mini be the electrical
  engineer?** Short answer: no single local model can, at any price — but the right
  architecture gets there. Full analysis with hardware tiers in
  `03_llm_and_hardware_plan.md`.
- Identified the exact PLC software needed for this class of machine and a free
  learning path. See `04_plc_software_guide.md`.
- Defined the drawing-generation architecture and the first build step. See
  `05_drawing_pipeline_plan.md`.

## 3. The three big findings

### Finding 1 — Drawings are data, not art

A package like FMM3013 is structured data rendered onto templates: wire numbers,
cross-references, I/O maps, BOM tables, title blocks. So the system splits cleanly:

- **Brain (LLM):** decides the circuit, sizes wire and breakers, assigns PLC I/O,
  writes wire lists and BOMs as structured data (JSON/CSV).
- **Drafter (plain code):** a Python renderer turns that data into DXF/PDF sheets
  with the company title block. Deterministic, runs on any computer, never
  hallucinates.

No LLM at any size draws good schematics directly as images. Do not try.

### Finding 2 — The engineer brain should be a frontier hosted model (for now)

- A Mac Mini (16–64 GB) runs models up to roughly the 70B class — useful as a
  drafting assistant, not trustworthy for engineering judgment (wire sizing, breaker
  coordination, code compliance).
- The best money-can-buy local box (Mac Studio M3 Ultra 512 GB, ~$9,500) runs
  DeepSeek-class 671B models at maybe 85–90% of frontier quality on text, and weaker
  on reading drawings.
- A frontier hosted model (Claude) costs cents to a few dollars per drawing package.
  It would take years of heavy use to spend $9,500 on API calls.

**Recommendation:** frontier model as the engineer, existing Mac Mini as the drafting
department (renderer, parts database, templates). Buy big local hardware only if
drawings must never leave the building.

### Finding 3 — The PLC world runs on Windows, and the entry path is free

The FMM3013 uses Allen-Bradley CompactLogix, programmed only by **Studio 5000 Logix
Designer** (Windows-only, ~$1,500+). But learning starts free: **Do-more Designer**
(free, built-in simulator, no hardware needed), then **Connected Components
Workbench** (free, Rockwell) with a ~$250 Micro820 PLC, then Studio 5000 when working
on real CompactLogix machines. A cheap used Windows laptop (~$300) is the practical
tool; Mac virtualization of these programs is unreliable.

## 4. Decisions made (with reasons)

| Decision | Reason |
|---|---|
| LLM generates data; code renders drawings | Rendering must be exact and repeatable; LLM image output is not. |
| Frontier hosted model over local hardware purchase | Better quality where it matters (judgment, reading drawings), tiny marginal cost. |
| Keep local Mac Mini in the loop | Runs the renderer, templates, and parts database; no AI needed for that half. |
| Learn PLC on simulators before touching real machines | The example machine is 230 V / 115 A UV equipment — never experiment live. |

## 5. Next steps, in order

Section 5 of the first version of this report said to build a drawing renderer from
scratch. That was wrong: it had already been built in another chat as the **FirstPass
Builder** (Google Drive, *Panel Business / FMM3013 Package*). It generates the FMM3013
drawings, O&M manual and cost model from one `data/` folder. See section 7 for what that
changed.

1. **Answer the 8 design questions** in `firstpass_plc/plc/FMM3013_PLC_Report.md` and fix
   them in the FirstPass `data/` folder, so the drawings, manual and PLC program change together.
2. **First Studio 5000 import** of `firstpass_plc/plc/FMM3013_Program.L5X` on a bench PLC or
   the Studio 5000 emulator. This is the acceptance test for the L5X format.
3. **Seed the parts library** (FirstPass roadmap step "NOW"): a Kirby quote or ProposalWorks
   export gives real prices, DIN widths and watts.
4. **PLC learning:** download Do-more Designer, run its simulator, write a start/stop rung
   (see `04_plc_software_guide.md`). Then read `FMM3013_Ladder.md`; every rung there has a
   plain-English comment.
5. **Next machine:** run the PLC builder on another package in Drive (FMM3020/3021/3050/3060)
   once its FirstPass `data/` exists. Most of the rules should carry over.

## 6. How to use this folder as an AI assistant

- Treat `02_machine_reference_FMM3013.md` as ground truth about the example machine;
  it was extracted from the actual as-built drawings.
- When the owner asks for drawings or PLC help, follow the decided architecture — don't
  reopen settled decisions (listed in `START_HERE.md`) without new information.
- Keep language simple and practical. The owner is hands-on and learning as they go;
  explain terms the first time they appear.
- When you add or learn something important, write it into these files (and mirror
  between Google Drive and GitHub) so the next assistant starts where you finished.

## 7. Update — September 25, 2026: PLC program builder, tested on the FMM3013

**What exists now.** `firstpass_plc/` is a PLC program builder that plugs into FirstPass.
It reads the same job `data/` files as the drawings (`io.csv`, `lamps.csv`, `drives.csv`,
`safety.csv`, `project.yaml`) plus one new file, `plc.yaml`, for timers and setpoints.
From those it produces a Studio 5000 L5X program, a ladder listing, an I/O map, an HMI tag
list and a build report. Run it with `python3 build/build_plc.py`.

**How it was tested on the FMM3013.**
- The ladder is run scan by scan in a simulator (`build/ladder_sim.py`) against a plant model
  of the machine.
- 22 tests each check one piece of the O&M sequence of operation: strike, cooldown, horn,
  E-stop recovery, cycle stop, part-left check, jam, focal lift, jog, and so on.
- On every scan the simulator also checks safety invariants, for example "nothing moves or
  lights without SafetyOK".
- To prove the tests are real, 12 bugs were planted in the program one at a time. The tests
  caught all 12. The first run caught only 10, which exposed two missing tests; both were added.

**Result:** 160 rungs, 135 tags, 20 alarms. All gates pass and 22 of 22 tests pass. The L5X
has not yet been imported into a real Studio 5000.

**What the test run found in the FMM3013 design** (details in the report):
- O:1/16 is listed on a 16-point output card that only has points 0-15.
- Six relays (CR3202 and others) are each both a lamp-enable output and a "lamp is on" input,
  so a lamp that fails to strike may be undetectable.
- The O&M manual requires an exhaust interlock, but no exhaust input exists.
- The focal lift has run enables but no direction output.
- The conveyor encoder is listed as a 4-20 mA analog input while the high-speed counter card
  on the BOM has nothing on it.
- The drawings say "speed ref EtherNet/IP" but `io.csv` wires analog speed references.
- The reciprocator has no home input.
- The PLC cannot tell the HMI which E-stop or door tripped.

**Where the AI fits** (matches the FirstPass roadmap): an AI read the O&M manual and drawings,
wrote the rules (`build/plc_rules.py`) and the audit, and wrote the tests. The generator itself
is deterministic. Change the data, rebuild, and the program, tests and report follow.

