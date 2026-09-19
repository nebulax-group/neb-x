"""Check ACV input shape while preserving cars with unavailable readings."""

from pathlib import Path

from pandas.errors import EmptyDataError, ParserError

from . import dataset, features


def validate(inputs: list[Path]) -> None:
    for path in inputs:
        try:
            frame, cars = dataset.load_case(path)
            features.temperature_excess(frame, cars)
        except (ValueError, KeyError) as exc:
            # Preserve parser errors for the app's unreadable-file classification.
            if isinstance(exc, (EmptyDataError, ParserError, UnicodeDecodeError)):
                raise
            raise ValueError(f"{path.name}: {exc}") from exc
