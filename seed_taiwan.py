"""Seed Taiwan timeline data into Supabase from the existing markdown file."""

import os
import math
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

from data_parser import parse_markdown
from styles import ERA_COLORS, ERA_SHORT_NAMES
from timeline_component import ERA_ORDER, ERA_YEAR_RANGES, ERA_DATE_LABELS, ERA_WIDTHS
from db import (
    _get_client,
    create_country,
    update_country,
    save_eras,
    save_events,
)


def seed():
    DATA_FILE = Path(__file__).parent / "taiwan_timeline.md"
    events = parse_markdown(str(DATA_FILE))
    print(f"Parsed {len(events)} events from markdown")

    # Check if Taiwan already exists
    client = _get_client()
    existing = (
        client.table("countries")
        .select("id")
        .eq("name_lower", "taiwan")
        .limit(1)
        .execute()
    )
    if existing.data:
        country_id = existing.data[0]["id"]
        print(f"Taiwan already exists (id={country_id}), updating...")
    else:
        record = create_country("Taiwan")
        country_id = record["id"]
        print(f"Created Taiwan (id={country_id})")

    # Build eras from the hardcoded Taiwan config
    eras_data = []
    for i, era_name in enumerate(ERA_ORDER):
        year_start, year_end = ERA_YEAR_RANGES.get(era_name, (0, 1))
        # Match to ERA_COLORS
        color = "#666666"
        for key, c in ERA_COLORS.items():
            if key.lower() in era_name.lower() or era_name.lower() in key.lower():
                color = c
                break

        short_name = era_name
        for key, s in ERA_SHORT_NAMES.items():
            if key.lower() in era_name.lower() or era_name.lower() in key.lower():
                short_name = s
                break

        eras_data.append({
            "name": era_name,
            "short_name": short_name,
            "sort_order": i,
            "year_start": year_start,
            "year_end": year_end,
            "date_label": ERA_DATE_LABELS.get(era_name, ""),
            "width_pct": ERA_WIDTHS.get(era_name, 8),
            "color": color,
        })

    save_eras(country_id, eras_data)
    print(f"Saved {len(eras_data)} eras")

    # Build events
    events_data = []
    for evt in events:
        lat, lng = (None, None)
        if evt.coordinates:
            lat, lng = evt.coordinates

        events_data.append({
            "era_name": evt.era,
            "sort_year": evt.sort_year,
            "display_date": evt.display_date,
            "title": evt.title,
            "description": evt.description,
            "categories": evt.categories,
            "lat": lat,
            "lng": lng,
            "is_major": evt.is_major,
        })

    save_events(country_id, events_data)
    print(f"Saved {len(events_data)} events")

    # Update country record
    update_country(
        country_id,
        status="ready",
        center_lat=23.7,
        center_lng=121.0,
        default_zoom=7,
        event_count=len(events_data),
        refreshed_at="now()",
    )
    print("Updated country status to 'ready'")
    print("Done!")


if __name__ == "__main__":
    seed()
