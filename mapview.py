"""Satellite / street map rendering for itinerary locations.

Uses a pydeck TileLayer pointed at keyless public tile servers, so no Mapbox
token or API key is needed. `map_provider=None` stops pydeck from trying to
load its own default basemap underneath.
"""
import pydeck as pdk

# Esri templates use {z}/{y}/{x}; OSM uses {z}/{x}/{y}. deck.gl substitutes both.
BASEMAPS = {
    "🛰️ Satellite + labels": {
        "url": "https://server.arcgisonline.com/ArcGIS/rest/services/"
               "World_Imagery/MapServer/tile/{z}/{y}/{x}",
        "overlay": "https://server.arcgisonline.com/ArcGIS/rest/services/"
                   "Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
        "max_zoom": 19,
        "attribution": "Imagery © Esri, Maxar, Earthstar Geographics · Labels © Esri",
    },
    "🛰️ Satellite": {
        "url": "https://server.arcgisonline.com/ArcGIS/rest/services/"
               "World_Imagery/MapServer/tile/{z}/{y}/{x}",
        "max_zoom": 19,
        "attribution": "Imagery © Esri, Maxar, Earthstar Geographics",
    },
    "🗺️ Streets": {
        "url": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        "max_zoom": 19,
        "attribution": "© OpenStreetMap contributors",
    },
    "⛰️ Terrain": {
        "url": "https://server.arcgisonline.com/ArcGIS/rest/services/"
               "World_Topo_Map/MapServer/tile/{z}/{y}/{x}",
        "max_zoom": 19,
        "attribution": "© Esri",
    },
}

DEFAULT_BASEMAP = "🛰️ Satellite + labels"


def hex_to_rgb(value, alpha=255):
    value = str(value).lstrip("#")
    return [int(value[i:i + 2], 16) for i in (0, 2, 4)] + [alpha]


def view_state_for(points):
    """Center on the points and pick a zoom that fits their spread."""
    if not points:
        return pdk.ViewState(latitude=20.0, longitude=0.0, zoom=1.3, pitch=0, bearing=0)

    lats = [p["lat"] for p in points]
    lons = [p["lon"] for p in points]
    center_lat = (min(lats) + max(lats)) / 2
    center_lon = (min(lons) + max(lons)) / 2
    spread = max(max(lats) - min(lats), max(lons) - min(lons))

    for limit, zoom in ((0.005, 15.0), (0.02, 13.5), (0.1, 11.5), (0.5, 9.5),
                        (2.0, 7.5), (10.0, 5.0)):
        if spread < limit:
            break
    else:
        zoom = 2.8
    return pdk.ViewState(latitude=center_lat, longitude=center_lon, zoom=zoom,
                         pitch=35, bearing=0)


def build_deck(points, routes=None, basemap=DEFAULT_BASEMAP, show_labels=True,
               show_routes=True):
    """Build a pydeck Deck for the given locations.

    points: dicts with lat, lon, name, label, color (hex), meta
    routes: dicts with path ([[lon, lat], ...]) and color (hex)
    """
    config = BASEMAPS.get(basemap, BASEMAPS[DEFAULT_BASEMAP])

    layers = [
        pdk.Layer(
            "TileLayer",
            data=config["url"],
            min_zoom=0,
            max_zoom=config["max_zoom"],
            tile_size=256,
            pickable=False,
        )
    ]

    # Place-name / boundary labels drawn over the imagery.
    if config.get("overlay"):
        layers.append(
            pdk.Layer(
                "TileLayer",
                data=config["overlay"],
                min_zoom=0,
                max_zoom=config["max_zoom"],
                tile_size=256,
                pickable=False,
            )
        )

    if show_routes and routes:
        layers.append(
            pdk.Layer(
                "PathLayer",
                data=[
                    {"path": r["path"], "colorRGBA": hex_to_rgb(r["color"], 210),
                     "name": r.get("name", "")}
                    for r in routes if len(r.get("path", [])) > 1
                ],
                get_path="path",
                get_color="colorRGBA",
                # Width is clamped in pixels rather than set via widthUnits:
                # 'pixels' units are mis-scaled by the bundled deck.gl build.
                get_width=1,
                width_min_pixels=3,
                width_max_pixels=3,
                rounded=True,
                pickable=False,
            )
        )

    marker_data = [
        {
            "position": [p["lon"], p["lat"]],
            "name": p["name"],
            "label": p.get("label", ""),
            "meta": p.get("meta", ""),
            "fillRGBA": hex_to_rgb(p.get("color", "#7c6cff"), 235),
        }
        for p in points
    ]

    # Marker sizes are pinned by clamping min == max pixels. Setting
    # radiusUnits='pixels' instead makes the bundled deck.gl build blow the
    # radius up until it floods the whole canvas.
    layers.append(
        # Soft glow ring behind each marker so pins stay legible over imagery.
        pdk.Layer(
            "ScatterplotLayer",
            data=marker_data,
            get_position="position",
            get_fill_color="fillRGBA",
            get_radius=1,
            radius_min_pixels=14,
            radius_max_pixels=14,
            opacity=0.25,
            stroked=False,
            pickable=False,
        )
    )
    layers.append(
        pdk.Layer(
            "ScatterplotLayer",
            data=marker_data,
            get_position="position",
            get_fill_color="fillRGBA",
            get_line_color=[255, 255, 255, 240],
            get_radius=1,
            radius_min_pixels=7,
            radius_max_pixels=7,
            line_width_min_pixels=2,
            stroked=True,
            filled=True,
            pickable=True,
            auto_highlight=True,
        )
    )

    if show_labels:
        # Legibility comes from a solid background box rather than an SDF
        # outline: enabling fontSettings.sdf together with a custom
        # font_family/font_weight collapses the glyphs in this deck.gl build.
        # character_set is deliberately left at deck.gl's default ASCII atlas —
        # passing one (as a list or a string) breaks the layer outright. Labels
        # outside that range fall back to blanks, but the hover tooltip is HTML
        # and always shows the full name.
        layers.append(
            pdk.Layer(
                "TextLayer",
                data=marker_data,
                get_position="position",
                get_text="label",
                get_size=13,
                get_color=[255, 255, 255, 250],
                get_alignment_baseline="'top'",
                get_text_anchor="'middle'",
                get_pixel_offset=[0, 15],
                background=True,
                get_background_color=[8, 12, 28, 205],
                background_padding=[7, 4],
                pickable=False,
            )
        )

    return pdk.Deck(
        layers=layers,
        initial_view_state=view_state_for(points),
        # No provider/style: the basemap is our own TileLayer, so nothing should
        # try to fetch a Mapbox or Carto style sheet.
        map_provider=None,
        map_style=None,
        tooltip={
            "html": "<b>{name}</b><br/><span style='opacity:.8'>{meta}</span>",
            "style": {
                "backgroundColor": "rgba(10,14,30,0.94)",
                "color": "#eaf0ff",
                "border": "1px solid rgba(255,255,255,0.16)",
                "borderRadius": "10px",
                "padding": "8px 10px",
                "fontSize": "12px",
            },
        },
    )


def attribution(basemap=DEFAULT_BASEMAP):
    return BASEMAPS.get(basemap, BASEMAPS[DEFAULT_BASEMAP])["attribution"]
