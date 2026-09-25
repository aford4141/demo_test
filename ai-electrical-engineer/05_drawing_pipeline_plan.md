# Drawing Pipeline Plan — How drawings get generated

> **Status, September 25, 2026: this pipeline already exists.** It is the **FirstPass
> Builder**, built in another chat. It lives in Google Drive under *Panel Business / FMM3013
> Package* (`data/` and `build/`, with `MANIFEST.txt`). It renders the FMM3013 drawing package
> FP010021 (31 sheets), the O&M manual and the cost model from one `data/` folder. Verify gates
> stop the build on errors. Read its *FirstPass Builder Roadmap.pdf* for what comes next. This
> document keeps the principle and the JSON idea below. Sections 2 and 3 are updated; where
> this plan and FirstPass differ, FirstPass wins.

**Principle (settled decision):** the LLM never draws. The LLM produces structured
data; a deterministic Python renderer produces the sheets. This is how we get
AUV-quality packages (`source_drawings/`) with near-zero manual drafting.

## 1. The pipeline

```
1. Machine description  →  2. Engineering pass (LLM)  →  3. Render pass (code)  →  4. Review
   (what the machine        - loads, wire sizes,          - JSON → DXF/PDF          (human)
    is and does, plain       breakers, I/O list,           sheets w/ title block
    language or form)        wire numbers, BOM      
```

### Stage 2 output — the "machine data file" (JSON)

One JSON file fully describes the electrical design. Draft schema, keep it simple:

```json
{
  "project": {"number": "P0001", "name": "Example Machine", "engineer": "A. Ford",
               "voltage": "230VAC", "phase": 3, "fla": 115},
  "sheets": [
    {"number": "020", "title": "Incoming Power and Distribution", "type": "power"}
  ],
  "devices": [
    {"tag": "CB2001", "desc": "150A breaker disconnect", "part": "…", "enclosure": "EC1", "sheet": "020"}
  ],
  "wires": [
    {"number": "20011", "from": "CB2001:T1", "to": "TB2009:L1", "awg": "2", "color": "BK", "sheet": "020"}
  ],
  "plc_io": [
    {"point": "I/00", "module": "1769-IQ16", "tag": "PRS7001", "desc": "Incoming part photoeye", "sheet": "070"}
  ]
}
```

The FMM3013 numbering conventions to copy (see `02_machine_reference_FMM3013.md` §7):
sheet 070 → wires 70xx; line number + suffix makes the wire number; every wire that
leaves a sheet gets a "from (xxxx)/to (xxxx)" cross-reference.

### Stage 3 — the renderer

- Python + **ezdxf** library → DXF (opens in AutoCAD/LibreCAD/QCAD) and PDF.
- Template parts: title block (company name, project, sheet #, prev/next sheet),
  ladder rails with line numbers, standard symbols (breaker, contactor, photoeye,
  PLC point, terminal), BOM table.
- Runs on the Mac Mini. No AI involved — same input always gives the same sheet.

## 2. What exists and what to build next

- **Drawings:** done in FirstPass (`build/gen_drawings.py`, `sheet.py`, `schem.py`, `io_sheet.py`).
  FirstPass uses CSV/YAML job data (`io.csv`, `loads.csv`, `drives.csv`, `lamps.csv`,
  `safety.csv`, `panels.csv`, `bom.csv`, `project.yaml`) rather than the single JSON file
  sketched above. The idea is the same.
- **PLC program:** done in `firstpass_plc/` (this repository), generated from the same FirstPass
  data. See `firstpass_plc/README.md`.
- **Next, per the FirstPass roadmap:** seed the parts library from a real quote; DXF footprints
  for the panel layout sheet 090; terminal strip sheet and coil cross-references; thermal, fit
  and SCCR rules.

## 3. The "Brad files"

*Brads Operation and Maintenance Manual.pdf* is in Google Drive under *Panel Business*. The
FirstPass reference material is in *FMM3013 Package / reference*: *AUV Drafting Standard
(measured from 300dpi scan)* and *AUV Terminology and Convention Reference*. The FirstPass
drawings follow those conventions.

## 4. Parts database (feeds the BOMs)

Start a simple spreadsheet (`parts_database.xlsx`, not created yet):

| Column | Example |
|---|---|
| Internal part # | EYB1050 |
| Description | 3-pole breaker, 20 A |
| Manufacturer + catalog # | (to be filled from supplier quotes) |
| Category | breaker / contactor / terminal / VFD / relay / sensor |
| Typical price | $ |

Seed it from the FMM3013 BOM extracts in `02_machine_reference_FMM3013.md` — those
are real, proven parts for a real panel.
