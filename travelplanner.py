import streamlit as st
import pandas as pd
from datetime import datetime, time

# --- Page Config ---
st.set_page_config(page_title="Travel Itinerary Builder", page_icon="✈️", layout="wide")

# --- Session State Initialization ---
# We use session state to keep data alive as you interact with the app
if 'bucket_list' not in st.session_state:
    st.session_state.bucket_list = []

if 'itinerary' not in st.session_state:
    st.session_state.itinerary = []

# --- Helper Functions ---
def add_to_bucket_list(place, category, notes):
    st.session_state.bucket_list.append({
        "Place": place,
        "Category": category,
        "Notes": notes,
        "id": len(st.session_state.bucket_list) # simple ID for selection
    })

def move_to_itinerary(place_index, day, time_val):
    # Get the place details
    place_data = st.session_state.bucket_list.pop(place_index)
    
    # Add schedule details
    place_data['Day'] = day
    place_data['Time'] = time_val
    
    # Add to itinerary
    st.session_state.itinerary.append(place_data)
    
    # Sort itinerary by Day then Time
    st.session_state.itinerary.sort(key=lambda x: (x['Day'], x['Time']))

# --- UI Layout ---
st.title("✈️ Dynamic Travel Itinerary Builder")
st.markdown("Use this tool to capture ideas first, then schedule them when you're ready.")

col1, col2 = st.columns([1, 2])

# ==============================
# COLUMN 1: The Idea Stage
# ==============================
with col1:
    st.header("1. Bucket List")
    st.info("Add places you want to visit here without worrying about time yet.")
    
    with st.form("add_place_form", clear_on_submit=True):
        new_place = st.text_input("Location Name", placeholder="e.g., Osaka Castle")
        new_category = st.selectbox("Category", ["📸 Sightseeing", "🍜 Food", "☕ R&R", "🛍️ Shopping", "🚶 Exploration"])
        new_notes = st.text_area("Notes", placeholder="e.g., Buy tickets in advance")
        submitted = st.form_submit_button("Add to List")
        
        if submitted and new_place:
            add_to_bucket_list(new_place, new_category, new_notes)
            st.success(f"Added {new_place}!")

    st.divider()
    
    st.subheader("📍 Unscheduled Places")
    if not st.session_state.bucket_list:
        st.write("Your bucket list is empty.")
    else:
        # Create a clearer display for selecting items
        place_names = [f"{p['Category']} {p['Place']}" for p in st.session_state.bucket_list]
        selected_place_idx = st.radio("Select a place to schedule:", range(len(st.session_state.bucket_list)), format_func=lambda x: place_names[x])
        
        # Scheduling Controls
        st.markdown("#### 📅 Schedule It")
        day_input = st.selectbox("Select Day", ["Day 1", "Day 2", "Day 3", "Day 4", "Day 5"])
        time_input = st.time_input("Select Time", value=time(9, 0))
        
        if st.button("Move to Itinerary ➡️"):
            move_to_itinerary(selected_place_idx, day_input, time_input)
            st.rerun()

# ==============================
# COLUMN 2: The Master Plan
# ==============================
with col2:
    st.header("2. Your Final Itinerary")
    
    if not st.session_state.itinerary:
        st.write("No items scheduled yet. Move items from the left to see them here.")
    else:
        # Convert to DataFrame for cleaner display
        df = pd.DataFrame(st.session_state.itinerary)
        
        # Reorder columns
        df = df[['Day', 'Time', 'Category', 'Place', 'Notes']]
        
        # Formatting for display
        # Group by Day to make it look like a real itinerary
        days = sorted(df['Day'].unique())
        
        for day in days:
            with st.expander(f"🗓️ {day}", expanded=True):
                day_data = df[df['Day'] == day]
                
                # Custom HTML/Markdown table for a "Beautiful" look
                for _, row in day_data.iterrows():
                    time_str = row['Time'].strftime("%I:%M %p")
                    st.markdown(
                        f"""
                        <div style="
                            padding: 10px; 
                            border-radius: 5px; 
                            margin-bottom: 10px; 
                            background-color: #f0f2f6; 
                            border-left: 5px solid #ff4b4b;">
                            <strong>{time_str}</strong> | {row['Category']} 
                            <h4 style="margin:0; padding-top:5px;">{row['Place']}</h4>
                            <em style="color: #555;">{row['Notes']}</em>
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )

    # Export Button (Mockup)
    if st.session_state.itinerary:
        st.divider()
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Itinerary as CSV",
            data=csv,
            file_name='my_beautiful_itinerary.csv',
            mime='text/csv',
        )
