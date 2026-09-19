"""Keep the latest assessed batch for each system in one browser session."""

import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, MutableMapping

from src.app import cache, jobs, services
from src.app.config import (
    CARD_ABSENT,
    CARD_DONE,
    CARD_FAILED,
    CARD_IDLE,
    CARD_QUEUED,
    CARD_RUNNING,
    PANEL_STATE_KEY,
    REPORT_UNAVAILABLE,
    RESULT_VIEW_STATE_KEY,
    SUBSYSTEM_LABELS,
    UPLOAD_GENERATION_KEY,
)

STATE_KEY = "nx_review_runs"

IDLE = CARD_IDLE
QUEUED = CARD_QUEUED
RUNNING = CARD_RUNNING
READY = CARD_DONE
FAILED = CARD_FAILED

# The two standings that mean a system is on the queue and its files are settled.
ON_QUEUE = (QUEUED, RUNNING)


@dataclass
class Run:
    subsystem: str
    digest: str
    assessed_at: str
    sources: list[dict]
    reading: cache.Reading
    report: dict | None
    report_error: str | None = None


@dataclass(frozen=True)
class Outcome:
    """Where a system stands: nothing to do, waiting, working, answered or stopped."""

    state: str
    run: Run | None = None
    error: BaseException | None = None


def runs(state: MutableMapping) -> dict[str, Run]:
    if STATE_KEY not in state:
        state[STATE_KEY] = {}
    return state[STATE_KEY]


def reset(subsystem: str, state: MutableMapping) -> None:
    """Put one system back to where it was before any file was added to it.

    Everything the session holds about it goes: the batch, the job, the assessment,
    the memoised reading and its staged copy, and the view and step it was left on.
    Anything kept back would come straight back on the next batch and look like the
    new one's answer.
    """
    saved, table = runs(state), jobs.jobs(state)
    batch = table[subsystem].digest if subsystem in table else None
    if batch is None and subsystem in saved:
        batch = saved[subsystem].digest

    jobs.discard(subsystem, state)
    saved.pop(subsystem, None)

    # Two systems given the same files share one staged copy and one reading, so the
    # copy only goes when nothing else is still pointing at it.
    if batch is not None and not _shared(batch, state):
        cache.forget(batch)

    generations = state.setdefault(UPLOAD_GENERATION_KEY, {})
    generations[subsystem] = generations.get(subsystem, 0) + 1

    label = SUBSYSTEM_LABELS[subsystem]
    for key in (f"{PANEL_STATE_KEY}-{label}", f"{RESULT_VIEW_STATE_KEY}-{label}"):
        state.pop(key, None)


def _shared(batch: str, state: MutableMapping) -> bool:
    held = [job.digest for job in jobs.jobs(state).values()]
    held += [run.digest for run in runs(state).values()]
    return batch in held


def collect(state: MutableMapping) -> None:
    """Take in every finished assessment, not only the one being looked at.

    A system that finished while the reader was on another one still belongs in the
    handoff. Leaving it for whenever it is next selected is how a finished assessment
    goes missing from a review package that says it covers the session.
    """
    saved = runs(state)
    for subsystem, job in jobs.jobs(state).items():
        if not job.settled or job.error is not None:
            continue
        previous = saved.get(subsystem)
        if previous is None or previous.digest != job.digest:
            saved[subsystem] = job.result()


def standing(available: dict[str, bool], state: MutableMapping) -> dict[str, str]:
    """Where every system stands, whether or not it is the one being looked at."""
    table = jobs.jobs(state)
    saved = runs(state)
    places = {}
    for subsystem, ready in available.items():
        job = table.get(subsystem)
        if not ready:
            places[subsystem] = CARD_ABSENT
        elif job is not None and not job.settled:
            places[subsystem] = RUNNING if job.working else QUEUED
        elif job is not None:
            places[subsystem] = FAILED if job.error is not None else READY
        else:
            places[subsystem] = READY if subsystem in saved else IDLE
    return places


def assess(subsystem: str, uploads: list[Any], state: MutableMapping) -> Outcome:
    """Never leave a previous batch in the handoff after files change or fail."""
    saved = runs(state)
    if not uploads:
        # A system on the queue holds its uploader shut, so it has no way of being
        # emptied by the reader. An empty batch there is the widget, not an intention.
        if jobs.pending(subsystem, state):
            return _place(subsystem, state)
        jobs.discard(subsystem, state)
        saved.pop(subsystem, None)
        return Outcome(IDLE)

    batch = cache.digest(uploads)
    previous = saved.get(subsystem)
    if previous is not None and previous.digest == batch:
        return Outcome(READY, run=previous)

    saved.pop(subsystem, None)
    job = jobs.start(subsystem, batch, _assessment(subsystem, batch, uploads), state)
    if not job.settled:
        return Outcome(RUNNING if job.working else QUEUED)
    try:
        run = job.result()
    except Exception as exc:
        return Outcome(FAILED, error=exc)
    saved[subsystem] = run
    return Outcome(READY, run=run)


def _place(subsystem: str, state: MutableMapping) -> Outcome:
    job = jobs.jobs(state)[subsystem]
    return Outcome(RUNNING if job.working else QUEUED)


def _assessment(subsystem: str, batch: str, uploads: list[Any]) -> Callable[[], Run]:
    def work() -> Run:
        reading = cache.reading(subsystem, batch, uploads)
        try:
            report = services.review_report(
                subsystem, cache.staged(batch, uploads), reading
            )
            report_error = None
        except Exception:
            # Keep the prediction for inspection, but never label an absent report clear.
            report, report_error = None, REPORT_UNAVAILABLE
        sources = []
        for upload in uploads:
            payload = services._read_upload(upload)
            sources.append({
                "name": upload.name,
                "sha256": hashlib.sha256(payload).hexdigest(),
                "bytes": len(payload),
            })
        return Run(
            subsystem,
            batch,
            datetime.now(timezone.utc).isoformat(),
            sources,
            reading,
            report,
            report_error,
        )

    return work
