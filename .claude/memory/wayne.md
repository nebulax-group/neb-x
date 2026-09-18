# Wayne — Change Log

What Wayne changed, newest first. One entry per change the other two might depend on.

**Why:** the three of us work on mutually exclusive packages ([[team-split]]), so nobody reads
anyone else's diffs. This is where a change that crosses a package boundary gets announced.

**How to apply:** append an entry when you touch anything outside your own package — `common/`,
a shared constant, a file schema, a function signature, a cached artefact under `outputs/`. Purely
internal work inside your own subsystem does not need an entry.

**Role:** C — the app shell first (it blocks nothing but defines everyone's "done"), then
`src/shm/`, then the two upgrades: SHM via rainflow, and the app beyond minimal. See
[[team-split]].

## Scope — what this role writes

Set 2026-09-18. Anything outside this list belongs to someone else's package or is a read-only
input.

- **Write freely.** `src/app/` — the shell, and in `ui/` the shm view only — plus `src/shm/`, this
  file, and the generated `outputs/models/shm/` and `outputs/predictions/shm_predictions.csv`.
- **Write, then log it below.** `src/common/config.py`, `io.py`, `paths.py`. Already Wayne's work,
  but `common/` is shared, so a change there is a boundary crossing.
- **Ask before touching.** `src/submission/`, which [[team-split]] says is written together, and the
  root-level shared files: `requirements.txt`, `scripts/`, `CLAUDE.md`, `README.md`.
- **Never.** `src/rail/` (Jermaine); `src/door/`, `src/acv/`, `src/common/metrics.py` (Jou);
  [[jermaine]], [[jou]] and the shared memory files; `docs/`, `reference/` and `data/`.

**Why:** nobody reads anyone else's diffs ([[team-split]]), so an edit outside your own package is
invisible to its owner until it breaks their run.

**How to apply:** when a change needs a file from the last two bullets, describe it and wait.
Including it because it was needed is the failure mode this exists to prevent.

## Code style

**No unnecessary comments.** A comment earns its place only by explaining *why* — a constraint, a
trap, or a decision that looks wrong without it. Never restate what a line already says, never
label a section, never narrate a step. Names and structure carry the "what".

**Why:** [[project-structure]] rule 12 asks for why-not-what, but code drifts towards narration,
which ages badly and buries the one or two comments that actually mattered.

**How to apply:** write the file with no comments at all, then add back only the ones a reader
would be wrong without. This applies to every file written for this project, by anyone.

## Changes

### Template

```
### <time> — <short title>

**What:** the change, in one line.
**Why:** what forced it.
**Affects:** who has to do something differently, or "nobody".
```

### 2026-09-18 19:51 — SHM is a real model; checkpoints live under `outputs/models/`

**What:** `src/shm/` is finished — `features.py` (rainflow counting, ASTM E1049), `model.py` (the
S-N curve fit), `train.py`, and a `predict.py` that runs the model instead of returning a constant.
Leave-one-out MAPE is 2.5%, so SHM should score about 0.975. Four things cross a boundary:

1. **`outputs/models/shm/sn_curve.json` is a new cached artefact.** `outputs/` is gitignored, so it
   does not travel. On any machine that has not run `python -m src.shm.train`, SHM refuses to
   predict and says so. Training takes 46 s and needs the 6 GB `data/` folder.
2. **`outputs/predictions/shm_predictions.csv` is no longer the constant baseline** announced at
   19:10. It is model output now. Point 4 of that entry is superseded.
3. **`mape()` currently lives in `src/shm/model.py`**, because `src/common/metrics.py` does not
   exist yet. It is the fit objective there, not the official metric.
4. **`src/shm/config.py` now imports `src/common/config.py`** to derive `CHECKPOINT_PATH` from
   `MODEL_DIRS`. A subsystem config may import the common one; the reverse still must not happen.

**Why:** a fitted model has to be stored somewhere, and the checkpoint is the first thing in this
repo that a run *depends on* rather than produces. [[project-structure]] rule 10 says never commit
anything from `outputs/`, which is right for regenerable artefacts and awkward for this one, since
the demo video is a single take across all four subsystems on one machine.

**Affects:**

- **Everyone, for the demo video.** Whoever records it needs every subsystem's checkpoint present
  locally. Either that machine holds all of `data/` and runs each trainer, or we agree to ship
  checkpoints some other way — `Optional_Items/<Subsystem>/model/` is the obvious candidate and is
  a submission folder the organisers already ask for. This is still unresolved and it is the one
  thing that can stop a working submission from being demonstrable.
- **Jou.** When `src/common/metrics.py` lands, SHM will import its MAPE and report the official
  `max(0, 1 - MAPE)` from there. `model.mape` stays as the fit objective only.
- **Jermaine and Jou, when your models are ready.** The pattern that worked here, if it helps:
  `train.py` writes one JSON checkpoint to `MODEL_DIRS[<sub>]`, and `predict.py` loads it **inside**
  `predict()`, never at import. The app decides whether a subsystem is available by importing
  `predict.py`, so a checkpoint read at module scope turns a missing model into a crash at app
  startup instead of a sentence on screen. No silent fall back to a default value either — a
  plausible-looking number that no model produced is worse than a refusal.

### 2026-09-18 19:40 — Constants consolidated; `common/paths.py` deleted

**What:** `src/common/paths.py` is gone. It was a pure re-export of `src/common/config.py` and
nothing imported it, so paths now have exactly one home. Added `STREAMLIT_CONFIG_PATH` there. New
`src/app/config.py` owns every app dimension — page identity, on-screen copy, subsystem labels,
the palette and the font stacks — and no file under `src/app/` now holds a colour or a sentence as
a literal.

**Why:** [[project-structure]] rules 4-6. The palette in particular was stated twice, once in
Python and once in `.streamlit/config.toml`, which TOML cannot import from Python; `theme.apply()`
now reads that file at startup and raises if the two have drifted, so a stylesheet and a widget
theme cannot disagree on screen without someone noticing.

**Affects:** anyone who was about to `from src.common.paths import ...` — import
`src.common.config` instead, same names. Changing a palette value means changing it in
`src/app/config.py` **and** `.streamlit/config.toml`; the app refuses to start otherwise, and the
check names the key that disagrees.

### 2026-09-18 19:10 — App shell, SHM baseline, and the app's visual theme

**What:** `src/app/` and `src/shm/` now exist and run end to end. Four things cross a package
boundary:

1. **The subsystem contract.** Each subsystem exposes `predict(inputs: list[Path]) -> pd.DataFrame`
   in `src/<sub>/predict.py`, returning exactly that subsystem's submission rows with `file_id`
   echoed verbatim from disk. The app imports it lazily, so an absent or half-written module shows
   "not available yet" instead of taking the whole app down — nothing to coordinate, just keep the
   signature.
2. **`scripts/app.sh` / `scripts/app.bat`** start the app, creating `.venv` and reinstalling
   requirements when `requirements.txt` has moved since your last run.
3. **`.streamlit/config.toml` and `src/app/ui/theme.py`** hold the palette. Take colours from
   `theme.PALETTE`, never a hex literal, so the four subsystem views match.
4. **`outputs/predictions/shm_predictions.csv`** is a constant-value baseline, not a model.

**Why:** the app blocks nobody but defines everyone's "done", and the floor had to be banked before
modelling so a technicality cannot zero a subsystem.

**Affects:** everyone. Start the app with `./scripts/app.sh`. Write your view against the contract
in (1) and the tokens in (3). One trap worth knowing: Streamlit re-executes `main.py` on save but
**caches imported modules**, so a change inside `src/app/ui/` or your `predict.py` needs a server
restart, not just a browser refresh.

<!-- newest entries above this line -->
