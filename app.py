import streamlit as st
from collections import Counter
from io import BytesIO
import plotly.express as px
import pandas as pd
import json
import os

# Dynamically load tags and file sources from all JSONL files in a batch
all_tags = []
file_sources = []
entry_log = []
dataset_files = st.file_uploader("Upload one or more JSONL dataset files", type="jsonl", accept_multiple_files=True)

if dataset_files:
    for uploaded_file in dataset_files:
        filename = uploaded_file.name
        lines = uploaded_file.read().decode("utf-8").splitlines()
        for line in lines:
            try:
                entry = json.loads(line)
                if "tag" in entry:
                    all_tags.append(entry["tag"])
                    file_sources.append(filename)
                    entry_log.append({"File": filename, "Tag": entry["tag"]})
            except:
                continue

# Preview uploaded tags by file
tab1, tab2 = st.tabs(["📄 Chart", "📊 Preview Uploaded Data"])
with tab2:
    if entry_log:
        st.subheader("Uploaded Tags by File")
        df_log = pd.DataFrame(entry_log)
        st.dataframe(df_log)

        # Per-file summary
        st.subheader("Summary: Tag Counts by File")
        file_summary = df_log.groupby(["File", "Tag"]).size().reset_index(name="Count")

        # Optional filter by tag or file
        selected_tag = st.selectbox("Filter by tag (optional):", options=["All"] + sorted(df_log["Tag"].unique().tolist()))
        selected_file = st.selectbox("Filter by file (optional):", options=["All"] + sorted(df_log["File"].unique().tolist()))

        filtered_summary = file_summary.copy()
        if selected_tag != "All":
            filtered_summary = filtered_summary[filtered_summary["Tag"] == selected_tag]
        if selected_file != "All":
            filtered_summary = filtered_summary[filtered_summary["File"] == selected_file]

        st.dataframe(filtered_summary)

        # Summary chart
        if not filtered_summary.empty:
            st.subheader("Chart: Tag Counts by File")
            chart = px.bar(filtered_summary, x="Tag", y="Count", color="File", barmode="group",
                           title="Filtered Tag Counts by File", text="Count")
            st.plotly_chart(chart)

        # Download as CSV
        csv = filtered_summary.to_csv(index=False).encode('utf-8')
        st.download_button("Download Summary as CSV", csv, file_name="tag_summary_by_file.csv", mime="text/csv")

# Count tags
tag_counts = Counter(all_tags)

# Ensure user_id is defined before saving category mapping
user_id = st.text_input("Enter your user ID to load/save settings:", value="default")
category_mapping = {}
category_editor = st.expander("🔧 Customize Tag to Category Mapping")

with category_editor:
    unique_tags = sorted(set(all_tags))
    for tag in unique_tags:
        category = st.text_input(f"Category for tag '{tag}':", value=category_mapping.get(tag, "Other"), key=f"cat_{tag}")
        category_mapping[tag] = category
    if st.button("💾 Save My Category Mappings"):
        with open(f"category_mappings_{user_id}.json", "w") as f:
            json.dump(category_mapping, f)
        st.success("Category mappings saved!")
        st.dataframe(pd.DataFrame.from_dict(category_mapping, orient='index', columns=['Category']).rename_axis('Tag').reset_index())
    if os.path.exists(f"category_mappings_{user_id}.json"):
        with open(f"category_mappings_{user_id}.json", "r") as f:
            category_mapping.update(json.load(f))
        st.info("✅ Loaded saved category mappings:")
        st.dataframe(pd.DataFrame.from_dict(category_mapping, orient='index', columns=['Category']).rename_axis('Tag').reset_index())

# Build DataFrame with optional filename filtering
data = pd.DataFrame({
    'Tag': all_tags,
    'Source File': file_sources
})
data['Category'] = data['Tag'].map(category_mapping).fillna('Other')

# Optional file filter
selected_files = st.multiselect("Filter chart by uploaded file(s):", options=sorted(set(file_sources)), default=sorted(set(file_sources)))
data = data[data['Source File'].isin(selected_files)]

# Count again after filtering
tag_counts_filtered = data['Tag'].value_counts()
data_summary = pd.DataFrame({
    'Tag': tag_counts_filtered.index,
    'Count': tag_counts_filtered.values
})
data_summary['Category'] = data_summary['Tag'].map(category_mapping).fillna('Other')

# Chart settings
chart_type = st.selectbox("Select chart type:", ["Pie Chart", "Bar Chart"])
chart_title = st.text_input("Enter chart title:", value="Tag Distribution")

fig = None

if chart_type == "Pie Chart":
    fig = px.pie(data_summary, names='Category', values='Count', hover_name='Tag', title=chart_title)
else:
    fig = px.bar(data_summary, x='Category', y='Count', hover_name='Tag', title=chart_title,
                 color='Tag', text='Count')

st.plotly_chart(fig)

img_buffer_png = BytesIO()
fig.write_image(img_buffer_png, format='png')
st.download_button("Download Chart as PNG", img_buffer_png.getvalue(), file_name="tag_chart.png", mime="image/png")
