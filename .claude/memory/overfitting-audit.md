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
was chosen after seeing it work on five cases. Mitigating it, only two signals were ever tried
(cabin-temperature mean, and delta-to-setpoint) and both worked, so the search was shallow. Still,
5/5 on five cases cannot separate "reliably right" from "lucky", and the held-out margin (0.166) is
thinner than every training margin (0.47–1.13). **The bootstrap is the reason to be confident here,
not the 5/5.**

See also: [[jouyuan]], [[problem-statment]], [[bench-notes-artifact]].
