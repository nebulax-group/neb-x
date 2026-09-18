# Jou — Change Log

What Jou changed, newest first. One entry per change the other two might depend on.

**Why:** the three of us work on mutually exclusive packages ([[team-split]]), so nobody reads
anyone else's diffs. This is where a change that crosses a package boundary gets announced.

**How to apply:** append an entry when you touch anything outside your own package — `common/`,
a shared constant, a file schema, a function signature, a cached artefact under `outputs/`. Purely
internal work inside your own subsystem does not need an entry.

**Role:** B — `common/metrics.py` first (it blocks everyone's tuning), then `src/door/`, then
`src/acv/`, plus both those views. Finishes earliest, then reinforces Jermaine on rail model and
CV. See [[team-split]].

## Changes

### Template

```
### <time> — <short title>

**What:** the change, in one line.
**Why:** what forced it.
**Affects:** who has to do something differently, or "nobody".
```

### Door and ACV are done, both prediction files exist

**What:** `src/door/` and `src/acv/` are implemented and tested. `outputs/predictions/door_predictions.csv`
(38 rows) and `acv_predictions.csv` (1 row) are written and pass Wayne's validator sweep.
**Why:** they are two of the four subsystems and 50% of the Overall Score.
**Affects:** nobody's code. Wayne, for wiring both into the app views.

### src/submission/validate.py — Wayne's kept, mine dropped

**What:** we had both written one independently. Wayne's is kept; mine is deleted. Wayne's checks
column order, blank cells, a stray index column and `file_id` against real filenames; mine only
compared column lists.
**Why:** the app and `package.py` are already built against Wayne's, and it is the better one.
**Affects:** **Wayne — please confirm this was the right call.** Nobody else.

### tests/ now exists, and pytest is in requirements.txt

**What:** a `tests/` tree mirroring `src/`, 54 tests. `pytest==8.4.2` added to `requirements.txt`.
Ten of those tests cover `src/submission/validate.py`, which had none.
**Why:** Door and ACV were built test-first.
**Affects:** everyone — `uv pip install -r requirements.txt` to pick up pytest. Note the venv is
uv-managed and has **no pip**, so plain `pip install` fails. Run the suite with
`.venv/Scripts/python.exe -m pytest tests/ -q`; it takes about ten minutes because the ACV tests
read every workbook through openpyxl.

### team-split.md — Door is scored on accuracy, not macro-F1

**What:** corrected four numbers. Door's all-`Normal` floor is **~0.73**, not ~0.4; the banked
total is ~0.40 Overall, not 0.32; the IoU-weighted F1 collapses to plain **accuracy**; Door reaches
~0.95 in five hours, not ~0.85.
**Why:** §4.2 of the info kit pools every match into one harmonic mean, so with exact segmentation
both soft-recall and soft-precision reduce to `correct / 38`. Derivation and the reference
implementation that proves it are in [[jouyuan]] and `tests/door/official_metric.py`.
**Affects:** anyone planning against Door's value. It is a smaller win over baseline than the old
numbers implied.

### A pandas 3.x trap for whoever writes common/metrics.py

**What:** `datetime64` defaults to **microsecond** resolution on pandas 3.x, so the usual
`.astype("int64") / 1e9` for epoch seconds returns values **1000x too small, with no warning**. Use
`(stamps - pd.Timestamp("1970-01-01")).dt.total_seconds()` instead.
**Why:** hit while transcribing Door's IoU-weighted F1. It happened to change no result there,
because a uniform scale cancels out of every IoU ratio — but it will not always be harmless.
**Affects:** whoever implements `common/metrics.py`. The same line is waiting there.

### Six redundant .gitkeep files removed

**What:** deleted `.gitkeep` from `src/`, `src/acv/`, `src/common/`, `src/door/`, `src/submission/`
and `scripts/` — all now hold real tracked files. The ten guarding genuinely empty directories
(`outputs/*`, `src/app`, `src/app/ui`, `src/rail`, `src/shm`) are untouched.
**Why:** tidying; they no longer keep anything.
**Affects:** nobody.

<!-- newest entries above this line -->
