---
name: jouyuan
description: Jou Yuan owns Door and ACV — the verified data facts, the design decisions taken, and what is still open.
metadata:
  type: project
---

# Jou Yuan — Door and ACV

Jou Yuan owns `src/door/` and `src/acv/` end to end: modelling, the two prediction CSVs, and the
two app views. Together that is **50% of the Overall Score** ([[problem-statment]] weights each
subsystem at 25%).

**Why:** [[team-split]] assigns B both of these because they are the two cheapest subsystems per
point. Verification on 2026-09-18 confirmed that and then some — Door's segmentation step turns
out to be exact rather than approximate, and ACV's signal ranks the faulty car first on every
usable case.

**How to apply:** treat the numbers below as measured, not assumed — each was recomputed from
`data/`. The scripted evidence is on the bench-notes page ([[bench-notes-artifact]]).

## Door — the metric is accuracy

The §4.2 formula pools every match into one harmonic mean, so with exact segmentation and
`n_pred == n_true` both soft-recall and soft-precision equal `correct / 38`. **The score is plain
accuracy on 38 cycles.** Not macro-F1 — an all-`Normal` baseline scores ~**0.73**, and every error
costs 1/38 = 0.026 in either direction. Optimise accuracy; never optimise macro-F1 here.

Measured facts:

| | Value |
|---|---|
| Gap split at >100 ms | reproduces **110/110** true segments — start, end *and* row count |
| Margin | 20 ms inside a cycle vs 10.2 s between (11.1 s on test) |
| Test stream | splits to **38** segments |
| Operation from movement flags | **110/110** correct; also recoverable from position direction |
| Mean motor current, within operation | **AUC 1.000** both operations |

**Decision — normalise per stream, not per model.** Raw current does not transfer: the test door
sits offset, and 12 test Close cycles land above training's normal ceiling of 456 mA. Dividing each
cycle by the median current of *its own operation within its own file* gives 0/110 training errors
and a clean split on test. This is a **batch transform computed from the file being predicted** —
not a scaler fitted on training and frozen. Freezing it reintroduces exactly the offset the
normalisation exists to remove.

**Decision — echo timestamps, never format them.** `start_time`/`end_time` are the first and last
row's raw `Datetime` string copied verbatim. Native format is not zero-padded
(`2023-7-5-0-0-3-700`); any round trip through a formatter emits `2023-07-05…` and no segment
matches.

One test cycle (Open, ratio 1.067) sits inside training's empty gap — genuinely undecided by
current level alone. The current-vs-position shape feature exists to settle it.

## ACV — one subtraction, five for five

`mean(Indoor Average Temperature − ACV Control Temperature (Cooling))` ranked descending puts the
true faulty car **1st in all five cases that share the test file's schema**. On the test case it
gives `01|03|07|04|08|06|02|05` — car 01 is the only car above its own setpoint.

**Decision — exclude `acv_case_04.xlsx` from validation.** 483 columns, 59 parameters per car,
only cars 01–04 populated, and it carries refrigeration pressures the test file does not have. On
mapped columns its true car ranks 2nd of 4. It is a different problem wearing the same name;
tuning against it teaches the wrong lesson. Keep it for the write-up.

**Decision — add cooling duty cycle as an independent confirming signal**, not as a vote to
average. A leaking car should run cooling a larger fraction of the time to hold the same setpoint.
Agreement on car 01 is evidence; disagreement is a flag to investigate.

**Decision — no `model.py` or `train.py` in `src/acv/`.** A deliberate deviation from
[[project-structure]] rule 4: with five usable cases there is nothing to fit that would not be
memorisation, and a fitted model would score worse while looking more sophisticated. Document the
deviation where a reader hits it.

## Traps that cost a whole subsystem

- `Train_Labels.csv` needs `dtype=str` — `01` silently becomes int `1`, and the submission says
  `1|3|7` instead of `01|03|07`.
- `Car model` is caught by a naive `startswith("Car ")`. Match `^Car (\d{2}) - (.+)$`.
- Parameter names vary: case 06 says `Outside Temperature Sensor Reading` where the rest say
  `Outdoor Average Temperature`.
- `acv_case_04.xlsx` costs **121 s** through openpyxl every run. Cache it.
- `n` in the rank-decay score is per-file: case 04 would be n=4, the test file is n=8.

## State as of 2026-09-18

Design approved in chat; spec and implementation plan not yet written. Nothing under `src/door/`
or `src/acv/` exists. Converted CSVs and the bench-notes page are in `outputs/explore/`.

See also: [[team-split]], [[problem-statment]], [[project-structure]], [[bench-notes-artifact]].
