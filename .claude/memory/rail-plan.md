# Rail Corrugation — Build Plan

The ten phases that take `src/rail/` from empty to a validated `rail_predictions.csv`, the design
decisions behind them, and the measurements those decisions rest on. Jermaine owns this package
end to end ([[team-split]]). Written 2026-09-18, revised the same day against the data.

**Why:** the first draft of this plan was reasoned from `docs/rail/info_kit.md` alone. Probing the
data refuted three of its load-bearing claims — including one instruction that was exactly
backwards — and turned up two facts the info kit never mentions. Everything below is now either
measured or explicitly flagged as unverified.

**How to apply:** work the phases in order. Each has a "done when" checkable in one command. Design
decisions and negative results are recorded here, not in code comments — this file is the source
for the write-up's rail section.

## The task

One file is **one second of an 8-car train passing a section of track**, sampled at 10 kHz —
10,001 lines, a header plus 10,000 rows. Classify each file `Normal` / `Side I` / `Side II`,
graded on macro F1. 272 train files, 68 test files, 234 / 14 / 24.

The labels are mutually exclusive by construction (`docs/rail/info_kit.md` §2.2): `Side I` means
corrugation on rail I *while rail II is normal*. Both sides are never faulty in the same file.

Predicting `Normal` everywhere gives ~86% accuracy and **0.33 macro F1**. The 14 Side I files carry
a third of the score between them, roughly 2.4% of the rail metric each.

A doc inconsistency worth knowing: §4 of the info kit says "~9 Side I examples against ~190
Normal" while §2.2 and `Train_Labels.csv` both say 14 / 234. The label file is ground truth; the §4
figure appears to describe some internal split and is not a second dataset.

## Verified data facts

Measured 2026-09-18 across all 272 training files. These decide the design.

### Column layout — as documented, safe to derive

| Column | Contents |
|---|---|
| 1 | `Rotating speed` — 0/1 square wave; 90-tooth wheel, wheel diameter 0.85 m |
| 2–129 | 64 axle boxes × 2 channels, interleaved `vibration, shock`, Car 1 Pos 1 → Car 8 Pos 8 |

Confirmed against the real header: 64 columns named `Vibration of bearing in position P of car C`
at odd indices, 64 `Shock of…` at even indices. **Positions 1,3,5,7 are the Side I rail;
positions 2,4,6,8 are Side II** — 32 axle boxes per rail, four per car. No NaNs.

### Scale and resolution

Every sample is an exact integer multiple of **0.012207 = 50/4096** — a 12-bit ADC over ±25 m/s².
Vibration sits at RMS ≈ 0.19 (range ±1.5), shock at RMS ≈ 1.37 with peaks to 17.5. Vibration
therefore occupies only ~±75 quantisation steps: roughly 7 effective bits, so quantisation noise is
a real part of the spectrum. Shock is a different measurement at a different scale — **never pool
the two**.

### Speed varies 10×, and 38 files are stationary

Speed derives from the tachometer as `(edges / 2) / 90 × π × 0.85` m/s — two edges per tooth, since
the info kit says the output toggles as a tooth both enters and leaves.

| | Speed (m/s) | |
|---|---|---|
| Normal (n=234) | min 0.00 · median 8.13 · max 19.48 | 38 files with a dead tachometer |
| Side I (n=14) | min **9.70** · median 12.96 · max 18.60 | none |
| Side II (n=24) | min **11.69** · median 14.00 · max 18.51 | none |

Two consequences the info kit gives no warning of:

1. **38 files have zero tachometer edges and all 38 are `Normal`.** Their vibration energy is
   ~500× lower than the rest (2.7e-5 vs 1.35e-2). A stationary train — no excitation, trivially
   Normal. `estimate_speed` needs a defined branch for them, not a divide-by-zero.
2. **Speed confounds the label.** No fault file is below 9.70 m/s while **133 of 234 Normal files
   are**. "Slow ⇒ Normal" is free on 57% of Normal and never wrong on a fault. See
   **The speed confound** below — it is handled, but it must be reported.

### The corrugation band is tens to hundreds of Hz, and it moves with speed

Corrugation has wavelength λ of roughly 3–30 cm (`docs/rail/info_kit.md` §1.1: "a few centimetres
to dozens of centimetres"); a wheel crossing it excites `f = v / λ`. At the *measured* median speed
of 8.1 m/s that is **27–270 Hz**, and across the 9.7–19.5 m/s band the fault files occupy it spans
**32–650 Hz**.

*Corrected 2026-09-18: this section previously said 6–60 Hz, which was an arithmetic slip —
8.1 / 0.30 = 27 Hz, not 6. Both conclusions below are unchanged, and no code depended on the
figure, since the features bin in λ directly.*

The first consequence is concrete: **Welch needs `nperseg ≥ 4096`** (2.44 Hz resolution at 10 kHz).
A default 256-sample window resolves 39 Hz per bin, which buries the bottom of the band in its
first bin or two.

The second is why λ bands beat Hz bands by +0.06: the band's position scales with speed, and speed
varies 10× across these files, so a fixed Hz band is a different physical feature in every file.

### The files are independent — two exact duplicates aside

Checked 2026-09-18 (Phase 5, now closed). The worry was that the 272 files are consecutive
one-second chunks of a few longer runs, which would make a random CV split leak. **They are not.**

| Test | Result | Reading |
|---|---|---|
| Speed of file *n* vs *n+1* | median gap 5.363 m/s, vs 4.836 m/s for random pairs | consecutive files are *less* alike than random ones — not chunks of a run |
| Nearest neighbour is the adjacent file number | 2 / 272 | exactly chance (0.7%) |
| Side I files with consecutive numbers | 0 of 13 | faults are scattered singletons, not blocks |
| Byte-identical files (SHA-256 over all 272) | **2 pairs** | `Train107 == Train115`, `Train165 == Train187` |

Both duplicate pairs are `Normal`, so neither touches the classes where the score lives. Drop
`Train115.csv` and `Train187.csv`, or pin each pair to one fold. **Random stratified CV is sound**
— state that in the write-up with the evidence above, since "we checked and it is fine" is worth
more than silence.

Separately, the 44 files below 0.5 m/s (38 of them with a completely dead tachometer) are all
`Normal` and are much more self-similar than the moving files — median nearest-neighbour distance
14.4 against 23.2. Not leakage across classes, but it does mean part of Normal's high F1 is a
near-duplicate cluster of near-silent recordings rather than real discrimination.

### Extraction is not a bottleneck

`read_csv` 0.15 s/file; read plus Welch on all 128 channels 0.205 s/file; **56 s for all 272**.
[[team-split]]'s "5.6 GB, never block on the full rail run, build the pipeline on a 100-file
subsample" is obsolete. Caching is for iteration comfort, not feasibility.

## The core design decision

Both rails are crossed by the same train, at the same speed, in the same second. The **contrast
between the two sides** therefore cancels every confounder §1.2 of the info kit lists — speed,
ballast noise, track elasticity — and isolates what is genuinely asymmetric. Cross-side log-ratio
features are the main signal, and this held up under test.

But **the aggregation across the 32 boxes of a side must be an extreme-value statistic, not a
robust one.** The first draft of this plan prescribed median and IQR, reasoning that one failing
sensor in 32 should not move the feature. That is exactly backwards:

| 50–150 Hz vibration, log₁₀(side I / side II) | Normal | Side I | Side II |
|---|---|---|---|
| aggregated by **median** | −0.052 | −0.014 | −0.089 |
| aggregated by **max** | +0.046 | **+0.271** | **−0.434** |

Median yields no usable ordering; max separates cleanly in both directions. The reason is
localisation: within-side `max / median` spread runs ~11 on healthy sides but **19.3 on the faulty
side of a Side I file** and **16.2 on the faulty side of a Side II file**. At ~13 m/s the train
covers 13 m in one second, so the eight cars sit over different track and only some boxes ever
cross the corrugated section. The median is designed to discard exactly that.

**Max and p90 are the signal; median is context.**

## Measured baseline

Two numbers, on different feature sets. **The packaged one is current; the probe one below it is
kept because the negative results and the noise-floor argument are quoted against it.**

### The packaged feature set — 0.778 (Phases 1–4)

`src/rail/features.py` as built: 342 features — 19 per-box quantities (7 Hz bands, 7 λ bands, RMS,
Pearson kurtosis, crest, spectral centroid, peak Hz) aggregated over each side by max/p90/median,
plus the three cross-side log₁₀ contrasts, all of it twice for vibration and shock. Flat 3-class
`HistGradientBoostingClassifier(class_weight="balanced", max_iter=300)`, 5×5 repeated stratified CV,
seed 42, run off `features_train.npz`:

| Subset | macro F1 |
|---|---|
| **all 272 files** | **0.778 ± 0.070** |
| duplicates dropped (n=270) | 0.750 ± 0.117 |
| fast files only (n=139) | 0.765 ± 0.105 |

Per-class F1 on a single 5-fold pass: Normal 0.973, **Side I 0.593**, Side II 0.818.

```
[[230   2   2]
 [  6   8   0]
 [  3   3  18]]
```

**+0.096 over the probe baseline, and it is Side I that moved** — 0.333 → 0.593, 8 of 14 correct
instead of 4. The likely cause is the per-box scalars and the p90 aggregate, which the probe did not
carry; the exact probe configuration is not recoverable, so treat this as indicative rather than a
controlled comparison. What *is* controlled: all three subsets above ran on identical folds and all
three clear their probe counterparts (0.682 / 0.661 / 0.660).

Two cautions, both real:

- **The spread tripled**, 0.018 → 0.070. That is not instability that appeared from nowhere — Side I
  recall is now something that can vary, where at 0.333 it was stably wrong. It does mean 0.778 is a
  point estimate with ~±0.07 around it, and Phase 7 must compare on 10×5 fixed folds.
- Side I is still the weakest class by 0.22, so **Phase 7 keeps its whole rationale**.

### The probe baseline — 0.682, superseded

Flat 3-class, `HistGradientBoostingClassifier(class_weight="balanced")`, 5×5 repeated stratified
CV, features = per-side max/p90/median of band energies plus cross-side log-ratios:

| Feature set | macro F1 |
|---|---|
| Hz bands only | 0.625 ± 0.023 |
| **+ wavelength bands** | **0.682 ± 0.018** |
| + explicit speed feature | 0.680 ± 0.022 |
| fast files only (n=139) | 0.660 ± 0.016 |

Wavelength normalisation is worth **+0.06** and confirms the λ-binning decision.

Per-class F1 — **all remaining headroom is Side I**:

| | Normal | Side I | Side II |
|---|---|---|---|
| F1 | 0.956 | **0.333** | 0.766 |

Confusion (rows true, cols predicted, `Normal / Side I / Side II`):

```
[[226   4   4]
 [  9   4   1]
 [  4   2  18]]
```

Of 14 Side I files, 4 are correct and **9 are called Normal**. Side I alone costs ~0.14 of the
final macro F1. Side II is already learnable at 0.766, so the target is parity — which would put
the metric near 0.83.

### The noise floor — read this before believing any improvement

Removing the two duplicate `Normal` files moved macro F1 from 0.682 ± 0.018 to 0.661 ± 0.035, and
Side I F1 from 0.340 to 0.278. Dropping two *Normal* files cannot hurt Side I through leakage:
**that swing is pure fold-reshuffle noise.** With 14 Side I files, one file moving fold changes
Side I recall by 1/14 = 0.07.

So the macro F1 here carries roughly **±0.03–0.04 of run-to-run instability**, and a Phase 7 change
that gains less than that has proven nothing. Two consequences, both binding:

- Use **10×5 repeated CV, not 5×5**, once Phase 7 begins comparing candidates. It costs a minute.
- Compare candidates on **identical fold assignments** (same seeds, same dedup), never against a
  number quoted from a different run.

**Corrected 2026-09-18, and it matters for Phase 7: ±0.04 is the floor for *unpaired* comparison
only.** The figure above came from comparing numbers across different runs. On identical folds the
comparison is paired, fold difficulty differences out, and the detectable effect is roughly
**±0.03** — the GBM-vs-linear difference resolved to ±0.028 at 95% where the marginal spreads were
±0.076 and ±0.098. So:

- **Always difference per fold**, then take the mean and interval of the differences. Never compare
  two `mean ± sd` figures — at this spread that test cannot see a 0.03 effect that is really there.
- Report the win/loss count alongside. 22/25 across 50 folds reads as a tie far more clearly than
  two overlapping error bars do.
- A Phase 7 candidate worth **+0.03 paired** is therefore measurable, where the old rule would have
  discarded it. This makes Phase 7 more tractable, not less.

## The speed confound

Given the table above, a model *could* score respectably by learning "slow ⇒ Normal". Measurement
says this one does not:

- Adding speed as an explicit feature changes nothing: 0.682 → 0.680 on the probe.
- Restricted to the 139 files above 9.70 m/s, where the shortcut is unavailable by construction,
  it still reaches 0.660 on the probe and **0.765 on the packaged feature set** — within noise of
  that set's own 0.778.

So the discrimination is genuine, and **the fast-files-only figure is the honest one to quote**
alongside the headline: 0.765 as of Phase 4. This belongs in the write-up explicitly: a judge who
spots the confound unaided will otherwise assume the worst. Methodological soundness is graded
alongside the metric.

## Files, and the one thing each does

Nothing outside this list gets created.

| File | Purpose | Touches disk | State |
|---|---|---|---|
| `src/rail/config.py` | every rail dimension: column layout, side membership, sample rate, wheel geometry, band edges, Welch parameters, label vocabulary, hyperparameters | no | ✓ |
| `src/rail/dataset.py` | file → arrays; labels → DataFrame. No features. | reads only | ✓ |
| `src/rail/speed.py` | tachometer square wave → m/s. Nothing else. | no | ✓ |
| `src/rail/features.py` | arrays → fixed-length feature vector. No IO, no model. | no | ✓ |
| `src/rail/model.py` | the estimator and its hyperparameters. | no | ✓ |
| `src/rail/train.py` | CV, fit, write checkpoint and feature cache | writes `outputs/` | ~ extraction only |
| `src/rail/predict.py` | `predict(inputs) -> DataFrame` | writes `outputs/` | ~ fallback only |
| `src/app/ui/rail.py` | the rail view | no | ✗ |

`common/config.py` already owns the paths (`TRAIN_PATHS`, `TEST_PATHS`, `LABEL_PATHS`,
`MODEL_DIRS`, `PREDICTION_PATHS`) and `RANDOM_SEED`; `common/io.py` already owns `read_table` and
`list_data_files`. Nothing here restates any of them ([[project-structure]] rules 4 and 5).

`subsystem.py` is cut — the integration contract is one function, `predict(inputs) -> DataFrame`
([[team-split]]).

## The phases

Status as of 2026-09-18. **Phase 8 is next — the order changed, see below.**

| | Phase | State |
|---|---|---|
| 0 | Bank the floor | **done** — `config.py`, `predict.py`, 0.33 banked |
| 1 | Load one file correctly | **done** — `dataset.py` |
| 2 | Speed | **done** — `speed.py`, table reproduced exactly |
| 3 | Features | **done** — `features.py`, 342 features |
| 4 | Extract all, cache once | **done** — `train.py`, 790 KB cache, 0.003 s reload |
| 5 | Leakage check | **done** — split is sound, 2 duplicates to drop at fit time |
| 6 | Model | **done** — `model.py`, 0.758 at 10×5; estimator choice is a tie |
| 8 | Train and tune | **next** — nothing is banked above 0.33 until this exists |
| 9 | Real predict, app view | then this — the definition of done |
| 7 | Side I recall | **last** — upside, and only once 8 and 9 are safe |

### Run 8 and 9 before 7

The plan originally ordered these 7 → 8 → 9. **Do 8 → 9 → 7 instead.**

The 0.758 is measured but **not banked**. `predict.py` still returns constant `Normal`, no
checkpoint exists on disk, and nothing has run through the app. If the deadline arrived today rail
would score **0.33**, not 0.758. Phases 8 and 9 convert the measured number into a submitted one —
worth about **+0.42** — where Phase 7 is upside on top, plausibly +0.05 and possibly smaller than
what the paired test can resolve.

This is the plan's own standing constraint applied earlier than it expected: *ship the Phase 6
baseline and stop, Phase 7 is upside, not a dependency.* It assumed Phase 7 would be cheap enough to
take first. Phase 6's finding that the estimator is irrelevant removes the other reason to delay —
there is nothing left to tune before fitting.

**Phase 9 depends on Wayne's app shell.** If it does not exist yet, `predict.py`'s model path still
stands alone and `src/app/ui/rail.py` follows when the shell lands.

### Phase 0 — Bank the floor — DONE

Done 2026-09-18. Written: `src/rail/config.py`, `src/rail/predict.py` (fallback path only).

`config.py` owns every rail dimension and **derives** the column layout from the info-kit rule
rather than listing it — box order, channel indices, side membership, and `EXPECTED_HEADERS`, which
was verified string-for-string against all 129 shipped header names. Phase 1's header assertion is
therefore already proven, not merely specified.

`predict()` lists the test folder with `list_data_files`, echoes each `path.name` verbatim as
`file_id`, and predicts constant `Normal`. That branch is **not throwaway** — it stays permanently
as the "no checkpoint found" path, so the app cannot crash during the demo.

**Verified:** `outputs/predictions/rail_predictions.csv`, 68 rows, columns `file_id,prediction`
matching `reference/submission_format/`, names `Test1.csv` … `Test68.csv` exactly as shipped and
not zero-padded. 0.33 banked, technicality-zero impossible.

Note for later phases: `list_data_files` sorts lexicographically, so rows come back
`Test1, Test10, Test11, …`. Harmless because `file_id` is per-row, but never assume numeric order.

### Phase 1 — Load one file correctly — DONE

Done 2026-09-18. Written: `dataset.py` — `Recording` (frozen dataclass: `source_name`,
`speed_channel`, `vibration`, `shock`), `load_recording`, `load_labels`.

**Verified:** the 129 header strings match `EXPECTED_HEADERS` position for position across **all 272
training files** and a sample of the test folder, so the derived layout is now proven on the real
data rather than on one file. Vibration RMS 0.188 and shock RMS 1.374 against the 0.19 / 1.37 in
**Verified data facts** — the split is not transposed. Both side arrays hold 32 boxes; labels load
234 / 14 / 24. Shape, header and non-finite checks all raise.

Column indices are derived in `config.py` from the layout rule, never written by hand. The header
assertion stays on every load rather than running once: it costs microseconds and it is the only
thing standing between a re-ordered file and a model trained on the wrong rail.

### Phase 2 — Speed — DONE

Done 2026-09-18. Written: `speed.py` — `estimate_speed(channel)` only, as
`(edges / 2) / 90 × π × 0.85` over the window's own duration.

**Verified:** every figure in the speed table under **Verified data facts** reproduces exactly —
Normal 0.00 / 8.13 / 19.48 with 38 zero-edge files, Side I 9.70 / 12.96 / 18.60, Side II
11.69 / 14.00 / 18.51, 44 files under 0.5 m/s and all of them Normal, 139 files at or above
9.70 m/s.

One decision the spec left open: edges are counted against the **channel's own midpoint**,
`(min + max) / 2`, not a fixed 0.5. A test file recorded at another logic level still counts the
same edges, and a dead tachometer — held at one level, so `min == max` — counts zero rather than
noise. Zero edges return `0.0`, which callers read as "undefined" via `STATIONARY_SPEED_MS`.

### Phase 3 — Features — DONE

Done 2026-09-18. Written: `features.py` — `extract(recording) -> np.ndarray` and `FEATURE_NAMES`,
**342 features**, 0.09 s per recording.

**Verified:** 342 unique stable names, deterministic, finite on moving files. On the stationary
files exactly the **126 wavelength features are NaN** — 7 bands × (3 aggregates × 2 sides + 3
contrasts) × 2 channel types — with no infinities and no warnings. The design decision reproduces
off the packaged code: log₁₀(I/II) at 50–150 Hz aggregated by max gives −0.003 / +0.361 / −0.455
against the probe's +0.046 / +0.271 / −0.434, and by median −0.042 / −0.015 / −0.096 against
−0.052 / −0.014 / −0.089. The within-side max/median spread reproduces **exactly**: 19.3 on the
faulty side of a Side I file, 16.2 on the faulty side of a Side II file, ~12 healthy. Scoring is
under **Measured baseline**.

Two decisions the spec left open:

- **Undefined wavelength bands are NaN, not zero.** A zero claims a measurement we do not have and
  takes the log contrast to −infinity, which `HistGradientBoosting` rejects outright; NaN rides
  through the aggregates and the log untouched and the model routes it natively. A linear baseline
  in Phase 6 will need an imputer for those 126 columns.
- **Kurtosis is the Pearson form, not the excess form.** Every per-box quantity has to stay
  positive to survive the log in the cross-side contrast, and excess kurtosis goes negative.

**Original spec:** pure, recording in, `np.ndarray` out. Welch with **`nperseg ≥ 4096`**, then:

1. **Per box (64 per channel type):** band energies in **wavelength bands** (λ = v/f, speed-
   invariant, worth +0.06 over Hz) with Hz bands retained alongside — both are in the 0.682
   baseline. Plus RMS, kurtosis, crest factor, spectral centroid, dominant peak location.
2. **Per side (2):** aggregate the 32 boxes with **max and p90 as the primary statistics, median
   as context**. See **The core design decision** — this is the one instruction the first draft
   got backwards.
3. **Contrast:** `log(side_I) − log(side_II)` for every aggregate. The main signal.

Vibration and shock are featurised separately, never pooled — different scales, different physics.

### Phase 4 — Extract all, cache once — DONE

Done 2026-09-18. Written: the extraction half of `train.py` — `extract_features(directory)`,
`training_features(refresh=False)`, and a `main()` that rebuilds the cache.

**Verified:** `python -m src.rail.train` writes a 272×342 matrix to
`outputs/models/rail/features_train.npz` in 80 s (790 KB with the `files` and `columns` vectors),
and it reloads in **0.003 s**. Every cached file has a label. No subsampling path was built, per
the spec. Logged in [[jermaine]] as the first rail artefact under `outputs/`.

Three decisions the spec left open:

- **Recordings are streamed, not collected.** All 272 held at once is ~2.7 GB against 744 KB of
  features.
- **The cache holds all 272 files, duplicates included.** Dropping `Train115`/`Train187` is a
  fitting decision, not an extraction one — see Phase 5. A pre-filtered artefact would be silently
  wrong for anything that is not that one fit.
- **A stale cache raises rather than refreshing itself.** `training_features` compares the stored
  `columns` against `FEATURE_NAMES` and tells you to re-extract. Editing `features.py` and fitting
  on yesterday's columns is the exact failure that survives validation and only shows up in the
  submitted CSV ([[project-structure]] rule 11).

`predict.py` writes the same three-line loop rather than importing this one. Duplicating three
lines is cheaper than blurring a layer: `features.py` stays IO-free and `dataset.py` stays
feature-free ([[project-structure]] rule 7).

### Phase 5 — Leakage check — DONE

**Write:** the dedup step in `train.py`; one paragraph in the write-up.

Run and closed on 2026-09-18 — see **The files are independent** under **Verified data facts** for
the evidence. The chunking hypothesis is refuted on three independent tests, and exactly two
byte-identical pairs exist, both `Normal`.

All that remains is to act on it: **drop `Train115.csv` and `Train187.csv`** in the training loop,
and carry the finding into the write-up. Random stratified CV needs no grouping.

The cache built in Phase 4 deliberately keeps both files, so the drop happens **at fit time in
Phase 8**, where it is used. Measured cost of the drop: 0.778 → 0.750, which is fold-reshuffle
noise, not leakage — see **The noise floor**.

### Phase 6 — Model — DONE

Done 2026-09-18. Written: `model.py` — `build_classifier()` (the shipped flat 3-class
`HistGradientBoostingClassifier`, `class_weight="balanced"`, `max_iter=300`) and
`build_linear_baseline()` (impute → scale → L2 logistic). Both unfitted, no IO. lightgbm stays
excluded project-wide — its wheel needs libomp, which macOS does not ship ([[team-split]]).

**Verified:** the cache reproduces 0.778 ± 0.070 at 5×5 exactly. The linear pipeline converges in
59 of its 1000 iterations, so its number is a converged one.

**The phase's real finding: the model choice does not matter here.** See **Model comparison** below.
That is the write-up's model-selection line, and it means Phase 8 should not spend its budget
tuning the estimator.

### Model comparison

All on identical 10×5 folds, seed 42, off `features_train.npz`. **Differences are paired per fold**
— fold difficulty dominates both models' variance, so comparing two means against their marginal
spreads would hide a consistent difference. The reference is the shipped GBM at 0.758.

| Candidate | macro F1 | paired diff vs GBM (95% CI) | win/loss |
|---|---|---|---|
| **GBM, as shipped** | **0.758 ± 0.076** | — | — |
| Regularised linear, C=0.1 | 0.750 | **−0.008 ± 0.028** | 22/25 |

The interval straddles zero and the sign is a near-even split across 50 folds, so this is a genuine
tie and not merely an unresolved one — the paired test is sensitive to ±0.03 and still finds
nothing. Note the linear model had `C` chosen from {0.01, 0.1, 1, 10} on the same CV it is scored
against, where the booster ran at its defaults; that bias favours the linear model, which only
strengthens the conclusion that the booster wins nothing.

**What this implies:** the cross-side contrast features are separable enough that a penalised linear
model finds nearly all of it. The score lives in the features, not the estimator — so Phase 7 is the
only lever left on the metric, and the GBM is kept for the shipped model on the strength of
handling NaN natively rather than on accuracy.

### Phase 7 — Side I recall

**Write:** additions to `features.py`.

Still where the remaining score is, though less of it than when this plan was written. Normal is at
0.973 and Side II at 0.818; **Side I at 0.593** is 0.22 behind Side II, worth ~0.07 of the metric,
with 6 of its 14 files still called Normal. Untried ideas, cheapest first:

1. **A finer order spectrum** — the baseline integrates over 7 coarse λ bands, which smears a
   narrow corrugation peak. A proper order spectrum resampled onto a dense λ grid should isolate it.
2. **Harmonic structure at the passing frequency** — corrugation is periodic, so it should excite
   harmonics of `v/λ`. The current band energies integrate across them rather than exploiting the
   pattern.
3. **Envelope spectrum** — standard practice for modulated rolling-contact faults.
4. **Top-k boxes rather than the max alone** — max works, so the k next-largest may carry more.

**Done when:** Side I F1 has moved materially, or the ideas are exhausted and the result recorded
here. Parity with Side II would put macro F1 near 0.87. Note the bar has risen with the baseline:
against a ±0.07 spread, only a large move is readable, so compare on 10×5 fixed folds.

### Phase 8 — Train and tune against macro F1

**Write:** the rest of `train.py`. Phases 1–6 leave it holding only `extract_features`,
`training_features` and a `main()` that rebuilds the cache; everything below is new.

Starting state, so none of it is re-derived: the cache is 272×342 at
`outputs/models/rail/features_train.npz`, `model.build_classifier()` is the estimator,
`dataset.load_labels()` joins to the cached `files` vector, and the number to beat is **0.758 ±
0.076 at 10×5, seed 42**.

- **Repeated stratified k-fold, 10×5** — the plan said 5×5, but 5×5 read 0.778 for the same model
  and settings that 10×5 reads 0.758. Quote the 10×5 figure.
- **Drop `Train115.csv` and `Train187.csv` here**, at fit time — Phase 5's outstanding action. The
  cache deliberately keeps them.
- Score macro F1 directly. Never accuracy.
- Any threshold or decision rule is tuned on **out-of-fold** scores — and note that a threshold
  chosen on the same OOF scores it is then reported against is optimistic by roughly 0.04 here,
  measured. Quote the honest number.
- Report the fast-files-only figure alongside the headline, per **The speed confound**.
- Save the checkpoint, the fitted scaler, and the feature column names, so `predict.py` can assert
  the column order matches what was trained on.

**Done when:** an honest out-of-fold macro F1 with its spread, and a checkpoint on disk.

### Phase 9 — Real predict, then the app view

**Write:** `predict.py` (model path), `src/app/ui/rail.py`.

`predict()` loads the checkpoint, asserts feature-column order, and falls back to Phase 0's
constant `Normal` when no checkpoint exists. `file_id` is `path.name`, always — never reconstructed
with an f-string. The held-out names are `Test1.csv` … `Test68.csv`: capital T, **not**
zero-padded. Any `.lower()` or rebuilt name and §5.1 gives rail no score at all.

The view shows the prediction alongside **why** — the per-side band-energy contrast that drove the
call, and which axle boxes were the extreme ones, since the fault is localised. That is the
explainability line in Problem Fit, and it films well for the demo video.

**Done when:** the 68 test files run *through the app*, not a notebook, and the CSV passes
`validate.py`. That is the definition of done for the subsystem ([[team-split]]).

## Negative results

Recorded so they are not re-attempted, and for the write-up's model-comparison line.

### Per-side binary framing — refuted

The idea: each file yields two side-samples, so a `Normal` file gives two healthy sides and a
`Side I` file one corrugated plus one healthy. That turns 272 samples with 14 in the rarest class
into 544 with 38 positives, on the argument that corrugation on rail I and rail II are the same
phenomenon measured by different boxes. A file's label is then recovered by thresholding the two
side scores: neither over threshold → `Normal`, else the higher-scoring side.

Built and tested on the identical feature set at identical dimensionality (252 features each):

| Framing | macro F1 | Side I F1 |
|---|---|---|
| **Flat 3-class** | **0.682 ± 0.018** | 0.333 |
| Per-side binary, threshold tuned on OOF | 0.683 ± 0.004 | 0.357 |
| Per-side binary, fixed threshold 0.5 | 0.646 ± 0.025 | — |

It ties at best, and the tuned figure is optimistic because the threshold is chosen on the same
scores it is reported against. At an honestly chosen threshold it is **worse**.

**Why it fails:** the two sides are not symmetric. Side I files show a +0.271 log-ratio where Side
II files show −0.434 — Side II's signature is ~1.6× stronger. Either Side I corrugation is
physically milder here or those 14 files are simply harder, but either way pooling makes the
positive class heterogeneous rather than larger.

Note for anyone re-running it: the per-side framing **requires `StratifiedGroupKFold` grouped on
file**, or the healthy side of a fault file leaks its partner across folds.

### Explicit speed as a feature — no effect

0.682 → 0.680. The wavelength bands already carry the speed information. Keep the features, drop
the column.

### Smaller `min_samples_leaf` for the 14 Side I files — refuted, and the reason is not known

The argument, which still looks right: `HistGradientBoosting` defaults to `min_samples_leaf=20` and
counts **raw** samples, not class-weighted ones — verified in the sklearn grower source,
`left_child_node.n_samples < self.min_samples_leaf * 2`. There are only 14 Side I files in the whole
dataset, so no leaf can ever hold Side I alone whatever the trees find. Lowering it should free the
booster to isolate the class.

It does not. 10×5, identical folds:

| `min_samples_leaf` | macro F1 | Side I F1 (single 5-fold pass) |
|---|---|---|
| **20 (default, kept)** | **0.758 ± 0.076** | 0.593 |
| 10 | 0.749 ± 0.102 | 0.560 |
| 5 | 0.745 ± 0.100 | 0.500 |
| 3 | 0.742 ± 0.101 | 0.643 |

Macro F1 drifts down monotonically and the spread widens from 0.076 to ~0.100 — deeper trees buy
variance. The Side I column is a single 5-fold pass on 14 files, where one file changing fold moves
recall by 1/14 = 0.07, so its ordering carries no information; do not read 0.643 as an improvement.

Paired against the default on the same 50 folds, `min_samples_leaf=3` is **−0.016 ± 0.023** and
loses 26 folds to 12. The interval grazes zero, so call it "no gain, probably a small loss" — but
the direction is not in doubt and there is nothing here to chase.

**Why it fails is unknown.** An earlier draft of this entry claimed `class_weight="balanced"` makes
the raw-count constraint moot — that is wrong, and the source check above is what disproves it. The
untested hypothesis is that leaf size was never the binding constraint: if no feature split
separates Side I in the first place, a finer leaf has nothing to isolate it with. That would make
this a **Phase 7 problem, not a hyperparameter one**, which is consistent with the model comparison
finding the estimator irrelevant. Treat it as a hypothesis, not a result.

## Open questions

- **Why Side I is weaker than Side II.** Unknown — physical (curve direction, attack angle on the
  inner rail, which §1.1 of the info kit does discuss) or an artefact of these 14 files. Resolving
  it would likely resolve Phase 7.
- **Whether the held-out test set shares the speed distribution.** If it was drawn from the same
  pool the confound is harmless. Unknowable before the deadline — which is the reason to quote the
  fast-files-only figure rather than rely on the shortcut.

## Standing constraints

- **No improvement under ±0.04 is real.** See **The noise floor**. 10×5 CV on fixed folds, or the
  Phase 7 work will chase noise.
- Nothing in Phases 0–9 touches `common/`, so no [[jermaine]] log entry is needed unless that
  changes.
- The floor is banked at 0.33 in Phase 0 and the packaged feature set reaches **0.778** as of
  Phase 4. If rail is still fighting back late, ship the Phase 6 baseline and stop — Phase 7 is
  upside, not a dependency.

See also: [[team-split]], [[project-structure]], [[problem-statment]], [[jermaine]].
