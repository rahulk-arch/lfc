import streamlit as st
import pandas as pd
import threading
import time
import re
import html as html_lib
from automation_parallel import run_parallel_pipeline

# ── Page setup ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="LFC — Organization Discovery", page_icon="🔎", layout="centered")

# ── Brand styling (LFC identity: purple / orange, Baloo 2 + Nunito) ─────────
# NOTE: the light/neutral base theme itself lives in .streamlit/config.toml
# (that's what actually fixes the "black" look, since it applies to Streamlit's
# built-in widgets). This block just layers on fonts + a few custom components.
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Baloo+2:wght@500;600;700&family=Nunito:wght@400;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Nunito', sans-serif;
}
h1, h2, h3 {
    font-family: 'Baloo 2', sans-serif !important;
    color: #8B2A7A;
}
.stButton > button {
    border-radius: 8px;
    font-weight: 700;
    font-family: 'Nunito', sans-serif;
    background-color: #8B2A7A;
    color: #FFFFFF;
    border: none;
}
.stButton > button:hover {
    background-color: #6f2062;
    color: #FFFFFF;
}
.stButton > button:disabled {
    background-color: #E5DCE3;
    color: #9B8A97;
}
.stProgress > div > div > div > div {
    background-color: #F5A623;
}
.status-card {
    display: flex;
    align-items: center;
    gap: 10px;
    background: #F5EEF4;
    border-left: 4px solid #F5A623;
    border-radius: 8px;
    padding: 12px 16px;
    margin: 6px 0 18px 0;
    font-weight: 600;
    color: #4A2340;
}
.org-card {
    background: #FFFFFF;
    border: 1px solid #ECE3EA;
    border-radius: 10px;
    padding: 10px 14px;
    margin-bottom: 8px;
}
.org-card a {
    color: #8B2A7A;
    font-weight: 700;
    text-decoration: none;
}
.org-card a:hover {
    text-decoration: underline;
}
</style>
""", unsafe_allow_html=True)

st.title("LFC — Organization Discovery")

# ── Persistent state ──────────────────────────────────────────────────────────
if "running" not in st.session_state:
    st.session_state.running = False
if "shared" not in st.session_state:
    st.session_state.shared = None

# ── Inputs ────────────────────────────────────────────────────────────────────
category      = st.text_input("Category",      value="Child",              disabled=st.session_state.running)
location      = st.text_input("Location",      placeholder="e.g. New Delhi", disabled=st.session_state.running)
search_entity = st.text_input("Search Entity", placeholder="e.g. NGO/NPO",  disabled=st.session_state.running)
target_count  = st.number_input("Target Organizations", min_value=10, max_value=500, value=50, step=10,
                                 disabled=st.session_state.running)

col1, col2 = st.columns(2)
start_clicked = col1.button("▶ Start Search", disabled=st.session_state.running, use_container_width=True)
stop_clicked  = col2.button("⏹ Stop",         disabled=not st.session_state.running, use_container_width=True)

# ── Start ─────────────────────────────────────────────────────────────────────
if start_clicked and category and location and search_entity:
    st.session_state.running = True

    shared_dict = {
        "stage":       "Starting...",
        "total_found": 0,
        "results":     [],
        "done":        False,
        "cancelled":   False,
        "stop_event":  threading.Event(),
    }
    st.session_state.shared = shared_dict

    def progress_callback(stage, total_orgs, organizations, done):
        shared_dict["stage"]       = stage
        shared_dict["total_found"] = total_orgs
        shared_dict["results"]     = organizations
        shared_dict["done"]        = done

    def worker():
        run_parallel_pipeline(
            category=category,
            location=location,
            search_entity=search_entity,
            target_count=int(target_count),
            progress_callback=progress_callback,
            stop_event=shared_dict["stop_event"],
        )

    threading.Thread(target=worker, daemon=True).start()

# ── Stop ──────────────────────────────────────────────────────────────────────
# Fix: previously this only *signalled* the worker thread and then waited for
# it to set done=True before the UI would ever unlock. If the pipeline wasn't
# checking stop_event in its loop, the button looked "broken" because the app
# stayed stuck on "Stopping...". Now the UI unblocks immediately on click:
# Start re-enables, results-so-far become downloadable, and the loop stops
# polling for updates. stop_event is still set, so if run_parallel_pipeline
# checks it between iterations it will genuinely stop making further
# requests — but that check has to exist inside automation_parallel.py itself.
if stop_clicked and st.session_state.shared is not None:
    st.session_state.shared["stop_event"].set()
    st.session_state.shared["stage"] = "Stopped by user"
    st.session_state.shared["cancelled"] = True
    st.session_state.running = False

# ── Live display ──────────────────────────────────────────────────────────────
shared = st.session_state.shared

if shared is not None:
    if st.session_state.running:
        icon, text = "🔄", shared["stage"]
    elif shared.get("cancelled"):
        icon, text = "⏹", f"Stopped — {shared['total_found']} organizations collected before stopping"
    else:
        icon, text = "✅", "Search complete"

    st.markdown(f'<div class="status-card"><span>{icon}</span><span>{text}</span></div>', unsafe_allow_html=True)

    st.markdown(f"### {shared['total_found']} / {target_count}")
    st.progress(min(shared["total_found"] / max(target_count, 1), 1.0))

    if shared["results"]:
        st.markdown("**Organization List**")
        for org in shared["results"]:
            name = org.get("Title") or org.get("Organization", "Unknown")
            url  = org.get("Homepage") or org.get("URL", "")
            link = f'<a href="{url}" target="_blank">{name}</a>' if url else name
            st.markdown(f'<div class="org-card">{link}</div>', unsafe_allow_html=True)

    if shared["done"]:
        st.session_state.running = False

# ── Export cleanup ──────────────────────────────────────────────────────────
# Fix: the CSV was showing raw scraped HTML instead of clean text. This
# strips any markup out of text fields and drops obviously "raw" columns
# before export. If a specific field is still messy after this, the actual
# extraction likely needs a fix inside automation_parallel.py itself (e.g.
# storing soup.get_text() instead of the raw response) — happy to patch
# that directly if you share that file.
def _clean_text(value):
    if not isinstance(value, str):
        return value
    if "<" in value and ">" in value:
        value = re.sub(r"<[^>]+>", " ", value)
    value = html_lib.unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def prepare_export_df(results):
    df = pd.DataFrame(results)

    drop_cols = [c for c in df.columns if any(k in c.lower() for k in ("raw", "html", "source_code", "page_content"))]
    df = df.drop(columns=drop_cols, errors="ignore")

    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].map(_clean_text)

    preferred = ["Title", "Organization", "Homepage", "URL", "Category", "Location", "Email", "Phone", "Description"]
    ordered = [c for c in preferred if c in df.columns] + [c for c in df.columns if c not in preferred]
    return df[ordered]


# ── Download ──────────────────────────────────────────────────────────────────
if not st.session_state.running and shared is not None and shared["results"]:
    if shared.get("cancelled"):
        st.warning(f"Stopped early — {len(shared['results'])} organizations found so far")
    else:
        st.success(f"Found {len(shared['results'])} organizations")

    df  = prepare_export_df(shared["results"])
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇ Download CSV",
        data=csv,
        file_name="organizations.csv",
        mime="text/csv"
    )

# ── Auto-refresh while running ────────────────────────────────────────────────
if st.session_state.running:
    time.sleep(1)
    st.rerun()