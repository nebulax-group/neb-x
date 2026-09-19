# Deploying the App on Google Cloud Run

How the Streamlit app becomes a URL a judge can open, what the repo still needs for that, and
where the checkpoints travel. Written 2026-09-19, nothing deployed yet.

**Why:** the submission portal has a **Prototype URL** field ([[wayne]], 00:20) and we have no
running site. The 00:45 entry planned this against Streamlit Community Cloud; Wayne has since been
told to use Google Cloud, which changes the host but none of the contracts that entry set.

**How to apply:** read section 1 first, it answers the question that prompted this. Then sections 5
and 7 before touching anything, because the checkpoint decision changes the Dockerfile and the
prerequisites change the order. Sections 3 and 4 are the actual work.

## 1. Is this the link for our app?

**Yes.** A Google Cloud Run deployment gives back exactly one HTTPS URL, of the form
`https://<service>-<hash>.<region>.run.app`. That URL *is* the Prototype URL field. It is not a
separate thing, not a second app, and not a rebuild: it is `src/app/main.py`, the same file
`./scripts/app.sh` runs, reached over the internet instead of at `localhost:8501`.

The portal's three URL fields map cleanly and do not overlap:

| Portal field | Filled by |
|---|---|
| Pitch video URL | YouTube unlisted or Drive link sharing. Not this. |
| GitHub repository URL | `github.com/nebulax-group/neb-x`. Not this. |
| **Prototype URL** | **The Cloud Run service URL. This one.** |

**Confident about:** a Cloud Run service deployed with `--allow-unauthenticated` is a plain public
HTTPS link, opens in any browser with no Google account, and is precisely what a prototype URL asks
for. Nothing else in the submission needs a URL, so there is no second thing this could be.

**Wayne must confirm with the organisers**, in one message, what "submitted via Google Cloud"
means, because there are three readings and they differ in who pays:

1. *"Host your prototype somewhere; Google Cloud is the suggestion."* Then everything below is
   ours to do, on our own billing account.
2. *"Deploy into a GCP project we provide."* Everything below still applies unchanged, but the
   project id and billing account are theirs — ask for the project id and an IAM role on it.
3. *"Upload the submission folder to a Google Cloud Storage bucket."* This would be a **delivery
   channel, not a prototype URL**, and would not replace the deploy — §4.1 of
   [[problem-statment]] still wants the app itself, and the portal still has a Prototype URL field
   that a bucket link does not satisfy.

Under all three readings Cloud Run is the right target, so do not wait for the answer to start.

**One thing the deploy does not replace.** `docs/problem_statement.md` §4.1 item 3 puts the app's
"source/deployment" in `app/` inside the team folder, and `package.py` already builds that.
Deploying is *additional* to it, not instead of it.

## 2. Which service, and why

**Cloud Run**, deployed from a `Dockerfile`.

It runs any container, scales to zero between visits so a judge opening the link in three weeks
costs nothing and the free tier covers the whole event, and it terminates TLS and hands back a
working HTTPS URL with no domain, no certificate and no load balancer to own. It also passes
WebSockets through, which Streamlit is built on and which is the one requirement that rules hosts
out. App Engine flexible bills a VM around the clock and cannot scale to zero; Compute Engine means
owning a VM, a firewall rule, TLS renewal and an uptime problem for the weeks between submission
and judging. Neither buys anything here.

## 3. Nothing deployed, to a URL a judge can open

Every command below is one line and runs as written in **PowerShell** at the repo root. Do not add
backslash continuations — that is bash syntax, and PowerShell will read the next line as a separate
command. `gcloud` (SDK 567.0.0) and Docker (29.4.3) are both already on this machine; verified
2026-09-19.

Steps 1 to 5 are once per person, ever. Steps 7 to 10 are the loop repeated on every change.

```powershell
# 1. Sign in. Opens a browser.
gcloud auth login

# 2. Create the project. Project ids are globally unique, so add digits if this one is taken.
gcloud projects create nebulax-group1 --name="NebulaX Group1"
gcloud config set project nebulax-group1

# 3. Link billing. List first, then paste the account id into the second command.
gcloud billing accounts list
gcloud billing projects link nebulax-group1 --billing-account=XXXXXX-XXXXXX-XXXXXX

# 4. Enable the three APIs a container deploy needs. Takes a minute.
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com

# 5. Default the region to Singapore, so no later command needs --region.
gcloud config set run/region asia-southeast1
```

```powershell
# 6. Put the checkpoints where the image can see them. Read section 5 before running this.
mkdir models\door, models\shm
copy outputs\models\door\classifier.joblib models\door\
copy outputs\models\shm\sn_curve.json models\shm\
```

Then add `Dockerfile`, `.dockerignore` and `.gcloudignore` from section 4.

```powershell
# 7. Build locally first. Three minutes, and it catches a bad pin before Cloud Build does.
docker build -t neb-x .

# 8. Run it exactly as Cloud Run will, then open http://localhost:8080 and click through.
docker run --rm -p 8080:8080 -e PORT=8080 neb-x

# 9. Deploy. Builds in the cloud from the same Dockerfile. Five to ten minutes the first time.
gcloud run deploy neb-x --source . --allow-unauthenticated --memory 4Gi --cpu 2 --timeout 3600 --max-instances 1 --cpu-boost

# 10. Print the URL. This is what goes in the portal.
gcloud run services describe neb-x --format="value(status.url)"
```

If step 9 refuses the public flag (section 6, row 10), the service still deploys; grant access
separately:

```powershell
gcloud run services add-iam-policy-binding neb-x --member=allUsers --role=roles/run.invoker
```

**11. Smoke test before the URL goes anywhere.** Section 5 of the 00:45 entry in [[wayne]] already
sets the bar and it is unchanged: open the URL in a private window, signed out of Google, and for
each ready subsystem upload one real test file, confirm the result renders, the download carries
the right filename, and the downloaded CSV passes `.\scripts\validate.bat`. A judge's first click
must not be the first click.

## 4. The files the repo needs

Three new files at the repo root, and one new directory. **None of them are written yet — Wayne
decides when they land.** Nothing under `src/`, `common/` or any subsystem changes.

`models/` is a new top-level directory, tracked in git. It is a source input, not an artefact, so
rule 10 of [[project-structure]] is untouched. This is the 00:45 decision, unchanged.

### `Dockerfile`

```dockerfile
FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt

# src/ must sit directly under WORKDIR: src/common/config.py derives REPO_ROOT as
# parents[2] of itself, and every path in the project, .streamlit/config.toml
# included, hangs off that. A flattened copy resolves them all one level too high.
COPY .streamlit/ ./.streamlit/
COPY reference/ ./reference/
COPY src/ ./src/

# The app reads checkpoints from outputs/models/<sub>/ via MODEL_DIRS. Landing the
# committed copies there means no subsystem config has to learn a second path.
COPY models/ ./outputs/models/

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PORT=8080
EXPOSE 8080

# Shell form, so $PORT expands. Cloud Run injects it and routes only to that port;
# an exec-form CMD passes the literal string "$PORT" and the container never binds.
CMD streamlit run src/app/main.py --server.port=$PORT --server.address=0.0.0.0
```

Notes on the flags, since this is where the hours go:

- **`--server.address=0.0.0.0` is not optional.** Cloud Run's container contract requires the
  container to listen on `0.0.0.0` and says explicitly that it must not listen on `127.0.0.1`.
- **`.streamlit/config.toml` does not conflict.** Streamlit's precedence is command line, then
  environment, then the project `config.toml`, then the global one — and our file sets only
  `[server] headless = true`, never `server.port` or `server.address`. The flags win and there is
  nothing to win against. Do not add a port to that file; it would be shadowed and would mislead
  the next reader.
- **No CORS or XSRF flags.** Cloud Run passes the original `Host` header through, so Streamlit's
  origin checks see the real URL and pass. Reach for `--server.enableXsrfProtection=false` only if
  the uploader specifically returns 403, and put it back afterwards.
- **`python:3.13-slim`, not 3.14.** `requirements.txt` says it was verified on 3.14.7, but this
  machine's `.venv` is 3.13.7, which is what the pins have actually been resolving against here.
  Matching the image to the interpreter Wayne can reproduce locally is worth more than matching a
  comment.

### `.dockerignore`

Without this the build context is **6.6 GB** — `data/` alone is 6.1 GB and `.venv/` another 553 MB,
against under 2 MB of everything else. Docker tars and streams the whole context before it reads
the first `COPY`, so the absence of this file is minutes of waiting per build, not a detail.

```
.git/
.gitignore
.venv/
data/
outputs/
video/
tests/
docs/
.claude/
__pycache__/
*.py[cod]
.pytest_cache/
.ruff_cache/
.mypy_cache/
.DS_Store
Thumbs.db
```

`outputs/` is excluded deliberately: the checkpoints reach the image from `models/`, and excluding
`outputs/` guarantees a stale local prediction or a half-trained model can never be what ships.

### `.gcloudignore`

**`gcloud` never reads `.dockerignore`.** `gcloud run deploy --source .` skips what `--ignore-file`
names, or `.gcloudignore`, and when neither exists it generates one from `.gitignore`. A repo with
only a `.dockerignore` therefore uploads all 6.6 GB. The two files are read by different tools and
have to be kept in step by hand.

Do not lean on the `.gitignore` fallback either. It would work today by accident, but `.gitignore`
is being edited by other people for a different purpose — it has grown a `video/**` block with five
negations since this session started — and it answers "what is committable", not "what does the
image need". Write it out:

```
.gcloudignore
.git/
.gitignore
.venv/
data/
outputs/
video/
tests/
docs/
.claude/
__pycache__/
*.py[cod]
.pytest_cache/
.ruff_cache/
.mypy_cache/
.DS_Store
Thumbs.db
```

One trap in the difference between them: `.gcloudignore` uses gitignore syntax, where a bare
`video/` matches a directory of that name **at any depth** and would also drop `src/video/`.
`.dockerignore` matches from the context root only, and would not. Nothing in `src/video/` is
imported by the app today, so this costs nothing now — but it is why the two files are not copies
of each other even though they read alike.

### Optional, not required

`scripts/deploy.bat` / `.sh` wrapping step 9, in the house style of the other wrappers: creates
nothing, decides nothing, just runs the one command. Worth it only if we redeploy more than a few
times.

## 5. The checkpoints, and how each reaches the container

The blocker open since the 19:51 entry. A deployed app has no `data/`, so it cannot train, so
whatever is in the image is what the site predicts with, forever.

**What is actually on disk, measured 2026-09-19:**

| Checkpoint | Bytes | Needed by | State |
|---|---|---|---|
| `outputs/models/door/classifier.joblib` | 63,872 | `src/door/predict.py` via `train.checkpoint_path()` | gitignored by `outputs/**` |
| `outputs/models/shm/sn_curve.json` | 599 | `src/shm/predict.py` via `config.CHECKPOINT_PATH` | gitignored by `outputs/**` |
| ACV | — | nothing | `src/acv/predict.py` is a rule-based ranker; **no checkpoint at all** |
| Rail | — | — | `src/rail/` is empty; the board will show it dormant, which is honest |

**64,471 bytes, all in.** The whole payload is 63 KB against a 296 KB git pack. Every argument about
size, Git LFS or fetch-at-start is moot at this scale.

### The recommendation

**Copy both into `models/<sub>/` and commit them, and have the Dockerfile land them at
`outputs/models/`** (`COPY models/ ./outputs/models/`, as in section 4).

This is the 00:45 decision with one refinement. That entry proposed `models/` as the committed home
plus a resolution order in each `src/<sub>/config.py` of `MODEL_DIRS` then `COMMITTED_MODEL_DIRS`.
The refinement: **for Cloud Run that config change is not needed yet.** Copying `models/` to
`outputs/models/` inside the image means `MODEL_DIRS` already resolves, so the deploy can happen
today without a boundary-crossing change landing across all three people's packages at hour nine.
The two are compatible — when the fallback does land, the first existing path still wins and it is
the same file, so nothing changes behaviour.

### Why not just copy the gitignored file

The tempting shortcut is to skip the commit entirely: a Docker build will happily copy a file
`.gitignore` excludes, as long as `.dockerignore` does not also exclude it. One line, no commit.
Weighed, and rejected, for four reasons in descending order of what they would cost:

1. **It does not survive `--source .`.** Cloud Build never sees `.dockerignore`. With
   `.gcloudignore` absent it derives one from `.gitignore`, and `outputs/**` is line 29 of that
   file, so the checkpoints are dropped before the build starts. The symptom is not an error — it
   is a deployed app where the Door card reads "no model yet". Making it work means hand-writing a
   `.gcloudignore` that deliberately contradicts `.gitignore`, which is a trap left for whoever
   reads it next.
2. **Nobody can tell which model is live.** The deployed model becomes whatever happened to be on
   one laptop at one moment, untracked and unreviewable. With 25% of the score on it, "which Door
   classifier is the judge actually hitting" must have an answer.
3. **It leaves the demo-video problem open.** The 19:51 entry's real complaint was that one machine
   has to hold every subsystem's checkpoint to record one take. A git-tracked `models/` fixes both
   problems at once; a Dockerfile copy fixes only the container.
4. **It saves 63 KB.** Which is not a saving.

### Two constraints worth restating before anyone fits a final model

- **`classifier.joblib` is a pickle**, so it binds the deploy to `scikit-learn==1.9.1` exactly. That
  pin is load-bearing now and cannot be bumped casually — the image and the machine that wrote the
  file must agree. JSON or `.npz` avoids this entirely, as SHM's 599-byte `sn_curve.json` shows.
- **Promoting a checkpoint into `models/` stays a deliberate copy by its owner**, never a step
  inside `train.py`. A trainer that commits its own output is how a half-fitted model reaches a
  judge.

## 6. What can go wrong, and what it looks like

| # | Failure | Symptom |
|---|---|---|
| 1 | No ignore file | `docker build` prints `Sending build context to Docker daemon 6.6GB`, or `gcloud` sits on `Uploading sources` for twenty minutes |
| 2 | Checkpoint not in the image | Board shows Door dormant, or clicking it raises `No Door checkpoint at /app/outputs/models/door/classifier.joblib` |
| 3 | Exec-form `CMD`, or no `--server.address` | Deploy fails: *"The user-provided container failed to start and listen on the port defined provided by the PORT=8080 environment variable"* |
| 4 | `--allow-unauthenticated` forgotten | Judge gets a Google sign-in page or a bare `403 Forbidden`, never the app |
| 5 | Default 512 MiB memory | Page reloads mid-prediction or hangs on "Please wait…"; logs say `Memory limit of 512 MiB exceeded` |
| 6 | Default 300 s request timeout | The session drops and the app reruns from scratch after five minutes — Cloud Run's request timeout applies to the WebSocket too |
| 7 | More than one instance | Uploader spins and fails, or the app reports `No files were uploaded` — the upload POST is a separate HTTP request from the WebSocket and can land on a different instance |
| 8 | sklearn mismatch | Door raises an unpickling `AttributeError` or `ModuleNotFoundError` naming a sklearn internal |
| 9 | A pin with no wheel for 3.13 | Build stops at `pip install`: `Could not find a version that satisfies the requirement pandas==3.0.6` |
| 10 | Org policy blocks `allUsers` | `Setting IAM policy failed`, or *"one or more users named in the policy do not belong to a permitted customer"*. Fix: redeploy with `--no-invoker-iam-check` instead |
| 11 | Billing not linked | `gcloud services enable` fails with *"Billing must be enabled"* |
| 12 | A single upload over 32 MiB | HTTP 413. Headroom today — the largest test file is `data/rail/test/Test58.csv` at 17.5 MB — but it is a ceiling, not a guideline |

**Why rows 5, 6 and 7 are handled by the flags in step 9, and are not paranoia.** Cloud Run's
filesystem is **in-memory**, and `services.stage_uploads` writes every upload into a `tempfile`
directory — so staged files are charged against the memory limit before pandas has read a byte.
Rail is 68 test files of about 17.5 MB, roughly 1.19 GB staged, and SHM 16 files at about 6.8 MB.
Against the 512 MiB default, rail is an instant kill. `--memory 4Gi --cpu 2` covers it.
`--timeout 3600` keeps the WebSocket alive for the full hour. `--max-instances 1` sidesteps row 7
outright: Cloud Run's session affinity is best-effort only, and one instance at 4 GiB serves a judge
fine.

**Cold start is the one thing the flags do not fix.** With scale-to-zero, the first request after an
idle period waits for the container to start and for pandas, sklearn and Streamlit to import —
expect roughly 10 to 20 seconds to first paint, which looks broken to someone who does not know to
wait. `--cpu-boost` in step 9 helps. If it still reads badly, `--min-instances 1` removes it
entirely, at the cost of billing an idle 4 GiB instance around the clock, well outside the free
tier. **Recommendation: ship with min-instances 0, set it to 1 for judging week only, then put it
back.**

**Free tier.** Cloud Run's always-free allowance is 2M requests, 360,000 GiB-seconds and 180,000
vCPU-seconds a month, which at `4Gi`/`2 cpu` is about 25 hours of active request time — far beyond
anything a judge will do. A billing account with a card must still be linked (required since
2026-02-03), but scale-to-zero means an idle service bills nothing. Uncertain in one respect: that
is an estimate of judging traffic, not a guarantee — set a budget alert at $5 and stop worrying.

**Region.** `asia-southeast1` is Singapore and the closest Cloud Run region to the judges. Tier 2
pricing, which affects nothing inside the free tier.

## 7. Time, and what must be true first

**Roughly 90 minutes if nothing goes wrong; budget half a day for a first-ever GCP deploy.** Account,
project and billing 20–30 min · the three files 10 min · local Docker build and click-through 15 min ·
the deploy itself 5–10 min per attempt · public access and the signed-out smoke test 10 min.

**Must be true before starting:**

1. **A Google account with a billing account and a card on it.** The only hard blocker. Nothing past
   step 3 runs without it, and it is the step most likely to need someone else's approval.
2. **Docker Desktop running**, not merely installed, for steps 7 and 8. Skippable — step 9 builds in
   the cloud regardless — but skipping it moves every build failure from a three-minute local loop
   to a ten-minute cloud one.
3. **The checkpoint decision in section 5 taken**, because it fixes the `COPY` line. It needs a yes
   from Jermaine and Jou per [[team-split]], but only as a heads-up: it adds a directory and changes
   no code either of them owns.
4. **`python -m src.door.train` and `python -m src.shm.train` have been run on this machine**, so
   there is something to copy into `models/`. Both checkpoints are present as of 2026-09-19.

**Not blocking:** the organisers' answer about what "via Google Cloud" means (section 1), and Rail.
Rail has no code, and the board shows a subsystem with no model as dormant rather than broken — so
deploying with three of four live is honest and gets the portal field filled today. Each subsystem
joins later by a push and a redeploy, exactly as section 7 of the 00:45 entry in [[wayne]] argued.

See also: [[wayne]], [[project-structure]], [[problem-statment]], [[team-split]].
