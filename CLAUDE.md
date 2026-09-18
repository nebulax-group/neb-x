# neb-x

NebulaX Hackathon entry for **Problem Statement 3 — Train Condition Monitoring**.

Detect faults and estimate degradation from raw rail-vehicle sensor time series across four
independent subsystems. Each is worth 25% of the Overall Score and may be attempted on its own.

| Key | Subsystem | Task | Metric |
|---|---|---|---|
| `door` | Door | Find each open/close cycle in a continuous stream, classify `Normal` vs `Abnormal resistance` | IoU-weighted F1 |
| `acv` | ACV | Rank the cars from most- to least-likely to have a refrigerant leak | Linear rank-decay |
| `rail` | Rail Corrugation | Classify `Normal` / `Side I` / `Side II` | Macro F1 |
| `shm` | SHM | Regress cumulative fatigue damage | `max(0, 1 − MAPE)` |

Project memory lives in [.claude/memory/](.claude/memory/) — start at
[.claude/memory/MEMORY.md](.claude/memory/MEMORY.md).

@.claude/memory/MEMORY.md
@.claude/memory/problem-statment.md
@.claude/memory/project-structure.md

## Sources of truth, in order

1. [`docs/<subsystem>/info_kit.md`](docs/) — **authoritative** per-subsystem task, schema and
   scoring formula. The tables in memory and in this file are convenience summaries, not the spec.
2. [`docs/problem_statement.md`](docs/problem_statement.md) — deliverables, submission structure, rubric.
3. [`reference/submission_format/`](reference/submission_format/) — the prediction CSV schema as shipped.
4. `.claude/memory/` — our decisions and the reasoning behind them.

## Layout

`docs/` the organisers' words · `reference/` the schema contract · `data/` raw datasets (gitignored,
6 GB) · `src/` our code · `scripts/` thin wrappers · `outputs/` everything generated (gitignored).

Full tree and the rules behind it: [project-structure.md](.claude/memory/project-structure.md).

## How code gets written here

**One file, one purpose.** Separation of concerns is enforced by layer, not by convention:

- `src/common/` is subsystem-agnostic and imports no subsystem. Dependencies point one way:
  `common` ← subsystem ← app.
- `src/<sub>/` packages never import each other. Shared logic moves **down** into `common/`,
  never sideways.
- `src/<sub>/config.py` owns every dimension of that subsystem; `src/common/paths.py` owns every
  path. Nothing restates a constant it could derive.
- `dataset.py` does IO and no features. `features.py` does features and no IO. `model.py` does
  neither. Only `train.py` / `predict.py` write to `outputs/`.
- One app for all subsystems, routed through `src/common/registry.py` — the app never branches on
  subsystem internals.

The full twelve rules are in [project-structure.md](.claude/memory/project-structure.md#the-rules).

## Working notes

- **Never rename anything under `data/*/test/` or `docs/`.** The `file_id` column of the
  prediction CSVs must be the source file name exactly as shipped.
- Methodological soundness is graded alongside the headline metric — **a high score from a leaky
  split will not score well.** Design and justify the split; state assumptions where the docs leave
  a decision open.
- Units, sampling frequencies and column definitions vary by subsystem. Do not carry assumptions
  across. Check class balance before evaluating.
- The app is a **compulsory** deliverable, not an afterthought, and is how the submitted
  predictions must be generated.

## Environment

Virtualenv at `.venv` (Python 3.14.7). `source .venv/bin/activate`.
