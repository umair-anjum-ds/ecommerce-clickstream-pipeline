"""The launcher must be robust on slow or unstable internet (the cause of install failures)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import run  # noqa: E402


def test_old_pip_gets_long_timeouts_and_retries_but_no_resume_flag():
    command = run.pip_install_command("python", "requirements.txt", (24, 0))
    assert "--default-timeout" in command and command[command.index("--default-timeout") + 1] == "180"
    assert "--retries" in command
    assert "--resume-retries" not in command          # an old pip would reject this option
    assert command[-2:] == ["-r", "requirements.txt"]


def test_new_pip_can_resume_interrupted_downloads():
    command = run.pip_install_command("python", "requirements.txt", (25, 1, 1))
    assert "--resume-retries" in command


def test_wheels_folder_is_used_when_it_has_files(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    assert "--find-links" not in run.pip_install_command("python", "r.txt", (25, 1), str(empty))
    (empty / "pyspark-4.3.0.tar.gz").write_bytes(b"x")
    command = run.pip_install_command("python", "r.txt", (25, 1), str(empty))
    assert command[command.index("--find-links") + 1] == str(empty)
    assert "--find-links" not in run.pip_install_command("python", "r.txt", (25, 1), str(tmp_path / "missing"))


def test_pip_version_is_read_from_the_real_pip():
    version = run.pip_version(sys.executable)
    assert len(version) >= 2 and version[0] >= 20
