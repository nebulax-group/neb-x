"""Prove the claim the whole Door design rests on: the score is accuracy."""

import pandas as pd

from src.door import config, dataset, features
from tests.door.official_metric import iou_weighted_f1


def _truth_frame():
    answer = dataset.load_labels()
    return pd.DataFrame(
        {"start_time": answer["start_time"], "end_time": answer["end_time"],
         "prediction": answer[config.ANSWER_COLUMN_STATUS]}
    )


def test_a_perfect_submission_scores_one():
    truth = _truth_frame()
    assert iou_weighted_f1(truth, truth.copy()) == 1.0


def test_all_normal_scores_the_normal_share():
    truth = _truth_frame()
    predicted = truth.copy()
    predicted["prediction"] = config.LABEL_NORMAL
    assert abs(iou_weighted_f1(truth, predicted) - 80 / 110) < 1e-9


def test_the_score_equals_accuracy_for_every_error_count():
    """With exact segmentation the metric is accuracy - flipping k labels costs k/110."""
    truth = _truth_frame()
    for flips in (0, 1, 5, 17, 40):
        predicted = truth.copy()
        index = predicted.index[:flips]
        predicted.loc[index, "prediction"] = predicted.loc[index, "prediction"].map(
            {config.LABEL_NORMAL: config.LABEL_ABNORMAL,
             config.LABEL_ABNORMAL: config.LABEL_NORMAL}
        )
        accuracy = (predicted["prediction"] == truth["prediction"]).mean()
        assert abs(iou_weighted_f1(truth, predicted) - accuracy) < 1e-9


def test_one_to_one_matching_is_enforced_when_predictions_compete():
    """Guards against a many-to-one matcher.

    With exact segmentation every true segment has exactly one same-label
    candidate, so the accuracy-equivalence tests above never make two
    predictions compete for the same true segment - a matcher that assigned
    both would still pass them. This constructs the competition directly: one
    true Normal segment, two overlapping predicted Normal segments, one a
    perfect match (IoU 1.0) and one a partial overlap (IoU 0.2). Only the
    better pair may match; the other must be left an unmatched false positive.
    """
    truth = pd.DataFrame(
        {"start_time": ["2023-1-1-0-0-0-0"],
         "end_time": ["2023-1-1-0-0-10-0"],
         "prediction": [config.LABEL_NORMAL]}
    )
    predicted = pd.DataFrame(
        {"start_time": ["2023-1-1-0-0-0-0", "2023-1-1-0-0-0-0"],
         "end_time": ["2023-1-1-0-0-10-0", "2023-1-1-0-0-2-0"],
         "prediction": [config.LABEL_NORMAL, config.LABEL_NORMAL]}
    )
    # Only the perfect pair matches: total_iou = 1.0. soft_recall = 1.0/1,
    # soft_precision = 1.0/2 -> harmonic mean = 2*1*0.5/1.5 = 2/3.
    # A many-to-one bug that matched both (total_iou = 1.2) would give a
    # different score instead.
    assert abs(iou_weighted_f1(truth, predicted) - 2 / 3) < 1e-9


def test_wrong_label_cannot_match_even_with_perfect_timing():
    """Guards against a matcher that ignores the label filter under overlap.

    With exact segmentation every predicted segment shares its true segment's
    label, so the accuracy-equivalence tests above never present the matcher
    with a same-timing, different-label pair - a matcher that dropped the
    label check would still pass them, since it would just match on IoU alone
    and IoU doesn't know about labels. This constructs that pair directly:
    identical timing, opposite labels, for a single segment.
    """
    truth = pd.DataFrame(
        {"start_time": ["2023-1-1-0-0-0-0"],
         "end_time": ["2023-1-1-0-0-10-0"],
         "prediction": [config.LABEL_NORMAL]}
    )
    predicted = pd.DataFrame(
        {"start_time": ["2023-1-1-0-0-0-0"],
         "end_time": ["2023-1-1-0-0-10-0"],
         "prediction": [config.LABEL_ABNORMAL]}
    )
    assert iou_weighted_f1(truth, predicted) == 0.0


def test_our_rule_scores_perfectly_on_the_training_stream():
    stream, bounds, status = dataset.labelled_segments()
    table = features.build(stream)
    labels = [
        config.LABEL_ABNORMAL if r > config.RATIO_THRESHOLD else config.LABEL_NORMAL
        for r in table["ratio"]
    ]
    predicted = pd.DataFrame(
        {"start_time": bounds["start_time"], "end_time": bounds["end_time"],
         "prediction": labels}
    )
    assert iou_weighted_f1(_truth_frame(), predicted) == 1.0
