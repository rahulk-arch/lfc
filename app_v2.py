import streamlit as st
from automation_v2 import run_automation
import pandas as pd

st.title("NGO Finder")

with st.form("search_form"):
    category = st.text_input("Category", placeholder="Education NGO")
    location = st.text_input("Location", placeholder="New Delhi")
    search_entity = st.selectbox("Search Entity", ["NGO", "School"])
    target_count = st.slider("Target number of organizations", 10, 200, 50)
    submitted = st.form_submit_button("Run Search")

if submitted:
    if not category or not location or not search_entity:
        st.error("Please fill in all fields.")
    else:
        status_box = st.empty()
        progress_bar = st.progress(0)

        def update_progress(tier, batch_orgs, total_orgs, queries_run, done=False):
            pct = min(total_orgs / target_count, 1.0)
            progress_bar.progress(pct)
            status_box.markdown(
                f"**Tier:** {tier}  \n"
                f"**Queries run so far:** {queries_run}  \n"
                f"**New Org this batch:** {batch_orgs}  \n"
                f"**Total Organizations Found:** {total_orgs}/{target_count}"
            )

        results = run_automation(
            category=category,
            location=location,
            search_entity=search_entity,
            target_count=target_count,
            progress_callback=update_progress
        )

        progress_bar.progress(1.0)

        if not results:
            st.warning("No organizations found. Try a broader category or location.")
        else:
            st.success(f"Found {len(results)} organizations!")

            df = pd.DataFrame(results)
            st.dataframe(df, use_container_width=True)

            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="Download as CSV",
                data=csv,
                file_name=f"{category}_{location}_organizations.csv",
                mime="text/csv"
            )