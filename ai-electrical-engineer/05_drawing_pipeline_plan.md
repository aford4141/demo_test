# Drawing Pipeline Plan — How drawings get generated

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

## 2. First build step (do this next)

Build `render_sheet.py`, a script that:

1. Reads a JSON file with a title block + one power-distribution circuit
   (~the content of FMM3013 sheet 020: 3-phase incoming, breaker, distribution block).
2. Outputs `sheet_020.dxf` and `sheet_020.pdf` with numbered ladder lines,
   wire numbers, device tags, and the title block.
3. Success = put it next to the real AUV sheet 020 and it reads the same way.

That one script proves the whole architecture end to end. After that: symbol
library, multi-sheet packages, cross-reference generator, BOM table generator.

## 3. The "Brad files"

Drawing templates were started with another AI chat (called the Brad files).
They are **not in this folder yet**. Next step for whoever reads this: get them
from Alan, put them in `templates/` here, and reconcile them with the JSON schema
above so there is one single format.

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
