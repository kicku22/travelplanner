# travelplanner

A Streamlit app for planning a trip: capture ideas in a bucket list, schedule them into a day-by-day itinerary, and track budget and packing along the way. Trips are saved to disk so you can pick up editing later.

## Features

- **Immersive UI** — a gradient hero banner shows the current trip name, destination, and departure countdown; pill-style tabs and card-based layouts throughout.
- **My Trips (persistent storage)** — save the current trip locally with one click, reload any saved trip to keep editing it, start a fresh trip, or delete a saved one — no manual file handling required. Saved trips live in `saved_trips/` (git-ignored) as JSON, keyed by trip name.
- **Trip settings** — name, destination, start date, trip length, currency, and total budget, with a countdown to departure.
- **Bucket list** — capture places with category, priority, notes, estimated cost, duration, and optional coordinates; search and filter before scheduling.
- **Itinerary** — schedule bucket-list items onto a day/time, edit or reschedule them in place, unschedule back to the bucket list, or remove them entirely. Overlapping items on the same day are flagged with a conflict warning.
- **Budget tracker** — total budget vs. planned spend, a progress bar, an over-budget warning, and a spend-by-category breakdown chart.
- **Packing list** — a simple checklist with quantities and packed/unpacked progress.
- **Trip stats** — counts by category and priority, total planned time, and a fill-rate chart per day.
- **Map** — any itinerary item with latitude/longitude renders on a map.
- **Export** — download the itinerary as CSV, an `.ics` calendar file (importable into Google/Apple/Outlook calendars), or Markdown.
- **Backup / transfer** — export the entire trip as a portable JSON file and re-import it on another machine, in addition to the in-app "My Trips" storage.
- **Undo** — restore the most recently deleted bucket-list or itinerary item.

## Running locally

```bash
pip install -r requirements.txt
streamlit run travelplanner.py
```
