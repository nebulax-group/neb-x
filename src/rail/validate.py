"""Check an upload is a rail recording before the model is loaded.

The app calls this before ``predict`` and classifies what it raises differently:
a ValueError from here reads as "these files do not match Rail Corrugation",
where the same sentence raised inside ``predict`` reads as "the assessment was
interrupted" -- which blames the app for a file belonging to another system.
Rejecting early is therefore about the message, not about speed.

The check is the header and nothing else. Whether these files were recorded by
this system is settled outright by the 129 column names, and the sample count
and finiteness checks in ``dataset.load_recording`` cost a full 21 MB parse to
reach a verdict ``predict`` is about to reach anyway.
"""

from pathlib import Path

from .dataset import SCHEMA_MISMATCH, describe_header_mismatch, read_header


def validate(inputs: list[Path]) -> None:
    for path in inputs:
        mismatch = describe_header_mismatch(read_header(path))
        if mismatch:
            raise ValueError(SCHEMA_MISMATCH.format(name=path.name, mismatch=mismatch))
