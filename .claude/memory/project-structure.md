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
│   │   ├── config.py             OWNS every path and global constant: seed, keys, filenames     ✓
│   │   ├── io.py                 read csv/xlsx, list a dataset folder                           ✓
│   │   ├── paths.py              a pure re-export shim of config.py — debt, delete after        ~
│   │   ├── metrics.py            the four official metrics, one function each                   ✗
│   │   ├── interface.py · registry.py · splits.py · features.py     CUT — see rule 8            ✗
│   │
│   ├── door/ acv/ rail/ shm/     one package per subsystem, same file names throughout:
│   │   ├── config.py             OWNS every dimension of that subsystem                    rail ✓
│   │   ├── dataset.py            raw files -> arrays/DataFrame. No feature logic.          rail ✓
│   │   ├── features.py           arrays -> feature matrix. No model, no IO.                rail ✓
│   │   ├── model.py              the estimator and its hyperparameters. No IO.             rail ✓
│   │   ├── train.py              fit, validate, checkpoint to outputs/models/<sub>/        rail ✓
│   │   ├── predict.py            predict(inputs: list[Path]) -> DataFrame. THE contract.   rail ✓
│   │   └── explain.py            optional: the same run as panels the app draws            rail ✓
│   │   (rail also: speed.py — tachometer square wave -> m/s)
│   │   (door also: segment.py — cycle detection in the continuous stream)
│   │   (acv  also: rank.py — per-car scoring into a ranked_cars string)
│   │   (subsystem.py is CUT — nothing wires a protocol; services.py imports by name)
│   │
│   ├── app/                      the compulsory non-technical UI       (Wayne's, not yet merged)
│   │   ├── main.py               entry point and routing ONLY                                   ~
│   │   ├── config.py             page identity, the words on screen, the palette                ~
│   │   ├── ui/                   one file per COMPONENT — never one per subsystem               ~
│   │   └── services.py           importlib to src.<sub>.predict / .explain. No model code.      ~
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
    ├── models/<sub>/   checkpoints, plus any cached feature matrix
    ├── predictions/    the four *_predictions.csv
    ├── plots/          figures for the write-up
    ├── logs/
    └── submission/     the packaged <Team Name>/ folder
```

Status column: ✓ exists and works, `~` exists but unrun or on a branch, ✗ planned. Reconciled
2026-09-18: **`common/` and `src/rail/` are done**, Wayne's `src/app/` and `src/shm/` are complete on
his branch and not yet merged, and `src/door/`, `src/acv/`, `src/submission/` and `scripts/` are
still empty. The tree is no longer scaffolding — check before assuming a file is absent.

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
5. **`common/config.py` owns every path.** No file builds a path from a literal, and nothing outside
   it reads `data/` or writes `outputs/` by string. A path *composed* from two owned constants —
   `MODEL_DIRS[key] / config.CHECKPOINT_NAME` — is a derivation, not a restatement, and two modules
   composing it identically is correct; importing one from the other would invert a layer.
   (`common/paths.py` is now a pure re-export shim of `config.py` and should be deleted.)
6. **Nothing that varies gets written as a literal.** If it could change, it lives in a config.
7. **The layers do not blur.** `dataset.py` does IO and no features. `features.py` does features and
   no IO. `model.py` does neither. `train.py` and `predict.py` are the only files that **write**
   under `outputs/`; `explain.py` may read a checkpoint but computes every number it shows from the
   same functions the feature vector is built from, so an explanation cannot drift from the
   prediction it explains.
8. **One app, all subsystems.** The app never branches on which subsystem is selected — it asks for
   a *capability* and gets one or does not. `registry.py` and `interface.py` were cut as overhead;
   `src/app/services.py` resolves `src.<sub>.predict.predict` (required) and
   `src.<sub>.explain.explain` (optional) by `importlib`, and `src/app/ui/explain.py` draws whatever
   panels come back by switching on each panel's `kind`. Two consequences: a subsystem is added
   without touching the app, and **there are no per-subsystem view files** — `src/app/ui/<sub>.py`
   must never be written.
9. **`docs/`, `reference/` and `data/` are read-only inputs.** Never edit, never rename. The
   organisers' file names are part of the submission contract (`file_id`).
10. **`outputs/` is the only place anything is written**, and it is entirely regenerable. Never
    commit an artefact from it.
11. **Errors are `raise SystemExit("message")` in scripts, real exceptions in libraries.** No
    silent fallbacks — a subsystem that cannot load its data must say so and stop.
12. **Comments explain why, not what.** Match the density of the surrounding file.

See also: [[problem-statment]].
