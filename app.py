import streamlit as st
from collections import Counter
from io import BytesIO
import plotly.express as px
import pandas as pd
import json

# Upload and batch-process multiple JSONL files
st.title("🧠 Mental Health Dataset Visualizer")

all_tags = []
file_sources = []
entry_log = []

uploaded_files = st.file_uploader("Upload one or more JSONL files", type="jsonl", accept_multiple_files=True)

if uploaded_files:
    for file in uploaded_files:
        filename = file.name
        for line in file.read().decode("utf-8").splitlines():
            try:
                record = json.loads(line)
                tag = record.get("tag", None)
                if tag:
                    all_tags.append(tag)
                    file_sources.append(filename)
                    entry_log.append({"File": filename, "Tag": tag})
            except json.JSONDecodeError:
                continue

# Display charts and summary tables
if entry_log:
    tab1, tab2 = st.tabs(["📊 Chart", "📋 Summary Table"])

    df = pd.DataFrame(entry_log)
    summary = df.groupby(["File", "Tag"]).size().reset_index(name="Count")

    with tab2:
        st.subheader("🗂 Tag Summary Table")
        selected_tag = st.selectbox("Filter by tag (optional):", ["All"] + sorted(df["Tag"].unique()))
        selected_file = st.selectbox("Filter by file (optional):", ["All"] + sorted(df["File"].unique()))

        filtered = summary.copy()
        if selected_tag != "All":
            filtered = filtered[filtered["Tag"] == selected_tag]
        if selected_file != "All":
            filtered = filtered[filtered["File"] == selected_file]

        st.dataframe(filtered)

        csv = filtered.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download CSV", csv, "summary_by_file.csv", "text/csv")

    with tab1:
        st.subheader("📊 Chart View")
        if not filtered.empty:
            fig = px.bar(filtered, x="Tag", y="Count", color="File", barmode="group", text="Count")
            st.plotly_chart(fig)
            png = BytesIO()
            fig.write_image(png, format="png")
            st.download_button("⬇️ Download Chart as PNG", png.getvalue(), "chart.png", "image/png")
