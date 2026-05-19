# TODO - Chronoscape (multi-country history timeline)

Last updated: 2026-05-19
Current branch: `master` (synced to GitHub `main`)
GitHub: `charlierochfordgroup/chronoscape`
Deployed (Streamlit Cloud): pending URL slug rename + secrets

---

## Outstanding

### Streamlit Cloud finishing touches

- [ ] **Add Streamlit Cloud Secrets** in app Settings -> Secrets (TOML):
  ```toml
  SUPABASE_URL = "https://xbhhdpcbrsgmactfuxlq.supabase.co"
  SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIs... (anon key from local .env)"
  ```
  Anon key only - the deployed app does reads only. Do NOT put `SUPABASE_SERVICE_ROLE_KEY` here yet - see Phase 4 architectural decision below.
- [ ] **Rename Streamlit Cloud URL slug** to `chronoscape` (Settings -> General -> App URL). Old URL won't redirect.
- [ ] **Verify deployed app** at `https://chronoscape.streamlit.app/` - type "Taiwan" and "Iceland", confirm both render.
- [ ] **Tag v2.0 release** once deployed app verified working.

### Phase 2 follow-ups from verification

- [ ] **Card click doesn't select event** - have to click the "View details ->" link instead. Investigate whether the card was intended to be clickable; if so, fix the click handler. Low priority - functionality works via the link.
- [ ] **Confirm timeline-dot and map-marker click selection both work** - only verified the list-item path in this session.

### Phase 3 - Multi-country app shell polish

- [ ] Loading state UI (currently just `st.info + sleep(5) + st.rerun()`) - make it nicer with a progress indicator / stage description.
- [ ] Error state UI with retry button - test the failed-generation path works.
- [ ] Empty state / welcome screen on first load (already in app.py, but visually polish).
- [ ] Country autocomplete from existing DB entries (`list_countries()` already in db.py, just wire it up).

### Phase 4 - Data pipeline (not started)

- [ ] **Add `ANTHROPIC_API_KEY` to local `.env`.** Currently empty. Needed before any of the below will work.
- [ ] Write `pipeline.py`:
  - `fetch_wikipedia(country_name)` - pulls 4-5 articles ("History of X", "X", "Timeline of X history", auto-discovered 1-2 long sub-articles). Rate limit 1 req/sec. Truncate combined to 80k chars.
  - `extract_with_claude(country_name, wiki_text)` - Claude Sonnet, structured JSON prompt matching `iceland_data.json` shape. Target: 80-200 events, 5-15 eras, 10-25 major events, lat/lng inline. Universal categories.
  - `store_results(country_id, extraction)` - reuse `seed_country.py` storage logic (delete old + insert new, batch 500). Log-scaled `width_pct = log10(year_span + 1)` with 5% minimum. Assign era colours from `ERA_PALETTE`.
  - `run_pipeline(country_name)` - orchestrator with error handling + status updates via `update_country()`.
- [ ] Write `worker.py`:
  - `generate_in_background(country_name)` - `threading.Thread(daemon=True)` running `run_pipeline`.
  - Recovery: on app startup, re-queue any country stuck in `generating` for >10 min.
- [ ] End-to-end test: type "Japan", wait 30-60s, verify timeline renders.

### Phase 4 architectural decision (resolve before merging Phase 4)

The deployed Streamlit Cloud app currently uses the anon key (reads only - safe). When `worker.py` lands, writes are needed to create new countries and seed extracted data. Two paths:
- **Option A**: put `SUPABASE_SERVICE_ROLE_KEY` in Streamlit Cloud Secrets and let the in-process worker write directly. Simple but the key sits on a hosted service.
- **Option B (cleaner)**: move the worker out-of-band - e.g. a GitHub Actions workflow triggered by polling `countries.status='generating'` rows. Streamlit Cloud keeps anon-only.

### Phase 5 - Polish

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
