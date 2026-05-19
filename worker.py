"""Background worker for country generation jobs.

Wraps pipeline.run_pipeline in a daemon thread spawned from the Streamlit
process. MVP-grade - daemon threads die with the parent process, so app
startup also runs recover_stuck_jobs() to flip stuck 'generating' rows back
to 'failed' so the UI can offer a retry button.

For production this would be a separate worker process (or a GitHub Actions
job triggered by a `status='generating'` row), but daemon threads are
adequate for a side project with maybe one generation per day.
"""

import threading
from datetime import datetime, timedelta, timezone

from db import _get_client, update_country
from pipeline import run_pipeline


# Tracks live threads so recover_stuck_jobs() doesn't clobber an in-flight job
# in the same process. Streamlit reruns the script but the module-level dict
# survives because the process doesn't restart.
_active_threads: dict[str, threading.Thread] = {}


def generate_in_background(country_name: str) -> threading.Thread:
    """Spawn run_pipeline in a daemon thread. Returns the thread handle.

    If a thread is already running for this country in this process,
    returns the existing handle instead of starting a duplicate.
    """
    existing = _active_threads.get(country_name)
    if existing is not None and existing.is_alive():
        return existing

    t = threading.Thread(
        target=_run_safe,
        args=(country_name,),
        daemon=True,
        name=f"chronoscape-pipeline-{country_name}",
    )
    _active_threads[country_name] = t
    t.start()
    return t


def _run_safe(country_name: str):
    """Wrap run_pipeline so unhandled exceptions don't kill the worker silently."""
    try:
        run_pipeline(country_name)
    except Exception as ex:
        # Pipeline already marked the row failed via update_country; log for ops
        print(f"[worker] {country_name} generation failed: {ex}")


def recover_stuck_jobs(stale_minutes: int = 10) -> int:
    """Find countries stuck in 'generating' for >stale_minutes and reset to 'failed'.

    Called once on app startup. Streamlit Cloud or a local restart can kill
    daemon threads mid-job; this lets the UI offer a retry button instead of
    showing 'generating' forever.

    Returns the number of countries recovered.
    """
    client = _get_client()
    cutoff = (
        datetime.now(timezone.utc) - timedelta(minutes=stale_minutes)
    ).isoformat()

    result = (
        client.table("countries")
        .select("id, name, created_at")
        .eq("status", "generating")
        .lt("created_at", cutoff)
        .execute()
    )

    recovered = 0
    for c in result.data or []:
        # Skip ones we're still working on in this process
        live = _active_threads.get(c["name"])
        if live is not None and live.is_alive():
            continue
        print(f"[worker] Recovering stuck country: {c['name']}")
        update_country(c["id"], status="failed")
        recovered += 1
    return recovered
