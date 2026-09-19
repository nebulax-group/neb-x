# Wayne — Change Log

### 2026-09-19 — `requirements.txt` moved into `scripts/`, and the submission is built at the root

Three changes that reach every machine here. All three were asked for.

**1. `requirements.txt` is now `scripts/requirements.txt`**, and `install.sh` / `install.bat`
moved with it. Muscle memory for `pip install -r requirements.txt` at the root now
installs nothing. `video/requirements.txt` is untouched — that one is manim's and stays
where `scripts/render.sh` looks for it.

- `src/common/config.py` gained `REQUIREMENTS_PATH = SCRIPTS_DIR / "requirements.txt"`.
- Both install scripts now `cd` one level up before doing anything: `.venv` belongs to
  the repository root, not to `scripts/`.
- All sixteen wrappers were repointed, including the SHA stamp they hash to decide
  whether to reinstall. The stamp is over the file's contents, which did not change, so
  nobody's venv reinstalls because of this.
- `package.copy_app` copies it to the **bare name** `app/requirements.txt`, because the
  `run.sh` shipped beside it looks for exactly that. `APP_CONTENTS` is now paths relative
  to the repo root rather than names, and the copy uses `name.name`. Diffed a fresh
  `copy_app` against the last shipped `app/`: **identical but for `common/config.py`
  itself**, which ships because the app imports it.

**2. `./submit.sh` builds `<Team Name>/` at the repository root**, not `submission/<Team Name>/`.
The folder is what gets uploaded, so nothing wraps it that could be sent in its place.

- `SUBMISSION_DIR` → **`SUBMISSION_ROOT = REPO_ROOT`**. `PREDICTIONS_ZIP_PATH` is **deleted**:
  nothing imported it, and it would now resolve to `REPO_ROOT/predictions.zip`, which is a
  path that never exists.
- **`.gitignore` had to change with it, and this one has a consequence.** The folder carries
  the registered team name, so no rule can match it by name. `/*/` now ignores every
  top-level folder and the ten that belong in git are listed back by name. So: **a new
  top-level folder is invisible to git until someone adds a line there.** If `git add`
  ever appears to do nothing, that is why.
- The old `submission/` folder at the root is orphaned. Delete it.

**3. `scripts/train.sh` / `.bat` is new — every subsystem in one pass.** It asks
`common/config` for `SUBSYSTEMS` and treats one as trainable exactly when it ships a
`train.py`, the same way the app decides what it can predict, so nothing restates the
list and a new subsystem joins by existing. ACV lands in *"no trainer, nothing to fit"*,
which is correct: its ranking fits no parameters. Each subsystem runs as its own process,
so one whose data is absent on that machine costs only itself; the script exits non-zero
naming what failed. **It takes no arguments on purpose** — `--refresh` means something to
rail and is an error everywhere else, so per-subsystem flags stay with the per-subsystem
wrappers.

**README.** Quick start is now one command, `./scripts/app.sh`, which is the whole setup.
The `uv venv` / `uv pip` instructions are gone: **this venv has pip** (26.2.1), so the
warning that it did not was stale and sent people around the install scripts. Training is
documented per subsystem as its script plus the unified one, and the `python -c` predict
one-liners are gone with it — `./submit.sh` is the documented way to produce the CSVs.
The only raw reference left is `src.acv.report.confirmation`, kept because Jou's note says
to read it before trusting a ranking and it has no CLI.


### 2026-09-19 — `./submit.sh` was broken on a fresh clone, and the app it shipped could not predict

Two faults in the submission path, both found by running `./submit.sh` end to end for
the first time rather than by reading it.

**1. Five wrappers were committed without their executable bit.** `scripts/generate.sh`,
`scripts/render.sh` and all three `scripts/train_*.sh` were mode 100644 in git, so
`./submit.sh` died on *"Permission denied"* at step 1 of 3 on any clean checkout, and
so did the training and video wrappers the README documents. `chmod +x` on the five;
the mode change is what git records. The `.bat` twins are unaffected, Windows has no
executable bit. **Check this after any clone or any `git archive`.**

**2. The `app/` we shipped reported every system as ready and failed on the first
click.** `app/` carried no `outputs/models/`, and `services.is_available` only imports
the predictor, so the board drew four ready systems and each one raised *"No Door
checkpoint at .../app/outputs/models/door/classifier.joblib"* when used. The
checkpoints were in the submission the whole time, in `Optional_Items/<Subsystem>/model/`,
with nothing pointing the app at them. `package.copy_checkpoints` now lands each ready
subsystem's `MODEL_DIRS` at the same path relative to `app/` that it has relative to
the repo root, which is what makes it findable with no subsystem config change. All
1.3 MB of it; the folder went 2.1 MB to 3.3 MB. **This is the 19:51 checkpoint problem
closed for the submission folder.** The Cloud Run deploy still needs the same move,
and [[deploy-gcloud]] §5 already describes it as `COPY models/ ./outputs/models/`.

Verified by running all four subsystems through `services.run_prediction` from inside
`submission/Group1/app`, with the repository's own `outputs/` out of reach: door 38
rows, acv 1, rail 1, shm 1.

**`app/` now holds what starts the app and nothing else.** It was the whole of `src/`
plus every wrapper in `scripts/` plus `install.*`, `submit.*` and the project README.
Two of those were worse than clutter: `scripts/render.sh` calls `src.video.render`,
whose manim dependency `requirements.txt` deliberately lacks, and the train wrappers
need a `data/` §4.1 says not to send back, so a judge exploring the folder found
controls that error. It now ships `.streamlit/`, `requirements.txt`,
`src/{__init__.py, app, common, door, acv, rail, shm}`, `outputs/models/` and one
entry point. `src/submission/` and `src/video/` are gone from it, confirmed by grep
that nothing the app loads imports either.

**The entry point is `run.sh` / `run.bat` at the top of `app/`**, kept as real scripts
under `src/submission/runner/` rather than as strings in the packager. The
repository's own `scripts/app.sh` cannot serve: it climbs to a repository root that is
not there and calls an `install.sh` that no longer ships. The runner creates `.venv`
on first use, installs `requirements.txt`, and starts Streamlit. Its mode is **set to
0755 by the packager rather than inherited**, because a lost executable bit is exactly
what broke `./submit.sh`, and here the same bit is the only thing between a judge and
the app.

Proved by copying `submission/Group1/app` somewhere with no repository around it and
running `./run.sh`: it built its own venv, installed, started, drew four ready systems,
took an upload and returned the right Door verdict (8 of 38 abnormal), with the review
download present, no exceptions and no console errors. **First launch on a fresh
machine takes a minute or two** — pip, then a bytecode-cold first import of pandas,
sklearn and openpyxl. After that the board is up **5.7 s** from a cold process and
0.4 s on reload. Worth knowing before anyone films the demo on a clean machine.

**Also added: the optional write-up now has a slot.** `write_up.<pdf|docx|md>` at the
repository root is copied to the top of `Optional_Items/`, where §4.2 puts it, and its
absence is reported at the end like the video's rather than stopping the build. New
constants `WRITE_UP_DIR`, `WRITE_UP_STEM`, `WRITE_UP_EXTENSIONS` in
`src/common/config.py`. New `tests/test_submission_package.py`, 6 tests, which had none: the app holds only
the runnable set, the runner is executable, the checkpoints land where the copied app
looks, and the write-up is placed or reported.

**What `./submit.sh` does, confirmed against §4 by building it:** derives all four
prediction CSVs itself and never reuses one left on disk, validates them, then writes
`submission/<team>/` with `predictions.zip` flat at the top, `app/` once at the team
root, and `Optional_Items/<Subsystem>/{code,model}/` under the organisers' own folder
names. No dataset, no `04_Example_Submission/`, no `outputs/`. A CSV that exists but
fails its schema still stops the build, deliberately: the organisers score the zip
as-is. Everything else missing is a line under *"not submittable yet"* and the build
carries on, because the video and the write-up are made last.

**Affects: everyone.** `./submit.sh --team Group1` now runs to completion. Jermaine and
Jou: your checkpoint travels inside `app/` automatically, with nothing to coordinate,
as long as it is in `outputs/models/<sub>/` when the submission is built. Still
outstanding and unchanged: the demo video, and a write-up if we want one.


### 2026-09-19 — Systems are queued and assessed one at a time; the board carries the live state

Each system's assessment now runs off the script thread, so starting one no longer
holds the page. **One worker drains the queue**, so systems are assessed in the order
they were started and two models never compete for the machine; running four at once
was tried first and Wayne reported the app felt slower for it. New `src/app/jobs.py`
keeps one job per system on that queue;
`src/app/workspace.assess` starts or collects rather than blocking, and returns an
`Outcome` of idle/queued/running/ready/failed instead of a `Run` that raised.
`workspace.standing` answers where every system stands, not just the selected one.
New `src/app/ui/progress.py` draws the queued and running panels under the same
Assessment head the verdict uses, and polls with a `st.fragment(run_every=...)` mounted
only while something is outstanding. A settled job is kept, so a batch that failed is
reported once rather than retried on every rerun.

**The board is now three colours, which the reader asked for: blue is nothing assessed,
red is on the queue, green is an assessment that finished.** A system with no model
keeps the resting hairline and still says "No model yet". The colour lives in one
`--nx-tone` variable per card, so the edge, the lamp and the selected ring cannot
drift apart, and selection became a doubled inner edge rather than a recolour.
**Worth knowing before anyone builds on it: green here means "finished", not "healthy",
so a card is green while its own verdict reads CAUTION or ALERT.** That is a second
meaning for the signal aspects the palette had reserved for severity, and it was taken
deliberately rather than by accident.

One trap, found only by driving the real app: **the watch has to compare against the
standing the board drew, not the standing at the end of the run.** The worker usually
starts between those two moments, so recording the later one left the fragment already
holding the change it existed to notice, and a working system reported itself "Queued"
for its whole run. Tests did not catch it; the board did.

**The handoff takes in every finished assessment, not only the selected one.**
`workspace.collect` walks the job table on each run and harvests any settled job whose
result is not already saved; a failed one is never collected. Before this, `runs` was
written only by `assess`, which runs for the selected system alone, so a system that
finished while the reader was on another one went green on the board and stayed absent
from the review package until it was selected again. Reported by Wayne, confirmed in
the browser: ACV now reaches the handoff at the moment it finishes, with Door selected
throughout and ACV never revisited.

**A batch is assessed whole, and Clear all is the only way to change one.** The
uploader's per-file remove and its add control are hidden in the stylesheet, because
either one lets a reader change the batch under an answer that has already been given
about it. `workspace.reset` puts a system back to where it was before any file reached
it: batch, job, assessment, memoised reading, staged copy, and the view and step it was
left on. **A Streamlit uploader cannot be emptied by writing to its own state**, so
clearing draws a new widget instead: `config.UPLOAD_GENERATION_KEY` counts per system
and the count is part of the uploader's key. Clear all is offered only when there are
files and never while the system is on the queue, which is the same rule as the lock.

The staged copy is removed with the run, **but only when nothing else points at it** —
two systems given the same files share one staged directory and one reading. Without
that, a session working through several large batches carries every one of them until
the process ends, which on a filesystem held in memory is the whole budget.

**A system on the queue holds its uploader shut**, from the moment it joins until it
finishes. `st.file_uploader(disabled=...)`, which disables the browse control and every file's remove button and refuses
drops. Measured in the browser, not assumed. The widget keeps its value, and
`assess` additionally refuses to drop a batch that reports empty while its job is on
the queue, because a locked uploader has no way of being emptied by the reader.

`src/app/cache.py` no longer uses `st.cache_data`: a pool thread has no script context
for it. It is a bounded LRU behind `digest` / `staged` / `reading(subsystem, batch,
uploads)` / `clear()`, built outside its lock so two systems do not queue. The digest
is now memoised against Streamlit's own upload ids, so a large batch is hashed once
rather than on every rerun; it was being re-read three times per interaction.

**`.streamlit/config.toml` gained `fileWatcherType = "none"`, and this, not the
threading, is what actually bought the responsiveness.** Without it the page still froze: Streamlit
re-walks `sys.modules` and realpaths every entry after each script run, on the event
loop, and polls those paths from four threads because watchdog is not installed. A
subsystem that imports a large dependency mid-run grows that set enough to stall the
loop for the whole length of its model. Measured with ACV: **a click on another system
took 32 s to be answered before the change and 0.23 s after.** Nothing reloaded on edit
anyway, so this costs only what a restart already cost.

**Everything not selected recedes.** Name and blurb drop to 0.78 opacity on a darker
ground, while the lamp and the coloured edge keep full strength: a system's standing
has to stay readable right across the board, which is the whole point of colouring it.
Measured rather than eyeballed, the dimmed blurb sits at **5.08:1**, so it clears AA
with margin; 0.72 was tried first and landed on 4.5:1 exactly.

Removed: the masthead's "4 of 4 systems ready" chip and the per-card "Model ready"
line, with `READY_CHIP`, `BOARD_READY`, `SPINNER_MESSAGE`, the `chip` argument to
`masthead.render` and the `.nx-chip` rule. A ready system now shows a lit lamp and no
words; "No model yet" and "Running" stay, because those are the two states a reader
has to act on or wait for. Motion added in five places, all transform/opacity and
150-220 ms: the running lamp pulse, a sweep on a working card's foot and in the
running panel, the verdict entrance, a stepped panel entrance, and card hover plus
button press. Entrances are confined to things that genuinely arrive — verified that
the verdict does **not** replay its entrance on an unrelated rerun, which is what
would have made it a twitch. One `prefers-reduced-motion` block now covers all of it.

**Affects: Jermaine and Jou — nothing in your packages changes.** `predict`, `explain`,
`validate` and `handoff.build` are called exactly as before, with the same signatures,
and the panel contract in `services.py` is untouched. Two things are newly true of
your code, though: **it runs on a queue worker, so it must not touch `st`**, and a
reader can be looking at another system while yours works, so it must not rely on
mutable module-level state surviving between calls. Only one subsystem runs at a time,
so nothing you write contends with another subsystem's run. Restart the app after
editing anything under `src/app/`; that was always required and is now enforced by the
watcher being off.

**Jou, one measurement worth having:** `src/acv/validate.py` parses the whole workbook,
so the app reads `acv_test_case.xlsx` twice per assessment. Validate alone is 9.5 s and
validate plus predict is 20.0 s, so about half of ACV's wall time on the board is the
same file being read a second time. Rail hit this and fixed it by reading the header
alone with `nrows=0` (see [[jermaine]], 2026-09-19): the question "was this recorded by
this system" is settled by the column names either way. Not changed here, it is your
package.

Validation: 235 tests pass, including new ones for the queue order, the board's
standing for every system, a locked system keeping its batch, a reset clearing every
key it should, and three assessments in a row through one reset each.

Browser checks at 1440/768/390. Queue: ACV red and pulsing while Door sat red and still
at "Queued", Door starting only once ACV finished, both ending green with Rail and SHM
still blue, the uploader locked throughout. **Continuous use: three Door batches
assessed and cleared in a row on one running app, each going blue to red to green and
back to blue, the handoff gaining and losing its row each time, no per-file control
reachable in any round, and SHM still assessing normally afterwards.** No console
errors, no page errors, no exceptions, no horizontal overflow, reduced motion honoured.
Screenshots are in the session scratchpad, not under `outputs/`.

### 2026-09-19 — Session windows and maintenance handoff

Each subsystem keeps its uploader, latest assessed batch, view and cycle selection
while the browser session is active. `src/app/workspace.py` owns those run records;
changing or removing files invalidates the old batch before inference, including
failed replacements. This is not durable storage or a history of every run.

The app now resolves an optional `src.<sub>.handoff.build(inputs, frame, panels)`
capability, implemented for Door, ACV and SHM. It returns selected findings, suggested
recipient roles, actions, method, limitations and chart evidence. Missing/failed
evidence is explicitly incomplete, never an all-clear. Subsystems remain independent.

A single bottom-centered download replaces the UI prediction downloads. The ZIP
contains Summary.txt, an offline Report.html, a source-checksum manifest and per-system
README.txt, with findings.csv and SVG bars only where there are selected findings.
No raw recordings, full prediction tables or model binaries. SHM is per-recording
damage, not remaining lifetime; ACV candidates are not confirmed leaks. Source files
must be mapped to actual assets before action. Suggested roles are not verified contacts
and this is not an LTA approval. Submission CLI schemas and model outputs are unchanged;
the review ZIP is not the hackathon predictions.zip.

Validation: 109 app, Door and submission tests passed. Headless desktop/mobile checks
verified retained uploads, views and Door cycle selection, ZIP download and metadata,
and exclusion of a stale SHM assessment following an invalid replacement upload.

**Affects:** Wayne (app/SHM), Jou (Door/ACV handoff capabilities).

### 2026-09-19 — Door cycle selection and detail card polish

Removed the decorative train ends. Selected cycles now have a cyan outline and
checkmark, independent of their normal/abnormal colours. Door strip cells supply
optional structured fields for a selection card: cycle, operation, status, start,
end and elapsed duration. Controller timestamps are formatted for display with
readable dates and exact milliseconds; exported prediction timestamps stay verbatim.
The generic strip renderer still supports plain `detail` text from other producers.

Validation: 21 focused tests passed, including midnight and millisecond formatting;
headless browser checks verified normal/abnormal selection, keyboard navigation,
removed train graphics and the 375px layout. Screenshots: `outputs/logs/door-refresh-*.png`.

**Affects:** Jou (Door explanation cells), Wayne (shared strip renderer/styles).

### 2026-09-19 — Finish upload recovery, Door selection and assessment guidance

Continued the partial app work. `services.run_prediction` now asks an optional
`src.<subsystem>.validate.validate(inputs)` to check recordings before loading a model.
Door, ACV and SHM implement it; prediction CSV schemas and model calculations are unchanged.
Failures distinguish bad uploads, unreadable files, missing setup and processing errors.
The page shows expected layouts, recovery instructions and expandable diagnostics.

Door's strip uses native keyboard/touch/click selection, displays start/end times,
operation and status, and retains selection through reruns using the existing reading cache.
Strip subjects identify the source recording. Verdict panels may now include a
`recommendation` dictionary containing `title` and `steps`, supplied by the subsystem.
The app renders those instructions in both Answer and Details. SHM guidance explicitly
states that prior damage must be reviewed separately from the uploaded recording.

Validation: 115 app, Door, ACV and submission tests passed. Headless browser checks
cover wrong-system feedback, expandable diagnostics, Door selection persistence,
keyboard interaction, CSV download, 375px/mobile/landscape layouts, and real ACV/SHM
recordings. Local screenshots are under `outputs/logs/`.

**Affects:** Jou (Door/ACV validation and verdict contract), Wayne (SHM/app). A future
subsystem can implement the optional validator and recommendation without app routing changes.

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

### 2026-09-19 06:31 - The organisers' FAQ makes the interface half the problem

**What.** An organisers' FAQ answer, reported by Wayne, splits PS3 into two parts. Part 1 is the
model, and they say so plainly: the ML solution is *"intended to be relatively achievable"* and
*"serves as a baseline for your submission to be compliant."* Part 2 is the interface, and it
names two readers:

- **the operator**, who has to use this information for **split-second judgements**;
- **a new engineer**, who may not be familiar with the data parameters or train behaviour.

The ask is to translate *"such technically complex information"* for those two *"in a user-friendly
interface so they can act on this information"*.

**Why this changes the weighting.** [[team-split]] already argued the app carries Ease of Use
outright and contributes to Problem Fit. The FAQ goes further: a good model is the *floor*, not the
differentiator. Nothing in the metric tables or the info kits says this — it exists only in the FAQ
— so it belongs in memory or it is lost.

It also settles something the app has been guessing at. `src/app/config.py` writes its blurbs for
"someone who maintains trains rather than someone who wrote the model", but that was house style,
not a brief. The two readers are now named, and they want different things: the operator wants a
decision and its urgency, the new engineer wants to know why the system reached it.

**The gap, as the app stands.** Recorded as a gap, not a plan — no decision taken here:

1. **The results screen shows the submission CSV.** `ui/results.py` renders the scored artefact
   verbatim — `start_time,end_time,prediction` for door, a `|`-separated rank string for acv. That
   is right for the judge and close to useless for an operator on a platform.
2. **Only SHM explains itself.** `explain` is optional by design in `app/services.py`, and three of
   the four subsystems do not offer it.
3. **Nothing on screen carries urgency.** The palette deliberately holds green/amber/red back "for
   signal aspects — they carry meaning a subsystem supplies, never a severity the app invented".
   The FAQ implies the subsystems should now supply it: a rank or a damage figure is not yet an
   answer to "do I act on this today".

**Affects.** Everyone, and it lands in each person's own files rather than in shared ones —
[[team-split]] gives rail's view to Jermaine, door and acv to Jou, shm to Wayne. If we act on this,
the per-subsystem work is an `explain` module and a severity the subsystem decides, not a change to
the app shell; the shell already draws whatever panels it is handed and never branches on which
subsystem sent them.

### 2026-09-19 00:45 - Merge and deploy plan for the prototype URL

**What.** The order of operations that turns four separate packages into one deployed site, and
what each of us has to hand over for it to work. None of this is built yet. It is written now so
merge day is assembly rather than design.

**Why.** The portal's prototype URL (00:20 entry) needs a running site, and a site has no `data/`,
so every subsystem on it predicts from a checkpoint that travelled in git. That is a contract
between three packages, and a contract agreed after the merge is a contract agreed too late.

#### 1. What each subsystem owes the deployed app

Three things, per subsystem. Two of them are not code and are the ones that get forgotten.

| Owed | Shape | Whose |
|---|---|---|
| `src/<sub>/predict.py` with `predict(inputs: list[Path]) -> DataFrame` | Rows exactly as the schema, `file_id` echoed verbatim from disk | Owner |
| A fitted checkpoint committed outside `outputs/` | See section 2 | Owner |
| Its runtime deps in `requirements.txt` | Pinned, resolving on the deploy's Python | Owner, announced here |

`src/<sub>/explain.py` stays optional. `services.py` already treats its absence as normal and
renders the table alone.

Two failure modes to design out rather than discover:

1. **Code without its checkpoint.** `is_available()` imports the module, so a pushed `src/rail/`
   with no checkpoint shows Rail as ready on the board and then fails when a judge clicks it. The
   two must land in the same commit.
2. **A checkpoint that cannot be refitted on the host.** Nothing on the deploy can train. Whatever
   is in git is what the site predicts with, forever.

#### 2. Where a committed checkpoint lives

`models/<sub>/` at the repository root, tracked in git.

The 00:20 entry proposed `Optional_Items/<Subsystem>/model/`. That was wrong: `Optional_Items/` is
generated by `package.py` under `outputs/submission/`, so committing into it would collide with
the packager and still sit under a generated tree. A top-level `models/` is a source input, not an
artefact, so [[project-structure]] rule 10 stands untouched.

The changes that needs, all of them boundary crossings and none of them written yet:

- `src/common/config.py`: `COMMITTED_MODELS_DIR = REPO_ROOT / "models"` and
  `COMMITTED_MODEL_DIRS`, mirroring `MODEL_DIRS`.
- `src/<sub>/config.py`: resolve the checkpoint as the first of `MODEL_DIRS[...]` then
  `COMMITTED_MODEL_DIRS[...]` that exists. `train.py` keeps writing to `outputs/` only.
- `.gitignore`: nothing. `models/` is not matched by the `outputs/**` rule.
- Promoting a checkpoint stays a deliberate copy by its owner, never a step inside `train.py`.
  A trainer that commits its own output is how a half-fitted model reaches a judge.

Format and size, worth agreeing before anyone fits anything final:

- Prefer JSON or `.npz`. SHM's `sn_curve.json` is 576 bytes because the model is its parameters.
- A pickle binds the deploy to the exact scikit-learn that wrote it. If a pickle is unavoidable,
  the pin in `requirements.txt` is then load-bearing and cannot be bumped casually.
- Keep each under roughly 25 MB. Past that, git and the deploy both get slow, and we should talk
  about a smaller model rather than about Git LFS at hour nine.

#### 3. Merge day, in order

1. Each owner pushes their branch: package, checkpoint under `models/<sub>/`, deps.
2. Merge into `main` one at a time, running the app after each. A merge that leaves the board
   showing a system as ready when it is not is the only merge that must be reverted immediately.
3. `requirements.txt` becomes the union. Whoever merges last resolves conflicts and reinstalls
   from scratch in a fresh venv, not into their existing one.
4. `python -m src.<sub>.predict` for each, on the real test folder, then `./validate.sh` across
   all four. The CSVs the site produces must match the CSVs the CLI produces.
5. `DEFAULT_TEAM_NAME` to `Group1` in `src/common/config.py` (00:05 entry) so the bare
   `./submit.sh` is correct.

#### 4. Deploying

Streamlit Community Cloud, free, deploys from a GitHub repo and redeploys on push.

1. The repo must be reachable by the deploy. Public is simplest and the portal wants a repository
   URL anyway, so check the history for anything private before flipping it, in particular that no
   dataset was ever committed.
2. New app, main file `src/app/main.py`. `main.py` already puts the repo root on `sys.path`, so no
   packaging change is needed.
3. **Python version is the one real risk.** `requirements.txt` says it was verified on 3.14.7;
   Community Cloud tops out below that. Pick the highest it offers, then resolve
   `requirements.txt` on that version locally first. If `pandas==3.0.6` or `numpy==2.5.3` has no
   wheel there, we relax those two pins for the deploy rather than rewriting code.
4. No secrets, no environment variables, no `data/`. If the site asks for any of them, something
   imported a training path and that is the bug.
5. Resource limit is about 1 GB of RAM. A subsystem that reads a whole multi-hundred-MB upload
   into memory will be killed rather than slowed, so whoever owns the largest test file should
   check theirs on the deployed site, not locally.

#### 5. After it is up, before the URL goes in the portal

Upload one real test file per subsystem through the site, in a private window, signed out. For
each: the result renders, the download gives the right filename, and the downloaded CSV passes
`./validate.sh`. A judge's first click must not be the first click.

#### 6. If the deploy will not come up

In order: Hugging Face Spaces (same Streamlit app, a different host), then a Cloudflare tunnel to
a laptop, which is last because the URL dies when the laptop sleeps and a judge may open it days
later.

#### 7. What I do before any of this arrives

Deploy SHM alone, now. The board already shows the other three as having no model, so the site is
honest, the portal field gets filled today, and every problem in section 4 surfaces while there is
still time to fix it. Each subsystem then joins by a push.

**Affects.** Everyone. Jermaine and Jou: sections 1 and 2 are asks, and the checkpoint format and
size question is worth answering before you fit your final model. Whoever merges last owns
section 3.

### 2026-09-19 00:20 - The submission portal wants three URLs and three short answers

**What.** Wayne reported what the submission portal actually asks for. This is not in
`docs/problem_statement.md`, which describes only the team folder, so both sets of requirements
apply and neither replaces the other.

| Portal field | State | Who |
|---|---|---|
| Pitch video URL | Not recorded, not hosted | Everyone, one take |
| GitHub repository URL | `github.com/nebulax-group/neb-x` exists | Needs checking it is reachable by a judge |
| Prototype URL | **Nothing deployed.** This is new work | Wayne, the app is his |
| What the solution does | Not written | Wayne can draft |
| Tech stack used | Not written | Wayne can draft |
| Challenges faced | Not written | Everyone, each subsystem had its own |

**Why this matters more than it looks.** Three of these are new work that no one had scheduled,
and one of them, the prototype URL, is blocked by a problem we have had open since the 19:51
entry.

1. **A video file is not a video URL.** The recording has to be hosted somewhere a judge can open,
   YouTube unlisted or Google Drive with link sharing. The file still goes in `video/` for the
   team folder; the portal needs the link as well.
2. **The repository has to be reachable.** If `nebulax-group/neb-x` is private, a judge opening
   that URL sees a 404 and the field is worthless. Someone has to confirm, and if we make it
   public, check nothing sensitive is in the history first.
3. **A prototype URL means deploying the app**, most likely Streamlit Community Cloud, which is
   free and reads straight from a GitHub repo. **The blocker is the checkpoint.** A deployed app
   has no `data/`, so it cannot train, so `outputs/models/shm/sn_curve.json` has to be in the
   repository for the deployed app to predict anything. `outputs/` is gitignored, and
   [[project-structure]] rule 10 says never commit an artefact from it.

   The way out that does not break rule 10: commit the checkpoints under
   `Optional_Items/<Subsystem>/model/`, which the problem statement already asks for and which is
   not under `outputs/`, then have `predict.py` fall back to that path when the `outputs/` one is
   absent. That needs a decision from the three of us, not from one.

**Affects.** Everyone. The pitch video and the challenges answer need all three of us. The
prototype URL is Wayne's, and it cannot be done until the checkpoint question is settled, so it is
the long pole. Jermaine and Jou: if your subsystem is to work on the deployed prototype, your
checkpoint has to travel in git too.

### 2026-09-19 00:05 - The team name is Group1

**What.** Wayne confirmed the registered team name: **Group1**. The submission's top-level folder
must carry it exactly, since that is how the organisers identify and score us.

    ./submit.sh --team Group1

`DEFAULT_TEAM_NAME` in `src/common/config.py` is still the placeholder `neb-x`. Changing it to
Group1 is a one line edit and would make the bare `./submit.sh` correct by default, but the
prompt covers it either way. Say if you want it changed.

**Affects.** Whoever builds the final submission: pass `--team Group1`, or type `Group1` at the
prompt. Do not rename the folder by hand afterwards, rebuild it instead, so the name in the
folder and the name the packager reports cannot disagree.

### 2026-09-18 23:45 - submit.sh asks for the team name; where every file goes

**What.** `./submit.sh` now prompts for the team name before it does anything, and anything it
cannot find is reported and skipped rather than failing the run. The demo video is picked up from
`video/` at the repo root.

    ./submit.sh                      asks: Team name, exactly as registered:
    ./submit.sh --team "Depot Crew"  skips the prompt

Only a failed validation stops it. A CSV that does not match the schema is scored as-is by the
organisers, so it must never reach the zip. Everything else missing is a line under "not
submittable yet" and the build continues.

### Where every file goes

**What you put where, by hand:**

| Put it here | What |
|---|---|
| `video/` | The demo recording, any of mp4, mov, m4v, webm, avi, mkv. Gitignored, it is too large to commit. Packaging renames it to `demo_video.<ext>`; if several are there it takes the first by name. |
| `data/<sub>/` | The organisers' datasets, unchanged. Gitignored, never renamed. |
| `src/<sub>/` | Your subsystem's code. Copied into `Optional_Items/<Subsystem>/code/`. |

**What the tools write, all regenerable:**

| Written to | By | Becomes |
|---|---|---|
| `outputs/models/<sub>/` | `train.py` | `Optional_Items/<Subsystem>/model/` |
| `outputs/predictions/<sub>_predictions.csv` | `predict.py`, or the app's download button | a flat entry in `predictions.zip` |
| `outputs/submission/<team>/` | `package.py` | the folder we send |

**The folder that gets submitted:**

    <team>/
    |-- demo_video.<ext>       from video/
    |-- predictions.zip        flat, only the CSVs that validated
    |-- app/                   src, scripts, .streamlit, requirements.txt, install, submit
    `-- Optional_Items/
        `-- <Subsystem>/{code,model}/      Door, ACV, Rail Corrugation, SHM

`data/` and `outputs/` are never copied into it. Section 4.1 says not to send the datasets back,
and the whole folder is currently 264 KB.

Two things cross a boundary:

1. **`VIDEO_DIR`, `VIDEO_EXTENSIONS` and `DEMO_VIDEO_STEM` are in `src/common/config.py`**, and
   `video/` is now gitignored.
2. **Missing is never an error except for a bad CSV.** `copy_video` returns `None` when there is
   no recording yet, and the build says "file not found, skipped" and carries on. That is
   deliberate: everything else has to be packageable before the video exists, or we cannot
   rehearse the submission until the last hour.

**Verified.** Driven through a real pty: typing "Depot Crew" at the prompt produces
`outputs/submission/Depot Crew/` with `demo_video.mov` copied from `video/`. With no video it
reports the file as not found and still builds. `--team` skips the prompt. The `.bat` twins
mirror these line for line and remain untested, since neither of us has Windows.

**Affects.** Jermaine, Jou: run `./submit.sh` any time to see where the submission stands. Your
subsystem appears in the zip and in `Optional_Items/` automatically once your `predict.py` writes
a valid CSV, with nothing to coordinate.

### 2026-09-18 23:20 - package.py, submit.sh, and what every script does

**What.** The submission now builds itself. `./submit.sh` validates then packages, and is the
one command to run before sending anything.

### Every script in the repo, and what it does

| Command | What it does |
|---|---|
| `./install.sh` / `.bat` | Creates `.venv` and installs `requirements.txt`. Called by the others when `.venv` is absent. |
| `./scripts/check.sh` / `.bat` | Runs `scripts/check_env.py`, which reports whether the environment and datasets are in place. |
| `./scripts/app.sh` / `.bat` | Starts the Streamlit app. This is the compulsory deliverable and how the submitted predictions must be produced. |
| `./scripts/validate.sh` / `.bat` | Checks prediction CSVs against `reference/submission_format/`. No argument sweeps all four subsystems and skips the ones nobody has produced; a path checks that one file. Exit 1 only when a file that exists fails. |
| `./scripts/package.sh` / `.bat` | Builds `outputs/submission/<team>/`. Takes `--team "Your Name"`. |
| `./submit.sh` / `.bat` | Runs validate then package, stopping at the first failure. Passes `--team` through. |

Every script is a thin wrapper: it creates or refreshes `.venv`, then hands off to a module. The
layout, the paths and the checks all live in Python, so a change of structure never means editing
six shell scripts.

### What package.py builds

    <team>/
    |-- predictions.zip        flat, only the CSVs of subsystems that validated
    |-- app/                   src, scripts, .streamlit, requirements.txt, install and submit
    `-- Optional_Items/
        `-- <Subsystem>/{code,model}/

Currently 264 KB, one subsystem, `predictions.zip` containing exactly
`['shm_predictions.csv']`. `data/` and `outputs/` are excluded; section 4.1 says not to send the
datasets back.

Three things cross a boundary:

1. **A CSV that fails validation stops the build.** Packaging refuses rather than zipping a bad
   file, because the organisers score the zip as-is and nothing downstream would notice.
2. **`Optional_Items/<Subsystem>/model/` is now filled automatically** from `MODEL_DIRS`. That
   closes the checkpoint problem open since the 19:51 entry: `outputs/` is gitignored and never
   reaches the machine that records the demo, but this folder travels with the submission.
3. **Two constants moved into `src/common/config.py`:** `SUBSYSTEM_LABELS`, which was in
   `src/app/config.py` and is now imported from common, and a new `DEFAULT_TEAM_NAME`. The
   submission layer needs the organisers' folder names and nothing may import the app.

**Still needed by hand:** `demo_video.mp4`, and renaming the folder to the registered team name.
Both are printed at the end of every run, and `--team` sets the name directly.

**Affects.** Jermaine, Jou: your subsystem joins the zip automatically once `predict.py` writes a
valid CSV, and your `src/<sub>/` and any checkpoint in `outputs/models/<sub>/` are copied into
`Optional_Items/` with no action from you. Point 3 changes an import if you referenced
`SUBSYSTEM_LABELS` from the app config.

### 2026-09-18 22:55 - scripts/validate.sh and .bat; validate with no argument sweeps everything

**What.** `./scripts/validate.sh` (and `scripts\\validate.bat`) creates or refreshes `.venv` the
same way `app.sh` does, then runs the validation. Two modes:

    ./scripts/validate.sh                       every subsystem
    ./scripts/validate.sh path/to/x.csv         that one file

`python -m src.submission.validate` with no argument now sweeps all four subsystems. A subsystem
that has not produced a prediction file prints "nothing found, skipping" and the sweep carries on.
That is not a failure and does not affect the exit code, because we are working in separate
packages and a sweep has to tell "no file" apart from "bad file".

Today it reports: door, acv and rail nothing found; shm ok.

Two things cross a boundary:

1. **`validate_subsystem(subsystem)` returns `None` when no CSV exists**, and a list of problems
   otherwise. `validate_all()` returns that per subsystem. Use these rather than re-deriving
   paths; they come from `PREDICTION_PATHS` and `TEST_PATHS` in `common/config.py`, so door's
   `Test.csv` is handled without anyone special casing it.
2. **Exit code is 1 only when a file that exists fails.** Safe to put in CI or a pre-zip step now
   and it will not go red just because your subsystem is unfinished.

**Verified.** Sweep, single file, and both exit codes on macOS. `validate.bat` mirrors `app.bat`
line for line but has not been run; neither of us has Windows here, so someone should try it
before we rely on it.

**Affects.** Jermaine, Jou: run `./scripts/validate.sh` any time. It will start reporting your
subsystem the moment your `predict.py` writes its CSV, with no change to the script.

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
