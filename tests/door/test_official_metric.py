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
