---
name: overfitting-audit
description: What was measured to rule out overfitting on Door and ACV, and the two limits the checks do not cover.
metadata:
  type: project
---

# Overfitting Audit — Door and ACV

Run 2026-09-18 against the real data, after both subsystems were implemented. These are the numbers
to quote if a judge asks whether the results are real.

**Why:** [[problem-statment]] says methodological soundness is graded alongside the headline metric
and *"a high score from a leaky split will not score well"*. Door reports CV accuracy 1.0000 and
ACV reports 5/5 top-1, and both numbers are the kind that should invite suspicion.

**How to apply:** quote the three Door checks and the ACV bootstrap in the write-up. State the two
limits honestly — they are the difference between a defensible result and an overclaimed one.

## Door

| Check | Result |
|---|---|
| Is the transductive baseline leakage? | **No.** Recomputing the per-operation median from *only each training fold* gives CV accuracy 1.0000 ± 0.0000 — identical to the shipped whole-stream baseline. The transduction buys nothing, so it cannot be leaking anything. |
| Is the threshold tuned to a knife edge? | **No.** 1.07–1.13 all give 0/110 training errors; 1.07–1.14 all flag the same 8 test cycles. The shipped 1.10 is the middle of a shelf, not a sharp optimum. |
| Does the held-out stream separate without labels? | **Yes.** Its largest ratio gap is 0.1315 (1.0672 → 1.1986) and splits the 38 exactly **30 low / 8 high**, with 1.10 inside it. The runner-up gap (0.1166) is at the bottom — a lone low outlier at 0.819 — not a rival boundary. |

That third row is the real cross-door evidence: an unsupervised look at the test stream alone
reaches the same 30/8 answer the trained model does.

## Harder Door protocols — the CV flatters the classifier, not the feature

Random CV folds over segments of ONE continuous recording can be optimistic: neighbouring cycles
leak into each other's folds. Protocols that cannot cheat that way:

| Protocol | Learned split | Fixed 1.10 threshold |
|---|---|---|
| Temporal 50/50 (train first half) | 0.9091 (5 errors) | **1.0000** |
| Temporal 70/30 | 1.0000 | 1.0000 |
| Train on Close only → validate Open | 1.0000 | 1.0000 |
| Train on Open only → validate Close | 0.8545 (8 errors) | **1.0000** |

**The feature is not weak — the estimator places its split badly on small subsets.** Where the
learned split actually lands:

- trained on all 110: ratio ≈ **1.102** (inside the safe zone)
- trained on the first 55: ratio ≈ 1.015 (below it)
- trained on Open only: ratio ≈ 1.013 (below it)

The zone that works for both operations is **1.068 < t < 1.135**. HistGradientBoosting hugs
whatever its training subset's highest normal happens to be rather than centring in the global gap,
so with half the data it drifts low and starts calling normals abnormal.

**What this means for the shipped system.** It trains on all 110, lands at 1.102, and is correct —
and the `test_the_fitted_model_agrees_with_the_documented_threshold` test in
`tests/door/test_model.py` fails if that ever drifts, so the guard already exists. But describe the result accurately: **the robustness
comes from the fixed threshold sitting in a wide gap, with the classifier verified to agree — not
from the classifier.** Do not quote the 1.0000 CV as evidence of robustness on its own.

## ACV

Block bootstrap on the held-out file, 200 resamples of contiguous 6-hour blocks:
**car 01 ranked first in 200/200**, mean rank 1.00, expected rank-decay score 1.0000.

By calendar day, car 01 leads on 3 of 4. The exception is 2021-06-24, where car 03 edges it by
**0.0140 °C** — noise-level, and car 01 is still second there. The other days give margins of 0.086,
0.357 and 0.169.

## The two limits these checks do NOT cover

**Door's CV answers a narrower question than it appears to.** There is one training door and one
test door. Repeated stratified CV over segments of the *same* recording measures within-door
separability — it cannot estimate transfer to a different door. The cross-door evidence is the
principled normalisation, the shift-stress test (0/110 at every factor from 0.85× to 1.20×), and
the unsupervised 30/8 split above. Lean on those, not on the 1.0000.

Related: the test ratio distribution was inspected while choosing the threshold. The plateau means
the choice was not *driven* by it, but this is not a blind holdout and should not be described as one.

**ACV fits no parameters, so it cannot overfit them — but n=5 is n=5.** The method is a fixed
physical formula with zero learned coefficients. The exposure is *specification* bias: the signal
was chosen after seeing it work on five cases. 5/5 on five cases cannot separate "reliably right"
from "lucky" on its own, and the held-out margin (0.166) is thinner than every training margin
(0.47–1.13). **The bootstrap and the specification-bias check below are the reasons to be confident
here, not the 5/5.**

## Robustness to specification bias - the strongest ACV evidence

With five reference cases the real exposure is picking the one signal definition that happens to
work. Six alternatives were written, each validated on the five labelled cases, then applied to the
held-out file:

| Variant | Passes validation (5/5)? | Rank of car 01 on the test file |
|---|---|---|
| mean delta to setpoint (shipped) | **PASS** | 1 |
| cooling-mode rows only | **PASS** | 1 |
| fraction of samples above setpoint | **PASS** | 1 |
| 90th percentile of delta | **PASS** | 1 |
| peer z-score vs the other seven cars per timestamp | **PASS** | 1 |
| median delta | fail (3/5) | 1 |
| hot-weather rows only | fail (4/5) | 1 |

**Five independent definitions pass validation and all five pick car 01** - as do the two that
fail. Seven ways of asking, one answer. This is what answers the "you tuned it to five files"
objection, and it is stronger evidence than the 5/5 itself.

## A cross-check that did NOT work - recorded so nobody retries it

The plan was to corroborate Door's 8 flagged test cycles with the current-vs-stroke shape, a
measurement the shipped model never uses. It separates the labelled data perfectly on its own
(0/110 errors). **But it does not transfer between doors:** training abnormals score 406+ on the
per-stream-normalised shape measure while the test stream's flagged cycles score 25-72 - a tenfold
scale difference that makes any training-derived shape threshold meaningless on another door. This
is the same instability that disqualified shape as a model input. Do not retry it as a cross-check.

What Door has instead: the two streams align almost exactly once normalised - normal cycles top out
at 1.068 (train) against 1.067 (test), abnormal ranges overlap (1.135-1.722 against 1.199-1.373),
and the abnormal rate is 27% against 21%. A transfer failure would show as a shifted ceiling. It
does not.

See also: [[jouyuan]], [[problem-statment]], [[bench-notes-artifact]].
