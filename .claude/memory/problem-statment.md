---
name: problem-statment
description: NebulaX Hackathon Problem Statement 3 — Train Condition Monitoring across four rail subsystems.
metadata:
  type: project
---

We are working on **Problem Statement 3 — Train Condition Monitoring** from the NebulaX Hackathon
(https://github.com/aochinwen/NebulaX-Hackathon-ProblemStatement, folder `PS3/`).

## The task

Detect faults and estimate degradation from raw rail-vehicle sensor time series across four
**independent, self-contained** subsystems. A team may attempt one or several.

| # | Subsystem | Task | Signal type | Metric | Weight |
|---|---|---|---|---|---|
| 1 | Door | Temporal segment detection — find each door open/close cycle in a continuous stream, classify `Normal` vs `Abnormal resistance` | Motor current / voltage / back-EMF + door position | IoU-weighted F1 | 25% |
| 2 | ACV | Fault localisation — identify the car with a refrigerant leak | Cabin/ambient temperature + control-mode telemetry | Linear rank-decay score | 25% |
| 3 | Rail Corrugation | Multi-class classification — `Normal` / `Side I` / `Side II` | Axle-box vibration + shock (multi-channel) | Macro F1 | 25% |
| 4 | SHM | Regression — cumulative fatigue damage estimation | Dynamic stress time series | `max(0, 1 − MAPE)` | 25% |

Each subsystem's Info Kit in `03_References/<Subsystem>/` is the **authoritative** problem definition
(business background, schema, reference labels, exact scoring formula with worked example) — the
summary table above is not.

## Repository layout (upstream PS3)

```
FOR PARTICIPANTS/
├── 01_Problem_Statement_3_Specifications.md
├── 02_Datasets/{Door,ACV,Rail_Corrugation,SHM}/     # raw .txt / .csv / .xlsx
├── 03_References/{Door,ACV,Rail_Corrugation,SHM}/   # .._Info_Kit.md
└── 04_Example_Submission/                            # schema examples only, not real data
```

## Data conventions

- Data given up front is for training/validation. A held-out test set exists per subsystem; the
  **unlabelled test input files are distributed before the deadline** — only the answers are withheld.
- We design and justify our own train/validation split (e.g. by operating condition or by file).
- Units, sampling frequencies, and column definitions vary by subsystem — do not carry assumptions across.
- Class balance varies significantly; check label distribution before evaluating.

## Compulsory deliverables (all three, per subsystem attempted)

1. **Demo video** — ≤3 min screen recording of the app end to end (select subsystem, upload file,
   view and download result). Primary evidence for the Ease of Use criterion.
2. **`predictions.zip`** — the `*_predictions.csv` files at the top level of the zip (no subfolders),
   produced by running the held-out test inputs through our own app.
3. **The app** — one single app covering every subsystem attempted, usable by a **non-technical user**
   without touching code (e.g. upload/drag-drop a file → prediction on screen + download).

### Prediction file schemas

| Subsystem | Filename | Columns |
|---|---|---|
| Door | `door_predictions.csv` | `start_time`, `end_time`, `prediction` — one row per *predicted segment* in the continuous `Test.csv` stream. **No `file_id`.** |
| ACV | `acv_predictions.csv` | `file_id`, `ranked_cars` — every car most- to least-likely faulty, `\|`-separated, using the car id exactly as in that file's column headers (e.g. `03`, not `Car 3`). **No `prediction`.** |
| Rail Corrugation | `rail_predictions.csv` | `file_id`, `prediction` ∈ {`Normal`, `Side I`, `Side II`} |
| SHM | `shm_predictions.csv` | `file_id`, `prediction` — a single numeric cumulative-damage value |

`file_id` is the source file name including its extension.

## Submission folder structure

```
<Team Name>/
├── demo_video.<mp4|mov|...>
├── predictions.zip
├── app/
└── Optional_Items/          # write-up, plus <Subsystem>/{code,model}/
```

Optional but strengthens the submission: a write-up (approach, feature engineering, model selection,
assumptions) and our development code / trained models.

## Scoring

- **Overall Score** — sum across all 4 subsystems ÷ 4 always. Rewards breadth; a skipped subsystem
  contributes 0, so attempting more can only raise it.
- **Average Score** — sum across only the subsystems attempted ÷ number attempted. Rewards depth.
- Per-subsystem leaderboards also published.
- Technical Execution is scored automatically by the organisers' `judge_leaderboard.py` from
  `predictions.zip` — our code is not re-run.

Three overall grading criteria: **Problem Fit** (dataset coverage, fit with LTA predictive maintenance
needs, model comparison/benchmarking, explainability, UI, code quality), **Technical Execution**
(held-out performance), and **Ease of Use** (non-technical usability, clarity of visuals, usefulness).

Methodological soundness is judged alongside the headline metric — **a high score from a leaky split
will not score well**. Where the docs leave a decision open, state the assumption and why.
