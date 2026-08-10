import json
import uuid
from datetime import datetime, date, time, timedelta

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Travel Itinerary Builder", page_icon="✈️", layout="wide")

CATEGORIES = ["📸 Sightseeing", "🍜 Food", "☕ R&R", "🛍️ Shopping", "🚶 Exploration", "🚗 Transport", "🏨 Lodging"]
PRIORITIES = ["🔥 Must Do", "👍 Would Like", "🤷 Optional"]
CATEGORY_COLORS = {
    "📸 Sightseeing": "#ff4b4b",
    "🍜 Food": "#ffa421",
    "☕ R&R": "#7defa1",
    "🛍️ Shopping": "#8e7cff",
    "🚶 Exploration": "#4bb3ff",
    "🚗 Transport": "#a3a3a3",
    "🏨 Lodging": "#ff7cd1",
}

# --- Session State Initialization ---
if "trip" not in st.session_state:
    st.session_state.trip = {
        "name": "My Trip",
        "destination": "",
        "start_date": date.today(),
        "num_days": 5,
        "currency": "$",
        "budget": 0.0,
    }

if "bucket_list" not in st.session_state:
    st.session_state.bucket_list = []

if "itinerary" not in st.session_state:
    st.session_state.itinerary = []

if "packing_list" not in st.session_state:
    st.session_state.packing_list = []

if "last_deleted" not in st.session_state:
    st.session_state.last_deleted = None


# --- Helper Functions ---
def new_id():
    return uuid.uuid4().hex[:8]


def day_label(day_index):
    trip = st.session_state.trip
    d = trip["start_date"] + timedelta(days=day_index)
    return f"Day {day_index + 1} · {d.strftime('%a, %b %d')}"


def day_options():
    return list(range(st.session_state.trip["num_days"]))


def add_to_bucket_list(place, category, notes, priority, cost, duration, lat, lon):
    st.session_state.bucket_list.append({
        "id": new_id(),
        "Place": place,
        "Category": category,
        "Notes": notes,
        "Priority": priority,
        "Cost": cost,
        "Duration": duration,
        "Lat": lat,
        "Lon": lon,
    })


def find_by_id(items, item_id):
    for i, item in enumerate(items):
        if item["id"] == item_id:
            return i
    return None


def move_to_itinerary(item_id, day_index, time_val):
    idx = find_by_id(st.session_state.bucket_list, item_id)
    if idx is None:
        return
    item = st.session_state.bucket_list.pop(idx)
    item["Day"] = day_index
    item["Time"] = time_val
    st.session_state.itinerary.append(item)
    st.session_state.itinerary.sort(key=lambda x: (x["Day"], x["Time"]))


def move_to_bucket_list(item_id):
    idx = find_by_id(st.session_state.itinerary, item_id)
    if idx is None:
        return
    item = st.session_state.itinerary.pop(idx)
    item.pop("Day", None)
    item.pop("Time", None)
    st.session_state.bucket_list.append(item)


def delete_item(collection_name, item_id):
    items = st.session_state[collection_name]
    idx = find_by_id(items, item_id)
    if idx is None:
        return
    removed = items.pop(idx)
    st.session_state.last_deleted = (collection_name, removed)


def restore_last_deleted():
    if st.session_state.last_deleted is None:
        return
    collection_name, item = st.session_state.last_deleted
    st.session_state[collection_name].append(item)
    if collection_name == "itinerary":
        st.session_state.itinerary.sort(key=lambda x: (x["Day"], x["Time"]))
    st.session_state.last_deleted = None


def time_range_overlap(start_a, end_a, start_b, end_b):
    return start_a < end_b and start_b < end_a


def find_conflicts(day_index):
    day_items = [i for i in st.session_state.itinerary if i["Day"] == day_index]
    conflicts = []
    for a in range(len(day_items)):
        for b in range(a + 1, len(day_items)):
            item_a, item_b = day_items[a], day_items[b]
            start_a = datetime.combine(date.min, item_a["Time"])
            end_a = start_a + timedelta(minutes=item_a.get("Duration") or 60)
            start_b = datetime.combine(date.min, item_b["Time"])
            end_b = start_b + timedelta(minutes=item_b.get("Duration") or 60)
            if time_range_overlap(start_a, end_a, start_b, end_b):
                conflicts.append((item_a["Place"], item_b["Place"]))
    return conflicts


def export_state():
    state = {
        "trip": {**st.session_state.trip, "start_date": st.session_state.trip["start_date"].isoformat()},
        "bucket_list": st.session_state.bucket_list,
        "itinerary": [
            {**item, "Time": item["Time"].strftime("%H:%M")} for item in st.session_state.itinerary
        ],
        "packing_list": st.session_state.packing_list,
    }
    return json.dumps(state, indent=2)


def import_state(raw):
    data = json.loads(raw)
    trip = data["trip"]
    trip["start_date"] = date.fromisoformat(trip["start_date"])
    st.session_state.trip = trip
    st.session_state.bucket_list = data.get("bucket_list", [])
    itinerary = data.get("itinerary", [])
    for item in itinerary:
        item["Time"] = datetime.strptime(item["Time"], "%H:%M").time()
    st.session_state.itinerary = itinerary
    st.session_state.packing_list = data.get("packing_list", [])


def ics_escape(text):
    return str(text).replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;").replace("\n", "\\n")


def export_ics():
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Travel Itinerary Builder//EN"]
    trip = st.session_state.trip
    for item in st.session_state.itinerary:
        start_dt = datetime.combine(trip["start_date"] + timedelta(days=item["Day"]), item["Time"])
        end_dt = start_dt + timedelta(minutes=item.get("Duration") or 60)
        lines += [
            "BEGIN:VEVENT",
            f"UID:{item['id']}@travel-itinerary-builder",
            f"DTSTART:{start_dt.strftime('%Y%m%dT%H%M%S')}",
            f"DTEND:{end_dt.strftime('%Y%m%dT%H%M%S')}",
            f"SUMMARY:{ics_escape(item['Category'])} {ics_escape(item['Place'])}",
            f"DESCRIPTION:{ics_escape(item.get('Notes') or '')}",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return "\n".join(lines)


def export_markdown():
    trip = st.session_state.trip
    lines = [f"# {trip['name']}", f"**Destination:** {trip['destination']}", ""]
    for day_index in day_options():
        day_items = [i for i in st.session_state.itinerary if i["Day"] == day_index]
        if not day_items:
            continue
        lines.append(f"## {day_label(day_index)}")
        for item in sorted(day_items, key=lambda x: x["Time"]):
            cost_str = f" — {trip['currency']}{item['Cost']:.2f}" if item.get("Cost") else ""
            lines.append(f"- **{item['Time'].strftime('%I:%M %p')}** {item['Category']} {item['Place']}{cost_str}")
            if item.get("Notes"):
                lines.append(f"  - _{item['Notes']}_")
        lines.append("")
    return "\n".join(lines)


# --- Sidebar: Trip Settings & Data Management ---
with st.sidebar:
    st.header("🧭 Trip Settings")
    trip = st.session_state.trip
    trip["name"] = st.text_input("Trip Name", value=trip["name"])
    trip["destination"] = st.text_input("Destination", value=trip["destination"])
    trip["start_date"] = st.date_input("Start Date", value=trip["start_date"])
    trip["num_days"] = st.number_input("Number of Days", min_value=1, max_value=60, value=trip["num_days"])
    trip["currency"] = st.text_input("Currency Symbol", value=trip["currency"], max_chars=3)
    trip["budget"] = st.number_input("Total Budget", min_value=0.0, value=float(trip["budget"]), step=50.0)

    days_until = (trip["start_date"] - date.today()).days
    if days_until > 0:
        st.info(f"🗓️ {days_until} days until departure!")
    elif days_until == 0:
        st.success("✈️ Trip starts today!")
    else:
        st.caption(f"Trip started {-days_until} days ago.")

    st.divider()
    st.header("💾 Save / Load")
    st.download_button(
        "Export Trip (JSON)", data=export_state(), file_name=f"{trip['name'] or 'trip'}.json", mime="application/json"
    )
    uploaded = st.file_uploader("Import Trip (JSON)", type="json")
    if uploaded is not None and st.button("Load Imported Trip"):
        import_state(uploaded.getvalue().decode("utf-8"))
        st.success("Trip loaded!")
        st.rerun()

    if st.session_state.last_deleted is not None:
        st.divider()
        if st.button("↩️ Undo Last Delete"):
            restore_last_deleted()
            st.rerun()


st.title("✈️ Dynamic Travel Itinerary Builder")
st.markdown(f"**{trip['name']}** — {trip['destination'] or 'Destination TBD'}")

tab_plan, tab_itinerary, tab_budget, tab_packing, tab_stats = st.tabs(
    ["📋 Plan", "🗺️ Itinerary", "💰 Budget", "🎒 Packing List", "📊 Stats"]
)

# ==============================
# TAB: PLAN (Bucket List + Scheduling)
# ==============================
with tab_plan:
    col1, col2 = st.columns([1, 1])

    with col1:
        st.header("Bucket List")
        st.caption("Add places you want to visit here without worrying about time yet.")

        with st.form("add_place_form", clear_on_submit=True):
            new_place = st.text_input("Location Name", placeholder="e.g., Osaka Castle")
            new_category = st.selectbox("Category", CATEGORIES)
            new_priority = st.selectbox("Priority", PRIORITIES)
            c1, c2 = st.columns(2)
            new_cost = c1.number_input("Est. Cost", min_value=0.0, step=1.0)
            new_duration = c2.number_input("Duration (min)", min_value=0, step=15, value=60)
            c3, c4 = st.columns(2)
            new_lat = c3.number_input("Latitude (optional)", value=0.0, format="%.6f")
            new_lon = c4.number_input("Longitude (optional)", value=0.0, format="%.6f")
            new_notes = st.text_area("Notes", placeholder="e.g., Buy tickets in advance")
            submitted = st.form_submit_button("Add to List")

            if submitted and new_place:
                add_to_bucket_list(
                    new_place, new_category, new_notes, new_priority, new_cost, new_duration,
                    new_lat or None, new_lon or None,
                )
                st.success(f"Added {new_place}!")

        st.divider()
        st.subheader("📍 Unscheduled Places")

        search_col, filter_col = st.columns(2)
        search_term = search_col.text_input("Search", placeholder="Filter by name/notes")
        category_filter = filter_col.multiselect("Filter by category", CATEGORIES)

        visible = st.session_state.bucket_list
        if search_term:
            term = search_term.lower()
            visible = [p for p in visible if term in p["Place"].lower() or term in (p.get("Notes") or "").lower()]
        if category_filter:
            visible = [p for p in visible if p["Category"] in category_filter]

        if not st.session_state.bucket_list:
            st.write("Your bucket list is empty.")
        elif not visible:
            st.write("No places match your filters.")
        else:
            for place in visible:
                with st.container(border=True):
                    st.markdown(f"**{place['Category']} {place['Place']}**  ·  {place['Priority']}")
                    meta_bits = []
                    if place.get("Cost"):
                        meta_bits.append(f"{trip['currency']}{place['Cost']:.2f}")
                    if place.get("Duration"):
                        meta_bits.append(f"{place['Duration']} min")
                    if meta_bits:
                        st.caption(" · ".join(meta_bits))
                    if place.get("Notes"):
                        st.caption(place["Notes"])

                    sc1, sc2, sc3 = st.columns([1, 1, 1])
                    sched_day = sc1.selectbox(
                        "Day", day_options(), format_func=day_label, key=f"day_{place['id']}"
                    )
                    sched_time = sc2.time_input("Time", value=time(9, 0), key=f"time_{place['id']}")
                    sc3.write("")
                    sc3.write("")
                    b1, b2 = st.columns(2)
                    if b1.button("Schedule ➡️", key=f"sched_{place['id']}"):
                        move_to_itinerary(place["id"], sched_day, sched_time)
                        st.rerun()
                    if b2.button("🗑️ Delete", key=f"del_bucket_{place['id']}"):
                        delete_item("bucket_list", place["id"])
                        st.rerun()

    with col2:
        st.header("Quick Itinerary Preview")
        if not st.session_state.itinerary:
            st.write("No items scheduled yet. Schedule items from the left to see them here.")
        else:
            for day_index in day_options():
                day_items = [i for i in st.session_state.itinerary if i["Day"] == day_index]
                if not day_items:
                    continue
                st.markdown(f"**{day_label(day_index)}**")
                for item in sorted(day_items, key=lambda x: x["Time"]):
                    st.caption(f"{item['Time'].strftime('%I:%M %p')} — {item['Category']} {item['Place']}")
                conflicts = find_conflicts(day_index)
                for a, b in conflicts:
                    st.warning(f"⚠️ Time conflict on {day_label(day_index)}: **{a}** overlaps **{b}**")

# ==============================
# TAB: ITINERARY (Full schedule with editing)
# ==============================
with tab_itinerary:
    st.header("Your Full Itinerary")

    if not st.session_state.itinerary:
        st.write("No items scheduled yet. Use the Plan tab to schedule places.")
    else:
        for day_index in day_options():
            day_items = [i for i in st.session_state.itinerary if i["Day"] == day_index]
            if not day_items:
                continue

            with st.expander(f"🗓️ {day_label(day_index)}", expanded=True):
                conflicts = find_conflicts(day_index)
                for a, b in conflicts:
                    st.warning(f"⚠️ Time conflict: **{a}** overlaps **{b}**")

                for item in sorted(day_items, key=lambda x: x["Time"]):
                    color = CATEGORY_COLORS.get(item["Category"], "#ff4b4b")
                    time_str = item["Time"].strftime("%I:%M %p")
                    cost_str = f" · {trip['currency']}{item['Cost']:.2f}" if item.get("Cost") else ""
                    st.markdown(
                        f"""
                        <div style="
                            padding: 10px;
                            border-radius: 5px;
                            margin-bottom: 6px;
                            background-color: #f0f2f6;
                            border-left: 5px solid {color};">
                            <strong>{time_str}</strong> | {item['Category']} | {item['Priority']}{cost_str}
                            <h4 style="margin:0; padding-top:5px;">{item['Place']}</h4>
                            <em style="color: #555;">{item.get('Notes') or ''}</em>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    ec1, ec2, ec3 = st.columns([1, 1, 1])
                    new_day = ec1.selectbox(
                        "Move to day", day_options(), index=item["Day"], format_func=day_label,
                        key=f"edit_day_{item['id']}",
                    )
                    new_time = ec2.time_input("New time", value=item["Time"], key=f"edit_time_{item['id']}")
                    if ec3.button("Update", key=f"update_{item['id']}"):
                        item["Day"] = new_day
                        item["Time"] = new_time
                        st.session_state.itinerary.sort(key=lambda x: (x["Day"], x["Time"]))
                        st.rerun()
                    bc1, bc2 = st.columns(2)
                    if bc1.button("↩️ Unschedule", key=f"unsched_{item['id']}"):
                        move_to_bucket_list(item["id"])
                        st.rerun()
                    if bc2.button("🗑️ Remove", key=f"del_itin_{item['id']}"):
                        delete_item("itinerary", item["id"])
                        st.rerun()

        st.divider()
        st.subheader("📤 Export")
        df = pd.DataFrame(
            [
                {
                    "Day": day_label(i["Day"]),
                    "Time": i["Time"].strftime("%H:%M"),
                    "Category": i["Category"],
                    "Place": i["Place"],
                    "Priority": i["Priority"],
                    "Cost": i.get("Cost") or 0,
                    "Notes": i.get("Notes") or "",
                }
                for i in st.session_state.itinerary
            ]
        )
        e1, e2, e3 = st.columns(3)
        e1.download_button(
            "📥 Download CSV", data=df.to_csv(index=False).encode("utf-8"),
            file_name="itinerary.csv", mime="text/csv",
        )
        e2.download_button(
            "📅 Download Calendar (.ics)", data=export_ics(),
            file_name="itinerary.ics", mime="text/calendar",
        )
        e3.download_button(
            "📝 Download Markdown", data=export_markdown(),
            file_name="itinerary.md", mime="text/markdown",
        )

        mappable = [i for i in st.session_state.itinerary if i.get("Lat") and i.get("Lon")]
        if mappable:
            st.divider()
            st.subheader("🗺️ Map")
            map_df = pd.DataFrame({"lat": [i["Lat"] for i in mappable], "lon": [i["Lon"] for i in mappable]})
            st.map(map_df)

# ==============================
# TAB: BUDGET
# ==============================
with tab_budget:
    st.header("💰 Budget Tracker")

    all_items = st.session_state.bucket_list + st.session_state.itinerary
    total_spent = sum(item.get("Cost") or 0 for item in all_items)
    budget = trip["budget"]

    m1, m2, m3 = st.columns(3)
    m1.metric("Total Budget", f"{trip['currency']}{budget:,.2f}")
    m2.metric("Planned Spend", f"{trip['currency']}{total_spent:,.2f}")
    remaining = budget - total_spent
    m3.metric("Remaining", f"{trip['currency']}{remaining:,.2f}", delta=None)

    if budget > 0:
        pct = min(total_spent / budget, 1.0)
        st.progress(pct, text=f"{pct * 100:.0f}% of budget planned")
        if total_spent > budget:
            st.error("⚠️ You are over budget!")

    if all_items:
        st.divider()
        st.subheader("Spend by Category")
        cat_totals = {}
        for item in all_items:
            cat_totals[item["Category"]] = cat_totals.get(item["Category"], 0) + (item.get("Cost") or 0)
        chart_df = pd.DataFrame({"Category": list(cat_totals.keys()), "Cost": list(cat_totals.values())})
        chart_df = chart_df.set_index("Category")
        st.bar_chart(chart_df)

        st.subheader("All Costed Items")
        cost_df = pd.DataFrame(
            [
                {"Place": i["Place"], "Category": i["Category"], "Cost": i.get("Cost") or 0}
                for i in all_items if i.get("Cost")
            ]
        )
        if not cost_df.empty:
            st.dataframe(cost_df, hide_index=True, use_container_width=True)
    else:
        st.write("Add places with costs to see your budget breakdown.")

# ==============================
# TAB: PACKING LIST
# ==============================
with tab_packing:
    st.header("🎒 Packing List")

    with st.form("add_pack_form", clear_on_submit=True):
        pc1, pc2 = st.columns([3, 1])
        pack_item = pc1.text_input("Item", placeholder="e.g., Passport")
        pack_qty = pc2.number_input("Qty", min_value=1, value=1)
        if st.form_submit_button("Add Item") and pack_item:
            st.session_state.packing_list.append(
                {"id": new_id(), "Item": pack_item, "Qty": pack_qty, "Packed": False}
            )

    if not st.session_state.packing_list:
        st.write("Your packing list is empty.")
    else:
        packed_count = sum(1 for i in st.session_state.packing_list if i["Packed"])
        st.progress(
            packed_count / len(st.session_state.packing_list),
            text=f"{packed_count}/{len(st.session_state.packing_list)} packed",
        )
        for pack in st.session_state.packing_list:
            pcol1, pcol2, pcol3 = st.columns([3, 1, 1])
            pack["Packed"] = pcol1.checkbox(
                f"{pack['Item']} (x{pack['Qty']})", value=pack["Packed"], key=f"pack_{pack['id']}"
            )
            if pcol3.button("🗑️", key=f"del_pack_{pack['id']}"):
                delete_item("packing_list", pack["id"])
                st.rerun()

# ==============================
# TAB: STATS
# ==============================
with tab_stats:
    st.header("📊 Trip Stats")

    all_items = st.session_state.bucket_list + st.session_state.itinerary
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Total Places", len(all_items))
    s2.metric("Scheduled", len(st.session_state.itinerary))
    s3.metric("Unscheduled", len(st.session_state.bucket_list))
    total_minutes = sum(i.get("Duration") or 0 for i in st.session_state.itinerary)
    s4.metric("Planned Time", f"{total_minutes // 60}h {total_minutes % 60}m")

    if all_items:
        st.divider()
        st.subheader("Places by Category")
        cat_counts = {}
        for item in all_items:
            cat_counts[item["Category"]] = cat_counts.get(item["Category"], 0) + 1
        cat_df = pd.DataFrame({"Category": list(cat_counts.keys()), "Count": list(cat_counts.values())})
        st.bar_chart(cat_df.set_index("Category"))

        st.subheader("Places by Priority")
        pri_counts = {}
        for item in all_items:
            pri_counts[item["Priority"]] = pri_counts.get(item["Priority"], 0) + 1
        pri_df = pd.DataFrame({"Priority": list(pri_counts.keys()), "Count": list(pri_counts.values())})
        st.bar_chart(pri_df.set_index("Priority"))

        st.subheader("Fill Rate by Day")
        fill_data = []
        for day_index in day_options():
            day_minutes = sum(
                (i.get("Duration") or 0) for i in st.session_state.itinerary if i["Day"] == day_index
            )
            fill_data.append({"Day": day_label(day_index), "Hours Planned": round(day_minutes / 60, 1)})
        st.bar_chart(pd.DataFrame(fill_data).set_index("Day"))
    else:
        st.write("Add some places to see trip statistics.")
