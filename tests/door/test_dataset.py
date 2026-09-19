"""Loading is IO only - no feature logic lives here."""

from src.door import config, dataset


def test_labelled_segments_align_with_the_answer_file():
    stream, bounds, status = dataset.labelled_segments()
    assert len(bounds) == config.EXPECTED_TRAIN_SEGMENTS
    assert len(status) == config.EXPECTED_TRAIN_SEGMENTS
    assert set(status.unique()) == {config.LABEL_NORMAL, config.LABEL_ABNORMAL}
    assert (status == config.LABEL_ABNORMAL).sum() == 30
    assert (status == config.LABEL_NORMAL).sum() == 80
    assert len(stream) == 18036


def test_loading_a_stream_preserves_every_row():
    stream = dataset.load_stream(dataset.test_stream_path())
    assert len(stream) == 6253
    assert config.COLUMN_CURRENT in stream.columns
