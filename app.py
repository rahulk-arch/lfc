import streamlit as st
import pandas as pd
import threading
from automation_v2 import run_automation

st.title("LFC — Organization Discovery")

# --- Persistent state across reruns ---
if "running" not in st.session_state:
    st.session_state.running = False
if "shared" not in st.session_state:
    st.session_state.shared = None   # will hold the plain dict while a search runs

# --- Input form ---
category = st.text_input("Category", placeholder="e.g. Child Welfare")
location = st.text_input("Location", placeholder="e.g. New Delhi")
search_entity = st.selectbox("Search Entity", ["NGO", "School"])
target_count = st.number_input("Target Organizations", min_value=10, max_value=250, value=50, step=5)

col1, col2 = st.columns(2)
start_clicked = col1.button("▶ Start Search", disabled=st.session_state.running)
stop_clicked = col2.button("⏹ Stop", disabled=not st.session_state.running)

# --- Start ---
if start_clicked and category and location and search_entity:
    st.session_state.running = True

    # Plain dict — NOT st.session_state — safe to mutate from a background thread
    shared_dict = {
        "total_found": 0,
        "results": [],
        "current_tier": "",
        "done": False,
        "stop_event": threading.Event(),
    }
    st.session_state.shared = shared_dict

    def progress_callback(tier, total_orgs, organizations, done):
        # writes to the plain dict, not st.session_state — safe from a thread
        shared_dict["current_tier"] = tier
        shared_dict["total_found"] = total_orgs
        shared_dict["results"] = organizations
        shared_dict["done"] = done

    def worker():
        run_automation(
            category=category,
            location=location,
            search_entity=search_entity,
            target_count=target_count,
            progress_callback=progress_callback,
            stop_event=shared_dict["stop_event"]
        )

    threading.Thread(target=worker, daemon=True).start()

# --- Stop ---
if stop_clicked and st.session_state.shared is not None:
    st.session_state.shared["current_tier"] = "Stopping..."
    st.session_state.shared["stop_event"].set()

# --- Live display — main thread reads the plain dict, safe to touch st.session_state here ---
shared = st.session_state.shared

if shared is not None:
    st.subheader("Organizations Found")
    st.markdown(f"### {shared['total_found']} / {target_count}")
    st.progress(min(shared["total_found"] / target_count, 1.0))

    if st.session_state.running:
        with st.status("Searching...", state="running", expanded=False):
            st.write(f"Current Tier: {shared['current_tier']}")
    else:
        if shared["results"]:
            with st.status("Search complete", state="complete", expanded=False):
                st.write(f"Found {len(shared['results'])} organizations")

    if shared["results"]:
        st.markdown("**Organization List**")
        for org in shared["results"]:
            st.write(f"- {org.get('Organization', 'Unknown')}")

    if shared["done"]:
        st.session_state.running = False

# --- Download once finished ---
if not st.session_state.running and shared is not None and shared["results"]:
    st.success(f"✅ Found {len(shared['results'])} organizations")
    df = pd.DataFrame(shared["results"])
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", data=csv, file_name="organizations.csv", mime="text/csv")

# --- Keep refreshing the page while the search is running ---
if st.session_state.running:
    import time
    time.sleep(1)
    st.rerun()