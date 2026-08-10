# Voyager — Trip Planner

A Streamlit trip planner with user accounts. Capture ideas in a bucket list, schedule
them into a day-by-day itinerary, see every stop on a satellite map, and track budget
and packing. Trips are saved to your own account, so you can reopen and keep editing them.

## Features

**Accounts & storage**
- Real sign-up / log-in. Passwords are stored as salted PBKDF2-SHA256 hashes
  (240k iterations) — never in plain text.
- Trips live in a SQLite database, one owner per trip. Every read and write is
  scoped to the logged-in account, so accounts cannot see or delete each other's trips.
- Save as many trips per account as you like; opening one restores the whole
  workspace (settings, bucket list, itinerary, packing list) for further edits.
- Logging in reopens your most recently saved trip automatically, and an
  “Unsaved changes / Saved” indicator shows whether the current edits are committed.
- JSON export/import is still there for backups and moving a trip between machines.

**Planning**
- Bucket list with category, priority, estimated cost, duration, notes and coordinates,
  plus search and category filters.
- Schedule any idea onto a day and time; reschedule, unschedule, or remove it later.
- Overlapping stops on the same day are flagged (with a summary when several collide).
- Shortening a trip warns about stops that fall outside the new range and offers to
  move them back to the bucket list.
- Undo for the last deleted item.

**Satellite map**
- Four basemaps: satellite, satellite + place labels, streets, and terrain — rendered
  with pydeck/deck.gl over keyless public tile servers, so **no Mapbox token or API key
  is required**.
- Stops are colour-coded per day, numbered in visiting order, connected by per-day route
  lines, and hoverable for details. Filter to specific days, toggle labels/routes, or
  switch to compact numeric labels when stops sit close together.
- Coordinates can be looked up by name (OpenStreetMap Nominatim) instead of typed, and
  any place still missing coordinates gets a one-click **Locate** button.

**Budget, packing, insights**
- Budget vs. planned spend with per-category and per-day breakdowns and an over-budget alert.
- Packing checklist with quantities and progress.
- Insights: counts by category and priority, planned hours per day, and how many stops
  are mapped.

**Exports** — CSV, `.ics` calendar (with GEO coordinates), and Markdown.

## Running locally

```bash
pip install -r requirements.txt
streamlit run travelplanner.py
```

Create an account on first run. The database file (`travelplanner.db`) is created next to
the app and is git-ignored.

## Notes on deployment

- **Persistence.** Trips are stored in the SQLite file `travelplanner.db`. On hosts with an
  ephemeral filesystem (Streamlit Community Cloud, Render/Heroku free tiers, most container
  platforms) that file is wiped on redeploy or restart, and multiple replicas would each
  get their own copy. For a real deployment, put it on a persistent volume, or point
  `db.py` at a managed Postgres — the storage functions in `db.py` are the only place
  that would need to change. The database path can be overridden with the
  `TRAVELPLANNER_DB` environment variable.
- **Sessions.** Login lives in Streamlit's session state, so refreshing the page logs you
  out and unsaved edits are lost. Save before reloading.
- **Map tiles** are fetched by the viewer's browser. If the imagery stays blank, the
  network is blocking the tile server rather than the app being broken.
- **Place lookup** needs outbound internet. Without it the app says so and you can still
  enter coordinates by hand.
