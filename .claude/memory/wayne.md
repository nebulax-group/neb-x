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

### 2026-09-18 22:40 - validate.py exists; FILE_ID_COLUMN moved into common/config.py

**What.** `src/submission/` now has two files. `schema.py` reads a subsystem's columns off its
example CSV in `reference/submission_format/`; `validate.py` checks a prediction CSV against
that and returns every problem it finds. Run it as:

    python -m src.submission.validate <csv> [--inputs <test folder>]

It covers all four subsystems and special cases none of them. Door has no `file_id` and ACV has
no `prediction`, and both fall out of reading their own example file rather than out of a branch.

Three things cross a boundary:

1. **`FILE_ID_COLUMN` now lives in `src/common/config.py`.** It was defined in
   `src/shm/config.py`, which now imports it. If you were about to write your own, import it.
2. **The schema is never restated in code.** It is read from
   `reference/submission_format/<sub>_predictions.csv`, so the only way to disagree with the
   contract is to edit the contract. Do not hard code your columns in a check.
3. **`validate()` returns a list of problems, it does not raise.** Empty list means submittable.
   The command line turns a non-empty list into a `SystemExit`, so a caller cannot pass quietly.

**What it catches**, each verified against a deliberately broken copy: a stray index column, a
renamed column, columns in the wrong order, a rebuilt or lowercased `file_id`, a missing row, a
duplicate id, a blank cell, a header with no rows, and a wrong filename. The Door example from
`reference/` passes unmodified.

**What it does not check.** Value vocabularies. Rail's `Normal` / `Side I` / `Side II` and ACV's
`|`-separated car ids cannot be derived from a three row example, so they are left to their
owners. Add them in your own package if you want them, or tell me and I will put them behind the
schema.

**Why.** [[team-split]] says no subsystem is finished until its CSV passes validate, and these
are the failures that score zero while the file looks perfectly fine when opened. The organisers
do not re-run our code, so the CSV is the whole submission.

**Affects.** Jermaine, Jou: run it on your own CSV before the zip. Point 1 changes an import if
you defined `FILE_ID_COLUMN` yourself. `package.py` is still unwritten.

### 2026-09-18 22:05 - Explain panels are a stepped deck, one at a time

**What.** The explainability panels no longer stack down the page. `src/app/ui/explain.py` now
draws one panel per step, with a numbered rail plus back and next above it. Interface copy was
cut back across `src/app/config.py` and `src/shm/explain.py`, and em dashes are out of every
on-screen string.

Four things cross a boundary:

1. **A subsystem's panels are shown one at a time, in the order `explain()` returns them.** Put
   the panel that answers the question first; it is the one a viewer sees without clicking. The
   panel contract itself is unchanged, so nothing you write needs editing.
2. **A panel's `title` and `subject` are drawn by the rail, not above the chart.** Do not repeat
   the title inside a panel, it will show twice.
3. **New config names:** `PANEL_STATE_KEY`, `STEP_COUNTER`, `STEP_BACK`, `STEP_NEXT`,
   `STEP_NUMBER`, `CHART_PADDING_LEFT`. `_PANEL_HEAD` in `explain.py` is gone, along with the
   `.nx-panel-title` and `.nx-panel-titles` rules in `theme.py`.
4. **Interface copy is terse now and has no em dashes.** Match it if you add a string. One short
   sentence, two at most, and a full stop where an em dash would have gone.

**Two traps.**

- **A Streamlit button with `help=` renders two `button` nodes**, one of them the hidden tooltip
  target. A `.st-key-x button` selector in a test hits the hidden one first and reports "element
  is not visible". Use `button:visible`.
- **Do not put a spacer column between back and next.** Streamlit keeps that spacer's width when
  the sibling columns are hidden at phone width, and the two buttons collapse to nothing. They
  sit on their own two column row instead.

**Why.** Wayne asked for it: four stacked charts made a very long page, and scrolling is dead
time in a three minute demo video. Discrete steps also tell a viewer how many there are.

**Verified.** Playwright at 1440px, 768px and 390px, stepping through all four panels: zero
console errors, zero page errors, zero exceptions, zero horizontal overflow, exactly one chart
rendered per step. The numbered cells are hidden below 640px, where back and next carry the
navigation and the step counter says the position.

**Affects.** Jermaine, Jou: points 1 and 2 change how your panels appear if you write an
`explain.py`, and point 4 is the copy standard now. The checkpoint problem from the 19:51 entry
is still unresolved.

### 2026-09-18 21:25 — The app is a dark instrument board; every palette token renamed

**What.** The app was redesigned end to end. It was warm cream with a terracotta accent,
hairline rules and a `st.selectbox` that defaulted to Door — a subsystem with no model, so the
first thing anyone saw, judge included, was "not available yet". It is now a depot condition
desk: deep petrol ground, instrument cyan accent, Archivo over IBM Plex Mono, and a board of
four cards with readiness lamps in place of the dropdown.

Eight things cross a boundary:

1. **Every `PALETTE` key was renamed. The old ones are gone** and `PALETTE["oxide"]` is now a
   `KeyError`, not a wrong colour. The new names: `abyss` `deck` `deck-high` `hairline`
   `hairline-strong` `chalk` `chalk-dim` `instrument` `instrument-deep` `instrument-wash`
   `clear` `caution` `danger`. If you wrote anything against the old palette, it needs the
   mapping: oxide→instrument, paper→abyss, ink→chalk, ink-muted→chalk-dim, rule→hairline,
   rule-strong→hairline-strong, grid-header→deck-high.
2. **`.streamlit/config.toml` is `base = "dark"`** and still has to agree with `PALETTE`
   value-for-value; `theme.verify_widget_theme()` raises at startup and names the key that
   disagrees. Changing a colour still means changing both files.
3. **`upload.render_subsystem_picker` is gone.** Selection lives in the new
   `src/app/ui/board.py`, which loops over `SUBSYSTEM_LABELS` and asks `services.is_available`
   per key — still no branching on subsystem internals, so rule 8 holds.
4. **`upload.render_uploader(label, subsystem)` takes the subsystem key now.** The uploader is
   keyed per subsystem so switching systems clears the previous batch instead of carrying one
   system's recordings into another system's model.
5. **`src/app/config.py` gained `SUBSYSTEM_BLURBS`,** one line per subsystem saying what it
   listens to. It is checked against `SUBSYSTEMS` at import, so a missing key raises rather
   than quietly dropping a card. Adding a subsystem means adding a line there and in
   `SUBSYSTEM_LABELS`, and nothing else.
6. **New `src/app/ui/section.py`** draws the section heads. Use it rather than a fresh heading,
   or the board and the results drift apart in type and spacing.
7. **The panel contract in `src/app/services.py` is unchanged.** If you were going to write
   `src/<sub>/explain.py`, none of this affects you — the four kinds and their fields are the
   same, and the charts are now drawn in the new palette automatically.
8. **Three more traps, on top of the four in the 20:10 entry:**
   - **`_STYLESHEET` in `theme.py` is `%`-formatted**, so every literal `%` in the CSS must be
     written `%%`. A single `height: 100%` took the whole app down with
     `TypeError: not enough arguments for format string` — at import, before anything rendered.
   - **A card is `st.container(key=...)`**, which Streamlit turns into a stable
     `st-key-<key>` class. That is the only way to get one border around a markdown block and
     its button. State is carried by a class on the inner markup and read with `:has()`.
   - **Push the button to the foot of a card with `:has(.stButton)`, not `:last-child`.** The
     dormant cards have no button, so a `:last-child` rule bottom-aligns their text instead and
     the board looks broken in a way that only shows on the cards you were not testing.

**Why.** Ease of Use is a third of the grade outright and Problem Fit separately lists UI and
explainability, so the app carries more weight than any one subsystem's model. The old page had
two real faults underneath the aesthetics: it opened on a dead end, and it presented the result
as a bare table of floats that a non-technical reader cannot rank. The board fixes the first and
states readiness up front; the dark instrument ground exists because this is a condition
monitoring desk, and the stress trace in cyan on petrol reads as an instrument rather than as a
chart in a document.

**Verified.** Playwright drove the real app end to end at 1440px, 768px and 390px — pick SHM,
upload, wait for the panels, scroll to the trace. Zero console errors, zero page errors, zero
`stException` blocks, zero horizontal overflow, three charts with a rendered surface each, at
every width. `AppTest` would have caught none of it; the `%` fault above was an import-time
crash and the card misalignment was visible only in a screenshot.

**Affects.**

- **Jermaine, Jou.** Points 1 to 6 are the ones that can break something you have already
  written. Point 7 is the reassurance: the explain contract did not move.
- **Both, still unresolved.** The checkpoint problem from the 19:51 entry has not moved.
  `outputs/` is gitignored, the demo video is one take across four subsystems on one machine,
  and `Optional_Items/<Subsystem>/model/` remains the obvious home. Still needs a decision from
  the three of us.

### 2026-09-18 20:10 — Subsystems may now explain themselves; the app draws it generically

**What.** The app gained a second, optional capability alongside `predict`. If
`src/<sub>/explain.py` exists and exposes `explain(inputs) -> list[dict]`, the app renders those
panels under the results table. SHM has one; the other three do not, and nothing breaks for them —
`services.load_explainer` returns `None` and the page is exactly as it was.

Six boundary-crossing points:

1. **The panel contract is documented in `src/app/services.py`,** not here, so it stays next to the
   code that consumes it. A panel is a plain dict with `kind`, `title`, optional `caption` and
   `subject`, plus fields per kind: `metrics`, `bullet`, `bars`, `line`. The renderer
   (`src/app/ui/explain.py`) switches on `kind` only — never on the subsystem — so rule 8 still
   holds and neither of you has to touch the app to get charts.
2. **If you want this for rail, door or ACV, you write one file** — `src/<sub>/explain.py` — and
   nothing else. No app change, no `common/` change, no coordination with me. Rank confidence for
   ACV and per-class probability for rail would both drop straight into the `bars` kind.
3. **`src/shm/features.py` gained `cycle_damage(cycles, exponent)`,** returning the per-cycle terms
   `damage_sum` was already adding up; `damage_sum` now calls it. Internal to SHM, noted only
   because the SHM predictions are unchanged byte-for-byte after the refactor and I checked that
   rather than assumed it. `src/shm/config.py` gained `TRACE_TARGET_POINTS` and
   `CONCENTRATION_BANDS` alongside it.
4. **`src/app/ui/results.py` and the new chart code use `width="stretch"`,** not
   `use_container_width`, which Streamlit has deprecated past its removal date. If you add a
   `st.dataframe` or `st.altair_chart` anywhere, use `width=`; the old spelling prints a warning
   into the terminal during the demo recording.
5. **Four Streamlit traps, all of which cost me a round trip.** If you add any chart, read these
   first:
   - **A chart's `padding` must be the four-sided object**, never a single number. Streamlit sets
     `autosize.contains="padding"` and its wrapper then writes `padding.bottom` onto the spec,
     which throws `Cannot create property 'bottom' on number` *in the browser only*.
   - **A chart's `height` is the whole SVG**, not the plotting area — padding and the x-axis come
     out of it. `src/app/config.py` has `CHART_AXIS_ALLOWANCE` for this.
   - **In a layered chart, one `axis=None` anywhere removes that axis for every layer.** Either
     all layers declare it or none do.
   - **Streamlit's own CSS beats a bare class selector** (`.st-emotion-cache-x h1` is 0-1-1). Any
     rule for `h1`-`h3` or `p` must be qualified — `.stApp h2.my-class`.

   **`streamlit run` does not reliably reload imported modules.** Changes to anything under
   `src/app/ui/` need the server restarted; I spent a cycle diagnosing a CSS fix that had in fact
   worked but was never served.

6. **Streamlit's `AppTest` does not catch any of the above.** It runs the Python half only, so a
   spec that crashes the browser passes it silently — which is exactly how a broken chart reached
   Wayne. Charts have to be opened in a real browser, and these were: Playwright drove the running
   app end to end (pick SHM, upload ten files, wait for the panels) collecting console and page
   errors, at 1440px, 768px and 390px. Final state is zero console errors, zero page errors, zero
   `stException` blocks, and zero horizontal overflow at every width.

   The masthead title also became a real `<h1>` so the new `<h2>` is not orphaned; that is what
   exposed the CSS specificity trap above, since Streamlit then styled it.

**Why.** The app was showing a bare number. `0.4406` is correct and unreadable: a judge cannot tell
it apart from a random float, and Problem Fit scores explainability and UI while Ease of Use scores
clarity of visuals. The panels answer "why that number" with the model's own intermediate values —
damage against the Miner threshold of 1.0, the share of damage held by the largest cycles, and the
stress history itself.

Nothing in the panels invents a quantity the Info Kit does not define. It gives exactly one
threshold (§1.3.1, failure at D >= 1) and names remaining-life assessment as the business need
(§1.2), so the panels show damage against 1.0 and `(1 - D) / D` further runs, and no severity
bands of our own.

**Affects.**

- **Jermaine, Jou.** Point 2 is the offer: one file each, entirely inside your own package, and the
  app picks it up. Points 4 to 6 apply to any Streamlit call either of you adds — read them before
  writing a chart rather than after.
- **Both, still unresolved.** The checkpoint problem from the 19:51 entry has not moved.
  `outputs/` is gitignored, so `outputs/models/shm/sn_curve.json` does not travel, and the demo
  video is one take across all four subsystems on one machine. Whoever records it needs every
  model present locally. `Optional_Items/<Subsystem>/model/` is the obvious home and the
  problem statement already asks for trained models there. This needs a decision from the three
  of us, not from me.

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
