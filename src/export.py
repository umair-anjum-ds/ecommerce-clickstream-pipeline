"""Pack the results of one run into a single ZIP file the user can download."""
import io
import os
import zipfile


def results_zip(output_dir, reports_dir, include_parquet=False):
    """Return the bytes of a ZIP with tables, charts, models, the report and metrics."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        folders = [(os.path.join(output_dir, "tables"), "tables"),
                   (os.path.join(output_dir, "charts"), "charts"),
                   (os.path.join(output_dir, "models"), "models")]
        if include_parquet:
            folders.append((os.path.join(output_dir, "events_parquet"), "events_parquet"))
        for folder, arc in folders:
            for root, _, files in os.walk(folder):
                for name in files:
                    full = os.path.join(root, name)
                    zf.write(full, os.path.join(arc, os.path.relpath(full, folder)))
        for single, arc in [(os.path.join(reports_dir, "summary.md"), "summary.md"),
                            (os.path.join(output_dir, "metrics.json"), "metrics.json")]:
            if os.path.exists(single):
                zf.write(single, arc)
    return buffer.getvalue()
