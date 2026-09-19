"""The submission folder carries everything section 4 asks for, or says what is missing."""

import zipfile

import pytest

from src.common.config import (
    MODEL_DIRS,
    MODELS_DIR,
    PREDICTION_PATHS,
    REPO_ROOT,
    SUBSYSTEMS,
    WRITE_UP_STEM,
)
from src.submission import package

# Packages that exist in this repository but have no part in starting the app.
DEVELOPMENT_ONLY = ("submission", "video")


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """A repository with one ready subsystem, a checkpoint, and nothing else."""
    predictions = tmp_path / "outputs" / "predictions"
    predictions.mkdir(parents=True)
    csv = predictions / "rail_predictions.csv"
    csv.write_text("file_id,prediction\nTest1.csv,Normal\n")

    models = tmp_path / "outputs" / "models" / "rail"
    models.mkdir(parents=True)
    (models / "classifier.pkl").write_bytes(b"checkpoint")

    source = tmp_path / "src"
    source.mkdir()
    (source / "__init__.py").write_text("")
    for name in ("app", "common", *SUBSYSTEMS, *DEVELOPMENT_ONLY):
        (source / name).mkdir()
        (source / name / "__init__.py").write_text("")

    (tmp_path / ".streamlit").mkdir()
    (tmp_path / ".streamlit" / "config.toml").write_text("[theme]\n")
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "requirements.txt").write_text("streamlit\n")

    monkeypatch.setattr(package, "ready_subsystems", lambda: (["rail"], {}))
    monkeypatch.setattr(package, "PREDICTION_PATHS", {**PREDICTION_PATHS, "rail": csv})
    monkeypatch.setattr(package, "MODEL_DIRS", {**MODEL_DIRS, "rail": models})
    monkeypatch.setattr(package, "MODELS_DIR", tmp_path / "outputs" / "models")
    monkeypatch.setattr(package, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(package, "SRC_DIR", source)
    monkeypatch.setattr(package, "SUBMISSION_ROOT", tmp_path)
    monkeypatch.setattr(package, "VIDEO_DIR", tmp_path / "video")
    monkeypatch.setattr(package, "VIDEO_OUT_DIR", tmp_path / "video" / "out")
    monkeypatch.setattr(package, "WRITE_UP_DIR", tmp_path)
    return tmp_path


def built_app(repo):
    return package.build("Group1") / package.APP_DIR_NAME


def test_the_folder_is_built_at_the_repository_root(repo):
    # What gets uploaded is the folder itself, so nothing wraps it that could be sent
    # in its place.
    assert package.build("Group1") == repo / "Group1"


def test_the_app_holds_only_what_starts_it(repo):
    app = built_app(repo)
    assert {item.name for item in app.iterdir()} == {
        "run.sh", "run.bat", ".streamlit", "requirements.txt", "src", "outputs",
    }
    # requirements.txt is filed under scripts/ in the repository and lands here under
    # its bare name, which is the only place the runner beside it will look.
    assert (app / "requirements.txt").read_text() == "streamlit\n"
    shipped = {item.name for item in (app / "src").iterdir()}
    assert shipped == {"__init__.py", "app", "common", *SUBSYSTEMS}
    # Section 4.1 item 3 asks for the app, not for how the app is developed.
    assert not shipped & set(DEVELOPMENT_ONLY)


def test_the_runner_is_executable(repo):
    runner = built_app(repo) / "run.sh"
    # A lost executable bit is the whole distance between a judge and the app.
    assert runner.stat().st_mode & 0o111


def test_the_shipped_app_carries_the_checkpoints_it_needs(repo):
    relative = MODELS_DIR.relative_to(REPO_ROOT)
    shipped = built_app(repo) / relative / "rail" / "classifier.pkl"
    # The copied app resolves its model directory against its own root, so landing the
    # checkpoint at the same relative path is what makes it findable there.
    assert shipped.is_file()
    assert shipped.read_bytes() == b"checkpoint"


def test_the_write_up_is_placed_at_the_top_of_optional_items(repo):
    (repo / f"{WRITE_UP_STEM}.md").write_text("# Approach\n")
    built = package.build("Group1")
    placed = built / package.OPTIONAL_DIR_NAME / f"{WRITE_UP_STEM}.md"
    assert placed.is_file()
    assert placed.read_text() == "# Approach\n"


def test_a_missing_write_up_is_reported_rather_than_fatal(repo, capsys):
    built = package.build("Group1")
    reported = capsys.readouterr().out
    assert not list((built / package.OPTIONAL_DIR_NAME).glob(f"{WRITE_UP_STEM}.*"))
    assert "the write-up" in reported and "the demo video" in reported
    # The folder is still built: both are made last and neither blocks a rehearsal.
    assert (built / "predictions.zip").is_file()


def test_the_archive_stays_flat_and_holds_only_what_was_ready(repo):
    built = package.build("Group1")
    with zipfile.ZipFile(built / "predictions.zip") as archive:
        assert archive.namelist() == ["rail_predictions.csv"]
