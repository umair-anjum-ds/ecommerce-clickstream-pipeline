#!/usr/bin/env python3
"""One-command launcher. It installs everything it needs, then runs what you ask for.

    python run.py            start the web app (same as: python run.py app)
    python run.py app        start the web app (open http://localhost:8501)
    python run.py test       run all automated tests
    python run.py test --quick   run only the fast tests (a few seconds)
    python run.py sample     create fake data/events.csv
    python run.py pipeline --input your_file.csv     run the analysis from the command line
    python run.py lint       check the code style
    python run.py setup      only install the packages
    python run.py doctor     show what was found (Python, Java, ...) when something does not work

The first run creates a private virtual environment in the folder `.venv` and installs
all packages from requirements.txt. Later runs reuse it (and re-install only if the
requirements file changed). Only the Python standard library is used in this file.
"""
import hashlib
import os
import platform
import re
import shutil
import subprocess
import sys
import threading
import venv
import webbrowser

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
from src import java_env  # noqa: E402  (standard library only, so it works before packages are installed)

VENV_DIR = os.path.join(ROOT, ".venv")
MIN_PYTHON = (3, 10)
MIN_JAVA = java_env.MIN_JAVA
QUICK_TESTS = "mapping or missing_required or app_starts"      # tests that do not start Spark


def say(message):
    print(f"[run] {message}", flush=True)


def fail(message):
    print(f"\n[run] PROBLEM: {message}\n", file=sys.stderr)
    sys.exit(1)


# ------------------------------------------------------------------ checks
def check_python():
    if sys.version_info < MIN_PYTHON:
        fail(f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]} or newer is needed, you have {platform.python_version()}. "
             "Download it from https://www.python.org/downloads/")


def windows_notes():
    """Friendly hints for Windows users. They never stop the program."""
    if os.name != "nt":
        return
    if " " in ROOT:
        say("Tip: this folder path contains spaces. If Spark ever reports 'Python worker failed to connect back', "
            "move the project to a path without spaces, for example C:\\projects\\clickstream.")
    if "OneDrive" in ROOT:
        say("Tip: this folder is inside OneDrive. Sync locks can break Spark; C:\\projects\\clickstream is safer.")
    if not os.environ.get("HADOOP_HOME"):
        say("Note: HADOOP_HOME is not set. The analysis, charts, models and report work without it. Only the "
            "optional Parquet export may be skipped (you will see a warning). See 'Running on Windows' in the README.")


def check_java():
    """Find Java the way Spark does. Only stops when no Java exists at all or a too-old one is the best found."""
    windows_notes()
    found = java_env.prepare_java()
    if found is None:
        fail("Java was not found (looked at PATH, JAVA_HOME, conda and the usual install folders).\n"
             + java_env.INSTALL_HELP)
    version = found["version"]
    if version is None:
        say(f"Java found at {found['path']} (found via {found['how']}), but its version could not be read. "
            "Continuing anyway. Spark will tell us if it does not work.")
    elif version < MIN_JAVA:
        fail(f"Only Java {version} was found ({found['path']}). Java {MIN_JAVA} or newer is needed.\n"
             + java_env.INSTALL_HELP)
    else:
        say(f"Java {version} found ({found['how']}: {found['path']}).")


def doctor():
    """Print what this program can see. Send this output if something does not work."""
    print(f"Python      : {sys.version.split()[0]}  ({sys.executable})")
    print(f"System      : {platform.platform()}")
    print(f"Project     : {ROOT}")
    print(f"JAVA_HOME   : {os.environ.get('JAVA_HOME', '(not set)')}")
    print(f"CONDA_PREFIX: {os.environ.get('CONDA_PREFIX', '(not set)')}")
    print(f"java on PATH: {shutil.which('java') or '(not found)'}")
    print("\nJava candidates:")
    any_found = False
    for path, how in java_env._candidates():
        exists = os.path.isfile(path)
        any_found = any_found or exists
        if exists:
            version, raw = java_env.read_version(path)
            first_line = raw.splitlines()[0] if raw else ""
            print(f"  FOUND   [{how}] {path}\n          version = {version}   ({first_line})")
        elif how in ("JAVA_HOME", "PATH"):
            print(f"  missing [{how}] {path}")
    if not any_found:
        print("  (no Java found anywhere)")
    chosen = java_env.prepare_java()
    print("\nChosen Java :", chosen["path"] if chosen else "(none)")
    if chosen is None:
        print("\n" + java_env.INSTALL_HELP)
    elif chosen["version"] is not None and chosen["version"] < MIN_JAVA:
        print(f"\nThis Java is too old (need {MIN_JAVA}+).\n" + java_env.INSTALL_HELP)
    else:
        print("JAVA_HOME used for Spark:", os.environ.get("JAVA_HOME", "(PATH is used)"))
    venv_ready = os.path.exists(venv_python())
    print(f"\nVirtual environment (.venv) created: {venv_ready}")
    if os.name == "nt":
        hadoop = os.environ.get("HADOOP_HOME", "(not set, only the optional Parquet export is affected)")
        print(f"HADOOP_HOME : {hadoop}")


# ------------------------------------------------------------------ virtual environment
def venv_python():
    folder, name = ("Scripts", "python.exe") if os.name == "nt" else ("bin", "python")
    return os.path.join(VENV_DIR, folder, name)


def requirements_hash(files):
    digest = hashlib.sha256()
    for name in files:
        with open(os.path.join(ROOT, name), "rb") as f:
            digest.update(f.read())
    return digest.hexdigest()


def pip_version(python):
    """Return the pip version of that Python as a tuple like (25, 1, 1), or (0,) when unknown."""
    try:
        text = subprocess.run([python, "-m", "pip", "--version"], capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=60).stdout
    except Exception:
        return (0,)
    match = re.search(r"pip (\d+)\.(\d+)(?:\.(\d+))?", text)
    return tuple(int(x) for x in match.groups() if x is not None) if match else (0,)


def pip_install_command(python, requirements_path, version, wheels_dir=None):
    """Build the pip command. Long timeouts and retries help on slow or unstable internet.

    * pip 25.1 or newer can RESUME an interrupted download (important for PySpark, about 450 MB)
    * a folder `wheels` next to this file can hold manually downloaded files (offline / very slow networks)
    """
    command = [python, "-m", "pip", "install", "--disable-pip-version-check",
               "--default-timeout", "180", "--retries", "10"]
    if version >= (25, 1):
        command += ["--resume-retries", "10"]
    if wheels_dir and os.path.isdir(wheels_dir) and os.listdir(wheels_dir):
        command += ["--find-links", wheels_dir]
    return command + ["-r", requirements_path]


def pip_install(python, requirements_path, attempts=3):
    """Upgrade pip, then install the requirements, retrying when the network fails. Returns True on success."""
    subprocess.call([python, "-m", "pip", "install", "--upgrade", "pip", "--disable-pip-version-check",
                     "--default-timeout", "180", "--retries", "10"], cwd=ROOT)          # small, best effort
    command = pip_install_command(python, requirements_path, pip_version(python), os.path.join(ROOT, "wheels"))
    for attempt in range(1, attempts + 1):
        if subprocess.call(command, cwd=ROOT) == 0:
            return True
        if attempt < attempts:
            say(f"The download was interrupted (attempt {attempt} of {attempts}). Trying again ...")
    return False


MANUAL_INSTALL_HELP = (
    "The packages could not be downloaded (slow or blocked internet, VPN, proxy or antivirus are the usual reasons).\n"
    "Options:\n"
    "  1. Run the same command again. Finished downloads are kept and interrupted ones are resumed.\n"
    "  2. Try another network (for example a phone hotspot) or switch off the VPN for the first install.\n"
    "  3. Download the big file yourself with your browser (or a download manager):\n"
    "       - open https://pypi.org/project/pyspark/#files and download the newest 4.x file ending in .tar.gz\n"
    "       - create a folder named 'wheels' inside the project folder and put the file in it\n"
    "       - run the same command again. The launcher uses the 'wheels' folder automatically."
)


def ensure_environment(dev=False):
    """Create .venv and install the packages when needed. Returns the path of the venv's Python."""
    python = venv_python()
    if not os.path.exists(python):
        say("Creating a private virtual environment in .venv (one time) ...")
        try:
            venv.EnvBuilder(with_pip=True, clear=False).create(VENV_DIR)
        except Exception as error:
            fail(f"Could not create the virtual environment: {error}\n"
                 "On Ubuntu/Debian run:  sudo apt install python3-venv")

    requirements_file = "requirements-dev.txt" if dev else "requirements.txt"
    stamp = os.path.join(VENV_DIR, ".installed-dev" if dev else ".installed")
    wanted = requirements_hash(["requirements.txt"] + (["requirements-dev.txt"] if dev else []))
    installed = open(stamp, encoding="utf-8").read().strip() if os.path.exists(stamp) else ""
    if installed != wanted:
        say("Installing packages. The first time this downloads about 700 MB (PySpark alone is about 450 MB), "
            "so it can take a while on a slow connection ...")
        if not pip_install(python, os.path.join(ROOT, requirements_file)):
            fail(MANUAL_INSTALL_HELP)
        with open(stamp, "w", encoding="utf-8") as f:
            f.write(wanted)
        say("All packages are installed.")
    return python


# ------------------------------------------------------------------ commands
def run_command(command):
    sys.exit(subprocess.call(command, cwd=ROOT))


def main(argv):
    check_python()
    command = argv[0] if argv else "app"
    extra = argv[1:]

    if command in ("-h", "--help", "help"):
        print(__doc__)
        return

    if command == "doctor":
        doctor()
        return

    if command == "setup":
        check_java()
        ensure_environment(dev=True)
        say("Setup finished. Next: python run.py test --quick   or   python run.py app")
        return

    if command == "sample":
        python = ensure_environment()
        arguments = extra or ["--sessions", "6000", "--out", "data/events.csv"]
        run_command([python, "scripts/generate_sample_data.py", *arguments])

    if command == "lint":
        python = ensure_environment(dev=True)
        run_command([python, "-m", "ruff", "check", "."])

    if command == "test":
        check_java()
        python = ensure_environment(dev=True)
        if "--quick" in extra:
            extra = [a for a in extra if a != "--quick"] + ["-k", QUICK_TESTS]
        run_command([python, "-m", "pytest", *extra])

    if command == "pipeline":
        check_java()
        python = ensure_environment()
        run_command([python, "-m", "src.run_pipeline", *extra])

    if command == "app":
        check_java()
        python = ensure_environment()
        port = "8501"
        if "--port" in extra:
            port = extra[extra.index("--port") + 1]
        url = f"http://localhost:{port}"
        say(f"Starting the app. Open {url} in your browser (press Ctrl+C here to stop it).")
        if "--no-browser" not in extra:
            threading.Timer(6.0, lambda: webbrowser.open(url)).start()
        run_command([python, "-m", "streamlit", "run", "app.py", "--server.port", port,
                     "--server.headless", "true"])

    fail(f"Unknown command '{command}'. Use one of: app, test, sample, pipeline, lint, setup, doctor (or --help).")


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except KeyboardInterrupt:
        say("Stopped.")
