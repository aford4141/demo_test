# LLM & Hardware Plan — Can a local model be the electrical engineer?

**Question asked:** Is there an LLM that can work as our electrical engineer, doing
the drawings and everything, that fits on a Mac Mini? If not, what size model and
what hardware would we have to buy?

**Short answer:** No single local model — at any size or price — is "the best
electrical engineer you've ever had." But the job splits into a *brain* and a
*drafter*, and with that split the goal is reachable today: frontier hosted model
as the brain, ordinary code on the Mac Mini as the drafter.

## 1. What the job actually requires

From the FMM3013 package (see `02_machine_reference_FMM3013.md`), the "engineer"
must do four different things:

1. **Engineering judgment** — size wire (2 AWG for 115 FLA), coordinate breakers,
   apply NEC / NFPA 79 rules, pick parts.
2. **Read drawings** (vision) — understand existing schematics, cross-references,
   panel layouts.
3. **Structured output** — wire lists, I/O maps, BOMs, with zero format errors.
4. **Drawing production** — render title-blocked schematic sheets.

Item 4 should never be done by an AI directly. It is deterministic template
rendering (Python → DXF/PDF). Items 1–3 are the AI's job, and items 1–2 are
exactly where small local models fall down.

## 2. Local model ladder (what fits where)

Sizes assume ~4-bit quantized models running under LM Studio / Ollama / MLX.

| Hardware | Cost | Biggest useful models | Honest capability |
|---|---|---|---|
| Mac Mini M4, 16 GB | ~$600 | 7–8B (Qwen3-8B, gpt-oss-20b) | Toy tier. Confidently wrong on wire sizes. Not viable as engineer. |
| Mac Mini M4 Pro, 64 GB | ~$2,000 | 70B class (Llama 3.3 70B), Qwen3-32B, Gemma 3 27B (has vision) | Drafting assistant. Fills templates, drafts I/O lists. Human checks everything. |
| Mac Studio M4 Max, 128 GB | ~$3,500 | gpt-oss-120b, Qwen2.5-VL-72B (vision) | Competent junior drafter. Reads drawings passably. Still misjudges engineering calls. |
| Mac Studio M3 Ultra, 256 GB | ~$5,600 | Qwen3-235B-A22B (MoE, fast) | Solid mid-level assistant. |
| Mac Studio M3 Ultra, 512 GB | ~$9,500 | DeepSeek-V3/R1 class 671B (~404 GB, ~15–18 tok/s) | Best single-box local AI available. ~85–90% of frontier on text; weaker on vision and multi-step drawing work. |
| PC route: RTX 6000-class 96 GB GPU | ~$8,500+ | 70–123B dense, fast | Similar tier to the 128 GB Mac, faster, louder, more setup. |

## 3. The recommendation

**Do not buy the $9,500 box.**

- A frontier hosted model (Claude) is stronger than any local model precisely on
  the skills this job needs: judgment, reading drawings, multi-step agent work.
- Generating a full drawing package via API costs cents to a few dollars. Years of
  heavy use would not add up to the price of the big Mac Studio.
- The Mac Mini you already own is fully sufficient for the other half: the
  renderer, the templates, and the parts database run there with no AI at all.
- Optional: if the Mini has 32 GB+, a small local model (Qwen3-14B/32B) can be an
  offline helper for quick questions. Treat it as an intern, not the engineer.

**When to revisit:** buy the Mac Studio M3 Ultra 512 GB (plus Qwen2.5-VL for
reading drawings) only if a hard requirement appears that customer drawings can
never leave the building, or a local model is released that demonstrably matches
frontier quality on engineering + vision tasks.

## 4. Division of labor (the target system)

```
Customer request
      │
      ▼
Frontier LLM (the engineer brain)
  - asks clarifying questions
  - decides circuits, sizes wire/breakers
  - assigns PLC I/O
  - outputs machine description as structured data
      │
      ▼
Mac Mini (the drafting department, plain code)
  - FirstPass Builder: drawings, O&M manual, costing
  - PLC Program Builder: tested Studio 5000 program (L5X)
  - parts database lookup (internal # → catalog # → price)
      │
      ▼
Windows PC (Studio 5000): import, verify, download to a bench PLC
      │
      ▼
Human review (owner / engineer of record) → issue to customer
```
