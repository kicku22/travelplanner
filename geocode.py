"""Best-effort place -> coordinates lookup via OpenStreetMap Nominatim.

Uses only the standard library. Network access is optional: if the host has no
outbound internet the caller gets a clear message and can still type
coordinates by hand.
"""
import json
import socket
import urllib.error
import urllib.parse
import urllib.request

ENDPOINT = "https://nominatim.openstreetmap.org/search"
# Nominatim's usage policy requires identifying the application.
USER_AGENT = "travelplanner-itinerary-builder/1.0 (Streamlit trip planner)"
TIMEOUT = 6


class GeocodeUnavailable(Exception):
    """Raised when the lookup service could not be reached."""


def search(query, limit=5):
    """Return [{name, lat, lon}] for a place query, best match first."""
    query = (query or "").strip()
    if not query:
        return []

    url = ENDPOINT + "?" + urllib.parse.urlencode(
        {"q": query, "format": "json", "limit": limit, "addressdetails": 0}
    )
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, socket.timeout, TimeoutError) as exc:
        raise GeocodeUnavailable(
            "Could not reach the place-lookup service. Check the host's internet "
            "access, or enter latitude/longitude manually."
        ) from exc
    except json.JSONDecodeError as exc:
        raise GeocodeUnavailable("Unexpected response from the lookup service.") from exc

    results = []
    for entry in payload:
        try:
            results.append({
                "name": entry.get("display_name", query),
                "lat": float(entry["lat"]),
                "lon": float(entry["lon"]),
            })
        except (KeyError, TypeError, ValueError):
            continue
    return results
