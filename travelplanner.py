import json
import uuid
from datetime import datetime, date, time, timedelta

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Voyager · Trip Planner", page_icon="🧭", layout="wide")

import db
import geocode
import mapview
import theme
from theme import CATEGORY_COLORS, day_color

CATEGORIES = list(CATEGORY_COLORS.keys())
PRIORITIES = ["🔥 Must Do", "👍 Would Like", "🤷 Optional"]

db.init_db()
theme.inject()


# ==================================================================
# STATE
# ==================================================================
def blank_trip():
    return {
        "name": "My Trip",
        "destination": "",
        "start_date": date.today(),
        "num_days": 5,
        "currency": "$",
        "budget": 0.0,
    }


def reset_workspace(trip=None):
    st.session_state.trip = trip or blank_trip()
    st.session_state.bucket_list = []
    st.session_state.itinerary = []
    st.session_state.packing_list = []
    st.session_state.last_deleted = None
    st.session_state.current_trip_id = None
    st.session_state.dirty = False


for key, default in (("user", None), ("current_trip_id", None),
                     ("last_deleted", None), ("pending_coords", None),
                     ("geocode_results", None), ("dirty", False)):
    if key not in st.session_state:
        st.session_state[key] = default

if "trip" not in st.session_state:
    reset_workspace()


def new_id():
    return uuid.uuid4().hex[:8]


def mark_dirty():
    st.session_state.dirty = True


# ==================================================================
# SERIALIZATION
# ==================================================================
def serialize_state():
    trip = st.session_state.trip
    return {
        "trip": {**trip, "start_date": trip["start_date"].isoformat()},
        "bucket_list": st.session_state.bucket_list,
        "itinerary": [
            {**item, "Time": item["Time"].strftime("%H:%M")}
            for item in st.session_state.itinerary
        ],
        "packing_list": st.session_state.packing_list,
    }


def apply_state(data):
    trip = dict(data.get("trip") or {})
    base = blank_trip()
    base.update({k: v for k, v in trip.items() if k in base})
    base["start_date"] = date.fromisoformat(trip["start_date"]) if trip.get("start_date") \
        else date.today()
    base["num_days"] = int(base["num_days"] or 1)
    base["budget"] = float(base["budget"] or 0)

    itinerary = [dict(i) for i in data.get("itinerary", [])]
    for item in itinerary:
        item["Time"] = datetime.strptime(item["Time"], "%H:%M").time()
    itinerary.sort(key=lambda x: (x["Day"], x["Time"]))

    st.session_state.trip = base
    st.session_state.bucket_list = [dict(i) for i in data.get("bucket_list", [])]
    st.session_state.itinerary = itinerary
    st.session_state.packing_list = [dict(i) for i in data.get("packing_list", [])]
    st.session_state.last_deleted = None
    st.session_state.dirty = False


# ==================================================================
# AUTH SCREEN
# ==================================================================
def render_auth():
    st.markdown(
        """
        <div class="tp-authwrap">
            <span class="tp-logo">🧭</span>
            <h1>Voyager</h1>
            <p>Design your trip day by day — bucket list, budget, satellite map
            and packing, all in one place.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    left, middle, right = st.columns([1, 1.25, 1])
    with middle:
        login_tab, signup_tab = st.tabs(["🔓 Log in", "✨ Create account"])

        with login_tab:
            with st.form("login_form"):
                username = st.text_input("Username", key="login_user")
                password = st.text_input("Password", type="password", key="login_pw")
                if st.form_submit_button("Log in", type="primary", width="stretch"):
                    try:
                        user = db.verify_user(username, password)
                    except db.AuthError as exc:
                        st.error(str(exc))
                    else:
                        st.session_state.user = user
                        recent = db.list_trips(user["id"])
                        if recent:
                            loaded = db.load_trip(user["id"], recent[0]["id"])
                            apply_state(loaded["state"])
                            st.session_state.current_trip_id = loaded["id"]
                        else:
                            reset_workspace()
                        st.rerun()

        with signup_tab:
            with st.form("signup_form"):
                new_user = st.text_input("Username", help="3-32 chars: letters, numbers, . _ -")
                display = st.text_input("Display name (optional)")
                pw1 = st.text_input("Password", type="password",
                                    help=f"At least {db.MIN_PASSWORD_LENGTH} characters")
                pw2 = st.text_input("Confirm password", type="password")
                if st.form_submit_button("Create account", type="primary", width="stretch"):
                    if pw1 != pw2:
                        st.error("Those passwords don't match.")
                    else:
                        try:
                            user = db.create_user(new_user, pw1, display or new_user)
                        except db.AuthError as exc:
                            st.error(str(exc))
                        else:
                            st.session_state.user = user
                            reset_workspace()
                            st.rerun()

        st.markdown(
            """
            <div style="margin-top:1.4rem">
                <div class="tp-feature">🗓️ <span>Drag ideas from a bucket list onto real
                days and times, with overlap warnings.</span></div>
                <div class="tp-feature">🛰️ <span>See every stop on a satellite map with
                per-day routes.</span></div>
                <div class="tp-feature">🔐 <span>Your trips are saved to your own account —
                reopen and edit them any time.</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )


if st.session_state.user is None:
    render_auth()
    st.stop()

user = st.session_state.user


# ==================================================================
# HELPERS
# ==================================================================
def day_options():
    return list(range(int(st.session_state.trip["num_days"])))


def day_date(day_index):
    return st.session_state.trip["start_date"] + timedelta(days=day_index)


def day_label(day_index):
    return f"Day {day_index + 1} · {day_date(day_index).strftime('%a, %b %d')}"


def find_by_id(items, item_id):
    for index, item in enumerate(items):
        if item["id"] == item_id:
            return index
    return None


def move_to_itinerary(item_id, day_index, time_val):
    index = find_by_id(st.session_state.bucket_list, item_id)
    if index is None:
        return
    item = st.session_state.bucket_list.pop(index)
    item["Day"] = day_index
    item["Time"] = time_val
    st.session_state.itinerary.append(item)
    st.session_state.itinerary.sort(key=lambda x: (x["Day"], x["Time"]))
    mark_dirty()


def move_to_bucket_list(item_id):
    index = find_by_id(st.session_state.itinerary, item_id)
    if index is None:
        return
    item = st.session_state.itinerary.pop(index)
    item.pop("Day", None)
    item.pop("Time", None)
    st.session_state.bucket_list.append(item)
    mark_dirty()


def delete_item(collection, item_id):
    items = st.session_state[collection]
    index = find_by_id(items, item_id)
    if index is None:
        return
    st.session_state.last_deleted = (collection, items.pop(index))
    mark_dirty()


def restore_last_deleted():
    if not st.session_state.last_deleted:
        return
    collection, item = st.session_state.last_deleted
    st.session_state[collection].append(item)
    if collection == "itinerary":
        st.session_state.itinerary.sort(key=lambda x: (x["Day"], x["Time"]))
    st.session_state.last_deleted = None
    mark_dirty()


def item_end(item):
    start = datetime.combine(date.min, item["Time"])
    return start + timedelta(minutes=item.get("Duration") or 60)


def find_conflicts(day_index):
    items = sorted(
        [i for i in st.session_state.itinerary if i["Day"] == day_index],
        key=lambda x: x["Time"],
    )
    conflicts = []
    for a in range(len(items)):
        for b in range(a + 1, len(items)):
            first, second = items[a], items[b]
            start_first = datetime.combine(date.min, first["Time"])
            start_second = datetime.combine(date.min, second["Time"])
            if start_first < item_end(second) and start_second < item_end(first):
                conflicts.append((first["Place"], second["Place"]))
    return conflicts


def all_items():
    return st.session_state.bucket_list + st.session_state.itinerary


def day_minutes(day_index):
    return sum((i.get("Duration") or 0) for i in st.session_state.itinerary
               if i["Day"] == day_index)


def money(amount):
    return f"{st.session_state.trip['currency']}{amount:,.2f}"


def has_coords(item):
    return item.get("Lat") not in (None, 0) and item.get("Lon") not in (None, 0)


# ==================================================================
# EXPORTS
# ==================================================================
def ics_escape(text):
    return (str(text).replace("\\", "\\\\").replace(",", "\\,")
            .replace(";", "\\;").replace("\n", "\\n"))


def export_ics():
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Voyager Trip Planner//EN"]
    for item in st.session_state.itinerary:
        start = datetime.combine(day_date(item["Day"]), item["Time"])
        end = start + timedelta(minutes=item.get("Duration") or 60)
        lines += [
            "BEGIN:VEVENT",
            f"UID:{item['id']}@voyager-trip-planner",
            f"DTSTART:{start.strftime('%Y%m%dT%H%M%S')}",
            f"DTEND:{end.strftime('%Y%m%dT%H%M%S')}",
            f"SUMMARY:{ics_escape(item['Category'])} {ics_escape(item['Place'])}",
            f"DESCRIPTION:{ics_escape(item.get('Notes') or '')}",
        ]
        if has_coords(item):
            lines.append(f"GEO:{item['Lat']};{item['Lon']}")
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return "\n".join(lines)


def export_markdown():
    trip = st.session_state.trip
    lines = [f"# {trip['name']}", "", f"**Destination:** {trip['destination']}",
             f"**Dates:** {trip['start_date']:%b %d, %Y} · {trip['num_days']} days", ""]
    for index in day_options():
        items = sorted([i for i in st.session_state.itinerary if i["Day"] == index],
                       key=lambda x: x["Time"])
        if not items:
            continue
        lines.append(f"## {day_label(index)}")
        for item in items:
            cost = f" — {money(item['Cost'])}" if item.get("Cost") else ""
            lines.append(f"- **{item['Time']:%I:%M %p}** {item['Category']} "
                         f"{item['Place']}{cost}")
            if item.get("Notes"):
                lines.append(f"  - _{item['Notes']}_")
        lines.append("")
    if st.session_state.bucket_list:
        lines.append("## Not yet scheduled")
        for item in st.session_state.bucket_list:
            lines.append(f"- {item['Category']} {item['Place']}")
    return "\n".join(lines)


def itinerary_dataframe():
    return pd.DataFrame([
        {
            "Day": day_label(i["Day"]),
            "Date": day_date(i["Day"]).isoformat(),
            "Time": i["Time"].strftime("%H:%M"),
            "Place": i["Place"],
            "Category": i["Category"],
            "Priority": i["Priority"],
            "Duration (min)": i.get("Duration") or 0,
            "Cost": i.get("Cost") or 0,
            "Latitude": i.get("Lat") or "",
            "Longitude": i.get("Lon") or "",
            "Notes": i.get("Notes") or "",
        }
        for i in st.session_state.itinerary
    ])


# ==================================================================
# SIDEBAR
# ==================================================================
with st.sidebar:
    trip = st.session_state.trip

    st.markdown(
        f'<div style="display:flex;align-items:center;gap:.6rem;margin-bottom:1rem">'
        f'<span class="tp-logo" style="width:40px;height:40px;font-size:1.2rem;'
        f'border-radius:13px">🧭</span>'
        f'<div><div style="font-family:Sora;font-weight:700">'
        f'{theme.esc(user["display_name"])}</div>'
        f'<div style="font-size:.74rem;color:var(--muted)">@{theme.esc(user["username"])}'
        f'</div></div></div>',
        unsafe_allow_html=True,
    )
    if st.button("Log out", width="stretch"):
        st.session_state.user = None
        reset_workspace()
        st.rerun()

    st.divider()

    saved = db.list_trips(user["id"])
    status = "● Unsaved changes" if st.session_state.dirty else "✓ Saved"
    st.markdown(
        f'<div style="font-family:Sora;font-weight:700;font-size:1.05rem">🧳 My Trips</div>'
        f'<div style="font-size:.75rem;color:{"#ffb457" if st.session_state.dirty else "#4ade80"};'
        f'margin:.2rem 0 .6rem">{status}</div>',
        unsafe_allow_html=True,
    )

    if st.button("💾 Save trip", type="primary", width="stretch"):
        trip_id = db.save_trip(user["id"], trip["name"], serialize_state())
        st.session_state.current_trip_id = trip_id
        st.session_state.dirty = False
        st.toast(f"Saved “{trip['name']}” to your account", icon="💾")
        st.rerun()

    if saved:
        labels = {
            f"{t['name']}  ·  {datetime.fromisoformat(t['updated_at']):%b %d, %H:%M}": t
            for t in saved
        }
        chosen_label = st.selectbox("Saved trips", list(labels), label_visibility="collapsed")
        chosen = labels[chosen_label]

        col_load, col_del = st.columns(2)
        if col_load.button("📂 Open", width="stretch"):
            loaded = db.load_trip(user["id"], chosen["id"])
            if loaded is None:
                st.toast("That trip no longer exists.", icon="⚠️")
            else:
                apply_state(loaded["state"])
                st.session_state.current_trip_id = loaded["id"]
                st.toast(f"Opened “{loaded['name']}”", icon="📂")
            st.rerun()
        if col_del.button("🗑️ Delete", width="stretch"):
            db.delete_trip(user["id"], chosen["id"])
            if st.session_state.current_trip_id == chosen["id"]:
                st.session_state.current_trip_id = None
            st.toast(f"Deleted “{chosen['name']}”", icon="🗑️")
            st.rerun()
    else:
        st.caption("No saved trips yet. Plan below, then hit Save trip.")

    if st.button("🆕 Start a new trip", width="stretch"):
        reset_workspace()
        st.rerun()

    st.divider()
    st.markdown('<div style="font-family:Sora;font-weight:700">⚙️ Trip settings</div>',
                unsafe_allow_html=True)

    name = st.text_input("Trip name", value=trip["name"])
    destination = st.text_input("Destination", value=trip["destination"])
    start_date = st.date_input("Start date", value=trip["start_date"])
    num_days = st.number_input("Number of days", min_value=1, max_value=60,
                               value=int(trip["num_days"]))
    currency = st.text_input("Currency symbol", value=trip["currency"], max_chars=3)
    budget = st.number_input("Total budget", min_value=0.0, value=float(trip["budget"]),
                             step=50.0)

    updates = {"name": name, "destination": destination, "start_date": start_date,
               "num_days": int(num_days), "currency": currency, "budget": float(budget)}
    if any(trip[k] != v for k, v in updates.items()):
        trip.update(updates)
        mark_dirty()

    # Items scheduled beyond a shortened trip would silently disappear.
    stranded = [i for i in st.session_state.itinerary if i["Day"] >= int(num_days)]
    if stranded:
        st.warning(f"{len(stranded)} scheduled item(s) fall outside Day 1-{int(num_days)}.")
        if st.button("↩️ Move them back to the bucket list", width="stretch"):
            for item in list(stranded):
                move_to_bucket_list(item["id"])
            st.rerun()

    st.divider()
    st.markdown('<div style="font-family:Sora;font-weight:700">📤 Backup</div>',
                unsafe_allow_html=True)
    st.download_button("Export trip (JSON)",
                       data=json.dumps(serialize_state(), indent=2, ensure_ascii=False),
                       file_name=f"{trip['name'] or 'trip'}.json",
                       mime="application/json", width="stretch")
    uploaded = st.file_uploader("Import trip (JSON)", type="json")
    if uploaded is not None and st.button("Load imported file", width="stretch"):
        try:
            apply_state(json.loads(uploaded.getvalue().decode("utf-8")))
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            st.error(f"That file could not be read: {exc}")
        else:
            st.session_state.current_trip_id = None
            st.session_state.dirty = True
            st.toast("Trip imported — remember to save it", icon="📥")
            st.rerun()

    if st.session_state.last_deleted:
        st.divider()
        if st.button("↩️ Undo last delete", width="stretch"):
            restore_last_deleted()
            st.rerun()


# ==================================================================
# HERO
# ==================================================================
trip = st.session_state.trip
days_until = (trip["start_date"] - date.today()).days
if days_until > 0:
    countdown = f"🗓️ {days_until} days to go"
elif days_until == 0:
    countdown = "✈️ Departing today"
else:
    countdown = f"🏁 Started {-days_until} days ago"

planned_spend = sum(i.get("Cost") or 0 for i in all_items())
theme.hero(
    trip["name"] or "Untitled Trip",
    trip["destination"] or "Destination TBD",
    [
        (countdown, True),
        (f"📅 {trip['num_days']} days", False),
        (f"📍 {len(st.session_state.itinerary)} scheduled", False),
        (f"💡 {len(st.session_state.bucket_list)} ideas", False),
        (f"💰 {money(planned_spend)} planned", False),
    ],
)

tab_plan, tab_itinerary, tab_map, tab_budget, tab_packing, tab_stats = st.tabs(
    ["✨ Plan", "🗓️ Itinerary", "🛰️ Map", "💰 Budget", "🎒 Packing", "📊 Insights"]
)


# ==================================================================
# TAB: PLAN
# ==================================================================
with tab_plan:
    left, right = st.columns([1, 1], gap="large")

    with left:
        theme.section("Add a place", "Capture the idea now, schedule it later")

        with st.expander("📍 Look up coordinates (optional)"):
            lookup = st.text_input("Search for a place", key="geo_query",
                                   placeholder="e.g., Senso-ji Temple, Tokyo")
            if st.button("Search", key="geo_search"):
                if lookup.strip():
                    try:
                        st.session_state.geocode_results = geocode.search(lookup)
                    except geocode.GeocodeUnavailable as exc:
                        st.session_state.geocode_results = None
                        st.warning(str(exc))
            results = st.session_state.geocode_results
            if results:
                for index, hit in enumerate(results):
                    row_text, row_button = st.columns([4, 1])
                    row_text.caption(f"{hit['name']}  \n`{hit['lat']:.5f}, {hit['lon']:.5f}`")
                    if row_button.button("Use", key=f"geo_use_{index}"):
                        st.session_state.pending_coords = (hit["lat"], hit["lon"])
                        st.session_state.geocode_results = None
                        st.rerun()
            elif results == []:
                st.caption("No matches found.")

        pending = st.session_state.pending_coords
        if pending:
            st.success(f"Using coordinates {pending[0]:.5f}, {pending[1]:.5f}")

        with st.form("add_place", clear_on_submit=True):
            place = st.text_input("Location name", placeholder="e.g., Senso-ji Temple")
            col_a, col_b = st.columns(2)
            category = col_a.selectbox("Category", CATEGORIES)
            priority = col_b.selectbox("Priority", PRIORITIES)
            col_c, col_d = st.columns(2)
            cost = col_c.number_input("Est. cost", min_value=0.0, step=5.0)
            duration = col_d.number_input("Duration (min)", min_value=0, step=15, value=60)
            col_e, col_f = st.columns(2)
            latitude = col_e.number_input("Latitude", value=float(pending[0]) if pending else 0.0,
                                         format="%.6f")
            longitude = col_f.number_input("Longitude", value=float(pending[1]) if pending else 0.0,
                                          format="%.6f")
            notes = st.text_area("Notes", placeholder="Tickets, opening hours, reminders…")

            if st.form_submit_button("Add to bucket list", type="primary", width="stretch"):
                if not place.strip():
                    st.warning("Give the place a name first.")
                else:
                    st.session_state.bucket_list.append({
                        "id": new_id(), "Place": place.strip(), "Category": category,
                        "Priority": priority, "Notes": notes.strip(), "Cost": float(cost),
                        "Duration": int(duration),
                        "Lat": float(latitude) or None, "Lon": float(longitude) or None,
                    })
                    st.session_state.pending_coords = None
                    mark_dirty()
                    st.toast(f"Added {place.strip()}", icon="✨")
                    st.rerun()

    with right:
        theme.section("Bucket list",
                      f"{len(st.session_state.bucket_list)} idea(s) waiting for a slot")

        if st.session_state.bucket_list:
            filter_search, filter_category = st.columns([1, 1])
            query = filter_search.text_input("Search", placeholder="Filter by name or notes",
                                             label_visibility="collapsed")
            categories = filter_category.multiselect("Categories", CATEGORIES,
                                                     placeholder="All categories",
                                                     label_visibility="collapsed")
            visible = st.session_state.bucket_list
            if query:
                needle = query.lower()
                visible = [p for p in visible
                           if needle in p["Place"].lower()
                           or needle in (p.get("Notes") or "").lower()]
            if categories:
                visible = [p for p in visible if p["Category"] in categories]
        else:
            visible = []

        if not st.session_state.bucket_list:
            theme.empty_state("💡", "Nothing here yet — add a place on the left to get started.")
        elif not visible:
            theme.empty_state("🔍", "No places match those filters.")
        else:
            for place_item in visible:
                accent = CATEGORY_COLORS.get(place_item["Category"], "#7c6cff")
                meta = []
                if place_item.get("Duration"):
                    meta.append(f"{place_item['Duration']} min")
                if has_coords(place_item):
                    meta.append("📍 located")
                theme.place_card(
                    place_item, accent,
                    time_text=" · ".join(meta),
                    cost_text=money(place_item["Cost"]) if place_item.get("Cost") else "",
                )
                col_day, col_time, col_go, col_del = st.columns([1.9, 1.2, 1.2, 0.6])
                chosen_day = col_day.selectbox("Day", day_options(), format_func=day_label,
                                               key=f"day_{place_item['id']}",
                                               label_visibility="collapsed")
                chosen_time = col_time.time_input("Time", value=time(9, 0),
                                                  key=f"time_{place_item['id']}",
                                                  label_visibility="collapsed")
                if col_go.button("Schedule", key=f"sched_{place_item['id']}",
                                 width="stretch"):
                    move_to_itinerary(place_item["id"], chosen_day, chosen_time)
                    st.rerun()
                if col_del.button("🗑️", key=f"delb_{place_item['id']}", width="stretch"):
                    delete_item("bucket_list", place_item["id"])
                    st.rerun()


# ==================================================================
# TAB: ITINERARY
# ==================================================================
with tab_itinerary:
    if not st.session_state.itinerary:
        theme.empty_state("🗓️", "Nothing scheduled yet. Add places in Plan, then schedule them.")
    else:
        total_conflicts = sum(len(find_conflicts(d)) for d in day_options())
        cols = st.columns(4)
        with cols[0]:
            theme.stat("Scheduled", len(st.session_state.itinerary), "activities")
        with cols[1]:
            total = sum(day_minutes(d) for d in day_options())
            theme.stat("Planned time", f"{total // 60}h {total % 60}m", "across the trip")
        with cols[2]:
            theme.stat("Days in use",
                       sum(1 for d in day_options() if day_minutes(d) > 0),
                       f"of {trip['num_days']}")
        with cols[3]:
            theme.stat("Clashes", total_conflicts,
                       "overlapping" if total_conflicts else "all clear")

        st.write("")
        for index in day_options():
            items = sorted([i for i in st.session_state.itinerary if i["Day"] == index],
                           key=lambda x: x["Time"])
            minutes = day_minutes(index)
            spend = sum(i.get("Cost") or 0 for i in items)
            meta = (f"{len(items)} stops · {minutes // 60}h {minutes % 60}m"
                    f"{' · ' + money(spend) if spend else ''}") if items else "Nothing planned"
            theme.day_header(index, day_label(index), meta)

            if not items:
                st.caption("— free day —")
                continue

            # A pile-up of items at one time produces every pairwise combination,
            # so show a couple of examples and summarise the rest.
            clashes = find_conflicts(index)
            for first, second in clashes[:2]:
                st.warning(f"⚠️ **{first}** overlaps **{second}**")
            if len(clashes) > 2:
                st.warning(f"⚠️ …and {len(clashes) - 2} more overlapping pair(s) on this day.")

            for item in items:
                theme.place_card(
                    item,
                    day_color(index),
                    time_text=item["Time"].strftime("%I:%M %p"),
                    cost_text=money(item["Cost"]) if item.get("Cost") else "",
                )
                col_day, col_time, col_update, col_back, col_remove = st.columns(
                    [2, 1.4, 1, 1.2, 0.8]
                )
                new_day = col_day.selectbox("Day", day_options(), index=item["Day"],
                                            format_func=day_label,
                                            key=f"eday_{item['id']}",
                                            label_visibility="collapsed")
                new_time = col_time.time_input("Time", value=item["Time"],
                                               key=f"etime_{item['id']}",
                                               label_visibility="collapsed")
                if col_update.button("Update", key=f"upd_{item['id']}", width="stretch"):
                    if (item["Day"], item["Time"]) != (new_day, new_time):
                        item["Day"] = new_day
                        item["Time"] = new_time
                        st.session_state.itinerary.sort(key=lambda x: (x["Day"], x["Time"]))
                        mark_dirty()
                    st.rerun()
                if col_back.button("Unschedule", key=f"uns_{item['id']}", width="stretch"):
                    move_to_bucket_list(item["id"])
                    st.rerun()
                if col_remove.button("🗑️", key=f"deli_{item['id']}", width="stretch"):
                    delete_item("itinerary", item["id"])
                    st.rerun()

        st.divider()
        theme.section("Export", "Take the plan with you")
        frame = itinerary_dataframe()
        col1, col2, col3 = st.columns(3)
        col1.download_button("📥 CSV", data=frame.to_csv(index=False).encode("utf-8"),
                             file_name="itinerary.csv", mime="text/csv", width="stretch")
        col2.download_button("📅 Calendar (.ics)", data=export_ics(),
                             file_name="itinerary.ics", mime="text/calendar",
                             width="stretch")
        col3.download_button("📝 Markdown", data=export_markdown(),
                             file_name="itinerary.md", mime="text/markdown",
                             width="stretch")


# ==================================================================
# TAB: MAP
# ==================================================================
with tab_map:
    theme.section("Satellite view", "Every located stop, coloured by day")

    scheduled_located = [i for i in st.session_state.itinerary if has_coords(i)]
    bucket_located = [i for i in st.session_state.bucket_list if has_coords(i)]
    missing = [i for i in all_items() if not has_coords(i)]

    controls_left, controls_right = st.columns([2, 1.4])
    basemap = controls_left.radio("Basemap", list(mapview.BASEMAPS),
                                  index=list(mapview.BASEMAPS).index(mapview.DEFAULT_BASEMAP),
                                  horizontal=True)
    show_labels = controls_right.checkbox("Show name labels", value=True)
    show_routes = controls_right.checkbox("Draw day routes", value=True)
    compact_labels = controls_right.checkbox(
        "Compact labels", value=False,
        help="Show just day/stop numbers — useful when stops sit close together.",
    )

    day_filter = st.multiselect("Days to show", day_options(), format_func=day_label,
                                placeholder="All days")
    active_days = day_filter or day_options()

    points, routes = [], []
    for index in active_days:
        day_items = sorted([i for i in scheduled_located if i["Day"] == index],
                           key=lambda x: x["Time"])
        for order, item in enumerate(day_items, start=1):
            stop_ref = f"D{index + 1}.{order}"
            points.append({
                "lat": float(item["Lat"]), "lon": float(item["Lon"]),
                "name": item["Place"],
                # Map labels use deck.gl's ASCII font atlas, so no emoji here.
                "label": stop_ref if compact_labels else f"{stop_ref}  {item['Place']}",
                "meta": (f"{day_label(index)} · {item['Time']:%I:%M %p} · "
                         f"{item['Category']}"),
                "color": day_color(index),
            })
        if len(day_items) > 1:
            routes.append({
                "path": [[float(i["Lon"]), float(i["Lat"])] for i in day_items],
                "color": day_color(index),
                "name": day_label(index),
            })

    if not day_filter:
        for item in bucket_located:
            points.append({
                "lat": float(item["Lat"]), "lon": float(item["Lon"]),
                "name": item["Place"],
                "label": "" if compact_labels else item["Place"],
                "meta": f"Unscheduled · {item['Category']}",
                "color": "#94a3c8",
            })

    if points:
        legend_entries = [(day_label(d), day_color(d)) for d in active_days
                          if any(i["Day"] == d for i in scheduled_located)]
        if bucket_located and not day_filter:
            legend_entries.append(("Unscheduled ideas", "#94a3c8"))
        if legend_entries:
            theme.legend(legend_entries)

        st.pydeck_chart(
            mapview.build_deck(points, routes=routes, basemap=basemap,
                               show_labels=show_labels, show_routes=show_routes),
            height=620,
        )
        st.caption(f"{len(points)} location(s) shown · {mapview.attribution(basemap)}")
        st.caption("Tiles are fetched by your browser — if the imagery stays blank, "
                   "the network is blocking the tile server.")
    else:
        theme.empty_state(
            "🛰️",
            "No coordinates yet. Add latitude/longitude to a place — the "
            "“Look up coordinates” tool in Plan can find them for you.",
        )

    if missing:
        st.divider()
        theme.section("Missing coordinates", f"{len(missing)} place(s) not on the map")
        for item in missing:
            col_name, col_action = st.columns([3, 1])
            col_name.markdown(f"{item['Category']} **{theme.esc(item['Place'])}**")
            if col_action.button("📍 Locate", key=f"loc_{item['id']}", width="stretch"):
                try:
                    hits = geocode.search(f"{item['Place']} {trip['destination']}", limit=1)
                except geocode.GeocodeUnavailable as exc:
                    st.warning(str(exc))
                else:
                    if hits:
                        item["Lat"] = hits[0]["lat"]
                        item["Lon"] = hits[0]["lon"]
                        mark_dirty()
                        st.toast(f"Located {item['Place']}", icon="📍")
                        st.rerun()
                    else:
                        st.warning(f"No match found for “{item['Place']}”.")


# ==================================================================
# TAB: BUDGET
# ==================================================================
with tab_budget:
    theme.section("Budget", "Estimated costs across everything you've added")

    spend = sum(i.get("Cost") or 0 for i in all_items())
    budget_total = trip["budget"]
    remaining = budget_total - spend

    cols = st.columns(4)
    with cols[0]:
        theme.stat("Budget", money(budget_total), "total set")
    with cols[1]:
        theme.stat("Planned", money(spend), f"{len([i for i in all_items() if i.get('Cost')])} costed items")
    with cols[2]:
        theme.stat("Remaining", money(remaining),
                   "over budget" if remaining < 0 else "still available")
    with cols[3]:
        per_day = spend / max(trip["num_days"], 1)
        theme.stat("Per day", money(per_day), "average")

    st.write("")
    if budget_total > 0:
        ratio = min(spend / budget_total, 1.0)
        st.progress(ratio, text=f"{ratio * 100:.0f}% of budget allocated")
        if spend > budget_total:
            st.error(f"⚠️ Over budget by {money(spend - budget_total)}.")
    else:
        st.caption("Set a total budget in the sidebar to track progress against it.")

    if any(i.get("Cost") for i in all_items()):
        st.divider()
        chart_left, chart_right = st.columns([1, 1], gap="large")

        with chart_left:
            theme.section("By category")
            totals = {}
            for item in all_items():
                if item.get("Cost"):
                    totals[item["Category"]] = totals.get(item["Category"], 0) + item["Cost"]
            st.bar_chart(pd.DataFrame({"Cost": totals}), color="#7c6cff", height=280)

        with chart_right:
            theme.section("By day")
            per_day_totals = {
                day_label(d): sum(i.get("Cost") or 0 for i in st.session_state.itinerary
                                  if i["Day"] == d)
                for d in day_options()
            }
            st.bar_chart(pd.DataFrame({"Cost": per_day_totals}), color="#38dbff", height=280)

        theme.section("All costed items")
        st.dataframe(
            pd.DataFrame([
                {"Place": i["Place"], "Category": i["Category"],
                 "When": day_label(i["Day"]) if "Day" in i else "Unscheduled",
                 "Cost": i["Cost"]}
                for i in all_items() if i.get("Cost")
            ]).sort_values("Cost", ascending=False),
            hide_index=True, width="stretch",
        )
    else:
        theme.empty_state("💰", "Add costs to your places to see the breakdown.")


# ==================================================================
# TAB: PACKING
# ==================================================================
with tab_packing:
    theme.section("Packing list", "Tick things off as they go in the bag")

    with st.form("add_pack", clear_on_submit=True):
        col_item, col_qty, col_add = st.columns([3, 1, 1])
        pack_name = col_item.text_input("Item", placeholder="e.g., Passport",
                                        label_visibility="collapsed")
        pack_qty = col_qty.number_input("Qty", min_value=1, value=1,
                                        label_visibility="collapsed")
        col_add.write("")
        if col_add.form_submit_button("Add", type="primary", width="stretch"):
            if pack_name.strip():
                st.session_state.packing_list.append({
                    "id": new_id(), "Item": pack_name.strip(),
                    "Qty": int(pack_qty), "Packed": False,
                })
                mark_dirty()
                st.rerun()

    packing = st.session_state.packing_list
    if not packing:
        theme.empty_state("🎒", "Your packing list is empty.")
    else:
        packed = sum(1 for i in packing if i["Packed"])
        st.progress(packed / len(packing), text=f"{packed} of {len(packing)} packed")
        st.write("")
        for entry in packing:
            col_check, col_del = st.columns([6, 1])
            checked = col_check.checkbox(f"**{entry['Item']}**  ×{entry['Qty']}",
                                         value=entry["Packed"], key=f"pack_{entry['id']}")
            if checked != entry["Packed"]:
                entry["Packed"] = checked
                mark_dirty()
            if col_del.button("🗑️", key=f"delp_{entry['id']}", width="stretch"):
                delete_item("packing_list", entry["id"])
                st.rerun()


# ==================================================================
# TAB: INSIGHTS
# ==================================================================
with tab_stats:
    theme.section("Insights", "How the plan is shaping up")

    items = all_items()
    total_minutes = sum(day_minutes(d) for d in day_options())
    cols = st.columns(4)
    with cols[0]:
        theme.stat("Places", len(items), "total ideas")
    with cols[1]:
        theme.stat("Scheduled", len(st.session_state.itinerary),
                   f"{len(st.session_state.bucket_list)} still loose")
    with cols[2]:
        theme.stat("Planned time", f"{total_minutes // 60}h {total_minutes % 60}m",
                   f"~{total_minutes / max(trip['num_days'], 1) / 60:.1f}h per day")
    with cols[3]:
        located = sum(1 for i in items if has_coords(i))
        theme.stat("On the map", f"{located}/{len(items)}" if items else "0",
                   "have coordinates")

    if not items:
        st.write("")
        theme.empty_state("📊", "Add some places to unlock trip insights.")
    else:
        st.divider()
        left_chart, right_chart = st.columns([1, 1], gap="large")

        with left_chart:
            theme.section("By category")
            counts = {}
            for item in items:
                counts[item["Category"]] = counts.get(item["Category"], 0) + 1
            st.bar_chart(pd.DataFrame({"Places": counts}), color="#7c6cff", height=280)

        with right_chart:
            theme.section("By priority")
            counts = {}
            for item in items:
                counts[item["Priority"]] = counts.get(item["Priority"], 0) + 1
            st.bar_chart(pd.DataFrame({"Places": counts}), color="#ff6b8b", height=280)

        theme.section("Hours planned per day", "Spot the days that are too full or too empty")
        st.bar_chart(
            pd.DataFrame({"Hours": {day_label(d): round(day_minutes(d) / 60, 1)
                                    for d in day_options()}}),
            color="#38dbff", height=300,
        )
