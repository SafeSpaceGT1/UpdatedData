import streamlit as st
import matplotlib.pyplot as plt
from collections import Counter
from io import BytesIO
import plotly.express as px
import pandas as pd
import json
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Authenticate and connect to Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
gc = gspread.authorize(credentials)

# Open or create a sheet
sheet_name = "Tag_Distribution_Chart"
try:
    worksheet = gc.open(sheet_name).sheet1
except:
    sh = gc.create(sheet_name)
    worksheet = sh.get_worksheet(0)
    worksheet.append_row(["Category", "Count"])

# Dynamically load tags from saved_datasets folder
import glob

# Extract tags from dataset files
all_tags = []
dataset_files = glob.glob("saved_datasets/*.jsonl")
for file_path in dataset_files:
    with open(file_path, "r") as f:
        for line in f:
            try:
                entry = json.loads(line)
                if "tag" in entry:
                    all_tags.append(entry["tag"])
            except:
                continue

# Count tags
tag_counts = Counter(all_tags)

# Ensure user_id is defined before saving category mapping
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

data = pd.DataFrame({
    'Tag': list(tag_counts.keys()),
    'Count': list(tag_counts.values())
})
data['Category'] = data['Tag'].map(category_mapping).fillna('Other')

# Update Google Sheet
worksheet.clear()
worksheet.append_row(["Tag", "Count"])
for index, row in data.iterrows():
    worksheet.append_row([row['Category'], row['Count']])

# 🆕 Move user_id definition to the top
user_id = st.text_input("Enter your user ID to load/save settings:", value="default")

# User ID based settings
user_id = st.text_input("Enter your user ID to load/save settings:", value="default")
settings_file = f"chart_settings_{user_id}.json"

def load_settings():
    if os.path.exists(settings_file):
        with open(settings_file, "r") as f:
            return json.load(f)
    return {
        "chart_title": "Tag Distribution",
        "width": 700,
        "height": 500,
        "font_size": 16,
        "title_align": "center",
        "style_preset": "Pastel"
    }

def save_settings(settings):
    with open(settings_file, "w") as f:
        json.dump(settings, f)

# Load existing or default settings
saved_settings = load_settings()

# User selects chart type
chart_type = st.selectbox("Select chart type:", ["Pie Chart", "Bar Chart"])

# User inputs customizations
chart_title = st.text_input("Enter chart title:", value=saved_settings["chart_title"])
width = st.slider("Chart Width (px)", min_value=400, max_value=1200, value=saved_settings["width"], step=100)
height = st.slider("Chart Height (px)", min_value=300, max_value=1000, value=saved_settings["height"], step=100)
font_size = st.slider("Font Size", min_value=10, max_value=30, value=saved_settings["font_size"], step=1)
title_align = st.selectbox("Title Alignment", ["center", "left", "right"], index=["center", "left", "right"].index(saved_settings["title_align"]))

# User selects style preset
style_preset = st.selectbox("Color Style Preset", ["Pastel", "Bold", "Professional"], index=["Pastel", "Bold", "Professional"].index(saved_settings["style_preset"]))

# Save updated settings
if st.button("Save My Chart Settings"):
    new_settings = {
        "chart_title": chart_title,
        "width": width,
        "height": height,
        "font_size": font_size,
        "title_align": title_align,
        "style_preset": style_preset
    }
    save_settings(new_settings)
    st.success("Settings saved!")

# Set color palette based on preset
if style_preset == "Pastel":
    color_sequence = px.colors.qualitative.Pastel
elif style_preset == "Bold":
    color_sequence = px.colors.qualitative.Bold
else:
    color_sequence = px.colors.qualitative.Safe

fig = None

if chart_type == "Pie Chart":
    fig = px.pie(data, names='Category', values='Count', hover_name='Tag', title=chart_title,
                 color_discrete_sequence=color_sequence, hover_data=['Count'],
                 width=width, height=height)
else:
    fig = px.bar(data, x='Category', y='Count', hover_name='Tag', title=chart_title,
                 color='Tag', text='Count', color_discrete_sequence=color_sequence,
                 hover_data={'Tag': True, 'Count': True}, width=width, height=height)

fig.update_layout(
    title_font_size=font_size,
    title_x={"center": 0.5, "left": 0.0, "right": 1.0}[title_align]
)

st.plotly_chart(fig)

# Download chart as image or PDF
img_buffer_png = BytesIO()
fig.write_image(img_buffer_png, format='png')
st.download_button("Download Chart as PNG", img_buffer_png.getvalue(), file_name="tag_chart.png", mime="image/png")

img_buffer_pdf = BytesIO()
fig.write_image(img_buffer_pdf, format='pdf')
st.download_button("Download Chart as PDF", img_buffer_pdf.getvalue(), file_name="tag_chart.pdf", mime="application/pdf")
