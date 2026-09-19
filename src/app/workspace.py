"""Keep the latest assessed batch for each system in one browser session."""

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from typing import Any, MutableMapping

from src.app import cache, services

STATE_KEY = "nx_review_runs"


@dataclass
class Run:
    subsystem: str
    digest: str
    assessed_at: str
    sources: list[dict]
    reading: cache.Reading
    report: dict | None
    report_error: str | None = None


def runs(state: MutableMapping) -> dict[str, Run]:
    if STATE_KEY not in state:
        state[STATE_KEY] = {}
    return state[STATE_KEY]


def assess(subsystem: str, uploads: list[Any], state: MutableMapping) -> Run | None:
    """Never leave a previous batch in the handoff after files change or fail."""
    saved = runs(state)
    if not uploads:
        saved.pop(subsystem, None)
        return None
    digest = services.upload_digest(uploads)
    previous = saved.get(subsystem)
    if previous is not None and previous.digest == digest:
        return previous
    saved.pop(subsystem, None)
    reading = cache.reading(subsystem, uploads)
    try:
        report = services.review_report(subsystem, cache._staged(digest, uploads), reading)
        report_error = None
    except Exception:
        # Keep the prediction for inspection, but never label an absent report clear.
        report, report_error = None, "Review evidence could not be prepared. Open the assessment and ask the app maintainer to review it."
    sources = []
    for upload in uploads:
        payload = services._read_upload(upload)
        sources.append({
            "name": upload.name,
            "sha256": hashlib.sha256(payload).hexdigest(),
            "bytes": len(payload),
        })
    result = Run(subsystem, digest, datetime.now(timezone.utc).isoformat(), sources, reading, report, report_error)
    saved[subsystem] = result
    return result
