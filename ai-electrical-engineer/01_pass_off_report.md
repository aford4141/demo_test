# Pass-Off Report — AI Electrical Engineer Project

**Date:** September 23, 2026
**Prepared for:** Alan Ford and any AI assistant continuing this work
**Read `START_HERE.md` first for orientation.**

---

## 1. What this project is trying to do

Build an AI-driven system for Alan's panel business that can:

1. **Produce complete electrical drawing packages** (title sheets, power distribution,
   control wiring, PLC I/O sheets, panel layouts with BOMs, terminal strip details)
   at the quality of a professional controls house — with minimal manual effort.
2. **Program PLCs** — starting with Alan learning the tools, working toward the
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

## 5. What has NOT been done yet (next steps, in order)

1. **Collect the "Brad files"** (drawing templates started in another chat) into this
   folder under `templates/`.
2. **Build the first renderer:** Python + ezdxf script that takes a small JSON wire
   list and outputs one title-blocked schematic sheet matching the AUV sheet format.
   (Detailed spec in `05_drawing_pipeline_plan.md`.)
3. **Build the parts database:** start a spreadsheet of real parts used in FMM3013
   (breakers, contactors, terminal blocks, VFDs — see the BOM extracts in
   `02_machine_reference_FMM3013.md`) with manufacturer part numbers and prices.
4. **PLC learning start:** download Do-more Designer, run the built-in simulator,
   write a first start/stop ladder program (guide in `04_plc_software_guide.md`).
5. Longer term: define a standard "machine description" input format so any LLM can
   take a customer request → structured machine description → drawing package.

## 6. How to use this folder as an AI assistant

- Treat `02_machine_reference_FMM3013.md` as ground truth about the example machine;
  it was extracted from the actual as-built drawings.
- When Alan asks for drawings or PLC help, follow the decided architecture — don't
  reopen settled decisions (listed in `START_HERE.md`) without new information.
- Keep language simple and practical. Alan is hands-on and learning as he goes;
  explain terms the first time they appear.
- When you add or learn something important, write it into these files (and mirror
  between Google Drive and GitHub) so the next assistant starts where you finished.
