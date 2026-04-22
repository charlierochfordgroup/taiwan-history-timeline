"""Supabase client wrapper for the History Timeline app."""

import os
from supabase import create_client, Client
from event_data import TimelineEvent


def _get_client() -> Client:
    """Create a Supabase client from environment variables."""
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_KEY", "")
    if not url or not key:
        try:
            import streamlit as st
            url = url or st.secrets.get("SUPABASE_URL", "")
            key = key or st.secrets.get("SUPABASE_KEY", "")
        except Exception:
            pass
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set")
    return create_client(url, key)


def get_country(name: str) -> dict | None:
    """Look up a country by name (case-insensitive). Returns dict or None."""
    client = _get_client()
    result = (
        client.table("countries")
        .select("*")
        .eq("name_lower", name.strip().lower())
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def list_countries() -> list[dict]:
    """Return all countries with status='ready', sorted by name."""
    client = _get_client()
    result = (
        client.table("countries")
        .select("name, name_lower, status, event_count")
        .eq("status", "ready")
        .order("name")
        .execute()
    )
    return result.data or []


def create_country(name: str) -> dict:
    """Insert a new country record with status='generating'."""
    client = _get_client()
    result = (
        client.table("countries")
        .insert({
            "name": name.strip(),
            "name_lower": name.strip().lower(),
            "status": "generating",
        })
        .execute()
    )
    return result.data[0]


def update_country(country_id: str, **fields) -> dict:
    """Update arbitrary fields on a country record."""
    client = _get_client()
    result = (
        client.table("countries")
        .update(fields)
        .eq("id", country_id)
        .execute()
    )
    return result.data[0] if result.data else {}


def get_eras(country_id: str) -> list[dict]:
    """Get all eras for a country, ordered by sort_order."""
    client = _get_client()
    result = (
        client.table("eras")
        .select("*")
        .eq("country_id", country_id)
        .order("sort_order")
        .execute()
    )
    return result.data or []


def get_events(country_id: str) -> list[dict]:
    """Get all events for a country, ordered by sort_year."""
    client = _get_client()
    result = (
        client.table("events")
        .select("*")
        .eq("country_id", country_id)
        .order("sort_year")
        .execute()
    )
    return result.data or []


def save_eras(country_id: str, eras: list[dict]):
    """Delete existing eras and insert new ones for a country."""
    client = _get_client()
    client.table("eras").delete().eq("country_id", country_id).execute()
    if eras:
        rows = [{**e, "country_id": country_id} for e in eras]
        client.table("eras").insert(rows).execute()


def save_events(country_id: str, events: list[dict]):
    """Delete existing events and insert new ones for a country."""
    client = _get_client()
    client.table("events").delete().eq("country_id", country_id).execute()
    if events:
        # Insert in batches of 500 to avoid payload limits
        rows = [{**e, "country_id": country_id} for e in events]
        for i in range(0, len(rows), 500):
            client.table("events").insert(rows[i:i+500]).execute()


def create_generation_job(country_id: str, job_type: str = "initial") -> dict:
    """Create a new generation job record."""
    client = _get_client()
    result = (
        client.table("generation_jobs")
        .insert({
            "country_id": country_id,
            "job_type": job_type,
            "status": "running",
        })
        .execute()
    )
    return result.data[0]


def update_generation_job(job_id: str, **fields) -> dict:
    """Update a generation job record."""
    client = _get_client()
    result = (
        client.table("generation_jobs")
        .update(fields)
        .eq("id", job_id)
        .execute()
    )
    return result.data[0] if result.data else {}


def load_country_data(country_name: str) -> tuple:
    """Load a country's full data from Supabase.

    Returns (events: list[TimelineEvent], eras_config: list[dict], country_config: dict)
    or (None, None, None) if the country doesn't exist or isn't ready.
    """
    country = get_country(country_name)
    if not country or country["status"] != "ready":
        return None, None, country

    eras_config = get_eras(country["id"])
    raw_events = get_events(country["id"])

    events = []
    for i, e in enumerate(raw_events):
        coords = None
        if e.get("lat") is not None and e.get("lng") is not None:
            coords = (e["lat"], e["lng"])
        events.append(
            TimelineEvent(
                id=i,
                raw_date=e.get("display_date", ""),
                sort_year=e["sort_year"],
                display_date=e["display_date"],
                title=e["title"],
                description=e.get("description", ""),
                era=e["era_name"],
                categories=e.get("categories", []),
                coordinates=coords,
                is_major=e.get("is_major", False),
            )
        )

    country_config = {
        "name": country["name"],
        "center_lat": country.get("center_lat", 0),
        "center_lng": country.get("center_lng", 0),
        "default_zoom": country.get("default_zoom", 5),
    }

    return events, eras_config, country_config
