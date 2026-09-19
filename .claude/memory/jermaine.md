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

### 2026-09-19 — rail's verdict quotes a measured ratio, not the model's probability, and a batch shows every file

**What:** `explain.py` only. The verdict detail is now the cross-side contrast in the band that
implicates the rail — *"3.4x louder than the other rail at 300-500 mm ripple spacing. A rail to
inspect, not a measure of how worn it is."* — where it used to read *">99% confident"*. The
probability moved into the metrics panel as **"Model probability · how sure the model is, not a
measured hit rate"**. New `strip` panel, one cell per uploaded file, leading the workings whenever
more than one file is uploaded, so it is what sits beside the verdict in the **Answer** view.
Internally `_subject` became `_read_batch`, which makes one pass and keeps the matrix, speeds, calls
and probabilities; `_side_maxima` is deleted.
**Why:** two things found by uploading the real 68 held-out files rather than one. The batch contains
**eight fault calls and the verdict named one of them** — the other seven were visible only as rows in
the Details table, which is the opposite of what `explain.py`'s own docstring claims to do for "a
reader opening a batch of sixty-eight". And ">99% confident" on `Test66` is the booster's raw
probability on 270 training files with 24 Side II examples, next to a measured Side II F1 of 0.790 —
true as a statement about the model, read as a guarantee about the track.
**Affects:** **nobody in code.** `predict(inputs) -> DataFrame` untouched, the 68-row CSV
byte-identical, no app file edited — the `strip` renderer already existed for Door's cycles. Verified
through `services.py` on all 68: panels `verdict · strip · line · metrics · bars`, 68 cells in two
states, JSON-clean.

One measurement worth keeping: **the margin now shown is read out of the classified feature row**
(`vibration_contrast_max_<band>`) rather than recomputed from `features.quantities` beside it. The two
are bit-identical — checked, `max abs diff 0.0` — so this costs nothing and removes a second source
for one number.

Two things to borrow, **Jou and Wayne**, both of which rail got wrong and you may already have right:

1. **A verdict that quotes a classifier probability reads as a guarantee.** Door counts cycles
   ("longest unbroken run: 4"), ACV quotes degrees of separation plus "a ranking, not a confirmed
   leak", SHM quotes runs remaining. All three state a measured quantity in the subsystem's own units
   and say what the answer is not. **Rail was the only one quoting a model score, and the convention
   you three already had is the right one** — keep it.
2. **Check what your `explain` shows when someone uploads the whole test set, not one file.** One
   verdict for a 68-file batch hides everything except the worst row. ACV emits a verdict per file and
   Door's strip covers every cycle; rail had neither and did not notice until the app was driven with
   a real batch. This is the "verify through the real caller" lesson again, one level up: the right
   caller with the wrong *input size* still passes.

### 2026-09-19 — rail's constant-`Normal` fallback is gone; it now refuses like Door and SHM

**What:** `load_checkpoint` raises `FileNotFoundError` instead of returning `None`, `predict` has no
fallback branch, `explain` has no untrained panel, and `config.FALLBACK_LABEL` is deleted. New
`scripts/train_rail.sh` / `.bat`, mirroring `train_shm.*` — rail was the only trained subsystem
without a wrapper. The README's rail row, run block, method section and Status paragraph are updated.
**Why:** the fallback was indistinguishable from a working model everywhere it mattered. The warning
lived only in `predict.py`'s `main()`, which the submission path never calls, so on a machine with no
checkpoint `./submit.sh` would have written 68 rows of `Normal`, `src/submission/validate.py` would
have passed them, and a 0.308 submission would have packaged in silence. Door and SHM already refuse
on exactly this argument (`src/shm/predict.py`'s docstring states it).
**Affects:** **everyone who runs the submission.** Measured with the checkpoint moved aside: the app
reports *unavailable* ("not ready to run … this is an app setup issue"), `generate` skips rail with
the reason **and deletes the stale CSV**, and `explain` fails separately through the app's cache. With
it restored, the 68 rows are byte-identical. Nothing in `common/` or `src/app/` touched by this entry.
**The trade is real and was taken deliberately:** rail no longer contributes the banked 0.308 if the
deadline arrives untrained — it contributes 0, exactly as Door and SHM already do. `./submit.sh` runs
generate → validate → package and **does not train**, so training is a step the person building the
submission has to take.

**[[team-split]]'s "Bank a floor early" table still lists rail's dummy submission as constant
`Normal` at ~0.308.** That is history, not current behaviour: the floor was banked in Phase 0 and
then deliberately given up today. Read that table as what happened in hour one.

### 2026-09-19 — rail now returns a `verdict` panel and has a `validate.py`; one line of app copy changed

**What:** rail caught up to the two app capabilities that landed after its Phase 9. New
`src/rail/validate.py` (header-only check, so the app classifies a wrong upload as *mismatch*
rather than *internal*); `explain.py` returns a `verdict` panel first and leads its workings with
the spectrum chart; `config.py` gained `SEVERITIES`, `RECOMMENDATIONS` and `RECOMMENDATION_SCOPE`;
`dataset.py` gained `read_header` and made `describe_header_mismatch` and `SCHEMA_MISMATCH` public.
**In `src/app/config.py` I changed one string:** `UPLOAD_REQUIREMENTS["rail"]`, which still read
"when its model is available".
**Why:** rail was the only subsystem with no verdict, so the app's default **Answer** view drew
"This system does not summarise itself yet" over a working model — measured, not assumed. And
`services.validate_inputs` runs *before* the try-block, so the same sentence raised from inside
`predict` reaches the reader as "Assessment interrupted. This does not establish that your
recordings are incorrect", which blames the user's files for belonging to another system.
**Affects:** **Wayne** — that one line of `UPLOAD_REQUIREMENTS`, nothing else in `src/app/`.
Nothing in `common/` touched, `predict(inputs) -> DataFrame` is unchanged, and the 68-row CSV is
**byte-identical** after the change. Verified through `services.py`, not through rail's `main()`.

Two things worth borrowing, **Jou and Wayne**:

1. **Where you raise decides what the reader is told.** A `ValueError` from `src/<sub>/validate.py`
   is a *mismatch* and the same `ValueError` from `predict` is an *internal* failure, because
   `run_prediction` wraps everything after validation in `AssessmentFailed`. Rail had the right
   sentence in the wrong place for a day. Check yours by uploading another subsystem's file to
   yours and reading the headline.
2. **A validator does not have to parse the file.** Rail's reads the header alone with
   `nrows=0` — all 68 uploads validate in **1.0 s** against ~14 s to parse them, and the question
   "was this recorded by this system" is settled by the column names either way.

### 2026-09-19 — rail's feature set is 228 columns, not 342; every rail artefact under `outputs/` is stale

**What:** Phase 7 dropped the median aggregate. `src/rail/config.py` gained `AGGREGATES`, `features.py`
builds `_AGGREGATES` from it, and `FEATURE_NAMES` went from 342 names to **228**. `features_train.npz`,
`classifier.pkl` and `baseline_folds.npz` were all rebuilt; anything cached before today refuses to
load rather than predicting through mismatched columns.
**Why:** [[rail-plan]] Phase 7. Four added-feature ideas were refuted and the median columns turned out
to be a tie the model was carrying for nothing — 0.740 → 0.750 per fold, 0.757 pooled, Side I 0.494 →
0.515, and all 68 held-out predictions byte-identical.
**Affects:** **nobody** in code — `predict(inputs) -> DataFrame` and the `explain` panels are unchanged,
both re-verified against Wayne's real `src/app/services.py` (30 checks, including the staged-upload
path). If you have a rail `outputs/` from yesterday, `python -m src.rail.train --refresh` rebuilds it in
~390 s. Nothing in `common/` touched.

Three things worth borrowing, **Jou and Wayne**, all of which cost rail a day to learn:

1. **Adding columns buys score on its own.** 36 candidate columns with their *rows shuffled* — so they
   describe the wrong files — scored **+0.012 macro F1 and +0.027 on the rare class**, above five of the
   seven candidates tested that day and above every one that survived its own confound check. At 270
   files with 14 in the minority class, matrix width moves fold-level variance. **Price any new feature
   block against its own shuffled control, not against zero.** Door's 110 segments and SHM's 64 labels
   are in the same regime or worse.
2. **A gain on the full set that vanishes on the honest subset is the confound, not a gain.** Two of
   five candidates did exactly that, and a third hid a speed marker that the subset check waved through
   — so score the honest subset every run *and* read your new columns directly. Whatever your
   subsystem's equivalent of "slow ⇒ Normal" is — a file-length cue, a sensor only present in healthy
   cases — check what each column can tell about it, not just what the model scores.
3. **Best-of-N needs a replication on fresh folds.** Rail's winner read +0.022 when screened, +0.016
   confirmed on the same folds at the shipped settings, and **+0.002 on a new seed** with both sides
   re-measured. The first two numbers are the same measurement twice; only the third is evidence.

**Correcting a figure my earlier entries below both get wrong: rail's constant-`Normal` floor is 0.308,
not 0.33.** It was computed as `(1.0 + 0 + 0)/3`, and the majority class does **not** score F1 1.0 when
you predict it everywhere — recall is perfect but precision is only its share of the data, so its F1 is
`2p/(p+1)` = 0.924 at rail's 232/270. **Check your own floor the same way, Jou and Wayne**: the general
form for a constant prediction over k classes is `2p/(p+1)/k`, and 1/k is a limit you cannot reach.
Door's ~0.4 in [[team-split]] is already correct (0.842/2 = 0.421 at 80/110), and the banked Overall is
0.3229, so nothing downstream moves — but the two entries below say 0.33 and it is 0.308.

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
