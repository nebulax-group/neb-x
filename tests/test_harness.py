"""The harness itself: src must be importable and the datasets must be present."""

from src.common import config


def test_src_is_importable():
    assert config.SUBSYSTEMS == ("door", "acv", "rail", "shm")


def test_door_inputs_exist():
    assert config.TRAIN_PATHS["door"].is_file()
    assert config.TEST_PATHS["door"].is_file()
    assert config.LABEL_PATHS["door"].is_file()


def test_acv_inputs_exist():
    assert config.TRAIN_PATHS["acv"].is_dir()
    assert config.TEST_PATHS["acv"].is_dir()
    assert config.LABEL_PATHS["acv"].is_file()
