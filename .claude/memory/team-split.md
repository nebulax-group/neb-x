# Three-Person Work Split — 24-Hour Plan

How three people cover four subsystems plus the app in a 24-hour window, what gets cut to make
that fit, and the data facts that decide the allocation. Revised 2026-09-18 against the skeleton
already merged.

**Why:** a full-quality attempt at all four subsystems is ~142 person-hours. Three people over 24
hours is **~50 usable person-hours** — about a third. The plan is therefore not how to divide the
work but which work to delete.

**How to apply:** clear the two blocking items, then split along package boundaries so nobody
edits the same file, then converge on the app. Bank a valid floor before modelling anything.

## The existential constraint

[[problem-statment]] §4.1: *"Every team must submit all three of the following for each subsystem
they attempt. Submissions missing any of these will not be scored for that subsystem."*

**No app means no score on anything.** The app is not the last thing built.

## Already done — do not redo

| | State |
|---|---|
| `common/config.py` | Owns paths and constants. `PREDICTION_FILENAMES`, `TEST_PATHS`, `LABEL_PATHS` all derived; door's special-casing handled. |
| `common/io.py` | `read_table` (csv/xlsx, kwargs passthrough) and `list_data_files` (non-recursive, ignores `.DS_Store`/`~$`, **preserves source filenames**). |
| `requirements.txt` | Pinned. Streamlit for the app. lightgbm deliberately excluded — its wheel needs libomp, which macOS does not ship; use sklearn's `HistGradientBoosting`. |
| `install.sh/.bat`, `scripts/check_env.py` | Environment bootstrap. |

`io.py` already covers two traps: filenames survive verbatim into `file_id`, and SHM's headerless
single column loads via `header=None` through kwargs.

Minor debt, fix after the sprint not during: `paths.py` is now a pure re-export shim of
`config.py` — two files doing one job. And `list_data_files` sorts lexicographically, so rail
returns `Test1, Test10, Test11, … Test2`; correctness is unaffected because `file_id` is per-row,
but never assume numeric order.

## Blocking — clear these first

1. **App shell + the function signature.** The integration contract. ~3h, **Wayne**.
2. **`common/metrics.py`** — the four official formulas. Nobody can tune against a real number
   until it exists. ~1.5h, **Jou**, who owns the two odd metrics anyway (Door's IoU-weighted F1
   and ACV's rank-decay; macro-F1 and MAPE are near one-liners).

**Jermaine** starts rail extraction immediately — it depends on neither.

Skip `interface.py` and the registry protocol at this scale. The contract is one function:

```python
# src/<sub>/predict.py
def predict(inputs: list[Path]) -> pd.DataFrame:
    """Returns exactly the submission rows for this subsystem."""
```

The app does `list_data_files` → `predict` → `st.dataframe` → download button. Four dict entries,
no protocol.

## Bank a floor early

Before any modelling, every subsystem emits a *valid but dumb* CSV — correct filename, correct
schema, correct `file_id` spelling:

| Subsystem | Dummy submission | Expected |
|---|---|---|
| ACV | `01\|02\|03\|04\|05\|06\|07\|08` | ~0.56 — random ranking averages `(n−(r−1))/n` = 0.5625 |
| Door | gap-split segments, all `Normal` | ~0.4 — segmentation is exact, so only the 30/110 abnormals are lost |
| Rail | constant `Normal` | 0.33 — macro-F1 of (1.0 + 0 + 0)/3 |
| SHM | constant `0.23` (the training mean) | ~0 — MAPE floors it |

≈ **0.32 Overall for about 90 minutes of work**, and it makes a technicality-zero impossible.
Everything after is improvement on a banked position.

## What gets cut

| Cut | Why |
|---|---|
| `interface.py`, `registry.py`, `splits.py` | [[project-structure]] rule 8 is a six-day luxury. A four-entry dict is fine here. |
| Model benchmarking | One line in the write-up: default vs GBM. Ten minutes. |
| Write-up | Optional (§4.2). One page at the end, only if time remains. |

## The split

Mutually exclusive by package — nobody edits the same file:

| Jermaine (A) | Jou (B) | Wayne (C) |
|---|---|---|
| `src/rail/` | `common/metrics.py`, then `src/door/`, then `src/acv/` | app shell, then `src/shm/`, then both upgrades below |
| ~16h | ~16h | ~16h |

**Because nobody reads anyone else's diffs, boundary crossings get announced.** When a change
touches something outside your own package — `common/`, a shared constant, a file schema, a
function signature, a cached artefact under `outputs/` — append an entry to your own log:
[[jermaine]], [[jou]], [[wayne]]. Work internal to one subsystem needs no entry. This is the only
coordination overhead in the plan; skipping it is how two people end up disagreeing about a column
name at hour twenty.

**Jermaine is deliberately heaviest.** Rail is 5.6 GB and the only subsystem that cannot be
rushed, but it is also the worst value per hour — ~14h to reach maybe 0.5–0.7 macro-F1, where Door
reaches ~0.85 in five.

**Reinforcement:** Jou finishes both subsystems first — Door and ACV are genuinely fast now — and
then joins Jermaine on rail model and CV while Jermaine keeps extraction and features. Different
files, so no collision.

**Wayne's two upgrades.** `config.py` and `io.py` were already done and `src/submission/` is shared
end-work, so Wayne's column is otherwise light. Fill it with the two things this plan was
under-weighting — both *upgrades on a banked baseline*, so if Wayne runs out of time the submission is
unaffected:

1. **SHM properly, via rainflow (+3h).** Bank the cheap version first — stats features (RMS,
   percentiles, zero-crossings) + GBM against the 64 labels. Then implement rainflow counting +
   Miner's rule and fit `(m, C)`. The info kit §1.3 says that is exactly how the reference values
   were produced, so it is the one subsystem where the ground truth can be reverse-engineered
   rather than approximated. MAPE is unforgiving on the 0.028-damage files and a physics-based
   estimate should beat a 64-sample regression.
2. **The app beyond minimal (+2.5h).** Per-subsystem explainability — which band drove a rail
   call, which car's temperature diverged, where in the stream a door fault sits — plus a clean
   download flow and something that films well.

The second matters more than the hour count suggests. Of the three grading criteria in §6, **Ease
of Use maps entirely to the app**, and Problem Fit separately lists "explainability, UI, code
quality". The app carries a full third of the grade outright and contributes to a second third;
rail carries a quarter of *one* criterion. A three-hour shell next to fourteen hours of rail has
the weighting backwards.

## Converge at the end — everyone

The app and the submission are the combined end-work. Both still divide along the same
mutually-exclusive lines, so converging does not mean three people in one file:

| Shared task | How it divides |
|---|---|
| App views | `src/app/ui/` is one file per component — Jermaine writes rail, Jou writes door and acv, Wayne writes shm |
| `src/submission/` | Written together: `validate.py` checks a CSV against `reference/submission_format/`, `package.py` zips flat |
| **The submission run** | **Each person runs their own subsystem's test files through the app and validates their own CSV** — the person who knows the schema is the person who checks it |
| `predictions.zip` | One person zips, once all four CSVs are validated |
| Demo video | One take, ≤3 min, all four subsystems |

**Definition of done:** nobody declares a subsystem finished until it runs *through the app* and
its CSV passes `validate.py`. Not the notebook — the app. That is what the early shell buys.

## Two rules that save the run

1. **Cache every feature matrix to disk.** Rail extraction over 5.6 GB happens once. Re-extracting
   during tuning is how a 24-hour project dies. `read_table` returns whole DataFrames with no
   chunking, so extract file-at-a-time and persist.
2. **Jermaine never blocks on the full rail run.** Build the pipeline on a 100-file subsample; run
   the full extraction in the background.

If rail extraction is still fighting back with a third of the time left, drop it to a simple
per-side RMS/band-energy model and take the ~0.5. An unfinished pipeline scores 0.33.

## Verified data facts

Checked against `data/` on 2026-09-18. These decide the allocation.

**Door — segmentation is solved, and it is not in the opening/closing flags.** The stream is only
sampled *during* cycles, so boundaries are timestamp gaps:

| | Train.csv | Test.csv |
|---|---|---|
| Rows | 18,036 | 6,253 |
| Deltas of exactly 20 ms | 17,926 | 6,215 |
| Gaps > 100 ms | 109 | 37 |
| Implied segments | **110** | **38** |

`Train_Segments_Answer.csv` has exactly 110 rows, so a gap split is exact. Largest within-cycle
delta is 20 ms; smallest gap is 10.2 s — a 500× margin. IoU is therefore 1.0 and the IoU-weighted
F1 collapses to plain F1 on the labels. Door is a **110-sample binary classification**, 80 Normal
/ 30 Abnormal resistance. `door_predictions.csv` will have 38 rows.

**Rail** — 272 train files, labels 234 Normal / 24 Side II / **14 Side I**; 68 test files. Each
file 10,001 rows × 129 cols at 10 kHz. Macro-F1 makes those 14 files a third of the score, and any
single holdout leaves ~3 to validate against, so use repeated stratified CV. Side I is axle-box
positions 1,3,5,7; Side II is 2,4,6,8.

**SHM** — files are **single-column and headerless**, exactly 581,120 rows each (verified on
train01/32/64). The info kit says each file holds "all monitoring points", but on disk one file is
one measurement point — state that assumption in the write-up. Labels: 64 values, 0.0286 to 0.928,
mean 0.230. MAPE is relative, so the low-damage files dominate the score.

**ACV** — 6 training cases, faulty cars `01,02,03,01,04,06`; one test case. `acv_case_04.xlsx` is
**32 MB** against ~2 MB for the rest — the 60+-params-per-car schema the info kit warns about.
Schema-agnostic column reading is not optional.

**Held-out filenames — never rebuild these:**

| Subsystem | Inputs |
|---|---|
| rail | `Test1.csv` … `Test68.csv` — capital T, **not** zero-padded |
| shm | `test01.csv` … `test16.csv` — lowercase, **zero-padded** |
| acv | `acv_test_case.xlsx` |
| door | `Test.csv` — one stream, no `file_id` column at all |

`file_id` must be the source name verbatim. Any `.lower()`, any reconstructed `f"Test{i}.csv"`,
and §5.1 gives that subsystem **no score**. Echo the filename you read.

`Optional_Items/` uses the organisers' folder names — `Door`, `ACV`, `Rail Corrugation`, `SHM` —
not our keys `door`/`acv`/`rail`/`shm`.

## A discrepancy in the docs

All four info kits reference a `predict.py` with an `--input`/`--output` CLI, citing a "top-level
README's Deliverables section". `docs/problem_statement.md` §4.1 requires **the app** and never
mentions `predict.py` — the info-kit text appears left over from an earlier deliverables spec. Per
the source-of-truth order the info kit governs task/schema/scoring and the problem statement
governs deliverables, so the app wins. Giving each `predict.py` that CLI satisfies both at no cost,
if time allows.

See also: [[problem-statment]], [[project-structure]], [[prompting]].
