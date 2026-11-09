"""Find Java the same way Spark does, and make sure Spark can use it.

Uses only the Python standard library, so the launcher (run.py) can import it before any package is installed.

Spark finds Java through the JAVA_HOME variable first and through the PATH second. People also have Java inside a
conda environment or in a normal install folder that is on neither. This module looks in all those places, picks a
working Java 17 or newer, and sets JAVA_HOME / PATH for this program and the Spark processes it starts.
"""
import glob
import os
import re
import shutil
import subprocess

MIN_JAVA = 17
IS_WINDOWS = os.name == "nt"
EXE = "java.exe" if IS_WINDOWS else "java"


def parse_java_version(text):
    """Return the Java major version from the text printed by `java -version`, or None.

    Handles: openjdk version "17.0.9" | java version "1.8.0_392" (= Java 8) | version "21" | extra
    lines such as 'Picked up JAVA_TOOL_OPTIONS: ...'.
    """
    match = re.search(r'version\s+"(\d+)(?:\.(\d+))?', text or "")
    if not match:
        match = re.search(r"\b(?:openjdk|jdk|java)\s+(\d+)(?:\.(\d+))?", text or "", re.IGNORECASE)
    if not match:
        return None
    major = int(match.group(1))
    return int(match.group(2)) if major == 1 and match.group(2) else major


def read_version(java_path):
    """Run `java -version`. Returns (major version or None, raw text)."""
    try:
        result = subprocess.run([java_path, "-version"], capture_output=True, text=True,
                                encoding="utf-8", errors="replace", timeout=40)
    except Exception as error:                                   # a bad file, no permission, timeout ...
        return None, f"could not run it: {error}"
    raw = ((result.stderr or "") + (result.stdout or "")).strip()
    return parse_java_version(raw), raw


def _candidates():
    """Yield (path to a java executable, where it came from). Nothing here checks that the file works."""
    on_path = shutil.which("java")
    if on_path:
        yield on_path, "PATH"

    home = os.environ.get("JAVA_HOME", "").strip().strip('"').rstrip("\\/")
    if home:
        yield os.path.join(home, "bin", EXE), "JAVA_HOME"
        yield os.path.join(home, EXE), "JAVA_HOME (points at the bin folder)"

    prefix = os.environ.get("CONDA_PREFIX")                      # Java installed inside a conda environment
    if prefix:
        for relative in ("Library/bin", "bin", "lib/jvm/bin"):
            yield os.path.join(prefix, *relative.split("/"), EXE), "conda environment"

    patterns = []
    if IS_WINDOWS:
        vendors = ["Eclipse Adoptium", "Java", "Microsoft", "Zulu", "Amazon Corretto", "BellSoft", "Semeru",
                   "AdoptOpenJDK", "Eclipse Foundation", "OpenJDK"]
        for variable in ("ProgramFiles", "ProgramW6432", "ProgramFiles(x86)", "LOCALAPPDATA"):
            root = os.environ.get(variable)
            if root:
                patterns += [os.path.join(root, vendor, "*", "bin", EXE) for vendor in vendors]
        patterns += [os.path.join("C:\\", "Java", "*", "bin", EXE)]
    else:
        patterns += ["/usr/lib/jvm/*/bin/java", "/Library/Java/JavaVirtualMachines/*/Contents/Home/bin/java",
                     "/opt/homebrew/opt/openjdk*/bin/java", "/usr/local/opt/openjdk*/bin/java"]
    for pattern in patterns:
        for path in sorted(glob.glob(pattern), reverse=True):    # newest folder name first
            yield path, "common install folder"


def find_java():
    """Return a dict {path, how, version, raw} for the best Java found, or None when there is none.

    A Java 17+ wins. If only an older one exists it is returned so the caller can explain the problem.
    """
    seen, fallback = set(), None
    for path, how in _candidates():
        key = os.path.normcase(os.path.realpath(path))
        if key in seen or not os.path.isfile(path):
            continue
        seen.add(key)
        version, raw = read_version(path)
        entry = {"path": path, "how": how, "version": version, "raw": raw}
        if version is not None and version >= MIN_JAVA:
            return entry
        fallback = fallback or entry
    return fallback


def _java_home_of(java_path):
    """The JAVA_HOME that belongs to a java executable, or None when it does not look like a JDK/JRE folder."""
    home = os.path.dirname(os.path.dirname(os.path.realpath(java_path)))
    if os.path.isfile(os.path.join(home, "bin", EXE)) and os.path.isdir(os.path.join(home, "lib")):
        return home
    return None


def prepare_java():
    """Find Java and set JAVA_HOME and PATH so Spark uses it. Returns the find_java() dict, or None.

    Safe to call many times. It never raises.
    """
    found = find_java()
    if found is None:
        return None
    home = _java_home_of(found["path"])
    if home:
        os.environ["JAVA_HOME"] = home
        bin_dir = os.path.join(home, "bin")
        if bin_dir not in os.environ.get("PATH", "").split(os.pathsep):
            os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")
    else:
        # A wrong JAVA_HOME would make Spark ignore a perfectly good java on the PATH
        current = os.environ.get("JAVA_HOME", "")
        if current and not os.path.isfile(os.path.join(current.strip('"'), "bin", EXE)):
            os.environ.pop("JAVA_HOME", None)
    return found


INSTALL_HELP = (
    "Install Java 17 or newer:\n"
    "  Windows : winget install EclipseAdoptium.Temurin.17.JDK   (then open a NEW terminal)\n"
    "  macOS   : brew install --cask temurin@17\n"
    "  Ubuntu  : sudo apt install openjdk-17-jre-headless\n"
    "  Other   : https://adoptium.net/\n"
    "Already installed? Run:  python run.py doctor   (it shows where Java was looked for).\n"
    "If your Java lives inside a conda environment, activate that environment first. You can also point to "
    "Java yourself, for example on Windows:  set JAVA_HOME=C:\\Program Files\\Eclipse Adoptium\\jdk-17.0.9.9-hotspot"
)
