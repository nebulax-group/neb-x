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

### 2026-09-18 — rail needs the app shell earlier than planned

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
