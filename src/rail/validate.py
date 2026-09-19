"""Check an upload is a rail recording before the model is loaded.

The app calls this before ``predict`` and classifies what it raises differently:
a ValueError from here reads as "these files do not match Rail Corrugation",
where the same sentence raised inside ``predict`` reads as "the assessment was
interrupted" -- which blames the app for a file the reader could fix themselves.
Rejecting early is therefore about the message, not about speed.

The header is asked first and on its own: whether these files were recorded by
this system at all is settled outright by the 129 column names, at 5 ms against
the 132 ms a file whose header already answers no does not deserve.

The samples are then read too, which is the part that costs. A truncated export
and a channel with a hole in it are the reader's to fix as much as a wrong file
is, and ``dataset.load_recording`` is the only thing that checks either -- raised
there, inside ``predict``, both reach the page as the app breaking rather than as
the file being wrong. One extra parse per file buys every malformed rail CSV the
sentence that names it, which is what door and shm already do for theirs.
"""

from pathlib import Path

from .dataset import (
    SCHEMA_MISMATCH,
    describe_header_mismatch,
    load_recording,
    read_header,
)


def validate(inputs: list[Path]) -> None:
    for path in inputs:
        mismatch = describe_header_mismatch(read_header(path))
        if mismatch:
            raise ValueError(SCHEMA_MISMATCH.format(name=path.name, mismatch=mismatch))
        # The sample count and the finiteness check, which nothing short of the
        # full read settles. The arrays are dropped again; predict re-reads them.
        load_recording(path)
