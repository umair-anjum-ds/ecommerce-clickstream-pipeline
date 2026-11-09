"""Start page: landing, upload, check the columns, run the analysis."""
import os
import shutil

import streamlit as st

from scripts.generate_sample_data import generate
from src import demo, mapping, run_pipeline
from ui import nav, state, theme

NONE_CHOICE = "(none)"
STAGES = [("Checking your columns", 0.0), ("Starting the Spark engine", 0.05), ("Reading and cleaning the data", 0.08),
          ("Business analysis", 0.25), ("RDD cross-check", 0.50), ("Saving the cleaned data", 0.62),
          ("Training prediction models", 0.70), ("Drawing charts and writing the report", 0.92)]


@st.cache_data(show_spinner=False)
def cached_event_values(path, column, delimiter):
    return mapping.distinct_values(path, column, delimiter)


def render():
    theme.hero(
        "PySpark analytics studio",
        'Turn raw clicks into <span class="grad">decisions</span>',
        "Upload any e-commerce clickstream CSV. ClickPulse cleans it, analyses it with Apache Spark, finds the "
        "story in your data and predicts which carts will turn into purchases.",
        chips=["Apache Spark", "DataFrame + SQL windows", "RDD API", "Spark MLlib", "scikit-learn", "Streamlit"])
    theme.feature_grid([
        ("Any CSV", "Bring your own data", "Detects columns, separators and time formats. You stay in control."),
        ("6 steps", "A real big-data pipeline", "Clean, analyse, cross-check with RDDs, store, model, report."),
        ("14 models", "Purchase prediction", "Spark MLlib and scikit-learn compared, plus a what-if simulator."),
        ("1 click", "Insights and reports", "Findings written in plain English and a ZIP with everything."),
    ])

    theme.html('<div class="theme-hint">Light or dark? ClickPulse follows your system setting. To choose by hand, open the '
               'menu at the top right (three dots) and pick System, Light or Dark.</div>')
    if demo.demo_available():
        left, right = st.columns([3, 1], vertical_alignment="center")
        left.markdown("**Want to see it first?** Open a complete example, no upload and no waiting.")
        if right.button("Explore the demo", type="primary", width="stretch"):
            state.open_demo()

    # ------------------------------------------------------------ upload
    theme.section("Analyse your own data", "Three quick steps. Your file is processed on the machine running this app.")
    data_path = st.session_state.get("data_path")
    info = state.results()
    step = 3 if (info and not info.get("demo")) else (2 if data_path else 1)
    theme.stepper(step)

    with st.container(key="card-upload"):
        uploaded = st.file_uploader("Drop your CSV here (or .csv.gz)", type=["csv", "gz"])
        if uploaded is not None and st.session_state.get("uploaded_name") != (uploaded.name, uploaded.size):
            folder = state.new_workdir()
            data_path = os.path.join(folder, uploaded.name)
            with open(data_path, "wb") as f:
                shutil.copyfileobj(uploaded, f)
            st.session_state.update(data_path=data_path, uploaded_name=(uploaded.name, uploaded.size))
            st.session_state.pop("results", None)
            st.rerun()
        if not data_path and st.button("Use generated sample data instead"):
            folder = state.new_workdir()
            sample_path = os.path.join(folder, "sample_events.csv")
            generate(sample_path, sessions=3000)
            st.session_state["data_path"] = sample_path
            st.session_state.pop("results", None)
            st.rerun()

    if not data_path:
        st.caption("Needed: event time, event type, session id, user id and price. "
                   "Optional: product id, category and brand.")
        return

    # ------------------------------------------------------------ check the data
    delimiter = mapping.detect_delimiter(data_path)
    try:
        preview = mapping.read_preview(data_path, nrows=1000, delimiter=delimiter)
    except Exception as error:
        st.error(f"Could not read this file as a CSV: {error}")
        return

    with st.container(key="card-check"):
        theme.card_title("Check your data", f"Separator detected: {delimiter!r}  |  {len(preview.columns)} columns  |  "
                                            "first rows shown")
        st.dataframe(preview.head(8), width="stretch", hide_index=True)

        suggested = mapping.suggest_mapping(list(preview.columns))
        options = [NONE_CHOICE] + list(preview.columns)
        column_map = {}
        st.markdown("**Which column means what?** We guessed from the names. Change anything that is wrong.")
        grid = st.columns(4)
        for i, (field, (required, label)) in enumerate(mapping.FIELDS.items()):
            default = suggested[field] if suggested[field] in options else NONE_CHOICE
            chosen = grid[i % 4].selectbox(label + (" *" if required else ""), options,
                                           index=options.index(default), key=f"map_{field}")
            column_map[field] = None if chosen == NONE_CHOICE else chosen

        event_map = {}
        if column_map.get("event_type"):
            values = cached_event_values(data_path, column_map["event_type"], delimiter)
            guess = mapping.suggest_event_map(values)
            st.markdown("**Which values mean view, add to cart and purchase?**")
            cols = st.columns(3)
            for i, role in enumerate(mapping.EVENT_ROLES):
                defaults = [v for v in values if guess.get(v) == role]
                for value in cols[i].multiselect(f"Means '{role}'", values, default=defaults, key=f"role_{role}"):
                    event_map[value] = role

        problems = mapping.validate_mapping(column_map, list(preview.columns), event_map)
        for problem in problems:
            st.warning(problem)

        with st.expander("Advanced options"):
            skip_rdd = not st.checkbox("RDD cross-check", value=True,
                                       help="Recompute key numbers with Spark's low-level RDD API")
            skip_ml = not st.checkbox("Train prediction models", value=True,
                                      help="Needs enough cart sessions with and without a purchase")
            row_limit = st.number_input("Analyse only the first N rows (0 = all)", min_value=0, value=0,
                                        step=100_000, help="Quick preview of a very large file")

    # ------------------------------------------------------------ run
    run_clicked = st.button("Run analysis", type="primary", disabled=bool(problems), width="stretch")
    if run_clicked:
        folder = st.session_state["workdir"]
        out_dir, reports_dir = os.path.join(folder, "outputs"), os.path.join(folder, "reports")
        shutil.rmtree(out_dir, ignore_errors=True)
        shutil.rmtree(reports_dir, ignore_errors=True)
        with st.container(key="card-progress"):
            theme.card_title("Analysing your data", "Spark is working. Larger files take longer.")
            bar, board = st.progress(0.0), st.empty()

            def update(fraction, message):
                bar.progress(min(float(fraction), 1.0))
                board.markdown(theme.stages_html(STAGES, float(fraction)), unsafe_allow_html=True)

            try:
                result = run_pipeline.run(data_path, out_dir, reports_dir, skip_ml=skip_ml, skip_rdd=skip_rdd,
                                          stop_spark=False, column_map=column_map, event_map=event_map,
                                          delimiter=delimiter, row_limit=int(row_limit) or None, progress=update)
                result["demo"] = False
                result["source"] = os.path.basename(data_path)
                state.set_results(result)
                st.rerun()
            except ValueError as error:                       # problems with the user's data: explain them
                st.error(str(error))
            except Exception as error:
                st.error(f"The analysis failed: {error}")
                st.exception(error)

    if info and not info.get("demo"):
        st.success("Your analysis is ready.")
        st.page_link(nav.PAGES["dashboard"], label="Open the dashboard", icon=":material/dashboard:")
