---
name: project-structure
description: How neb-x is laid out and how its code must be written — one file, one purpose; separation of concerns enforced by layer.
metadata:
  type: project
---

# Project Structure and Code Conventions

The shape of this repo, and the rules any new file must follow. Modelled on
`~/Documents/nus-y4s1/CG4002`, which is the house style we are matching.

**Why:** four subsystems ([[problem-statment]]) share a pipeline shape but nothing else — different
schemas, sampling rates, task types and metrics. Without hard separation, one subsystem's quirk
leaks into the others' code and the app becomes a pile of `if subsystem == ...`.

**How to apply:** before writing any file, decide which layer it belongs to and put it there. A file
that would need to sit in two layers is two files.

## The tree

```
neb-x/
├── CLAUDE.md                     project brief, loaded every session
├── README.md                     public-facing: what this is, how to set up
├── .gitignore
├── .venv/                        the ONE virtualenv (Python 3.14), gitignored
├── requirements.txt              pinned deps                                    ✗
│
├── .claude/memory/               durable project facts, one file per topic
│   ├── MEMORY.md                 the index
│   ├── problem-statment.md       the PS3 brief, deliverables, scoring
│   └── project-structure.md      this file
│
├── docs/                         the organisers' words, copied verbatim — READ-ONLY
│   ├── problem_statement.md      = PS3/01_Problem_Statement_3_Specifications.md
│   ├── door/  info_kit.md · data_headers.md
│   ├── acv/   info_kit.md
│   ├── rail/  info_kit.md · images/
│   └── shm/   info_kit.md
│
├── reference/submission_format/  the four example prediction CSVs — the schema contract
│
├── data/                         raw datasets, gitignored, copied verbatim — see data/README.md
│   └── {door,acv,rail,shm}/
│
├── src/
│   ├── common/                   subsystem-agnostic. Knows nothing about any one subsystem.
│   │   ├── paths.py              OWNS every path in the project, derived from the repo root      ✗
│   │   ├── config.py             global constants: seed, subsystem keys, output names            ✗
│   │   ├── interface.py          the Subsystem protocol every subsystem implements               ✗
│   │   ├── registry.py           subsystem key -> Subsystem; the only lookup the app uses        ✗
│   │   ├── io.py                 read csv/xlsx, list a dataset folder                            ✗
│   │   ├── splits.py             grouped train/val splitting helpers                             ✗
│   │   ├── features.py           generic time-series primitives (stats, FFT bands, envelopes)    ✗
│   │   └── metrics.py            the four official metrics, one function each                    ✗
│   │
│   ├── door/ acv/ rail/ shm/     one package per subsystem, same file names throughout:
│   │   ├── config.py             OWNS every dimension of that subsystem                          ✗
│   │   ├── dataset.py            raw files -> arrays/DataFrame. No feature logic.                ✗
│   │   ├── features.py           arrays -> feature matrix. No model, no IO.                      ✗
│   │   ├── model.py              the estimator and its hyperparameters. No IO.                   ✗
│   │   ├── train.py              fit, validate, write a checkpoint to outputs/models/<sub>/      ✗
│   │   ├── predict.py            checkpoint + test folder -> <sub>_predictions.csv              ✗
│   │   └── subsystem.py          wires the above into common/interface.py                        ✗
│   │   (door also: segment.py — cycle detection in the continuous stream)
│   │   (acv  also: rank.py — per-car scoring into a ranked_cars string)
│   │
│   ├── app/                      the compulsory non-technical UI
│   │   ├── main.py               entry point and routing ONLY                                    ✗
│   │   ├── ui/                   one file per screen/component                                   ✗
│   │   └── services.py           calls the registry; contains no model or feature code           ✗
│   │
│   └── submission/
│       ├── validate.py           check a CSV against reference/submission_format/                ✗
│       └── package.py            the CSVs -> predictions.zip (flat, no subfolders)               ✗
│
├── scripts/                      thin wrappers, no logic of their own                            ✗
│   ├── train.sh <subsystem>
│   ├── predict.sh <subsystem>
│   ├── app.sh
│   └── package.sh
│
└── outputs/                      everything generated, gitignored
    ├── models/<sub>/   checkpoints + fitted scalers
    ├── predictions/    the four *_predictions.csv
    ├── plots/          figures for the write-up
    ├── logs/
    └── submission/     the packaged <Team Name>/ folder
```

Status column: ✓ exists and works, `~` exists but unrun, ✗ planned. Everything under `src/` and
`scripts/` is ✗ as of 2026-09-18 — the tree is scaffolding.

## The rules

1. **One file, one purpose.** A file's name is its job. If you cannot name a file after the single
   thing it does, it is doing two things.
2. **`src/common/` never imports a subsystem.** Dependencies point one way: `common` ← subsystem ←
   app. A subsystem may import `common`; nothing imports the app.
3. **No subsystem imports another subsystem.** They are independent by the problem statement's own
   framing — keep them independent in code. Shared logic moves down into `common/`, never sideways.
4. **`<sub>/config.py` owns every dimension of that subsystem** — window sizes, sampling rates,
   column names, label vocabularies, thresholds, hyperparameters. Nothing else restates one
   without deriving it from there. A restated constant is how the trainer and the predictor end up
   disagreeing, which survives validation and only shows up in the submitted CSV.
5. **`common/paths.py` owns every path.** No file builds a path from a literal, and nothing outside
   it reads `data/` or writes `outputs/` by string.
6. **Nothing that varies gets written as a literal.** If it could change, it lives in a config.
7. **The layers do not blur.** `dataset.py` does IO and no features. `features.py` does features and
   no IO. `model.py` does neither. `train.py` and `predict.py` are the only files that touch disk
   under `outputs/`.
8. **One app, all subsystems.** The app never branches on subsystem internals — it asks
   `common/registry.py` for a Subsystem and calls the interface. Adding a fifth subsystem must not
   require editing the app.
9. **`docs/`, `reference/` and `data/` are read-only inputs.** Never edit, never rename. The
   organisers' file names are part of the submission contract (`file_id`).
10. **`outputs/` is the only place anything is written**, and it is entirely regenerable. Never
    commit an artefact from it.
11. **Errors are `raise SystemExit("message")` in scripts, real exceptions in libraries.** No
    silent fallbacks — a subsystem that cannot load its data must say so and stop.
12. **Comments explain why, not what.** Match the density of the surrounding file.

See also: [[problem-statment]].
