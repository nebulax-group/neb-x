# Jermaine — Change Log

What Jermaine changed, newest first. One entry per change the other two might depend on.

**Why:** the three of us work on mutually exclusive packages ([[team-split]]), so nobody reads
anyone else's diffs. This is where a change that crosses a package boundary gets announced.

**How to apply:** append an entry when you touch anything outside your own package — `common/`,
a shared constant, a file schema, a function signature, a cached artefact under `outputs/`. Purely
internal work inside your own subsystem does not need an entry.

**Role:** A — `src/rail/` end to end, plus the rail view. The heaviest column and the longest
serial loop; start extraction first and never block on the full run. See [[team-split]].

## Changes

### Template

```
### <time> — <short title>

**What:** the change, in one line.
**Why:** what forced it.
**Affects:** who has to do something differently, or "nobody".
```

### 2026-09-18 — rail ships: `predict` now takes `list[Path]`, and `explain.py` exists

**What:** `src.rail.predict.predict` takes `list[Path]` and returns the 68 real rows from the fitted
checkpoint, with an `--input`/`--output` CLI. New `src/rail/explain.py` supplies three panels to
Wayne's generic explainability capability. `src/rail/features.py` made two names public for it:
`quantities` (was `_quantities`) and `WAVELENGTH_BAND_NAMES`.
**Why:** Phase 9 of [[rail-plan]]. Rail was submitting the 0.33 fallback until `predict.py` loaded
the checkpoint Phase 8 wrote.
**Affects:** **Wayne** — rail now answers `is_available`, `run_prediction` and `explain_prediction`;
all three were exercised against your `services.py` on the real 68 files before this was written,
and the panels compile through `ui/explain.py`'s Altair layers. Nothing in `common/` touched. The
rail checkpoint under `outputs/models/rail/` also gained a `fingerprint` key: a checkpoint written
before today now refuses to load rather than predicting through mismatched features.

Two things for **everyone**, both found by running against Wayne's code rather than our own:

1. **`predict` takes a list of paths, not a folder.** Rail's took `str | Path` and fed
   `list_data_files`, which raises on a list — rail would have failed on the first click in the app
   and scored zero with a perfectly good model behind it. [[team-split]] has said `list[Path]` all
   along. **Check your own signature against `services.run_prediction`, not against your `main()`.**
2. **`src/app/ui/<sub>.py` is not how the app is extended any more.** A subsystem exposes
   `src/<sub>/explain.py::explain(inputs) -> list[dict]` and the app draws the panels generically.
   Rail's plan had `src/app/ui/rail.py` in its file list and that file should never be written.

### 2026-09-18 — rail feature cache gained a `speeds` vector; a fitted checkpoint now exists

**What:** `outputs/models/rail/features_train.npz` now carries two more arrays — `speeds` (one m/s
figure per file) and `fingerprint` (the settings that change a feature's value without changing its
name) — and `python -m src.rail.train` also writes `outputs/models/rail/classifier.pkl`, the fitted
classifier plus its 342 column names, as a stdlib pickle. Caches built before today raise on load;
`--refresh` rebuilds in 80 s.
**Why:** Phase 8 of [[rail-plan]]. The honest macro F1 has to be reported on the files fast enough
that "slow implies Normal" is unavailable, and recovering speed per file any other way means
re-reading all 272 CSVs.
**Affects:** nobody — rail's own model directory, nothing in `common/` touched, and
`predict(inputs) -> DataFrame` is unchanged. Two things worth borrowing, **Jou and Wayne**, both of
which cost rail a wrong number today:

1. Our per-class figures were being quoted from a single CV pass. Averaging ten complete
   out-of-fold sets instead moved rail's rarest class from 0.593 to 0.494 — with 14 files in a
   class, one file changing fold is worth 0.07, so a single pass mostly reports the split. Door's
   30 abnormals are in the same regime.
2. **The mean of per-fold macro F1 is not the macro F1 the organisers compute.** Theirs is one
   score over the whole prediction set; ours averaged 50 fold-level scores, each of which weights a
   3-file class against a 47-file one. Rail reads 0.740 the first way and 0.752 the second on
   identical predictions. Any per-class or macro metric on an imbalanced set has this gap — MAPE and
   the rank-decay score do not, so this one is Jou's to check, not Wayne's.

### 2026-09-18 — rail needs the app shell earlier than planned

*Superseded by the entry above: there is no `src/app/ui/rail.py` and there never will be — the app
draws panels a subsystem returns from its own `explain.py`.*

**What:** rail reordered its remaining phases to 8 → 9 → 7, so `src/app/ui/rail.py` is now wanted
as soon as the shell exists rather than last ([[rail-plan]]).
**Why:** rail's 0.758 macro F1 is measured but not banked — `predict.py` still returns constant
`Normal`, so rail would score 0.33 if the deadline arrived today. Fitting and shipping is worth
~+0.42; the remaining model work is worth ~+0.05.
**Affects:** **Wayne** — no new requirement, but rail will consume the shell sooner than the
original schedule implied. Rail's side of the contract is unchanged: `predict(inputs) -> DataFrame`.
Also worth borrowing, **Jou and Wayne**: comparing two models by their `mean ± sd` across folds
cannot resolve a real 0.03 difference at this sample size. Difference the scores **per fold** on
identical splits instead — paired, that is ±0.03 here against ±0.08 unpaired.

### 2026-09-18 — rail feature cache under `outputs/models/rail/`

**What:** `python -m src.rail.train` now writes `outputs/models/rail/features_train.npz` — a
272×342 float64 matrix plus `files` and `columns` vectors, 790 KB, built in 80 s and reloaded in
0.003 s.
**Why:** Phase 4 of [[rail-plan]]. Re-extracting during tuning is the thing that kills a 24-hour
project; the cache makes every iteration after the first instant.
**Affects:** nobody. New file in rail's own model directory, nothing in `common/` touched, and
`predict(inputs) -> DataFrame` is unchanged. Clearing `outputs/` costs rail 80 s and nothing else.

<!-- newest entries above this line -->
