# TODO - Taiwan Timeline (Multi-Country Refactor)

Last updated: 2026-04-22
Current branch: `multi-country-refactor`
Deployed (Streamlit Cloud): still on old single-country `master` / `main` code

---

## Outstanding

### Phase 2 verification (blocker for everything else)

- [ ] **End-to-end visual test of multi-country app shell.** Server crashed on every attempt in last session (port conflicts, background bash lifecycle). Start fresh on a clean port and click through:
  - Type "Taiwan" in the country search box -> should load from Supabase (166 events, 10 eras) identically to how the old markdown version rendered
  - Verify timeline, colour key, event list, map, detail panel all work
  - Verify filters (search, era, category, key-events toggle) all work
  - Verify "Clear selection" button still works
  - Check `get_era_color()` / `get_era_short()` lookups work via `set_era_config()` (runtime populated, not hardcoded)
- [ ] **Debug any Phase 2 bugs** surfaced by the test above. Likely suspects: `_match_era` fuzzy logic, styles fallback when no runtime config set, coord None handling.

### Phase 3 - Multi-country app shell polish

- [ ] Loading state UI (currently just `st.info + sleep(5) + st.rerun()`) - make it nicer with a progress indicator / stage description.
- [ ] Error state UI with retry button - test the failed-generation path works.
- [ ] Empty state / welcome screen on first load (already in app.py, but visually polish).
- [ ] Country autocomplete from existing DB entries (`list_countries()` already in db.py, just wire it up).

### Phase 4 - Data pipeline (not started)

- [ ] **Add `ANTHROPIC_API_KEY` to `.env`.** Currently empty. Needed before any of the below will work.
- [ ] Write `pipeline.py`:
  - `fetch_wikipedia(country_name)` - pulls 4-5 articles ("History of X", "X", "Timeline of X history", auto-discovered 1-2 long sub-articles). Rate limit 1 req/sec. Truncate combined to 80k chars.
  - `extract_with_claude(country_name, wiki_text)` - Claude Sonnet, structured JSON prompt. Target: 80-200 events, 5-15 eras, 10-25 major events, lat/lng inline. Universal categories.
  - `store_results(country_id, extraction)` - delete old eras/events for country, insert new ones. Log-scaled `width_pct = log10(year_span + 1)` with 5% minimum. Assign era colours from palette.
  - `run_pipeline(country_name)` - orchestrator with error handling + status updates.
- [ ] Write `worker.py`:
  - `generate_in_background(country_name)` - `threading.Thread(daemon=True)` running `run_pipeline`.
  - Recovery: on app startup, re-queue any country stuck in `generating` for >10 min.
- [ ] End-to-end test: type "Japan", wait 30-60s, verify timeline renders.

### Phase 5 - Polish

- [ ] Stale-data refresh logic: if `refreshed_at` > 14 days, serve stale + queue background refresh.
- [ ] Cost tracking: populate `generation_jobs.input_tokens`, `output_tokens`, `cost_usd` after each pipeline run.
- [ ] Feature flag: only refresh countries viewed in the past month to cap monthly cost.

### Deployment

- [ ] Add Streamlit Cloud Secrets (TOML format): `SUPABASE_URL`, `SUPABASE_KEY`, `ANTHROPIC_API_KEY`.
- [ ] Merge `multi-country-refactor` -> `master` -> push to `main` on GitHub only AFTER full Phase 2 test passes.
- [ ] Consider renaming repo `taiwan-history-timeline` -> `history-timeline` when multi-country goes live.
- [ ] Tag v2.0 release.

---

## Done

### Phase 1 - Database Foundation (2026-04-14)
- Created Supabase project `xbhhdpcbrsgmactfuxlq` (us-east-1, free tier).
- Created 4 tables with indexes + FK cascades: countries, eras, events, generation_jobs.
- Built `db.py` with full query wrapper.
- Seeded Taiwan data from existing markdown (166 events, 10 eras, status=ready, center 23.7/121.0).
- Verified `load_country_data('Taiwan')` returns valid data (166 events, 10 eras, 21 major, 45 with coords).

### Phase 2 - Code generalisation (code only, not tested)
- Stripped Taiwan-specific data out of `event_data.py`, `styles.py`, `timeline_component.py`, `map_component.py`.
- Added runtime-config pattern: `set_era_config(eras)` populates `_era_color_map` / `_era_short_map`.
- 15-colour `ERA_PALETTE` for dynamic assignment.
- Universal category list (added Social, Scientific, Religious; kept Aboriginal as alias to Indigenous).
- `render_timeline()` now takes `eras_config` param, `render_map()` takes `country_config`.
- `app.py` rewritten with country search bar at top, dynamic header + filters + colour key, loading/error state UI.

### Infrastructure
- `.env` file for local secrets (gitignored).
- `.gitignore` updated (.env, __pycache__, .claude).
- `requirements.txt` updated: +supabase, +python-dotenv, +anthropic.
- Branch `multi-country-refactor` pushed to GitHub (not merged to main yet).
- `PLAN.md` saved in project root.
