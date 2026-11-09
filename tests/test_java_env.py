"""Java detection must work in every setup people really have (the cause of 'Java not found' on Windows)."""
import os
import stat

import pytest

from src import java_env


@pytest.mark.parametrize("text, expected", [
    ('openjdk version "17.0.9" 2023-10-17\nOpenJDK Runtime Environment Temurin-17.0.9+9', 17),
    ('java version "1.8.0_392"\nJava(TM) SE Runtime Environment', 8),
    ('openjdk version "21" 2023-09-19', 21),
    ('Picked up JAVA_TOOL_OPTIONS: -Dfile.encoding=UTF-8\nopenjdk version "11.0.21" 2023-10-17', 11),
    ('java version "24.0.1" 2025-04-15', 24),
    ('openjdk 17.0.9 2023-10-17', 17),
    ("something unrelated", None),
    ("", None),
])
def test_parse_java_version(text, expected):
    assert java_env.parse_java_version(text) == expected


def make_fake_jdk(root, version="17.0.2"):
    """Create <root>/bin/java (a tiny script that prints a version) and <root>/lib, like a real JDK folder."""
    bin_dir = root / "bin"
    bin_dir.mkdir(parents=True)
    (root / "lib").mkdir()
    script = bin_dir / "java"
    script.write_text(f'#!/bin/sh\necho \'openjdk version "{version}" 2024-01-01\' >&2\n')
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return root


@pytest.mark.skipif(os.name == "nt", reason="uses a shell script as a fake java")
class TestFindJava:
    @pytest.fixture(autouse=True)
    def clean_environment(self, monkeypatch, tmp_path):
        monkeypatch.setenv("PATH", str(tmp_path / "empty"))            # no java on the PATH
        monkeypatch.delenv("JAVA_HOME", raising=False)
        monkeypatch.delenv("CONDA_PREFIX", raising=False)
        monkeypatch.setattr(java_env, "_candidates", _only_env_candidates)    # ignore this machine's own Java

    def test_found_through_java_home(self, monkeypatch, tmp_path):
        jdk = make_fake_jdk(tmp_path / "jdk17")
        monkeypatch.setenv("JAVA_HOME", str(jdk))
        found = java_env.find_java()
        assert found["version"] == 17 and found["how"] == "JAVA_HOME"

    def test_java_home_pointing_at_the_bin_folder(self, monkeypatch, tmp_path):
        jdk = make_fake_jdk(tmp_path / "jdk17")
        monkeypatch.setenv("JAVA_HOME", str(jdk / "bin"))              # a common mistake
        assert java_env.find_java()["version"] == 17

    def test_java_home_with_quotes_and_trailing_slash(self, monkeypatch, tmp_path):
        jdk = make_fake_jdk(tmp_path / "jdk17")
        monkeypatch.setenv("JAVA_HOME", f'"{jdk}/"')
        assert java_env.find_java()["version"] == 17

    def test_found_inside_conda_environment(self, monkeypatch, tmp_path):
        env = tmp_path / "conda_env"
        make_fake_jdk(env)
        monkeypatch.setenv("CONDA_PREFIX", str(env))
        assert java_env.find_java()["how"] == "conda environment"

    def test_nothing_found(self):
        assert java_env.find_java() is None

    def test_prepare_sets_java_home_and_path(self, monkeypatch, tmp_path):
        jdk = make_fake_jdk(tmp_path / "jdk17")
        monkeypatch.setenv("JAVA_HOME", str(jdk / "bin"))              # wrong form on purpose
        found = java_env.prepare_java()
        assert found is not None
        assert os.environ["JAVA_HOME"] == str(jdk)
        assert str(jdk / "bin") in os.environ["PATH"].split(os.pathsep)

    def test_wrong_java_home_is_removed_when_path_has_a_good_java(self, monkeypatch, tmp_path):
        jdk = make_fake_jdk(tmp_path / "jdk17")
        monkeypatch.setenv("PATH", str(jdk / "bin"))
        monkeypatch.setenv("JAVA_HOME", str(tmp_path / "does_not_exist"))
        java_env.prepare_java()
        assert os.environ.get("JAVA_HOME") == str(jdk)

    def test_older_java_is_reported_not_hidden(self, monkeypatch, tmp_path):
        jdk = make_fake_jdk(tmp_path / "jdk8", version="1.8.0_392")
        monkeypatch.setenv("JAVA_HOME", str(jdk))
        assert java_env.find_java()["version"] == 8


def _only_env_candidates():
    """The real candidate list minus the 'common install folders' (so the test machine's own Java is ignored)."""
    import shutil
    on_path = shutil.which("java")
    if on_path:
        yield on_path, "PATH"
    home = os.environ.get("JAVA_HOME", "").strip().strip('"').rstrip("\\/")
    if home:
        yield os.path.join(home, "bin", java_env.EXE), "JAVA_HOME"
        yield os.path.join(home, java_env.EXE), "JAVA_HOME (points at the bin folder)"
    prefix = os.environ.get("CONDA_PREFIX")
    if prefix:
        yield os.path.join(prefix, "bin", java_env.EXE), "conda environment"
