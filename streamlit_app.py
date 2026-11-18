"""Aurora-glass Streamlit studio for PromoFinder inference and ranked promo review."""
import hashlib
import json
import sqlite3
import tempfile
from pathlib import Path

import streamlit as st

import ui_theme as ui
from promofinder.ingestion.episode_parser import parse_episode
from promofinder.ingestion.file_loader import discover_files
from promofinder.ingestion.text_extractor import extract_text
from promofinder.main import run_pipeline
from promofinder.settings import load_settings


st.set_page_config(
    page_title="PromoFinder Studio",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.html(ui.CSS)


def _html(markup):
    """Render trusted, local visual markup from ui_theme."""
    st.html(markup)


settings = load_settings()
st.session_state.setdefault("inference_running", False)


def format_timestamp(seconds):
    seconds = int(seconds or 0)
    return "{:02d}:{:02d}".format(seconds // 60, seconds % 60)


def _begin_inference(selected_file_count):
    """Freeze the selected files' effective shortlist size before inference."""
    st.session_state["inference_running"] = True
    requested_top_k = st.session_state.get(
        "top_k_slider", settings.top_k)
    st.session_state["locked_top_k"] = requested_top_k
    st.session_state["locked_effective_top_k"] = min(
        requested_top_k, selected_file_count)
    st.session_state["inference_requested"] = True


def _episode_record(filename, text, index, path=None):
    episode = parse_episode(text, filename, index)
    return {"label": "{} · {}".format(episode.episode_id, filename),
            "filename": Path(filename).name, "text": text,
            "episode": episode, "path": Path(path) if path else None}


@st.cache_data(show_spinner=False)
def _cached_library_records(root_text, file_fingerprint):
    del file_fingerprint  # Included in Streamlit's cache key to invalidate changed files.
    root = Path(root_text)
    records, errors = [], []
    for index, path in enumerate(discover_files(root), 1):
        try:
            records.append(_episode_record(path.name, extract_text(path), index, path=path))
        except Exception as exc:
            errors.append("{}: {}".format(path.name, exc))
    return records, errors


def _read_inputs():
    records, errors = [], []
    controls_locked = st.session_state.get("inference_running", False)
    source_mode = st.sidebar.segmented_control(
        "Input source", ["Input library", "Drag & drop"], default="Input library",
        key="screenplay_source_mode", disabled=controls_locked,
    )
    if source_mode == "Input library":
        try:
            paths = discover_files(settings.input_dir)
            fingerprint = tuple(
                (str(path.relative_to(settings.input_dir)), path.stat().st_size,
                 path.stat().st_mtime_ns)
                for path in paths
            )
            records, errors = _cached_library_records(str(settings.input_dir), fingerprint)
        except Exception as exc:
            errors.append(str(exc))
    else:
        uploaded = st.sidebar.file_uploader(
            "Drop or browse for TXT screenplays", type=["txt"], accept_multiple_files=True,
            key="screenplay_uploads", disabled=controls_locked,
        ) or []
        for index, item in enumerate(uploaded, 1):
            try:
                text = item.getvalue().decode("utf-8-sig")
                records.append(_episode_record(item.name, text, index))
            except Exception as exc:
                errors.append("{}: {}".format(item.name, exc))
    if errors:
        st.sidebar.warning("{} input issue(s)".format(len(errors)))
        with st.sidebar.expander("Input details"):
            for error in errors:
                st.write(error)
    return source_mode, records, errors


def _read_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _materialize_records(records, folder):
    root = Path(folder)
    root.mkdir(parents=True, exist_ok=True)
    for index, record in enumerate(records, 1):
        destination_dir = root / "episode_{:03d}".format(index)
        destination_dir.mkdir(parents=True, exist_ok=True)
        episode_number = record["episode"].episode_id.split("_")[-1]
        destination_name = "episode-{}-{}".format(episode_number, record["filename"])
        (destination_dir / destination_name).write_text(record["text"], encoding="utf-8")
    return root


def _run_with_progress(run_settings, input_dir, top_k, force_reprocess):
    progress = st.progress(0.0)
    stage_note = st.empty()

    def update(event):
        stage = event["stage"]
        current, total = event["current"], event["total"]
        ratio = min(1.0, current / total) if total else 1.0
        if stage == "parse":
            fraction = 0.02 + (0.03 * ratio)
        elif stage == "generation":
            fraction = 0.05 + (0.70 * ratio)
        elif stage == "ranking":
            fraction = 0.76 + (0.22 * ratio)
        else:
            fraction = 1.0
        progress.progress(min(1.0, fraction))
        stage_note.caption(event["detail"])

    return run_pipeline(
        settings=run_settings, input_dir=input_dir, top_k=top_k,
        force_reprocess=force_reprocess, progress_callback=update,
    )


def _display_ranked_results(output_dir, input_records, run_episode_hashes, top_k):
    rankings = _read_json(Path(output_dir) / "rankings.json", [])
    if not rankings:
        rankings = _read_json(Path(output_dir) / "top_promos.json", [])
    promos = _read_json(Path(output_dir) / "valid_promos.json", [])
    promo_by_id = {item.get("promo_id"): item for item in promos}
    rankings.sort(key=lambda item: item.get("rank", 10 ** 9))
    rankings = rankings[:max(0, top_k)]
    if not rankings:
        st.info("No ranked promos are available yet. Run inference on selected files first.")
        return
    ranking_by_id = {item.get("promo_id"): item for item in rankings}
    promo_ids = list(ranking_by_id)
    selected_id = st.session_state.get("selected_output_promo_id")
    if selected_id not in ranking_by_id:
        selected_id = promo_ids[0]
        st.session_state["selected_output_promo_id"] = selected_id

    episode_by_id = {record["episode"].episode_id: record["episode"]
                     for record in input_records}

    totals = [float(item.get("total_score", 0) or 0) for item in rankings]
    all_scores = [item.get("scores", {}) for item in rankings]
    kpi_columns = st.columns(4)
    with kpi_columns[0]:
        _html(ui.kpi("Promos ranked", len(rankings), "#5eead4"))
    with kpi_columns[1]:
        best_score = max(totals)
        _html(ui.kpi("Best score", "{:.1f}".format(best_score), "#f472b6", best_score))
    with kpi_columns[2]:
        average_score = sum(totals) / len(totals)
        _html(ui.kpi("Average score", "{:.1f}".format(average_score), "#60a5fa", average_score))
    with kpi_columns[3]:
        _html(ui.kpi("Episodes covered", len({item.get("episode_id") for item in rankings}), "#fbbf24"))

    overview_left, overview_right = st.columns([1.4, 0.8], gap="large")
    with overview_left:
        with st.container(border=True):
            st.markdown("#### Score leaderboard")
            _html(ui.rank_chart([
                ("{} · {}".format(item.get("episode_id", ""), item.get("promo_id", "")),
                 float(item.get("total_score", 0) or 0))
                for item in rankings[:12]
            ]))
    with overview_right:
        with st.container(border=True):
            st.markdown("#### Shortlist strength profile")
            _html('<div style="display:grid;place-items:center">{}</div>'.format(
                ui.avg_profile(all_scores)))

    list_column, detail_column = st.columns([1.0, 1.0], gap="large")
    with list_column:
        st.markdown("#### Top K · rank order ({} promos)".format(len(promo_ids)))
        for promo_id in promo_ids:
            rank = ranking_by_id[promo_id]
            promo = promo_by_id.get(promo_id, {})
            scores = rank.get("scores", {})
            with st.container(border=True):
                _html(ui.promo_card_head(
                    rank.get("rank", "—"),
                    "{} · {} · {:.0f}s · {} segment(s)".format(
                        rank.get("episode_id", ""), promo_id,
                        promo.get("duration_seconds", 0), len(promo.get("segments", []))),
                    float(rank.get("total_score", 0) or 0), "promo_" + str(promo_id),
                ))
                _html(ui.micro_bars(scores))
                is_selected = promo_id == selected_id
                if st.button(
                    "Viewing details" if is_selected else "View promo details",
                    key="open_output_" + str(promo_id),
                    type="primary" if is_selected else "secondary",
                    width="stretch",
                ):
                    st.session_state["selected_output_promo_id"] = promo_id
                    st.rerun()

    with detail_column:
        rank = ranking_by_id[selected_id]
        promo = promo_by_id.get(selected_id, {})
        scores = rank.get("scores", {})
        total_score = float(rank.get("total_score", 0) or 0)
        with st.container(border=True):
            st.markdown("### Promo {} details".format(rank.get("rank", "—")))
            st.caption("{} · {} · {:.1f}s".format(
                rank.get("episode_id", ""), selected_id,
                promo.get("duration_seconds", 0)))
            ring_column, radar_column = st.columns([0.8, 1.2])
            with ring_column:
                _html('<div style="display:grid;place-items:center;margin-top:10px">{}</div>'.format(
                    ui.ring(total_score, 100, 150, "overall", "detail")))
            with radar_column:
                _html(ui.radar(scores, 250, "detail_radar"))
            _html(ui.dim_bars(scores))

            st.markdown("**Opening hook**")
            st.write(promo.get("hook", "—"))
            st.markdown("**Cliffhanger**")
            st.write(promo.get("cliffhanger", "—"))
            st.markdown("**Candidate explanation**")
            st.write(promo.get("explanation", "—"))

            source_episode = episode_by_id.get(rank.get("episode_id"))
            source_is_current = bool(
                source_episode
                and run_episode_hashes.get(source_episode.episode_id) == source_episode.source_sha256
            )
            blocks_by_id = ({block.block_id: (index, block)
                             for index, block in enumerate(source_episode.blocks)}
                            if source_is_current else {})
            segments = promo.get("segments", [])
            spans = []
            for segment in segments:
                start = blocks_by_id.get(segment.get("start_block_id"))
                end = blocks_by_id.get(segment.get("end_block_id"))
                if start and end:
                    spans.append((start[0], end[0]))
            if spans:
                _html(ui.segment_strip(spans, len(source_episode.blocks)))

            st.markdown("#### Selected segments ({})".format(len(segments)))
            for index, segment in enumerate(segments, 1):
                with st.container(border=True):
                    st.markdown("**Segment {} · {} → {}**".format(
                        index, segment.get("start_timestamp", "—"),
                        segment.get("end_timestamp", "—")))
                    st.caption("Blocks {} → {}".format(
                        segment.get("start_block_id", "—"),
                        segment.get("end_block_id", "—")))
                    st.write(segment.get("reason", ""))
                    start = blocks_by_id.get(segment.get("start_block_id"))
                    end = blocks_by_id.get(segment.get("end_block_id"))
                    if start and end:
                        with st.expander("Show screenplay excerpt", expanded=False):
                            for block in source_episode.blocks[start[0]:end[0] + 1]:
                                speaker = "{}: ".format(block.speaker) if block.speaker else ""
                                st.write("{} · {}{}".format(
                                    format_timestamp(block.start_seconds), speaker, block.text))
                    elif input_records:
                        st.caption("Source excerpt is unavailable for the current input version.")

            st.markdown("**Why it ranked here**")
            st.write(rank.get("ranking_reason", "—"))
            st.markdown("**Scoring justification**")
            st.write(scores.get("justification", "—"))
            weaknesses = rank.get("weaknesses") or scores.get("weaknesses") or []
            if weaknesses:
                st.warning("Review points: " + "; ".join(weaknesses))


def _display_run_history(database_path):
    path = Path(database_path)
    if not path.exists():
        st.info("Run history will appear after the first inference run.")
        return
    try:
        with sqlite3.connect(str(path)) as connection:
            rows = connection.execute(
                "SELECT run_id,started_at,status,summary_json FROM execution_runs "
                "ORDER BY started_at DESC LIMIT 20").fetchall()
        history, chart_rows = [], []
        for run_id, started, status, summary_json in rows:
            summary = json.loads(summary_json or "{}")
            history.append({"Run": run_id, "Started": started, "Status": status,
                            "Episodes": summary.get("total_episodes_processed", 0),
                            "Valid promos": summary.get("valid_promos", 0),
                            "Ranked": summary.get("ranked_promos", 0)})
            chart_rows.append((
                run_id,
                summary.get("valid_promos", 0),
                summary.get("ranked_promos", 0),
            ))
        if history:
            completed = sum(
                1 for item in history
                if str(item["Status"]).lower() in ("completed", "complete", "success")
            )
            failed = sum(1 for item in history if str(item["Status"]).lower() == "failed")
            other = len(history) - completed - failed
            chart_column, status_column = st.columns([1.5, 0.8], gap="large")
            with chart_column:
                with st.container(border=True):
                    st.markdown("#### Promos per run")
                    _html(ui.history_chart(list(reversed(chart_rows))))
            with status_column:
                with st.container(border=True):
                    st.markdown("#### Run outcomes")
                    _html(ui.status_donut([
                        ("Completed", completed, "#5eead4"),
                        ("Other", other, "#fbbf24"),
                        ("Failed", failed, "#f472b6"),
                    ]))
            st.dataframe(history, hide_index=True)
        else:
            st.info("Run history is empty.")
    except sqlite3.Error as exc:
        st.error("Could not read the run database: {}".format(exc))


def _clear_run_history(database_path):
    """Delete only the rows rendered in the Run history view."""
    path = Path(database_path)
    if not path.exists():
        return 0
    with sqlite3.connect(str(path)) as connection:
        result = connection.execute("DELETE FROM execution_runs")
        return max(0, result.rowcount)


def _reset_run_history_callback():
    """Handle the user-confirmed destructive action before widgets render."""
    if st.session_state.get("inference_running", False):
        st.session_state["run_history_reset_error"] = (
            "Wait for inference to finish before clearing run history."
        )
        return
    try:
        removed = _clear_run_history(settings.database_path)
    except sqlite3.Error as exc:
        st.session_state["run_history_reset_error"] = (
            "Could not reset run history: {}".format(exc)
        )
        return
    st.session_state["run_history_reset_message"] = (
        "Cleared {} run-history record(s). Ranked outputs and cached inputs were kept.".format(removed)
    )
    st.session_state["confirm_run_history_reset"] = False


st.sidebar.caption("PROMOFINDER STUDIO")
st.sidebar.markdown("## Workspace setup")
source_mode, input_records, input_errors = _read_inputs()
if input_records:
    labels = [record["label"] for record in input_records]
    source_signature = hashlib.sha1("\n".join(labels).encode("utf-8")).hexdigest()[:10]
    mode_key = "library" if source_mode == "Input library" else "uploads"
    selected_labels = st.sidebar.multiselect(
        "Files to include in the run", labels, default=labels[:1],
        key="included_files_{}_{}".format(mode_key, source_signature),
        help="Only checked files are passed to inference and ranking.",
        disabled=st.session_state.get("inference_running", False),
    )
    selected_label_set = set(selected_labels)
    selected_records = [record for record in input_records if record["label"] in selected_label_set]
else:
    selected_records = []
    st.sidebar.info("Choose project scripts or upload TXT files to begin.")

top_k_default = settings.top_k
top_k_max = max(50, top_k_default)
if st.session_state.get("_top_k_config_default") != top_k_default:
    st.session_state["_top_k_config_default"] = top_k_default
    st.session_state["top_k_slider"] = top_k_default
requested_top_k = st.sidebar.slider(
    "Shortlist size", min_value=0, max_value=top_k_max,
    key="top_k_slider", disabled=st.session_state["inference_running"],
    help=("Default is set by PROMOFINDER_TOP_K in .env. The effective shortlist "
          "is capped at the number of selected files and is locked during inference."),
)
if st.session_state["inference_running"]:
    requested_top_k = st.session_state.get("locked_top_k", requested_top_k)
    effective_top_k = st.session_state.get(
        "locked_effective_top_k", min(requested_top_k, len(selected_records)))
else:
    effective_top_k = min(requested_top_k, len(selected_records))
force_reprocess = st.sidebar.checkbox(
    "Force fresh generation", value=False,
    disabled=st.session_state["inference_running"],
    help="Bypass saved episode and API response results for this API-backed run.",
)

_html(ui.hero())

inference_tab, output_tab, history_tab = st.tabs(
    [":material/rocket_launch: Inference studio", ":material/leaderboard: Output",
     ":material/history: Run history"])

with inference_tab:
    st.subheader("Run inference on selected files")
    st.caption("Choose episodes from the input library or drag in TXT files, then run the API pipeline.")
    if st.session_state["inference_running"]:
        st.info("Inference is running. The selected files and effective shortlist are locked at Top {}.".format(
            effective_top_k))
    run_error = st.session_state.pop("inference_error", None)
    if run_error:
        st.error("Inference could not start: {}".format(run_error))
    selection_columns = st.columns(3)
    with selection_columns[0]:
        _html(ui.kpi(
            "Files selected", len(selected_records), "#5eead4",
            100.0 * len(selected_records) / max(1, len(input_records)),
        ))
    with selection_columns[1]:
        _html(ui.kpi(
            "Effective shortlist", "Top {}".format(effective_top_k), "#a78bfa",
            100.0 * effective_top_k / max(1, len(selected_records)),
        ))
    with selection_columns[2]:
        _html(ui.kpi("Available files", len(input_records), "#60a5fa"))
    with st.expander("Files included in this run", expanded=False):
        if selected_records:
            for record in selected_records:
                st.write(record["label"])
        else:
            st.caption("Select at least one screenplay in the sidebar.")
    if effective_top_k < requested_top_k:
        st.caption("Requested Top {} is capped at Top {} because {} file(s) are selected.".format(
            requested_top_k, effective_top_k, len(selected_records)))
    missing_api_settings = []
    for prefix, model in (("CANDIDATE", settings.candidate_model),
                          ("RANKING", settings.ranking_model)):
        if model.provider not in ("openai", "openai_compatible"):
            missing_api_settings.append(prefix + "_PROVIDER must be an API provider")
        if not model.model:
            missing_api_settings.append(prefix + "_MODEL")
        if not model.base_url:
            missing_api_settings.append(prefix + "_BASE_URL")
        if not model.api_key:
            missing_api_settings.append(prefix + "_API_KEY or LLM_KEY")
    models_ready = not missing_api_settings
    if missing_api_settings:
        st.warning("API mode is enabled. Missing configuration: {}. Set these in .env before running.".format(
            ", ".join(missing_api_settings)))
    run_clicked = st.button(
        "Run selected files", type="primary", width="stretch",
        key="run_selected_files",
        disabled=(not selected_records or not models_ready
                  or st.session_state["inference_running"]),
    )
    st.caption("Generation → validation → semantic review → ranking")

    if run_clicked:
        _begin_inference(len(selected_records))
        st.rerun()

    if st.session_state.pop("inference_requested", False):
        try:
            with st.status("Preparing inference", expanded=True) as status_box:
                with tempfile.TemporaryDirectory(prefix="promofinder-ui-") as temp_dir:
                    input_dir = _materialize_records(selected_records, temp_dir)
                    result = _run_with_progress(
                        settings, input_dir, effective_top_k, force_reprocess)
                st.session_state["last_run_result"] = result
                st.session_state["last_run_top_k"] = effective_top_k
                st.session_state["last_run_episode_hashes"] = {
                    record["episode"].episode_id: record["episode"].source_sha256
                    for record in selected_records
                }
                st.session_state.pop("selected_output_promo_id", None)
                state = "error" if result["status"] == "failed" else "complete"
                status_box.update(label="Inference {}".format(result["status"].replace("_", " ")),
                                  state=state, expanded=False)
            st.success("Run {} · {} valid promo(s) · {} ranked".format(
                result["run_id"], result["summary"].get("valid_promos", 0),
                result["summary"].get("ranked_promos", 0)))
        except Exception as exc:
            st.session_state["inference_error"] = str(exc)
        finally:
            st.session_state["inference_running"] = False
            st.session_state.pop("locked_top_k", None)
            st.session_state.pop("locked_effective_top_k", None)
        st.rerun()

    latest = st.session_state.get("last_run_result")
    if latest:
        summary = latest.get("summary", {})
        episodes = summary.get("total_episodes_processed", 0)
        valid = summary.get("valid_promos", 0)
        review = summary.get("failed_episodes", 0)
        retries = summary.get("candidate_retries", 0)
        result_left, result_middle, result_right = st.columns([1, 1, 1.2], gap="large")
        with result_left:
            _html(ui.kpi("Episodes processed", episodes, "#60a5fa"))
            _html(ui.kpi("Candidate retries", retries, "#fbbf24", min(100, retries * 10)))
        with result_middle:
            _html(ui.kpi("Validated promos", valid, "#5eead4"))
            _html(ui.kpi("Needs review", review, "#f472b6", 100.0 * review / max(1, episodes)))
        with result_right:
            with st.container(border=True):
                st.markdown("#### Episode outcome")
                _html(ui.status_donut([
                    ("Passed", max(0, episodes - review), "#5eead4"),
                    ("Needs review", review, "#f472b6"),
                ]))
        if latest.get("status") == "pending_responses":
            st.error("This run used a file-based model configuration. Set both model providers to an API provider in .env, then run again.")
        elif latest.get("status") == "failed":
            st.error("This run stopped with an error. See the execution report for details.")

with output_tab:
    st.subheader("Ranked promo output")
    latest = st.session_state.get("last_run_result")
    if latest:
        st.caption("Run {} · status: {} · episodes processed: {}".format(
            latest.get("run_id", "—"), latest.get("status", "—"),
            latest.get("summary", {}).get("total_episodes_processed", 0)))
    output_top_k = st.session_state.get("last_run_top_k", effective_top_k)
    st.markdown("Top {} promos, ordered by their overall ranking score. Select a promo card to inspect its segments and scoring details.".format(
        output_top_k))
    _display_ranked_results(
        settings.output_dir, input_records,
        st.session_state.get("last_run_episode_hashes", {}),
        output_top_k,
    )

with history_tab:
    st.subheader("Recent pipeline runs")
    st.caption("Inspect recent API-run states and output counts stored in the local SQLite database.")
    reset_message = st.session_state.pop("run_history_reset_message", None)
    reset_error = st.session_state.pop("run_history_reset_error", None)
    if reset_message:
        st.success(reset_message, icon=":material/check_circle:")
    if reset_error:
        st.error(reset_error, icon=":material/error:")
    _display_run_history(settings.database_path)
    with st.container(border=True):
        st.markdown("#### Reset run history")
        st.caption("This removes only the displayed local run-history records. It keeps inputs, outputs, reports, and API logs.")
        confirmed = st.checkbox(
            "I understand this cannot be undone.",
            key="confirm_run_history_reset",
            disabled=st.session_state["inference_running"],
        )
        st.button(
            "Reset run history",
            key="reset_run_history",
            icon=":material/delete_forever:",
            type="secondary",
            disabled=(not confirmed or st.session_state["inference_running"]),
            on_click=_reset_run_history_callback,
        )
