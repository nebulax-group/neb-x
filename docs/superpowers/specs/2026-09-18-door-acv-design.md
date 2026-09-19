# Door and ACV — Design

**Owner:** Jou Yuan · **Date:** 2026-09-18 · **Subsystems:** `door`, `acv` (25% each of Overall Score)

## Goal

Produce `door_predictions.csv` and `acv_predictions.csv` at the highest achievable held-out score,
generated through the team app, with a validation protocol that would survive a methodology
challenge.

## What the scores actually are

**Door is plain accuracy on 38 binary calls.** `docs/door/info_kit.md` §4.2 pools every match into a
single harmonic mean: `soft_recall = ΣIoU / n_true`, `soft_precision = ΣIoU / n_pred`. Gap-splitting
reproduces boundaries exactly, so every IoU is 1.0 and `n_pred == n_true == 38`; both terms reduce to
`correct / 38`. This is not macro-F1. The all-`Normal` floor is ≈0.73 and every error costs 0.026 in
either direction, so the objective is accuracy and nothing else.

**ACV is one rank-decay number on one file**: `(n − (r − 1)) / n` with `n = 8`. Rank 1 scores 1.000,
rank 2 scores 0.875. The only way to score 0 is to omit a car or misspell an id.

## Evidence the design rests on

Measured on 2026-09-18 from `data/`; scripts in the session scratchpad.

| Question | Answer | Measurement |
|---|---|---|
| Is gap-splitting exact? | Yes | 110/110 segments match on start, end and row count. Test → 38. |
| Is operation recoverable? | Yes | 110/110 from the movement flags; also from position direction. |
| Does mean current separate? | Yes | AUC 1.000 within each operation. |
| Does a raw mA threshold transfer? | **No** | 12 test Close cycles sit above training's normal ceiling. |
| Does per-stream normalisation transfer? | **Yes** | Any threshold in 1.08–1.13 gives **0/110** train errors and flags the same 8 of 38. |
| Does normalisation survive a current offset? | **Yes** | Scaling all currents by 0.85–1.20: normalised rule **0/110 errors at every factor**; raw mA threshold degrades to **13, 46 and 80/110**. |
| Does any model beat a single split? | **No** | HistGradientBoosting on `ratio` alone: CV accuracy **1.0000 ± 0.0000**. Logistic regression: 0.9818. Adding shape features: unchanged at 1.0000. |
| What about the one ambiguous cycle? | **Normal** | Test segment 34 (Open, ratio 1.067) reads Normal on the level feature and Normal on an independent shape feature (1.38 against an Open-abnormal minimum of 13.5). |
| Does the ACV delta signal work? | Yes | Rank 1 in all five same-schema cases; test ranks `01|03|07|04|08|06|02|05`. |

The shift-stress row is the one that decides the architecture. It is also the quantitative answer to
the info kit's own §1.2.2 ("data distributions differ among doors; a uniform threshold leads to false
alarms").

## Door design

**Pipeline.** stream → `segment` → `features` → `model` → rows.

1. **Segment.** Split wherever the inter-row gap exceeds 100 ms. Emit, per segment, the first and
   last raw `Datetime` **strings copied verbatim**, plus the row slice.
2. **Operation.** `Open` if `mean("Door is opening") > mean("Door is closing")`, else `Close`.
3. **Normalise.** `ratio = segment mean current ÷ median segment mean current of the same operation
   within the same stream`. This is a **batch transform computed from the file being predicted** —
   never a scaler fitted on training and frozen. That distinction is the entire reason the rule
   survives the offset.
4. **Classify.** `HistGradientBoostingClassifier` on the single `ratio` feature. With one perfectly
   separating feature this is a decision stump; it is used rather than a bare constant because it
   derives its own split from the data, reports a probability for the app, and gives the write-up a
   real model comparison. A documented constant `RATIO_THRESHOLD = 1.10` is the fallback and the
   assertion target — tests require the fitted model to agree with it on all 110.

**Rejected, with the measured reason:**

- *Shape features as model inputs* (`dev_area` of the current-vs-stroke profile against the stream's
  own median profile). CV is unchanged at 1.0000, and the feature's scale is unstable between
  streams — Open separates at ~10 while Close separates at ~400, and the test stream's values differ
  again. It adds overfitting risk for no measurable gain. **Kept as a displayed diagnostic and as an
  independent cross-check in tests, not as a model input.**
- *Logistic regression.* Measurably worse (0.9818 vs 1.0000).
- *Unsupervised calibration on the test stream* (mixture/Otsu/largest-gap). The supervised threshold
  is already shift-proof across ±20%, so this buys nothing and adds a failure mode when the abnormal
  count is small.

**Output.** `start_time`, `end_time`, `prediction`. No `file_id` column. Timestamps are the source
strings echoed, never reformatted — the native format is not zero-padded.

## ACV design

**Pipeline.** workbook → `dataset` → `features` → `rank` → one row.

1. **Parse schema-agnostically.** Per-car columns match `^Car (\d{2}) - (.+)$`. The `Car model`
   column must not match. Parameter names are resolved by candidate list, because case 06 says
   `Outside Temperature Sensor Reading` where others say `Outdoor Average Temperature`.
2. **Primary signal.** `mean(Indoor Average Temperature − ACV Control Temperature (Cooling))` per
   car. A healthy car sits at or below its target; a leaking car runs above its own target.
3. **Confirming signal — tested and disproven.** Cooling duty cycle (the fraction of rows in a
   cooling running mode) was included on the theory that a leaking car must run longer to hold the
   same setpoint. **Measured across all six case files, it does not discriminate:** duty cycle spans
   only 0.001–0.04 between the eight cars in every file (held-out: 0.8648–0.8672), and exact rank
   agreement with the temperature signal was false for the top-ranked car in all six — including the
   five where that car is the known-correct answer. It is reported for transparency, and no verdict
   is computed from it. ACV therefore rests on the temperature signal alone; see
   [[overfitting-audit]] for the bootstrap that justifies confidence in it.
4. **Rank** all cars present, descending by the primary signal, joined with `|`.

**No `model.py` or `train.py` in `src/acv/`** — a deliberate deviation from `project-structure.md`
rule 4. With five usable cases there is nothing to fit that would not be memorisation. Documented in
the package docstring.

**`acv_case_04.xlsx` is excluded from validation** and the exclusion is asserted in a test. It is a
different schema (483 columns, 59 parameters per car, only cars 01–04, carries refrigeration
pressures the test file lacks). Validation is leave-one-case-out over the five same-schema cases.

## Order of work

Both subsystems emit a **valid but dumb CSV before any modelling** — correct filename, correct
schema, correct spelling. Door all-`Normal` banks ≈0.73; ACV's delta ranker banks its score
immediately. Everything after is improvement on a banked position, and a technicality-zero becomes
impossible.

## Validation

- **Door:** `RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=0)` over the 110
  segments, scored as accuracy. Separately, a reference implementation of the §4.1–4.2 IoU-weighted
  F1 matcher lives in the test suite and is used to **prove** `score == accuracy` on the training
  segments rather than assert it from arithmetic.
- **Door robustness:** the shift-stress test is a committed test, not a one-off — currents scaled by
  0.85…1.20 must still give 0/110.
- **ACV:** leave-one-case-out over the five same-schema cases, reporting per-case rank and mean
  rank-decay score.

Note on leakage: the per-stream median uses no labels and is computed from the input file itself, so
computing it once over the whole stream before cross-validating is transductive but not leaky — the
same statistic is available at predict time. Fold-crossing label statistics are leakage and are
tested against.

## Risks

| Risk | Defence |
|---|---|
| Test stream mixes more than one door, so one per-file median is the wrong baseline | Segment counts and baselines are logged at predict time; the app displays the ratio distribution so a bimodal baseline is visible |
| Test abnormal rate differs from 27% | The rule is a per-cycle decision, not a quota — nothing assumes a count |
| ACV car 01 is wrong | Rank 2–8 order still earns 0.875 down to 0.125. A 200-resample block bootstrap puts car 01 first 200/200 times, so this risk is smaller than the thin 0.166 margin suggests |
| Timestamps or car ids reformatted | Asserted by test: output strings must be byte-identical to source |

## Expected outcome

Door 0.95–1.00 against a 0.73 floor; ACV 1.000 if car 01 is right, 0.875 if it is second. Neither
number is a stretch, and both rest on measurements rather than hope.
