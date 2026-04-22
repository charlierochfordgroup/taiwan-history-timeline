"""Custom horizontal scrollable timeline as a Streamlit v1 bidirectional component."""

import os
import streamlit.components.v1 as components

COMPONENT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "timeline_files")
_timeline_component = components.declare_component("tw_timeline", path=COMPONENT_DIR)


def _match_era(event_era: str, era_names: list[str]) -> str:
    """Match an event's era name to a canonical era from the config."""
    era_lower = event_era.lower()
    for canonical in era_names:
        if canonical.lower() == era_lower:
            return canonical
    # Fuzzy fallback
    for canonical in era_names:
        if canonical.lower() in era_lower or era_lower in canonical.lower():
            return canonical
        for word in canonical.lower().split():
            if len(word) > 4 and word in era_lower:
                return canonical
    return era_names[-1] if era_names else event_era


def _proportional_position(sort_year, year_start, year_end):
    if year_end == year_start:
        return 50.0
    y = max(year_start, min(year_end, sort_year))
    pct = (y - year_start) / (year_end - year_start)
    return 6 + pct * 88


def render_timeline(events, selected_id=None, height=160, eras_config=None):
    """Render the timeline and return clicked event ID or None.

    eras_config: list of dicts with keys: name, short_name, sort_order,
                 year_start, year_end, date_label, width_pct, color
    """
    if not eras_config:
        return None

    era_names = [ec["name"] for ec in eras_config]

    era_events = {}
    for e in events:
        matched = _match_era(e.era, era_names)
        if matched not in era_events:
            era_events[matched] = []
        era_events[matched].append(e)

    segments = []
    for ec in eras_config:
        era = ec["name"]
        width_pct = ec.get("width_pct", 8)
        color = ec.get("color", "#666666")
        era_evts = era_events.get(era, [])
        era_label = ec.get("short_name", era)
        date_label = ec.get("date_label", "")
        year_start = ec.get("year_start", 0)
        year_end = ec.get("year_end", 1)

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
