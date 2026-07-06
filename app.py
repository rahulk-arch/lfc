import streamlit as st
import pandas as pd
import threading
from automation_v2 import run_automation

st.title("LFC — Organization Discovery")

# --- Persistent state across reruns ---
if "running" not in st.session_state:
    st.session_state.running = False
if "stop_event" not in st.session_state:
    st.session_state.stop_event = threading.Event()
if "results" not in st.session_state:
    st.session_state.results = []
if "total_found" not in st.session_state:
    st.session_state.total_found = 0
if "current_tier" not in st.session_state:
    st.session_state.current_tier = ""
if "thread" not in st.session_state:
    st.session_state.thread = None

# --- Input form ---
category = st.text_input("Category", placeholder="e.g. Child Welfare")
location = st.text_input("Location", placeholder="e.g. New Delhi")
search_entity = st.selectbox("Search Entity", ["NGO", "School"])
target_count = st.number_input("Target Organizations", min_value=10, max_value=250, value=50, step=5)

col1, col2 = st.columns(2)
start_clicked = col1.button("▶ Start Search", disabled=st.session_state.running)
stop_clicked = col2.button("⏹ Stop", disabled=not st.session_state.running)

# --- Callback, called from the background thread ---
def update_progress(tier, total_orgs, organizations, done):
    st.session_state.current_tier = tier
    st.session_state.total_found = total_orgs
    st.session_state.results = organizations
    if done:
        st.session_state.running = False

# --- Start ---
if start_clicked and category and location and search_entity:
    st.session_state.running = True
    st.session_state.results = []
    st.session_state.total_found = 0
    st.session_state.stop_event = threading.Event()

    def worker():
        run_automation(
            category=category,
            location=location,
            search_entity=search_entity,
            target_count=target_count,
            progress_callback=update_progress,
            stop_event=st.session_state.stop_event
        )

    st.session_state.thread = threading.Thread(target=worker, daemon=True)
    st.session_state.thread.start()

# --- Stop ---
if stop_clicked:
    st.session_state.current_tier = "Stopping..."
    st.session_state.stop_event.set()

# --- Live display ---
if st.session_state.running or st.session_state.results:
    st.subheader("Organizations Found")
    st.markdown(f"### {st.session_state.total_found} / {target_count}")
    st.progress(min(st.session_state.total_found / target_count, 1.0))

    if st.session_state.running:
        with st.status("Searching...", state="running", expanded=False):
            st.write(f"Current Tier: {st.session_state.current_tier}")
    else:
        if st.session_state.results:
            with st.status("Search complete", state="complete", expanded=False):
                st.write(f"Found {len(st.session_state.results)} organizations")

    if st.session_state.results:
        names = [org.get("Organization", "Unknown") for org in st.session_state.results]
        st.markdown("**Organization List**")
        for name in names:
            st.write(f"- {name}")

# --- Download once finished ---
if not st.session_state.running and st.session_state.results:
    st.success(f"✅ Found {len(st.session_state.results)} organizations")
    df = pd.DataFrame(st.session_state.results)
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", data=csv, file_name="organizations.csv", mime="text/csv")

# --- Keep refreshing the page while the search is running ---
if st.session_state.running:
    import time
    time.sleep(1)
    st.rerun()