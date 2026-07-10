import streamlit as st
import pandas as pd
import threading
from automation_parallel import run_parallel_pipeline

st.title("LFC — Organization Discovery")

# ── Persistent state ──────────────────────────────────────────────────────────
if "running" not in st.session_state:
    st.session_state.running = False
if "shared" not in st.session_state:
    st.session_state.shared = None

# ── Inputs ────────────────────────────────────────────────────────────────────
category      = st.text_input("Category",      value="Child")
location      = st.text_input("Location",      placeholder="e.g. New Delhi")
search_entity = st.text_input("Search Entity", placeholder="e.g. NGO/NPO")
target_count  = st.number_input("Target Organizations", min_value=10, max_value=500, value=50, step=10)

col1, col2 = st.columns(2)
start_clicked = col1.button("▶ Start Search", disabled=st.session_state.running)
stop_clicked  = col2.button("⏹ Stop",         disabled=not st.session_state.running)

# ── Start ─────────────────────────────────────────────────────────────────────
if start_clicked and category and location and search_entity:
    st.session_state.running = True

    shared_dict = {
        "stage":       "Starting...",
        "total_found": 0,
        "results":     [],
        "done":        False,
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
if stop_clicked and st.session_state.shared is not None:
    st.session_state.shared["stop_event"].set()
    st.session_state.shared["stage"] = "Stopping..."

# ── Live display ──────────────────────────────────────────────────────────────
shared = st.session_state.shared

if shared is not None:
    st.subheader("Organizations Found")
    st.markdown(f"### {shared['total_found']} / {target_count}")
    st.progress(min(shared["total_found"] / max(target_count, 1), 1.0))

    state = "running" if st.session_state.running else "complete"
    label = "Searching..." if st.session_state.running else "Search complete"
    with st.status(label, state=state, expanded=False):
        st.write(f"Stage: {shared['stage']}")

    if shared["results"]:
        st.markdown("**Organization List**")
        for org in shared["results"]:
            name = org.get("Title") or org.get("Organization", "Unknown")
            url  = org.get("Homepage") or org.get("URL", "")
            st.write(f"- [{name}]({url})" if url else f"- {name}")

    if shared["done"]:
        st.session_state.running = False

# ── Download ──────────────────────────────────────────────────────────────────
if not st.session_state.running and shared is not None and shared["results"]:
    st.success(f" Found {len(shared['results'])} organizations")
    df  = pd.DataFrame(shared["results"])
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇ Download CSV",
        data=csv,
        file_name="organizations.csv",
        mime="text/csv"
    )

# ── Auto-refresh while running ────────────────────────────────────────────────
if st.session_state.running:
    time = __import__("time")
    time.sleep(1)
    st.rerun()