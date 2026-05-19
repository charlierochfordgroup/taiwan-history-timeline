# TODO - Chronoscape (multi-country history timeline)

Last updated: 2026-05-19
Current branch: `master` (synced to GitHub `main`)
GitHub: `charlierochfordgroup/chronoscape`
Deployed: `https://chronoscape.streamlit.app/` (live, chip-only Taiwan + Iceland)

---

## Outstanding

### Activating Phase 4 generation (when ready to spend on Anthropic API)

The chip-only picker (v2.x) deliberately hides the free-text country input until Phase 4 generation is wired through Streamlit Cloud. All the code exists - just needs keys and a UI nudge. Steps when you're ready:

- [ ] **Get an Anthropic API key** from https://console.anthropic.com/ and add `ANTHROPIC_API_KEY=sk-ant-...` to local `.env`.
- [ ] **Add to Streamlit Cloud Secrets** (Option A architecture: in-process worker writes via service_role):
  ```toml
  SUPABASE_URL = "..."
  SUPABASE_KEY = "..."  # anon, for reads
  SUPABASE_SERVICE_ROLE_KEY = "..."  # required so worker.py can write
  ANTHROPIC_API_KEY = "sk-ant-..."
  ```
- [ ] **Re-enable the free-text input in app.py** - search for "chip-only country picker" comment block and restore the `st.text_input` with `on_change=_on_country_change` callback. The generating/failed/retry branches are still in load logic, just unreachable from the chip-only UI.
- [ ] **End-to-end test**: type "Japan" in `https://chronoscape.streamlit.app/`, wait 30-60s, verify timeline renders. Check the `generation_jobs` row for token counts and cost (~$0.25 expected per country).

### Phase 2 follow-ups from verification

- [ ] **Card click doesn't select event** - have to click the "View details ->" link instead. Investigate whether the card was intended to be clickable; if so, fix the click handler. Low priority - functionality works via the link.
- [ ] **Confirm timeline-dot and map-marker click selection both work** - only verified the list-item path in this session.

### Phase 3 - Multi-country app shell polish

- [ ] Loading state UI (currently just `st.info + sleep(5) + st.rerun()`) - make it nicer with a progress indicator / stage description.
- [ ] Error state UI with retry button - test the failed-generation path works.
- [ ] Empty state / welcome screen on first load (already in app.py, but visually polish).
- [ ] Country autocomplete from existing DB entries (`list_countries()` already in db.py, just wire it up).

### Phase 5 - Polish (after Phase 4 is activated)

- [ ] Stale-data refresh logic: if `refreshed_at` > 14 days, serve stale + queue background refresh.
- [ ] Cost tracking: populate `generation_jobs.input_tokens`, `output_tokens`, `cost_usd` after each pipeline run.
- [ ] Feature flag: only refresh countries viewed in the past month to cap monthly cost.

---

## Done

### Phase 1 - Database Foundation (2026-04-14)
- Created Supabase project `xbhhdpcbrsgmactfuxlq` (us-east-1, free tier).
- Created 4 tables with indexes + FK cascades: countries, eras, events, generation_jobs.
- Built `db.py` with full query wrapper.
- Seeded Taiwan data from existing markdown (166 events, 10 eras, status=ready, centre 23.7/121.0).

### Phase 2 - Code generalisation + verification (2026-04-22, verified 2026-05-19)
- Stripped Taiwan-specific data out of `event_data.py`, `styles.py`, `timeline_component.py`, `map_component.py`.
- Added runtime-config pattern: `set_era_config(eras)` populates `_era_color_map` / `_era_short_map`.
- 15-colour `ERA_PALETTE` for dynamic assignment.
- Universal category list (added Social, Scientific, Religious; kept Aboriginal as alias to Indigenous).
- `render_timeline()` now takes `eras_config` param, `render_map()` takes `country_config`.
- `app.py` rewritten with country search bar at top, dynamic header + filters + colour key, loading/error state UI.
- **Verified end-to-end (2026-05-19)** via Claude in Chrome: Taiwan loads from DB (166 events, 10 eras, all renderers work), Iceland loads from DB (92 events, 10 eras), country-switch via search bar works, event selection via list works, detail panel populates, map markers render with tooltip-encoded IDs.

### Iceland seeded (2026-05-19)
- Hand-extracted 92 events / 10 eras from the Wikipedia History of Iceland article (Charlie pasted the text in chat).
- Pre-Settlement -> Settlement Age (874-930) -> Commonwealth (930-1262) -> Norwegian Rule -> Kalmar Union -> Danish Rule and Trade Monopoly -> Path to Independence -> Kingdom of Iceland -> Cold War Republic -> Modern Republic.
- 32 major events, 25 with map coordinates, centre 64.96 / -19.02, zoom 6.
- Created `iceland_data.json` (raw structured data) and generic `seed_country.py` (loads a JSON of this shape and inserts into Supabase) - the latter is the storage-layer prototype that Phase 4 `pipeline.py` will reuse.

### Phase 4 - Data pipeline shipped (2026-05-19)
- `pipeline.py` with `fetch_wikipedia()` (4-5 articles, 1 req/sec, 80k char cap), `extract_with_claude()` (claude-sonnet-4-6, structured output via `output_config.format` with full JSON schema enforcement, thinking disabled, max_tokens 16000), `store_results()` (reuses save_eras / save_events from db.py), `run_pipeline()` orchestrator with full job tracking in `generation_jobs` (input_tokens, output_tokens, cost_usd, wiki_pages, error_message).
- `worker.py` with `generate_in_background()` (threading.Thread daemon, dedupe via `_active_threads` so duplicate clicks don't spawn parallel workers), `recover_stuck_jobs()` (resets `status='generating'` rows older than 10min to `'failed'` so UI offers retry).
- `app.py` calls `recover_stuck_jobs()` once per Streamlit process on first load (gated by session_state flag, doesn't block on failure).
- Per-country cost ~$0.25 (Sonnet 4.6 pricing). 50-country monthly refresh ~$13.
- **Untested end-to-end** because ANTHROPIC_API_KEY is still empty in `.env` - that's the only blocker.

### Hardening (2026-05-19)
- **RLS enabled** on all 4 tables. anon + authenticated roles get SELECT only; service_role bypasses for writes. Future seeds and `pipeline.py` writes need the service_role key locally.
- **db.py updated** to prefer `SUPABASE_SERVICE_ROLE_KEY` if set, else fall back to `SUPABASE_KEY`. No app code changes required.
- **Service role key added to local `.env`** as `SUPABASE_SERVICE_ROLE_KEY`. Verified writes work.
- **GitHub Actions keep-alive cron** added (`.github/workflows/keep-alive.yml`) - hits Supabase REST API every 6 days to stop free-tier 7-day auto-pause.
- **GitHub repo secrets** `SUPABASE_URL` and `SUPABASE_ANON_KEY` added via `gh secret set` so the cron actually works.
- One-off discovery: the project had auto-paused. Restore took ~2 minutes via `restore_project`. PostgREST schema cache had to be reloaded post-restore (`NOTIFY pgrst, 'reload schema';`) before writes worked again. Worth noting for future restores.

### Deploy + Rename (2026-05-19)
- **Merged `multi-country-refactor` -> `master` -> pushed to GitHub `main`.** Streamlit Cloud auto-deploys from main.
- **Repo renamed**: `taiwan-history-timeline` -> `country-timelines` -> `chronoscape` (final). Local remote updated. GitHub redirects old URLs.
- **Repo description** updated to reflect multi-country scope.

### Infrastructure
- `.env` file for local secrets (gitignored).
- `.gitignore` updated (.env, __pycache__, .claude).
- `requirements.txt` updated: +supabase, +python-dotenv, +anthropic, +folium, +streamlit-folium, +branca.
- `PLAN.md` saved in project root.
