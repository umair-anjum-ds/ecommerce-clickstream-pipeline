"""Startup check: are all the project files from the same version?

This catches the situation where a new zip was unzipped over an old folder (some old files kept) or the app
was still running while files were replaced. Instead of a confusing traceback the app explains the fix.
"""
import importlib

REQUIRED = [
    ("ui.theme", "current_mode"), ("ui.theme", "inject_css"), ("ui.theme", "inject_theme_watcher"),
    ("ui.theme", "kpi_grid"), ("ui.charts", "set_mode"), ("ui.charts", "pal"), ("ui.charts", "segment_colors"),
    ("ui.state", "open_demo"), ("src.demo", "load_demo"), ("src.insights", "build_insights"),
    ("src.mapping", "resolve"), ("src.run_pipeline", "run"),
]

FIX = """**Some project files are from different versions.** This usually happens when a new zip is unzipped over an old
folder, or the app kept running while files were replaced.

How to fix it:
1. Stop the app (press **Ctrl+C** in the terminal window).
2. Unzip the newest zip into a **new, empty folder** (or overwrite *every* file when asked).
3. Delete the folders `ui\\__pycache__` and `src\\__pycache__` if they exist.
4. Start again with `run.bat` (Windows) or `python3 run.py`.
"""


def missing_parts():
    """Return the list of 'module.name' items the app needs but cannot find (empty list = all good)."""
    missing = []
    for module_name, attribute in REQUIRED:
        try:
            module = importlib.import_module(module_name)
        except Exception:
            missing.append(f"{module_name} (cannot be imported)")
            continue
        if not hasattr(module, attribute):
            missing.append(f"{module_name}.{attribute}")
    return missing
