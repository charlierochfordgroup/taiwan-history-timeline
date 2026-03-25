"""Custom horizontal scrollable timeline as a Streamlit v1 bidirectional component."""

import os
import streamlit.components.v1 as components
from styles import get_era_color

COMPONENT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "timeline_files")
_timeline_component = components.declare_component("tw_timeline", path=COMPONENT_DIR)

ERA_ORDER = [
    "Prehistory & Early Settlement",
    "Chinese Contact & Early Settlement",
    "Dutch & Spanish Colonial Period",
    "Koxinga & the Kingdom of Tungning",
    "Qing Dynasty Rule",
    "Republic of Formosa",
    "Japanese Colonial Rule",
    "Return of Chinese Rule & the White Terror",
    "Democratisation",
    "Modern Taiwan",
]

ERA_SHORT_LABELS = {
    "Prehistory & Early Settlement": "Prehistory",
    "Chinese Contact & Early Settlement": "Early Chinese",
    "Dutch & Spanish Colonial Period": "Dutch & Spanish",
    "Koxinga & the Kingdom of Tungning": "Koxinga",
    "Qing Dynasty Rule": "Qing Dynasty",
    "Republic of Formosa": "Rep. Formosa",
    "Japanese Colonial Rule": "Japanese Rule",
    "Return of Chinese Rule & the White Terror": "White Terror",
    "Democratisation": "Democratisation",
    "Modern Taiwan": "Modern",
}

ERA_YEAR_RANGES = {
    "Prehistory & Early Settlement": (-450000, 400),
    "Chinese Contact & Early Settlement": (230, 1623),
    "Dutch & Spanish Colonial Period": (1624, 1662),
    "Koxinga & the Kingdom of Tungning": (1661, 1683),
    "Qing Dynasty Rule": (1683, 1895),
    "Republic of Formosa": (1895, 1895),
    "Japanese Colonial Rule": (1895, 1945),
    "Return of Chinese Rule & the White Terror": (1945, 1987),
    "Democratisation": (1971, 2000),
    "Modern Taiwan": (2000, 2025),
}

ERA_DATE_LABELS = {
    "Prehistory & Early Settlement": "450,000 BC",
    "Chinese Contact & Early Settlement": "230 AD",
    "Dutch & Spanish Colonial Period": "1624",
    "Koxinga & the Kingdom of Tungning": "1661",
    "Qing Dynasty Rule": "1683",
    "Republic of Formosa": "1895",
    "Japanese Colonial Rule": "1895",
    "Return of Chinese Rule & the White Terror": "1945",
    "Democratisation": "1971",
    "Modern Taiwan": "2000",
}

ERA_WIDTHS = {
    "Prehistory & Early Settlement": 8,
    "Chinese Contact & Early Settlement": 8,
    "Dutch & Spanish Colonial Period": 11,
    "Koxinga & the Kingdom of Tungning": 8,
    "Qing Dynasty Rule": 14,
    "Republic of Formosa": 5,
    "Japanese Colonial Rule": 14,
    "Return of Chinese Rule & the White Terror": 14,
    "Democratisation": 10,
    "Modern Taiwan": 8,
}


def _match_era(event_era):
    era_lower = event_era.lower()
    for canonical in ERA_ORDER:
        if canonical.lower() in era_lower or era_lower in canonical.lower():
            return canonical
        for word in canonical.lower().split():
            if len(word) > 4 and word in era_lower:
                return canonical
    return ERA_ORDER[-1]


def _proportional_position(sort_year, year_start, year_end):
    if year_end == year_start:
        return 50.0
    y = max(year_start, min(year_end, sort_year))
    pct = (y - year_start) / (year_end - year_start)
    return 6 + pct * 88


def render_timeline(events, selected_id=None, height=160):
    """Render the timeline and return clicked event ID or None."""
    era_events = {}
    for e in events:
        matched = _match_era(e.era)
        if matched not in era_events:
            era_events[matched] = []
        era_events[matched].append(e)

    segments = []
    for era in ERA_ORDER:
        width_pct = ERA_WIDTHS.get(era, 8)
        color = get_era_color(era)
        era_evts = era_events.get(era, [])
        era_label = ERA_SHORT_LABELS.get(era, era)
        date_label = ERA_DATE_LABELS.get(era, "")
        year_start, year_end = ERA_YEAR_RANGES.get(era, (0, 1))

        dots = []
        if era_evts:
            era_evts.sort(key=lambda e: e.sort_year)
            for evt in era_evts:
                left_pct = _proportional_position(evt.sort_year, year_start, year_end)
                is_sel = selected_id is not None and evt.id == selected_id
                dots.append({
                    "id": evt.id,
                    "left": round(left_pct, 2),
                    "major": evt.is_major,
                    "selected": is_sel,
                    "tooltip": f"{evt.display_date}: {evt.title}",
                })

        segments.append({
            "width_pct": width_pct,
            "color": color,
            "era_label": era_label,
            "date_label": date_label,
            "dots": dots,
        })

    result = _timeline_component(
        segments=segments,
        selected_id=selected_id,
        height=height,
        key="timeline",
        default=None,
    )
    return result
