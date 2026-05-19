"""Wikipedia fetch + Claude extraction + Supabase storage for new countries.

Phase 4 of the Chronoscape multi-country pipeline. One pipeline run per country:

    fetch_wikipedia(name)  ->  extract_with_claude(name, text)  ->  store_results()

Per-country cost estimate (claude-sonnet-4-6, ~25k input / ~12k output):
  Input  ~25k × $3/M  = $0.075
  Output ~12k × $15/M = $0.18
  Total                = ~$0.25 per country, ~$13 for a 50-country monthly refresh.

The SDK auto-retries 429s and 5xx errors with exponential backoff (default
max_retries=2). The retry budget is set explicitly here so future tuning is
obvious. Anything else (network drops, schema-violation JSON, Wikipedia
missing-page errors) bubbles up to run_pipeline() which marks the job failed.
"""

import json
import time
from pathlib import Path

import requests
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

from db import (
    create_country,
    create_generation_job,
    get_country,
    save_eras,
    save_events,
    update_country,
    update_generation_job,
)
from styles import ERA_PALETTE


WIKI_API = "https://en.wikipedia.org/w/api.php"
USER_AGENT = (
    "Chronoscape/2.0 (Educational history timeline; "
    "charlie.t@rochford-group.com)"
)

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 16000

# Sonnet 4.6 pricing (per Anthropic pricing as of 2026-05; verify in production)
SONNET_INPUT_USD_PER_M = 3.0
SONNET_OUTPUT_USD_PER_M = 15.0

WIKI_RATE_LIMIT_SECONDS = 1.0
WIKI_MAX_COMBINED_CHARS = 80_000


# ---------- Wikipedia fetch ----------

def _wiki_get_extract(title: str) -> str:
    """Fetch plain-text extract for one Wikipedia article. Empty string if missing."""
    params = {
        "action": "query",
        "format": "json",
        "prop": "extracts",
        "titles": title,
        "explaintext": "1",
        "redirects": "1",
    }
    r = requests.get(
        WIKI_API,
        params=params,
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    r.raise_for_status()
    pages = r.json().get("query", {}).get("pages", {})
    for _, page in pages.items():
        if page.get("missing") is not None:
            return ""
        return page.get("extract", "") or ""
    return ""


def fetch_wikipedia(country_name: str) -> tuple[str, list[str]]:
    """Fetch 4-5 history-relevant Wikipedia articles.

    Tries the most-common naming patterns ("History of X", "X", "Timeline of X
    history", etc.). Rate-limited to 1 req/sec. Combined output truncated to
    80k chars to stay well under Sonnet's 200k context window.

    Returns (combined_text, list_of_article_titles_actually_used).
    """
    candidate_titles = [
        f"History of {country_name}",
        country_name,
        f"Timeline of {country_name} history",
        f"Timeline of {country_name}n history",
        f"Early history of {country_name}",
        f"Modern history of {country_name}",
    ]

    sources: list[str] = []
    combined_parts: list[str] = []

    for title in candidate_titles:
        if sum(len(p) for p in combined_parts) > WIKI_MAX_COMBINED_CHARS:
            break
        try:
            text = _wiki_get_extract(title)
            if text and len(text) > 1000:
                combined_parts.append(f"=== {title} ===\n{text}")
                sources.append(title)
        except Exception:
            # One missing article is fine - try the next candidate
            pass
        time.sleep(WIKI_RATE_LIMIT_SECONDS)

    if not combined_parts:
        return "", []

    out = "\n\n".join(combined_parts)
    if len(out) > WIKI_MAX_COMBINED_CHARS:
        out = out[:WIKI_MAX_COMBINED_CHARS]
    return out, sources


# ---------- Claude extraction ----------

EXTRACTION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["country", "eras", "events"],
    "properties": {
        "country": {
            "type": "object",
            "additionalProperties": False,
            "required": ["name", "center_lat", "center_lng", "default_zoom"],
            "properties": {
                "name": {"type": "string"},
                "center_lat": {"type": "number"},
                "center_lng": {"type": "number"},
                "default_zoom": {"type": "integer"},
            },
        },
        "eras": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "name", "short_name", "sort_order",
                    "year_start", "year_end", "date_label",
                    "width_pct", "color",
                ],
                "properties": {
                    "name": {"type": "string"},
                    "short_name": {"type": "string"},
                    "sort_order": {"type": "integer"},
                    "year_start": {"type": "number"},
                    "year_end": {"type": "number"},
                    "date_label": {"type": "string"},
                    "width_pct": {"type": "integer"},
                    "color": {"type": "string"},
                },
            },
        },
        "events": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "era_name", "sort_year", "display_date",
                    "title", "description", "categories",
                    "lat", "lng", "is_major",
                ],
                "properties": {
                    "era_name": {"type": "string"},
                    "sort_year": {"type": "number"},
                    "display_date": {"type": "string"},
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "categories": {"type": "array", "items": {"type": "string"}},
                    "lat": {"type": ["number", "null"]},
                    "lng": {"type": ["number", "null"]},
                    "is_major": {"type": "boolean"},
                },
            },
        },
    },
}


def _build_extraction_prompt(country_name: str, wiki_text: str) -> str:
    palette = ", ".join(ERA_PALETTE)
    return f"""Extract structured historical data for an interactive timeline of {country_name}.

Schema overview (full JSON schema is enforced server-side, output is guaranteed valid):

- country: name, center_lat (geographic centre, decimal degrees), center_lng,
    default_zoom (use 4 for very large countries like Russia or China, 5 for large
    countries, 6-7 for medium, 8+ for small island nations).

- eras: 5-12 distinct historical periods covering the full national timeline.
    Each era needs:
    * name: full era name (e.g. "Ming Dynasty Rule").
    * short_name: ≤15-char timeline-tag label (e.g. "Ming").
    * sort_order: integer 0..N in chronological order.
    * year_start, year_end: numeric years (negative for BCE; fractional allowed).
    * date_label: human label e.g. "1644-1912" or "1949-present".
    * width_pct: integer proportional display width. All eras together should
        sum to roughly 100. Use log-scaled widths so short eras don't disappear.
    * color: one hex code from the palette below. Each era must use a distinct
        colour. Choose colours that fit the era's character (warmer for unrest
        and conflict, cooler for stable or settled periods).

- events: aim for 80-150 events spread across all eras. Flag 10-25 as
    is_major: true for the genuinely pivotal moments. Each event:
    * era_name: must exactly match one of eras.name above.
    * sort_year: numeric year for ordering (negative for BCE; fractional for
        sub-year precision, e.g. 1944.46 for 17 June 1944).
    * display_date: human-readable, e.g. "c. 325 BCE", "10 May 1940", "1944",
        "mid-17th century".
    * title: ≤12 words.
    * description: 1-3 sentences. Australian English spelling. Hyphens only -
        no em dashes, no en dashes.
    * categories: subset of [Military, Political, Economic, Indigenous,
        Foreign Relations, Cultural, Social, Scientific, Religious]. Most
        events have 1-2 categories.
    * lat, lng: specific coordinates if the event has a clear location
        (a city, battlefield, signing site). null if the event is national or
        diffuse.
    * is_major: true for pivotal/turning-point events.

Era colour palette (use exactly one of these per era):
{palette}

Source articles (raw Wikipedia text follows):

{wiki_text}
"""


def extract_with_claude(country_name: str, wiki_text: str) -> tuple[dict, dict]:
    """Send Wikipedia text to Claude Sonnet, parse the structured JSON response.

    Returns (data_dict, usage_dict). The SDK auto-retries 429s and 5xx errors
    with exponential backoff. Anything else (auth, schema violation, JSON
    parse failure) raises and bubbles up to run_pipeline().
    """
    client = Anthropic(max_retries=3)

    prompt = _build_extraction_prompt(country_name, wiki_text)

    msg = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        thinking={"type": "disabled"},
        output_config={
            "format": {"type": "json_schema", "schema": EXTRACTION_SCHEMA},
        },
        messages=[{"role": "user", "content": prompt}],
    )

    text = next(b.text for b in msg.content if b.type == "text")
    data = json.loads(text)

    usage = {
        "input_tokens": msg.usage.input_tokens,
        "output_tokens": msg.usage.output_tokens,
    }
    return data, usage


def _estimate_cost_usd(input_tokens: int, output_tokens: int) -> float:
    return (
        input_tokens * SONNET_INPUT_USD_PER_M
        + output_tokens * SONNET_OUTPUT_USD_PER_M
    ) / 1_000_000


# ---------- Storage (reuses db.py helpers - same shape as iceland_data.json) ----------

def store_results(country_id: str, extraction: dict):
    """Persist extraction to Supabase. Reuses save_eras / save_events from db.py."""
    country_meta = extraction["country"]
    eras = extraction["eras"]
    events = extraction["events"]

    save_eras(country_id, eras)
    save_events(country_id, events)

    update_country(
        country_id,
        status="ready",
        center_lat=country_meta["center_lat"],
        center_lng=country_meta["center_lng"],
        default_zoom=country_meta.get("default_zoom", 6),
        event_count=len(events),
        refreshed_at="now()",
    )


# ---------- Orchestrator ----------

def run_pipeline(country_name: str):
    """End-to-end. Tracks the run in generation_jobs.

    On success: country.status = 'ready', job.status = 'completed'.
    On failure: country.status = 'failed', job.status = 'failed' with error_message.
    """
    country = get_country(country_name)
    if not country:
        country = create_country(country_name)
    country_id = country["id"]

    job_type = "refresh" if country.get("refreshed_at") else "initial"
    job = create_generation_job(country_id, job_type=job_type)
    job_id = job["id"]

    try:
        wiki_text, sources = fetch_wikipedia(country_name)
        if not wiki_text:
            raise RuntimeError(f"No Wikipedia content found for '{country_name}'.")

        extraction, usage = extract_with_claude(country_name, wiki_text)

        store_results(country_id, extraction)

        update_generation_job(
            job_id,
            status="completed",
            wiki_pages=sources,
            input_tokens=usage["input_tokens"],
            output_tokens=usage["output_tokens"],
            cost_usd=_estimate_cost_usd(usage["input_tokens"], usage["output_tokens"]),
            completed_at="now()",
        )
    except Exception as ex:
        update_country(country_id, status="failed")
        update_generation_job(
            job_id,
            status="failed",
            error_message=str(ex)[:500],
            completed_at="now()",
        )
        raise


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python pipeline.py <country-name>")
        sys.exit(1)
    run_pipeline(sys.argv[1])
    print(f"Pipeline complete for {sys.argv[1]}.")
