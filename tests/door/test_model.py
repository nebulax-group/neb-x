"""The model must be perfect under CV and must agree with the documented rule."""

from src.door import config, dataset, features, model, train


def test_cross_validation_is_perfect():
    result = train.cross_validate()
    assert result["mean_accuracy"] == 1.0
    assert result["n_errors"] == 0


def test_the_fitted_model_agrees_with_the_documented_threshold():
    stream, _, status = dataset.labelled_segments()
    table = features.build(stream)
    estimator = model.build_estimator()
    y = (status == config.LABEL_ABNORMAL).values
    estimator.fit(table[list(model.FEATURE_COLUMNS)].values, y)
    fitted = estimator.predict(table[list(model.FEATURE_COLUMNS)].values)
    rule = (table["ratio"] > config.RATIO_THRESHOLD).values
    assert (fitted == rule).all()
    assert (fitted == y).all()


def test_the_checkpoint_round_trips():
    import joblib

    path = train.fit_and_save()
    assert path.is_file()
    estimator = joblib.load(path)
    assert hasattr(estimator, "predict_proba")
