"""Queue each system's assessment and work through them one at a time, in order.

Streamlit re-executes the whole script on every interaction, so a predictor called at
flow level holds the page until it returns. The work is queued instead, and the page
collects each result once it lands.

One worker drains the queue, so systems are assessed in the order they were started
and two models never compete for the same machine.

Nothing here may touch ``st``. The worker carries no script context, so the work it is
given is ordinary Python and everything it produces is written into session state by
the caller, on the script thread.
"""

import threading
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, MutableMapping

from src.app.config import QUEUE_WORKERS

STATE_KEY = "nx_jobs"

_QUEUE_LOCK = threading.Lock()
_QUEUE: ThreadPoolExecutor | None = None


def _queue() -> ThreadPoolExecutor:
    global _QUEUE
    with _QUEUE_LOCK:
        if _QUEUE is None:
            _QUEUE = ThreadPoolExecutor(
                max_workers=QUEUE_WORKERS, thread_name_prefix="nx-assess"
            )
        return _QUEUE


@dataclass(frozen=True)
class Job:
    """One system's place in the queue, for one set of files."""

    subsystem: str
    digest: str
    future: Future

    @property
    def settled(self) -> bool:
        return self.future.done()

    @property
    def working(self) -> bool:
        """Whether its turn has come, as against still waiting for one."""
        return self.future.running()

    @property
    def error(self) -> BaseException | None:
        return self.future.exception() if self.settled else None

    def result(self) -> Any:
        """What the work returned, or whatever it raised."""
        return self.future.result()


def jobs(state: MutableMapping) -> dict[str, Job]:
    if STATE_KEY not in state:
        state[STATE_KEY] = {}
    return state[STATE_KEY]


def start(
    subsystem: str, digest: str, work: Callable[[], Any], state: MutableMapping
) -> Job:
    """This system's job for exactly these files, joining the queue if it is not on it.

    A settled job is kept rather than repeated, so a batch that failed is reported
    once instead of being retried on every rerun.
    """
    table = jobs(state)
    existing = table.get(subsystem)
    if existing is not None and existing.digest == digest:
        return existing
    discard(subsystem, state)
    job = Job(subsystem, digest, _queue().submit(work))
    table[subsystem] = job
    return job


def discard(subsystem: str, state: MutableMapping) -> None:
    """Forget this system's job. Its result stops mattering, finished or not."""
    job = jobs(state).pop(subsystem, None)
    if job is not None:
        job.future.cancel()


def pending(subsystem: str, state: MutableMapping) -> bool:
    """Whether this system is on the queue, waiting or under way."""
    job = jobs(state).get(subsystem)
    return job is not None and not job.settled


def pipeline(state: MutableMapping) -> frozenset[tuple[str, bool]]:
    """What is outstanding and which of it has begun, as a value the page compares."""
    return frozenset(
        (key, job.working) for key, job in jobs(state).items() if not job.settled
    )
