# Rail Corrugation — Build Plan

The ten phases that take `src/rail/` from empty to a validated `rail_predictions.csv`, the design
decisions behind them, and the measurements those decisions rest on. Jermaine owns this package
end to end ([[team-split]]). Written 2026-09-18, revised the same day against the data, and closed
2026-09-19 when Phase 7 finished.

**All ten phases are done.** The shipped model is 228 features at **0.750 ± 0.114 per fold / 0.757
pooled**, 0.770 / 0.777 on the files fast enough that "slow ⇒ Normal" is unavailable. Read
**Phase 7** before reopening any feature question: all five of its candidate blocks are refuted with
the measurements to show it, and the shuffled control under **The noise floor** says what a sixth has
to beat.

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

Predicting `Normal` everywhere gives ~86% accuracy and **0.308 macro F1**. The 14 Side I files carry
a third of the score between them, roughly 2.4% of the rail metric each.

*Corrected 2026-09-19: this figure was written as 0.33 here and in six other places, from
`(1.0 + 0 + 0) / 3`. **`Normal`'s own F1 is 0.924, not 1.0** — predicting it everywhere buys perfect
recall at 232/270 = 0.859 precision — so the floor is `0.924 / 3 = 0.308`, measured with
`sklearn.f1_score` on the real labels. In general the floor is `2p/(p+1)/3` for a `Normal` share of p,
so **0.333 is an unreachable limit**: it needs p = 1, which would mean no fault files exist at all. On
the held-out set the exact value depends on its own balance, which we cannot know — at a similar ~86%
it is ~0.31. The correction makes every improvement in this file slightly **larger** than claimed.*

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

**Max and p90 are the signal; median is context.** Phase 7 took the next step and measured whether
that context earns its place: it does not. Dropping all 114 median columns is a tie on macro F1 with
Side I consistently better, so the shipped set is max and p90 only — 228 features. The sentence above
is now literally the feature set rather than a description of its emphasis.

**But the contrast alone is not enough, and that corrects the paragraph above it.** Scored on the 114
cross-side contrast columns with every per-side absolute removed, the model collapses to **0.499
macro F1, Side I 0.114** — it loses 48 of 50 folds and all 10 repeats. So "the contrast cancels every
confounder and is therefore the signal" is half the story: the contrast is where the *discrimination*
lives, but the model needs each side's absolute level alongside it to know what a given ratio means at
that excitation. A −0.3 dex asymmetry on a near-silent rail and the same ratio at line speed are not
the same evidence, and only the absolutes distinguish them. Measured 2026-09-19; see **Negative
results**.

## Measured baseline

Four numbers now. **The Phase 7 figure is the one to quote.** The three below it are kept because
the per-class table, every negative result and the noise-floor argument are all stated against them.

### The shipped figure — 0.750 (Phase 7)

Everything as shipped after Phase 7 dropped the median aggregate: `features.py`'s **228** features,
`model.build_classifier()`, the two duplicates dropped, 10×5 repeated stratified CV, seed 42.
Reproduced three times — `confirm.py` against the banked folds, `python -m src.rail.train --refresh`,
and the baseline re-capture — identical to three decimals in every column each time.

| Subset | macro F1, per fold | pooled | Normal | Side I | Side II |
|---|---|---|---|---|---|
| **270 files, duplicates dropped** | **0.750 ± 0.114** | 0.757 | 0.966 | **0.515** | 0.790 |
| files ≥ 9.70 m/s (n=138) | 0.770 ± 0.103 | 0.777 | 0.937 | 0.560 | 0.835 |

Mean confusion per repeat, 270 files (rows true, cols predicted):

```
Normal     226.1     1.7     4.2
Side I       6.8     6.0     1.2
Side II      3.3     1.5    19.2
```

**Read this as a tie with a smaller model, not as a gain.** Paired against the 342-feature set on
identical folds it is **+0.0095** at the shipped settings and seed 42, and **+0.0072 on 100 folds at
seed 7**, both intervals straddling zero — under the ±0.03 bar this plan sets for itself. What is solid is the direction: 12
paired readings across three runs and two subsets, every one of them positive, and the worst reading
is a tie. It ships because 228 features that tie 342 are the better model, not because the score
moved. See **Phase 7** for the whole measurement.

**The submitted CSV did not change by a single row.** All 68 held-out calls are identical to the
342-feature model's, 60 Normal / 5 Side I / 3 Side II, file for file — so this carried no risk to the
submission, and the CV difference is not visible in the artefact that gets graded. Worth stating
plainly rather than implying the held-out score moved.

**Two number collisions to watch when quoting from this file into the write-up.** "0.750 ± 0.114" names
*both* the shipped 228-feature figure above and the 342-feature figure measured before Phase 9's
empty-band fix — they are separable only by the pooled column, 0.757 against 0.761. And "114" is both
the 342-era contrast count and the number of median columns Phase 7 removed. Neither is an error; both
are easy to quote as one.

### The 342-feature figure — 0.740 (Phases 8–9), superseded

The same harness before Phase 7 removed the median aggregate. Every comparison in **Model
comparison**, **Negative results** and **The noise floor** is differenced against these folds.

| Subset | macro F1, per fold | pooled | Normal | Side I | Side II |
|---|---|---|---|---|---|
| **270 files, duplicates dropped** | **0.740 ± 0.114** | 0.752 | 0.963 | **0.494** | 0.798 |
| files ≥ 9.70 m/s (n=138) | 0.754 ± 0.116 | 0.764 | 0.934 | 0.520 | 0.838 |

Before the empty-band fix below, the same run read 0.750 ± 0.114 / 0.761 on the full set, and on all
272 files with the duplicates kept it read 0.758 ± 0.076 — reproducing Phase 6's reference **to
three decimals on both figures**, which is what licensed reading the rest as measurements rather
than as a new harness disagreeing with an old one.

**The empty-band fix cost 0.010, and that 0.010 was the speed confound.** A wavelength band narrower
than Welch's 2.44 Hz bin spacing used to integrate to exactly 0.0; it now returns NaN (see the Phase
3 defect note). Three slow training files were affected. Removing it moved the full-set figure
0.750 → 0.740 and left the fast-files-only figure **identical to three decimals in every column** —
which is the proof that what those zeros encoded was not rail asymmetry but "this file is slow", a
marker only Normal files could carry. We paid 0.010 of measured score to stop reading a confound as
a physical measurement. Worth saying plainly in the write-up.

**The fast-only figure is *above* the headline**, not merely within noise of it — by 0.014 here and
by 0.020 on the shipped 228-feature set. The subset drops 132 Normal files, most of the near-silent
stationary cluster among them, and the model does better without them. Nothing about this model is
carried by the slow files.

**Two different quantities, and the gap is not noise.** "Per fold" is the mean of 50 fold-level
macro F1 scores; "pooled" scores each repeat's complete out-of-fold set once and averages the ten.
Macro F1 is not linear in the confusion matrix, so the two do not have to agree: a fold holding 3
Side I files reports that class as confidently as it reports its 47 Normal ones, and when it gets
none of the 3 the fold contributes a zero that pooling never produces. **Pooled is what the
organisers compute**, and here it reads 0.011 *higher* on the deduped set. Report the per-fold
figure for continuity with everything on record — every comparison in this plan is differenced
against fold scores — and the pooled figure as the expected held-out number.

Mean confusion per repeat, 270 files, 342 features (rows true, cols predicted). Against the shipped
set above, Side I goes from 5.6 correct to 6.0 and from 7.5 called Normal to 6.8:

```
Normal     226.2     2.1     3.7
Side I       7.5     5.6     0.9
Side II      4.0     1.0    19.0
```

**Correction to the Phase 4 per-class table: Side I is 0.494, not 0.593.** That 0.593 came from a
single 5-fold pass, where one of 14 files changing fold moves the class by 0.07. The figures above
average ten *complete* out-of-fold sets, so they carry ~1/√10 of that jitter. The same measurement
on all 272 files read 0.499 against the 0.593 quoted — so Phase 4's number was optimistic by 0.09,
which is most of what a Phase 7 idea would have to beat. **Never quote a per-class figure from one
pass again.**

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

**Added 2026-09-19, and it is the single most useful number Phase 7 produced: widening the matrix
buys score on its own.** The same 36 candidate columns, with their **rows shuffled** so they describe
the wrong files, scored **+0.0116 macro F1 and +0.0268 Side I** against the shipped set on the full
270. On the fast subset the same control read −0.0107 / −0.0077.

**Be precise about what it beat**, because the loose version of this sentence is wrong: +0.0116 beat
**six of the eight specs measured that day**, losing only to the envelope block at +0.0199 and the
confounded fine-wavelength block at +0.0250. What it beat outright is **every block that survived its
own confound check** — the fixed fine-wavelength block landed at +0.0045 and the fixed harmonic block
at +0.0054, both below the noise columns.

So 36 columns of *nothing* move macro F1 by ±0.01 and Side I by ±0.03 depending on the subset, at 270
files with 14 in the minority class. Three consequences:

- **Every candidate that adds columns must be priced against its own shuffled control**, not against
  zero. A block that gains +0.02 while its shuffle gains +0.012 has demonstrated +0.008.
- It explains why so many candidates read as small wins and none replicated: the booster's fold-level
  variance responds to matrix width, and with 14 Side I files a single reassignment is worth 0.07.
- **Narrowing is the cleaner lever.** A change that removes columns cannot borrow this effect — it
  runs against it — which is most of why the median drop is believable where the additions were not.

## The speed confound

Given the table above, a model *could* score respectably by learning "slow ⇒ Normal". Measurement
says this one does not — but one feature was quietly doing it, and had to be fixed:

- Adding speed as an explicit feature changes nothing: 0.682 → 0.680 on the probe.
- Restricted to the files at or above 9.70 m/s, where the shortcut is unavailable by construction,
  it reaches 0.660 on the probe, 0.765 on the Phase 4 feature set, 0.754 against the 342-feature
  model's 0.740, and **0.770 against the shipped model's own 0.750**.

**Phase 7 is the strongest evidence in this file that the subset check is worth its runtime.** Of five
candidate feature blocks, **two gained on the full 270 and reversed on the 138 fast files** — envelope
spectrum +0.020 → −0.005 and harmonic structure +0.010 → −0.006. Both of those full-set gains were
gains on slow Normal files. **A candidate that only helps where the slow files are has not helped.**

A **third** block had a speed marker inside it without showing that signature: the first
fine-wavelength version read +0.025 full and +0.033 fast, so the subset check passed it. What caught
that one was reading its columns directly — see Phase 7's point 2. **The subset check is necessary and
not sufficient**, which is the reason the per-column confound check exists alongside it.

**The fast-only figure is now above the headline, not merely within noise of it**, and Side I and
Side II both score higher there than on the full set. The subset removes 132 Normal files including
the near-silent stationary cluster, which was the part of Normal that came free. The shortcut is not
carrying the model; it was diluting it.

**One feature was encoding speed, and removing it cost 0.010.** The empty-wavelength-band bug under
Phase 3 gave three slow files a *band-energy* contrast of exactly 0.0 — a value no fault file could
produce, since every fault file is fast enough to resolve the band. (Scope that to band energies: the
`peak_hz` contrasts are exactly zero on 251 of 272 files for an unrelated and legitimate reason, and
the correction is under **Phase 3**.) That is the confound reappearing *inside* a
feature that claims to measure rail asymmetry. It is fixed, the fast-only figure did not move by a
thousandth in any column, and the full-set figure dropped by exactly the amount the confound was
worth. **That pair of facts is the single best piece of evidence we have that the rest of the score
is real**, and it belongs in the write-up.

The fast-only figure stays the one to quote alongside the headline, and that belongs in the write-up
explicitly: a judge who spots the confound unaided will otherwise assume the worst. Methodological
soundness is graded alongside the metric.

`config.FAST_SPEED_MS` owns the 9.70 threshold and `train.py` reports the subset on every run, so
this cannot quietly stop being checked.

## Files, and the one thing each does

Nothing outside this list gets created.

| File | Purpose | Touches disk | State |
|---|---|---|---|
| `src/rail/config.py` | every rail dimension: column layout, side membership, sample rate, wheel geometry, band edges, Welch parameters, label vocabulary, hyperparameters | no | ✓ |
| `src/rail/dataset.py` | file → arrays; labels → DataFrame. No features. | reads only | ✓ |
| `src/rail/speed.py` | tachometer square wave → m/s. Nothing else. | no | ✓ |
| `src/rail/features.py` | arrays → fixed-length feature vector. No IO, no model. | no | ✓ |
| `src/rail/model.py` | the estimator and its hyperparameters. | no | ✓ |
| `src/rail/train.py` | CV, fit, write checkpoint and feature cache | writes `outputs/` | ✓ |
| `src/rail/predict.py` | `predict(inputs: list[Path]) -> DataFrame` | writes `outputs/` | ✓ |
| `src/rail/explain.py` | the same run as panels the app draws. No IO beyond reading its inputs. | no | ✓ |
| `src/rail/validate.py` | is this upload a rail recording? The header, and nothing else. | reads only | ✓ |

`common/config.py` already owns the paths (`TRAIN_PATHS`, `TEST_PATHS`, `LABEL_PATHS`,
`MODEL_DIRS`, `PREDICTION_PATHS`) and `RANDOM_SEED`; `common/io.py` already owns `read_table` and
`list_data_files`. Nothing here restates any of them ([[project-structure]] rules 4 and 5).

`subsystem.py` is cut. The integration contract is two functions, both found by `importlib` from
`src/app/services.py` and neither registered anywhere: `predict.predict(inputs: list[Path]) ->
DataFrame`, which is required, and `explain.explain(inputs: list[Path]) -> list[dict]`, which is
optional and returns `metrics` / `bullet` / `bars` / `line` panels the app draws without importing
rail. **`src/app/ui/rail.py` is not part of this and must never be written** — the app does not have
per-subsystem view files any more.

## The phases

Status as of 2026-09-19. **All ten phases are done. Rail is finished.**

| | Phase | State |
|---|---|---|
| 0 | Bank the floor | **done** — `config.py`, `predict.py`, 0.31 banked |
| 1 | Load one file correctly | **done** — `dataset.py` |
| 2 | Speed | **done** — `speed.py`, table reproduced exactly |
| 3 | Features | **done** — `features.py`, 342 features, now 228 |
| 4 | Extract all, cache once | **done** — `train.py`, 545 kB cache, 0.003 s reload |
| 5 | Leakage check | **done** — split is sound, 2 duplicates to drop at fit time |
| 6 | Model | **done** — `model.py`, 0.758 at 10×5; estimator choice is a tie |
| 8 | Train and tune | **done** — 0.740 ± 0.114 at the time, checkpoint on disk; now 0.750 |
| 9 | Real predict, app view | **done** — 68 rows through the app, `explain.py` panels |
| 7 | Side I recall | **done** — five blocks refuted, the median aggregate dropped, 0.750 |

**Rail is shipped.** 0.750 ± 0.114 per fold / 0.757 pooled is submitted rather than measured, the app
renders it, and the phase list is closed. One thing to be precise about: **the app is Wayne's and is
not on this branch** — `src/app/` here holds a `.gitkeep`. "Through the app" throughout this file means
`src/app/services.py` read out of `origin/wayne` and driven against rail's real modules, which is the
caller that matters; it is not something `jermaine-rail` can run on its own.

*Superseded 2026-09-19: rail is merged (PR #5), so the app, `src/door/`, `src/acv/` and
`src/submission/` are all on this branch and the app runs here. Two capabilities had appeared in it
since Phase 9 and rail was the only subsystem not using either — a `verdict` panel, without which the
default **Answer** view drew "This system does not summarise itself yet" over a working model, and
`src/<sub>/validate.py`, without which a wrong upload was reported as an app failure rather than as a
file that belongs to another system. Both are now supplied; see [[jermaine]]. `python -m
src.submission.validate` reads `rail ok`, and the 68-row CSV did not change. Still not rail's:
`predictions.zip` (one person zips once all four validate) and the demo video.*

**Do not reopen the feature search without reading Phase 7 first.** All five blocks it tested are
refuted with the measurements to show it, and the shuffled control under **The noise floor** says what
a sixth would have to beat.

### Why 8 and 9 ran before 7 — closed, and it paid for itself

The plan originally ordered these 7 → 8 → 9 and was reordered to 8 → 9 → 7, on the argument that
0.758 was measured but **not banked**: `predict.py` returned constant `Normal`, no checkpoint
existed, and rail would have scored 0.31 if the deadline had arrived. Converting a measured number
into a submitted one was worth ~+0.42 where Phase 7 is upside worth perhaps +0.05.

*The reorder was right for a second reason nobody guessed: Phase 7 turned out to be worth **+0.010 and
not provably even that**, and it changed no held-out prediction at all. Had it run first it would have
spent the same day for the same nothing, with the 0.31 fallback still on disk underneath it.*

**The reorder earned more than that.** Phase 9 turned up an integration bug that would have taken
rail to **zero** in the app — `predict` took a folder path where `services.run_prediction` passes a
`list[Path]`, which `list_data_files` raises on. It surfaced only because the phase ran early and
against Wayne's real `services.py` rather than against rail's own `main()`. Had Phase 7 gone first,
that bug would have been sitting underneath a better model instead of a shipped one.

**The lesson generalises, and it is the one worth carrying into Phase 7:** a subsystem is not
verified by its own entry point. Run it through the caller that will actually call it.

### Phase 0 — Bank the floor — DONE

Done 2026-09-18. Written: `src/rail/config.py`, `src/rail/predict.py` (fallback path only).

`config.py` owns every rail dimension and **derives** the column layout from the info-kit rule
rather than listing it — box order, channel indices, side membership, and `EXPECTED_HEADERS`, which
was verified string-for-string against all 129 shipped header names. Phase 1's header assertion is
therefore already proven, not merely specified.

`predict()` lists the test folder with `list_data_files`, echoes each `path.name` verbatim as
`file_id`, and predicts constant `Normal`. ~~That branch is **not throwaway** — it stays permanently
as the "no checkpoint found" path, so the app cannot crash during the demo.~~

*Reversed 2026-09-19, and the reasoning above was wrong in a way worth keeping visible. The fallback
was indistinguishable from a working model in every caller that mattered: the app drew 68 rows,
`src/submission/generate.py` wrote them, `src/submission/validate.py` passed them, and the only
warning lived in `predict.py`'s `main()`, which the submission path never calls. So the branch that
existed to protect the demo would instead have packaged a 0.308 submission in silence. Rail now
raises `FileNotFoundError` like Door and SHM, which costs the banked floor — untrained, rail scores 0
rather than 0.308 — and buys the guarantee that nobody can submit a number no model produced. The
floor's real value was always Phase 0's other half: a schema-correct CSV with the right `file_id`
spelling, which cannot be un-learned. See [[jermaine]].*

**Verified:** `outputs/predictions/rail_predictions.csv`, 68 rows, columns `file_id,prediction`
matching `reference/submission_format/`, names `Test1.csv` … `Test68.csv` exactly as shipped and
not zero-padded. 0.31 banked, technicality-zero impossible.

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
**342 features** (228 since Phase 7), 0.09 s per recording.

**Verified:** 342 unique stable names, deterministic, finite on moving files. On the stationary
files exactly the **126 wavelength features are NaN** — 7 bands × (3 aggregates × 2 sides + 3
contrasts) × 2 channel types — with no infinities and no warnings.

The design decision reproduces off the packaged code: log₁₀(I/II) at 50–150 Hz aggregated by max gives
−0.003 / +0.361 / −0.455 against the probe's +0.046 / +0.271 / −0.434, and by median
−0.042 / −0.015 / −0.096 against −0.052 / −0.014 / −0.089. The within-side max/median spread reproduces
**exactly**: 19.3 on the faulty side of a Side I file, 16.2 on the faulty side of a Side II file, ~12
healthy. Scoring is under **Measured baseline**.

*Two figures in this section moved when Phase 7 dropped the median aggregate, re-measured 2026-09-19:
the shipped set is **228 features**, and a stationary file now reads **84 NaN** — 7 × (2 × 2 + 2) × 2 —
with `Train51` at 12, its single unresolvable band. Unchanged: the 19 per-box quantities, the NaN rule,
and both decisions below. One consequence for anyone re-checking the numbers in the paragraph above —
**the median rows no longer come off the packaged code**, since no median column is built; they have to
be computed by hand from `features.quantities`, which is what produced them in the first place.*

Two decisions the spec left open:

- **Undefined wavelength bands are NaN, not zero.** A zero claims a measurement we do not have and
  takes the log contrast to −infinity, which `HistGradientBoosting` rejects outright; NaN rides
  through the aggregates and the log untouched and the model routes it natively. A linear baseline
  in Phase 6 will need an imputer for those 126 columns — **84** since Phase 7 dropped the median
  aggregate.
- **Kurtosis is the Pearson form, not the excess form.** Every per-box quantity has to stay
  positive to survive the log in the cross-side contrast, and excess kurtosis goes negative.

**Defect found and fixed 2026-09-18 (Phase 9), and the impact was not nil.** The NaN rule above
originally fired only below `STATIONARY_SPEED_MS`. A wavelength band narrower than Welch's 2.44 Hz
bin spacing catches no bin at all and integrated to **exactly 0.0**, which the contrast read as
log(0)−log(0) = 0: "the two sides measured identical", the precise claim the NaN decision exists to
avoid. The 0.30–0.50 m band is unresolvable below ~1.83 m/s, and exactly 3 training files
(`Train51`, `Train52`, `Train118`, at 1.29–1.34 m/s) carried it.

`_band_energy` now returns NaN for an empty band, on the same argument as the stationary branch.
The first estimate — "3 slow Normal files, impact nil" — was **wrong**: the fix cost 0.010 of macro
F1, because an exactly-zero *band-energy* contrast was a marker no fault file could carry. See **The
shipped figure**. Verified after the fix: those 3 files read NaN in all 64 boxes of that band, and
files at 1.68–1.91 m/s still resolve it normally.

**Corrected 2026-09-19, and the earlier wording of this paragraph was wrong.** It said "no file reads
an exact zero", full stop. Measured across all 272 training files: **251 of them carry an exactly-zero
contrast** — 219 Normal, 22 Side II, 10 Side I — in **432 cells, every one of them a
`*_contrast_*_peak_hz` column**. The mechanism is not the defect above and is worth naming, so nobody
goes hunting for a bug that is not there: `peak_hz` is the only quantity in the vector with a
low-cardinality codomain. `max_peak_hz` is exactly an integer multiple of the 2.44 Hz Welch bin, so the
two sides' loudest bin simply coincides — 225 of 544 cells — and `p90_peak_hz`, which interpolates and
is not a bin multiple, still collides on 207 because the 32 per-side peak frequencies are heavily tied.
225 + 207 accounts for all 432. **Among the 56 band-energy contrasts and the 16 rms / kurtosis / crest
/ centroid contrasts there are no exact zeros at all**, on the 272 training files *and* on the 68 test
files.

Three limits on that, all of which matter more than the headline:

- **The fix established it for the band energies only.** `_band_energy` is what changed; that the four
  waveform and spectral scalars carry no zeros is incidental — those columns were never at risk.
- **It is a measured property, not one the code enforces.** `NUMERICAL_FLOOR` is a second route to an
  exactly-zero contrast that `_band_energy` does not guard: if both sides' energy fell to ≤ 1e-12,
  `np.maximum(x, floor)` would clamp both and the contrast would read 0.0 — the same "both rails
  measured the same thing" claim, arriving from the other side. Nowhere near live here: the smallest
  per-side band energy in the cache is **5.3e-6**, some five million times the floor.
- Keep the scope when quoting it. "No *band-energy* contrast is exactly zero" is true and
  load-bearing; "no contrast is exactly zero" is false on 251 of 272 files.

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
`outputs/models/rail/features_train.npz` in 80 s (790 KB with the `files` and `columns` vectors;
272×228 and 545 kB since Phase 7 — 496 kB of it the matrix — extracting in 155 s),
and it reloads in **0.003 s**. Every cached file has a label. No subsampling path was built, per
the spec. Logged in [[jermaine]] as the first rail artefact under `outputs/`.

Three decisions the spec left open:

- **Recordings are streamed, not collected.** All 272 held at once is ~2.7 GB against 496 kB of
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

Nor do the booster's own hyperparameters move it. Five settings, same 50 folds, paired against the
default:

| Setting | macro F1 | paired diff | win/loss |
|---|---|---|---|
| `max_iter=100` (sklearn's default) | 0.759 | +0.001 ± 0.008 | 4/1 |
| `max_leaf_nodes=8` | 0.750 | −0.008 ± 0.014 | 4/8 |
| `learning_rate=0.05` | 0.750 | −0.008 ± 0.014 | 5/10 |
| `l2_regularization=1.0` | 0.745 | −0.013 ± 0.023 | 14/18 |
| `min_samples_leaf=3` | 0.742 | −0.016 ± 0.023 | 12/26 |

**Nothing beats the default, in either direction — capacity up or capacity down.** Read the win/loss
counts: they sum to far fewer than 50 because most folds score *identically*, meaning the models
predict the same labels. `max_iter=100` ties on 45 of 50 folds outright, which says the booster has
saturated long before its 300th tree.

Two things follow. **`config.MODEL_MAX_ITER = 300` buys nothing** — 100 is the same number for a
third of the fit time, worth taking if Phase 7 iterates a lot (not changed yet; it would make the
CV loop ~3× faster and the accuracy is identical within ±0.008). And the search is closed: no more
estimator tuning in Phase 8.

**What this implies:** the features are separable enough that a penalised linear model finds nearly all
of it, and no amount of booster capacity adds to it. The score lives in the features, not the estimator
— so Phase 7 was the only lever left on the metric, and the GBM is kept for the shipped model on the
strength of handling NaN natively rather than on accuracy.

*Amended 2026-09-19: this paragraph used to say "the cross-side contrast features are separable
enough". Phase 7 measured the contrast columns alone at 0.499, so the separability is not theirs alone
— see **The core design decision**. The conclusion about the estimator is untouched.*

**Caveat for the write-up: every row of both tables was measured ad hoc.** `build_linear_baseline`
has no caller in the package and `train.py` runs one estimator only, so nothing here re-runs from a
command. That is a deliberate consequence of the search being closed — a permanent comparison path
would be dead code for a question nobody is reopening — but "model comparison/benchmarking" is a
Problem Fit line item, so the numbers have to be quoted from here rather than demonstrated.

### Phase 7 — Side I recall — DONE

Done 2026-09-19. **Written: one constant and the lookup that reads it.** `config.AGGREGATES =
("max", "p90")`, and `features.py` builds `_AGGREGATES` by looking each of those names up in a
catalogue of the aggregates that exist — so the names and the values cannot disagree, and an
uncatalogued name raises at import rather than mislabelling a column. That is the whole code change,
and it takes the feature set from 342 columns to **228** by dropping every median aggregate.

**All five candidate blocks are refuted** — four outright, and the fifth only ever looked like a win
because of a confound inside it. The change that shipped came from the opposite direction: **taking
columns away, not adding them.**

| | Shipped | Side I | Side II |
|---|---|---|---|
| before, 342 features | 0.740 ± 0.114 / 0.752 pooled | 0.494 | 0.798 |
| **after, 228 features** | **0.750 ± 0.114 / 0.757 pooled** | **0.515** | 0.790 |
| after, fast files only | 0.770 ± 0.103 / 0.777 pooled | 0.560 | 0.835 |

**All 68 held-out predictions are unchanged** — 60 Normal / 5 Side I / 3 Side II, file for file. The
phase cost nothing and risked nothing in the submitted artefact; what it bought is a third fewer
features for the same calls, and a great deal of evidence about what does *not* work.

#### What was tested, and what each one measured

**Count the population once, because three different numbers are all true of it and the write-up has to
pick the right one: five candidate blocks, measured as eight specs** (H and F were each re-measured
after a defect was fixed in them, and F once more with its per-side absolutes removed), **plus three
narrowings below — eleven looks in total.** Every diff is against the shipped set re-measured at
`max_iter=100` (a measured tie with 300, **Model comparison**), paired per fold on identical 50-fold
splits, with the fast subset reported alongside.

| Block | full-set paired | fast-subset paired | Side I full / fast | verdict |
|---|---|---|---|---|
| **T** t statistic + AUC over all 64 boxes | −0.013 | −0.015 | −0.032 / −0.030 | refuted |
| **L** within-side max/median, p90/median | −0.007 | −0.025 | −0.010 / −0.046 | refuted |
| **E** envelope spectrum, λ bands | +0.020 22/9 | −0.005 17/20 | +0.021 / −0.030 | slow-file gain |
| **H** harmonic structure at `v/λ` | +0.010 14/9 | −0.006 12/16 | +0.030 / −0.018 | slow-file gain |
| **H** same, baseline edge-padded | +0.005 17/13 | −0.006 12/16 | +0.027 / −0.018 | refuted |
| **F** fine λ contrast, first version | +0.025 28/12 | +0.033 26/12 | +0.031 / +0.029 | **confounded** |
| **F** same, on a fixed λ grid | +0.005 22/13 | +0.015 22/15 | +0.001 / **−0.011** | refuted |
| **F** same, contrast columns only | +0.004 21/14 | +0.011 20/15 | +0.010 / +0.006 | refuted |
| *shuffled control, 36 junk columns* | *+0.012 18/10* | *−0.011 10/15* | *+0.027 / −0.008* | the zero point |

Three things to take from that table:

1. **E and H gained only where the slow Normal files are.** Both reverse on the fast subset. See
   **The speed confound**.
2. **F's first version was the empty-band bug rebuilt.** It summarised the contrast curve on Welch's
   own bins, and the number of bins inside the wavelength window is proportional to speed — 20 bins at
   walking pace, 384 at line speed. Its `share_above`/`run_above` columns were therefore exactly 0.0
   on 8 files, all slow, all Normal: a value no fault file in that column can produce, which is
   precisely the marker the plan paid 0.010 to remove in Phase 9. Resampling onto a fixed 64-point λ grid removed it — the
   exact zeros moved to 1.88–18.6 m/s and onto Side I and Side II files, and the strongest column's
   ability to tell slow from fast fell from 0.888 to 0.57 — and with the mechanism gone, **the gain
   went with it**: +0.033 → +0.015 on the fast subset, with Side I reversing to −0.011.
3. **The shuffled control is why none of the survivors are believable.** Same 36 columns, rows
   permuted so they describe the wrong files, and it scored +0.012 on the full set — above six of the
   eight specs measured, and above every one that survived its own confound check. Anything in the
   ±0.01–0.03 range here is matrix width, not physics.

#### The change that shipped came from narrowing

Once the control showed width buys score, the obvious test was the other direction. Three narrowings,
same folds, same pairing:

| Narrowed set | full-set paired | fast-subset paired | Side I full / fast |
|---|---|---|---|
| `only:contrast`, the 114 contrast columns alone | **−0.238** 2/48 | −0.242 1/49 | −0.366 0/10 / −0.273 0/10 |
| **`drop:median`, the 228 max and p90 columns** | **+0.016** | **+0.022** | **+0.049 8/1 / +0.044 8/2** |
| `only:vibration`, 171 columns | +0.006 | −0.031 15/24 | +0.007 / −0.065 1/8 |

`only:contrast` collapsing to 0.499 is the important negative — it corrects a claim this plan made for
two days, and it is written up under **The core design decision**.

`drop:median` was then confirmed twice, because the best of eleven looks is optimistic by construction:

| Run | full-set | Side I | fast-subset | Side I |
|---|---|---|---|---|
| screening, `max_iter=100`, seed 42, 50 folds | +0.0155 | +0.0487 8/1 | +0.0216 | +0.0435 8/2 |
| confirmation, `max_iter=300`, seed 42, banked folds | +0.0095 | +0.0217 7/2 | +0.0164 | +0.0399 8/2 |
| **replication, `max_iter=300`, seed 7, 100 fresh folds** | **+0.0072** | +0.0178 10/6 | **+0.0019** | +0.0097 10/6 |

The replication is the one that counts: new folds, a new seed, both feature sets re-measured on them,
and nothing about them chosen by any earlier decision. It halves the effect — the signature of
regression to the mean after selection — and leaves **a tie on macro F1 with a consistently positive
Side I**.

**Why a tie shipped anyway**, stated plainly because the write-up has to defend it:

- Twelve paired readings across three runs and two subsets, and **not one of them is negative**. The
  worst case is that the two feature sets are equivalent.
- It removes 114 of 342 columns. A narrowing cannot borrow the width effect the shuffled control
  measured — it runs against it — so unlike every added block, this one is not explained by it.
- It is what **The core design decision** said all along: max and p90 are the signal, median is
  context. The measurement simply says the context was not earning its place.
- The submitted CSV is byte-identical either way, so there is no artefact risk in the choice.

It is *not* claimed as a score improvement, and the standing ±0.03 bar is not met. Anyone quoting
0.750 against 0.740 should say "the same score with a third fewer features".

#### The decision rule, fixed before the numbers were read

**Eleven looks were taken** — eight candidate specs and three narrowings — so a nominal 95% interval on
the best of them is worth about **57%** (0.95¹¹). The rule written down in advance: **the fast subset
decides, not the full set**, a candidate ships only if its fast-subset difference clears a Holm-adjusted
bar (≈ ±0.05 at eleven looks, against the ±0.03 single-comparison floor) *and* fast Side I improves, and
confirming at `max_iter=300` against the banked folds does **not** correct the selection because it
reuses the same 270 files and the same folds. Only the seed-7 replication is independent evidence.

*The count was written as nine while the table held six spec rows. Eleven is the honest figure and it
makes the bar **stricter**, so every verdict above stands unchanged — but quote eleven, not nine.*

**No added block came near that bar.** The median drop did not either, and ships on the four grounds
above rather than on the rule.

#### Step 0 — the baseline's fold scores, re-captured

`outputs/models/rail/baseline_folds.npz`, re-captured 2026-09-19 for the 228-feature set in 195 s; the
342-feature capture it replaces read 0.740 / 0.752 / 0.963 · 0.494 · 0.798 and is gone.

It exists because a paired comparison needs both feature sets scored on the same folds, but only
`mean` and `spread` reach the checkpoint — the fold array lives for the length of one run, and the
first `refresh=True` overwrites the cache it came from.

| Key | Contents |
|---|---|
| `full_folds`, `fast_folds` | (50,) macro F1 per fold, on the 270 files and on the 138 fast ones |
| `full_class_f1`, `fast_class_f1` | (10, 3) per-class F1, one row per repeat, in `labels` order |
| `fingerprint`, `columns` | which feature set produced it — check these before trusting it |

Verified on capture: full **0.750 ± 0.114** per fold / 0.757 pooled / 0.966 · 0.515 · 0.790, fast
**0.770 ± 0.103** / 0.777 / 0.937 · 0.560 · 0.835 — `train.py`'s own figures to three decimals.

`outputs/` is gitignored, so this is a local artefact on Jermaine's machine. **Re-capture it whenever
the shipped feature set changes** — a stale baseline silently flatters or buries every candidate
measured against it, and `columns` is how to tell.

#### How to run a candidate, if the search is ever reopened

Everything needed exists in the package; do not rebuild any of it. The harness that produced the tables
above was **never committed** — it lived in the session scratchpad, outside the repo, and goes away with
the session, deliberately: 300 lines for a question now answered, and [[project-structure]]'s file list
has no room for it. It was four pieces, each an afternoon to rebuild: a candidate extractor writing one
npz of every block at once (so a candidate costs a CV run, not a re-extraction — ~150 s for all 272
files), a screener that hstacks a selected block onto the cached matrix and pairs the folds, a shuffled
control, and a per-column confound check.

**If you rebuild the screener, guard its cached reference from the first line, not after a review finds
it.** The version written on the first day stored four fold arrays and nothing identifying them: the
arrays are (50,) whatever produced them, so a stale reference would have been differenced against in
silence and read plausibly. It was given a guard string — matrix shape, `FEATURE_FINGERPRINT`, seed,
split and repeat counts, `FAST_SPEED_MS`, the dedup list — and the file that existed at the end carried
both that and its 342 `columns`, which is the standard `baseline_folds.npz` already meets.

```python
from src.rail import train
training = train.training_set(refresh=True)      # refresh: features.py changed
result = train.cross_validate(training.matrix, training.labels)
result.fold_scores        # (50,) -- difference THESE against the saved baseline, per fold
result.macro_f1, result.pooled_macro_f1, result.class_f1.mean(axis=0)
```

```python
import numpy as np
from scipy import stats
from src.rail import features, train

banked = np.load(train.FEATURE_CACHE_PATH.with_name("baseline_folds.npz"), allow_pickle=False)
# Check the COLUMNS, not the fingerprint: AGGREGATES and the band edges are spelled
# out in the names and deliberately absent from FEATURE_FINGERPRINT, so a fingerprint
# check passes on a baseline from a different feature set. Which direction to assert
# depends on which workflow you are in, and getting it backwards aborts the run with
# a message that says the opposite of what happened:
#
#   editing features.py   -> the bank describes the PRE-EDIT set, which is the whole
#                            point of it, so the columns must NOT match:
#                            assert tuple(banked["columns"]) != features.FEATURE_NAMES
#   hstacking a side matrix (features.py untouched, as the screener did)
#                         -> the bank must describe today's set, so they MUST match:
#                            assert tuple(banked["columns"]) == features.FEATURE_NAMES
#
# Right now the second holds: the bank was re-captured after Phase 7's edit.

difference = result.fold_scores - banked["full_folds"]      # same folds, same seed, paired
interval = stats.t.interval(0.95, len(difference) - 1, difference.mean(), stats.sem(difference))
wins, losses = int((difference > 0).sum()), int((difference < 0).sum())
```

- **`refresh=True` is mandatory after editing `features.py`.** Forgetting it no longer silently
  fits stale numbers — the **column names** make the cache refuse, and `FEATURE_FINGERPRINT` catches
  the edits that change a value without changing a name, which a feature-set change is not — but
  the error costs a run either way.
- **Difference `fold_scores` per fold**, then take the mean and 95% interval of the differences. Never
  compare two `mean ± sd` figures: the marginal spread is ±0.114 and the paired test resolves ±0.03.
  Report the win/loss count beside it. See **The noise floor**.
- **Price an added block against its own shuffled control**, and treat the fast subset as the decision.
  Both lessons cost a full day to learn; neither is optional.
- The baseline to beat, same folds and seed: **0.750 ± 0.114 per fold, 0.757 pooled, Side I 0.515**.
- One full cycle is ~390 s including a 155 s re-extraction, or ~230 s off the cache.

#### What is left, honestly

- **Side I is still the weakest class by 0.28** (0.515 against Side II's 0.790), and 6.8 of its 14
  files are still called Normal on an average repeat. The phase did not solve that; it established
  that five plausible answers to it, across eight measured variants, do not solve it either.
- **Idea 4 was only half-tested.** "Top-k boxes rather than the max alone" was tested as within-side
  *ratios* (block L, refuted) rather than as a literal top-k aggregate. Given that removing an
  aggregate helped and the width control penalises adding one, another aggregate is the least
  promising thing left — but it is untested, and saying so is cheaper than implying otherwise.
- The open question below — **why** Side I is milder than Side II — is still the thing that would
  actually move it, and it is a question about the 14 files, not about the feature vector.

### Phase 8 — Train and tune against macro F1 — DONE

Done 2026-09-18. Written: the rest of `train.py` — `TrainingSet`, `CrossValidation`,
`training_set`, `cross_validate`, `fit_checkpoint`, `save_checkpoint`, and a `main(refresh)` that
prints the whole report. Plus `config.CHECKPOINT_NAME` and `config.FAST_SPEED_MS`.

**The honest number is 0.740 ± 0.114** at 10×5 on the 270 files that remain after the duplicates go,
seed 42; fast-files-only 0.754 ± 0.116; the full table and the confusion matrix are under
**Measured baseline**. *Phase 7 later took this to 0.750 / 0.770 on 228 features; everything else in
this section — the harness, the five decisions, the artefacts — is unchanged.* Phase 8 first measured 0.750 here and Phase 9's empty-band fix took 0.010 off
it — see **The speed confound** for why that subtraction is the good news it sounds like it is not.
`python -m src.rail.train` runs the lot in ~400 s including an 80 s re-extraction, or ~260 s off
the cache.

**Verified at the time, before Phase 9's empty-band fix:** the same harness read **0.758 ± 0.076** on
all 272 files, reproducing Phase 6's reference figure exactly, so the deduped 0.750 was a real 0.008
cost and not a harness difference. The speed table under **Verified data facts** reproduces from the
cached vector exactly, all 342 column names round-trip through the checkpoint, and the refitted
estimator predicts 234/14/24 on its own training matrix.

Five decisions the spec left open:

- **Per-class figures come from each repeat's complete out-of-fold set, averaged over the ten
  repeats** — not from one 5-fold pass. This is what exposed Phase 4's Side I 0.593 as optimistic by
  0.09. A single pass on 14 files reports mostly fold assignment.
- **Both the per-fold mean and the pooled figure are reported**, because they are different
  quantities and only the pooled one is what gets graded — see **Measured baseline**.
- **No threshold or decision rule was added.** Plain 3-class argmax. One tuned on the OOF scores it
  is then reported against is optimistic by ~0.04 here, and the estimator search is closed
  (**Model comparison**), so there was nothing left to tune that would not have been self-flattery.
- **No scaler is saved, because the shipped model has none.** The spec asked for one; the booster is
  scale-invariant across band energies spanning decades and takes the undefined wavelength features
  as NaN natively. Saving an unused scaler would imply `predict.py` must apply one.
- **The checkpoint is stdlib `pickle`, not joblib.** joblib is only a transitive sklearn dependency
  and is not pinned in `requirements.txt`; depending on it directly would be an unpinned dependency
  on all three machines for no gain on a 300-tree model.

**The cache gained a `speeds` vector and a `fingerprint` string**, and older caches now raise rather
than load — see [[jermaine]]. Speed is there because the fast-files-only figure otherwise costs a
40 s re-read of every CSV, which is how a standing check quietly stops being run. The fingerprint is
there because Phase 4's staleness check compared only `FEATURE_NAMES`, and `WELCH_NPERSEG`,
`STATIONARY_SPEED_MS` and the wheel geometry all change what a feature *is* without changing what it
is *called*. That was harmless while `main()` forced a rebuild every run and became a live trap the
moment it stopped.

One lever left unpulled, deliberately: `MODEL_MAX_ITER = 300` against sklearn's 100 is a measured
tie (+0.001 ± 0.008, identical on 45 of 50 folds) and costs ~3× the CV time. **If Phase 7 iterates,
drop it to 100 first** — that turns a four-minute loop into ninety seconds.

### Phase 9 — Real predict, then the app view — DONE

Done 2026-09-18. Written: `predict.py`'s model path and **`src/rail/explain.py`**. `features.py`
gained two public names for it, `quantities` and `WAVELENGTH_BAND_NAMES` — see [[jermaine]].

**Verified:** all 68 held-out files run through Wayne's own `src/app/services.py` — not through
rail's `main()` — returning 68 rows whose `file_id`s are the shipped names verbatim, with columns
matching `reference/submission_format/`, no duplicates and no label outside the vocabulary. 60
Normal / 5 Side I / 3 Side II. The explanation panels round-trip as plain JSON, the bar shares sum
to 1.0, and both Altair specs compile. `src/submission/validate.py` is shared end-work and does not
exist yet, so those checks were run by hand against the reference CSV.

**One check worth keeping: every one of the 8 fault calls sits above 9.70 m/s**, the slowest fault
in training, so the model is not extrapolating past its own evidence. The test set's speed
distribution is close to training's — median 11.13 m/s, 9 stationary files, 43 of 68 above the fast
threshold against 51% in training — which partly answers the open question below.

Three decisions the spec left open, and one thing it got wrong:

- **`src/app/ui/rail.py` was never written, and should not be.** Wayne made explainability a
  *generic* app capability: a subsystem optionally exposes `src/<sub>/explain.py::explain(inputs)`
  returning `metrics` / `bullet` / `bars` / `line` panels as plain dicts, and `src/app/ui/explain.py`
  draws them without importing any subsystem. Rail supplies panels, not a view. The file table above
  is updated.
- **`predict` takes `list[Path]`, not a folder path.** The Phase 0 signature was `str | Path` and
  fed `list_data_files`; the app passes a list of staged upload paths, which would have raised on
  the first click. [[team-split]] documented `list[Path]` all along — this was rail not matching it.
- ~~**Rail keeps its constant-`Normal` fallback where SHM deliberately refuses one.**~~ *Reversed
  2026-09-19: "both `main()` and the first explanation panel say out loud when it fires" was the
  load-bearing claim and it was false of the path that matters — `src/submission/generate.py` calls
  `predict` directly and prints neither. Rail now refuses too; see **Phase 0**.*
- **Two panel captions claimed more than the data supports and were rewritten.** They said
  concentrated per-car energy indicates a defect and that healthy rails track the centre line;
  `Test11` is called Normal with 49% of its energy in one car and a −1.35 log-ratio excursion.
  Concentration points an inspector at a stretch of track and decides nothing on its own.

The three panels: the call with the model's own probability and the train speed; the cross-side log
ratio against ripple wavelength drawn whole, rather than in the seven bands the features bin it
into; and each car's share of the implicated rail's energy in the band that most implicates it.
Everything comes from `features.quantities`, the same per-box function the feature vector is built
from, so the explanation cannot drift from the prediction it explains.

*Revised 2026-09-19 to five panels, after the app grew a `verdict` capability and rail was driven
with the real 68-file batch rather than one file ([[jermaine]]):*

- *A **verdict** card — the call, its severity (`Normal` clear, either rail caution, **never**
  danger: the model names a rail, it does not measure wear), and next steps. **Its detail line is the
  measured cross-side ratio, not the model's probability** — "3.4x louder than the other rail at
  300-500 mm ripple spacing". Door, ACV and SHM all quote a measured quantity there and rail was the
  outlier; a booster probability of 0.999 beside a measured Side II F1 of 0.790 reads as a guarantee
  it is not.*
- *A **strip** of one cell per uploaded file whenever more than one is uploaded. The 68-file batch
  holds **eight fault calls** and the verdict describes one; the other seven were reachable only as
  rows in the table. It reuses Door's own renderer — no app file was touched.*
- *The probability keeps its place in the metrics panel, labelled "how sure the model is, not a
  measured hit rate".*

*Also worth recording for the write-up: the margin shown is read out of the classified feature row
(`vibration_contrast_max_<band>`), not recomputed alongside it — bit-identical, verified — so the
invariant above now holds through the feature vector itself rather than through a parallel path.*

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

### Five candidate answers to Side I — all refuted (Phase 7)

Full tables, the confound found inside the first of them, and the shuffled control they all have to be
read against are in **Phase 7**. In one line each, so none of them is re-attempted:

- **Distributional side contrast** (a Welch t statistic and an AUC over all 64 boxes, in place of one
  side's extreme against the other's): −0.013 full, −0.015 fast. The mildness of Side I's signature is
  not what a rank statistic fixes.
- **Within-side localisation ratios** (log max/median and p90/median per side): −0.007 full,
  **−0.025 fast**, Side I −0.046. The plan's own 19.3-against-11 spread measurement is real; expressing
  it as an explicit ratio is not what the booster was missing.
- **Envelope spectrum** (Hilbert envelope, λ-band energies, per side and contrast): +0.020 full,
  −0.005 fast. A slow-file gain.
- **Harmonic structure** at 1×, 2×, 3× the passing frequency, scored against a median-filtered
  baseline: +0.010 full, −0.006 fast, and +0.005 / −0.006 once the baseline was fixed. Also a slow-file
  gain. The first implementation's baseline used a zero-padded median filter, which inflates the excess
  by up to 0.5 dex over exactly the first ~20 bins — where every file's fundamental search starts, by an
  amount speed decides. Edge-replicate the baseline if this is ever rebuilt; the fixed version was
  measured and is the second row of Phase 7's table.
- **Fine wavelength contrast**, the plan's own idea 1 and the only one that ever looked like a win:
  +0.033 on the fast subset **until** the bin-count confound inside it was removed, then +0.015 with
  Side I at −0.011. See Phase 7 for the mechanism; it is the empty-band defect in a new costume.

### Keeping only the contrast columns — refuted, and it corrects the design note

0.499 macro F1, Side I 0.114, losing 48 of 50 folds. The cross-side contrasts are where the
discrimination lives but they are not self-sufficient: the model needs each side's absolute level to
know what a given ratio means at that excitation. Written up under **The core design decision**.

### Vibration alone — refuted

Dropping the 171 shock columns: +0.006 full, **−0.031 fast**, Side I −0.065, losing 24 folds to 15 and
8 repeats to 1. Shock earns its half of the feature vector on the honest subset.

## Open questions

- **Why Side I is weaker than Side II.** Unknown — physical (curve direction, attack angle on the
  inner rail, which §1.1 of the info kit does discuss) or an artefact of these 14 files. Phase 7 makes
  this sharper rather than answering it: five independent views of the asymmetry all failed to
  separate the class, which is what you would expect if the 14 files are simply mild rather than if the
  feature vector were looking in the wrong place. **This is the question that would move the metric**,
  and it is a question about those files, not about `features.py`.
- **Why the contrast columns cannot stand alone.** The 114 of them score 0.499 without the per-side
  absolutes. The working explanation — a given log-ratio means different things at different excitation
  levels, and only the absolutes carry the level — is a hypothesis, not a measurement.
- **Whether the held-out test set shares the speed distribution.** If it was drawn from the same
  pool the confound is harmless. Unknowable before the deadline — which is the reason to quote the
  fast-files-only figure rather than rely on the shortcut.

## Standing constraints

- **No improvement under ±0.03 paired is real**, and for a change that *adds* columns the bar is its
  own shuffled control, which measured **+0.012 macro and +0.027 Side I on 36 columns of noise**. See
  **The noise floor**. 10×5 CV on fixed folds, differenced per fold, or the work will chase noise.
- **The fast-files-only subset decides, not the headline** — and it is necessary, not sufficient. Two of
  five Phase 7 candidates gained on the full 270 and reversed on the 138 fast files; a third carried a
  speed marker that the subset check waved through and only a per-column inspection caught. A gain that
  lives where the slow Normal files are is the speed confound wearing a feature's name.
- Nothing in Phases 0–9 touches `common/`. Phase 7 changed the shipped feature set, which invalidates
  the cached matrix and the checkpoint under `outputs/` — logged in [[jermaine]] for that reason alone.
- The fitted model measures **0.750 ± 0.114 per fold, 0.757 pooled**, submitted through the app.
  **Every phase is closed; rail is done.** The 0.31 floor banked in Phase 0 was given up on
  2026-09-19: rail refuses rather than falling back, so **an untrained rail now scores 0, not 0.308**
  — train before building the submission, because `./submit.sh` does not.

See also: [[team-split]], [[project-structure]], [[problem-statment]], [[jermaine]].
