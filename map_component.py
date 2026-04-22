"""Folium map component for the Taiwan Timeline app."""

import math
import folium
from streamlit_folium import st_folium
from styles import get_era_color


def build_map(events: list, selected_id: int = None, country_config: dict = None) -> folium.Map:
    """Build a dark-themed folium map with event markers."""

    cc = country_config or {}
    center_lat = cc.get("center_lat", 23.7)
    center_lng = cc.get("center_lng", 121.0)
    zoom = cc.get("default_zoom", 7)

    if selected_id is not None:
        for e in events:
            if e.id == selected_id and e.coordinates:
                center_lat, center_lng = e.coordinates
                zoom = 9
                break

    m = folium.Map(
        location=[center_lat, center_lng],
        zoom_start=zoom,
        tiles="cartodbdark_matter",
        zoom_control=False,
        control_scale=False,
    )

    position_counts = {}

    for evt in events:
        if not evt.coordinates:
            continue

        lat, lng = evt.coordinates

        pos_key = (round(lat, 3), round(lng, 3))
        count = position_counts.get(pos_key, 0)
        position_counts[pos_key] = count + 1
        if count > 0:
            angle = count * 0.8
            jitter = 0.008 * count
            lat += jitter * math.cos(angle)
            lng += jitter * math.sin(angle)

        color = get_era_color(evt.era)
        is_selected = selected_id is not None and evt.id == selected_id

        radius = 8 if evt.is_major else 5
        if is_selected:
            radius = 12

        fill_opacity = 0.9 if is_selected else (0.75 if evt.is_major else 0.45)
        border_color = "#4fc3f7" if is_selected else "#00000030"
        weight = 2 if is_selected else 0.5

        # Use regular Marker with DivIcon for clickability
        icon_size = radius * 2 + 4
        icon_html = (
            f'<div style="width:{icon_size}px;height:{icon_size}px;'
            f'background:{color};opacity:{fill_opacity};'
            f'border:{weight}px solid {border_color};'
            f'border-radius:50%;cursor:pointer;"></div>'
        )
        folium.Marker(
            location=[lat, lng],
            icon=folium.DivIcon(
                html=icon_html,
                icon_size=(icon_size, icon_size),
                icon_anchor=(icon_size // 2, icon_size // 2),
            ),
            tooltip=f"{evt.id}|{evt.display_date}: {evt.title}",
        ).add_to(m)

    return m


def render_map(events: list, selected_id: int = None, height: int = 450, country_config: dict = None):
    """Render the folium map in Streamlit and return clicked event id or None."""
    m = build_map(events, selected_id, country_config=country_config)
    map_data = st_folium(
        m,
        height=height,
        width="stretch",
        returned_objects=["last_object_clicked_tooltip"],
    )

    # Parse event id from tooltip text: "ID|date: title"
    if map_data and map_data.get("last_object_clicked_tooltip"):
        tooltip = map_data["last_object_clicked_tooltip"]
        if isinstance(tooltip, str) and "|" in tooltip:
            try:
                eid = int(tooltip.split("|")[0])
                return eid
            except (ValueError, IndexError):
                pass
    return None
