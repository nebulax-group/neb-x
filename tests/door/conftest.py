"""Every Door test that needs a checkpoint gets one, regardless of collection order.

Task 4's constant classifier let test_predict_shape.py pass without a model on disk.
Once predict.classify_segments requires a checkpoint, any test file collected on its
own - or before test_model.py - would fail on a missing file. A session-scoped,
autouse fit removes the ordering accident instead of relying on one test file's
side effect to feed another.
"""

import pytest

from src.door import train


@pytest.fixture(scope="session", autouse=True)
def door_checkpoint():
    train.fit_and_save()
