# Multi-Country History Timeline — Product Plan

## Context

The Taiwan History Timeline Streamlit app is working and deployed. The user wants to turn it into a general-purpose product where users type any country name and get an interactive historical timeline. The system fetches Wikipedia content, uses Claude API to extract structured events, caches results in Supabase, and serves them on future requests.

**User's decisions:** Claude API for extraction, Supabase for storage, Streamlit MVP (migrate later), queue+notify for first-load UX, side project ambition, tiered experience for casual + research users.

---

## 1. Database Schema (Supabase)

### `countries` table
| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | |
| name | text | Display name ("Japan") |
| name_lower | text UNIQUE | Lowercase lookup key ("japan") |
| center_lat | float | Map center |
| center_lng | float | Map center |
| default_zoom | int | Map zoom level |
| status | text | `pending` / `generating` / `ready` / `failed` |
| event_count | int | Cached count |
| refreshed_at | timestamptz | When data was last generated |
| created_at | timestamptz | |

### `eras` table
| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | |
| country_id | uuid FK | → countries.id |
| name | text | Full era name |
| short_name | text | Tag label |
| sort_order | int | Display order |
| year_start | float | Numeric start year |
| year_end | float | Numeric end year |
| date_label | text | Display label ("1624") |
| width_pct | float | Calculated display width |
| color | text | Hex colour assigned from palette |

### `events` table
| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | |
| country_id | uuid FK | → countries.id |
| era_name | text | Denormalized for easy queries |
| sort_year | float | Numeric, negative for BC |
| display_date | text | Human-readable date |
| title | text | Short title (≤12 words) |
| description | text | 1-3 sentences |
| categories | text[] | Postgres array |
| lat | float | Nullable |
| lng | float | Nullable |
| is_major | bool | Pivotal event flag |

### `generation_jobs` table
| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | |
| country_id | uuid FK | → countries.id |
| job_type | text | `initial` / `refresh` |
| status | text | `running` / `completed` / `failed` |
| wiki_pages | text[] | Which Wikipedia pages were fetched |
| input_tokens | int | Cost tracking |
| output_tokens | int | Cost tracking |
| cost_usd | float | Estimated cost |
| error_message | text | If failed |
| created_at | timestamptz | |
| completed_at | timestamptz | |

**Indexes:** `countries(name_lower)`, `events(country_id, sort_year)`, `generation_jobs(status)`.

---

## 2. Data Pipeline (`pipeline.py` — new file)

Three stages, orchestrated by `run_pipeline(country_name)`:

### Stage 1: Wikipedia Fetch
- Fetch **multiple** Wikipedia articles to maximise coverage:
  1. "History of {country}" — main history article (usually the richest source)
  2. "{country}" — general country article (has overview + modern context)
  3. "Timeline of {country} history" — chronological events list
  4. Auto-discover 1-2 additional long history-related articles by following "See also" links or searching for "{country} in the Xth century", "Colonial history of {country}", etc. — pick the longest ones
- Use Wikipedia REST API with `action=query&prop=extracts&explaintext=True`
- Combine all fetched articles, deduplicate overlapping content, truncate to 80k chars
- Rate limit 1 req/sec, `User-Agent` header

### Stage 2: Claude Extraction
- Use **Claude Sonnet** (not Opus) — ~5x cheaper, more than capable for factual extraction
- System prompt instructs JSON output with: `eras[]`, `events[]`, `center_lat`, `center_lng`, `default_zoom`
- Universal category list: Military, Political, Economic, Indigenous, Foreign Relations, Cultural, Social, Scientific, Religious
- Target: 80-200 events, 5-15 eras, 10-25 major events per country
- LLM provides lat/lng directly (no separate geocoding step)

### Stage 3: Store in Supabase
- Calculate era `width_pct` using log-scaled duration: `log10(year_span + 1)` with 5% minimum
- Assign era colours from a 15-colour dark-theme palette
- Delete old eras/events for the country, insert new ones
- Update `countries.status = 'ready'`, `refreshed_at = now()`

### Background Execution
- MVP: `threading.Thread` spawned from Streamlit process
- Thread runs `run_pipeline()` independently
- App polls `countries.status` every 5 seconds via `st.rerun()` with a timer
- Recovery: on startup, re-queue any countries stuck in `generating` for >10 minutes

### Cost Estimate
- ~10k input + ~15k output tokens per country ≈ $0.25 (Sonnet pricing)
- 50 countries initial: ~$13
- Monthly refresh of 50 active countries: ~$13/month
- Only refresh countries viewed in the past month to cap costs

---

## 3. What Changes in Each Existing File

### `event_data.py` — Strip to dataclass only
- **Keep:** `TimelineEvent` dataclass (lines 7-19) — already country-agnostic
- **Delete:** `LOCATION_COORDS` (40 Taiwan places), `CATEGORY_KEYWORDS`, `MAJOR_EVENT_MARKERS`, `assign_categories()`, `assign_coordinates()`, `check_is_major()` — all replaced by LLM extraction

### `styles.py` — Dynamic palette
- **Delete:** `ERA_COLORS` (10 hardcoded Taiwan entries), `ERA_SHORT_NAMES` (20 entries)
- **Add:** `assign_era_colors(n_eras)` — assigns from a 15-colour palette
- **Update:** `CATEGORY_COLORS` — rename "Aboriginal" → "Indigenous", add Social, Scientific, Religious
- **Update:** `get_era_color()` / `get_era_short()` — become simple dict lookups on runtime data
- **Keep:** `DARK_CSS` and `inject_styles()` — app chrome, not country-specific

### `timeline_component.py` — Accept dynamic config
- **Delete:** 5 hardcoded dicts (ERA_ORDER, ERA_SHORT_LABELS, ERA_YEAR_RANGES, ERA_DATE_LABELS, ERA_WIDTHS)
- **Change:** `render_timeline()` accepts `eras_config` parameter (list of dicts from DB)
- **Change:** `_match_era()` becomes exact-match lookup
- **Keep:** `timeline_files/` JS unchanged — already data-driven

### `map_component.py` — Accept country config
- **Change:** `center_lat/lng` and `zoom` read from `country_config` dict instead of hardcoded Taiwan values
- **Change:** `build_map()` signature gains `country_config` parameter

### `data_parser.py` — Keep as Taiwan fallback + add DB loader
- **Keep:** `parse_markdown()` and `filter_events()` intact as offline fallback
- **Add:** `load_country_from_db(country_name)` → returns `(events, eras_config, country_config)`

### `app.py` — Country search + dynamic rendering
- **Add:** Country search bar at top
- **Change:** Header becomes dynamic: `f"{country_name} History Timeline"`
- **Change:** All rendering uses runtime-loaded eras/colours/map config
- **Add:** Loading state UI (polling when `status='generating'`)
- **Add:** Error state UI with retry
- **Keep:** All existing layout, interactions, and styling

---

## 4. New Files

| File | Purpose |
|------|---------|
| `db.py` | Supabase client wrapper — `get_country()`, `get_eras()`, `get_events()`, `create_country()`, `update_country_status()` |
| `pipeline.py` | Wikipedia fetch → Claude extraction → Supabase storage |
| `worker.py` | Background thread management — `generate_in_background(country_name)` |
| `.env` | `SUPABASE_URL`, `SUPABASE_KEY`, `ANTHROPIC_API_KEY` |

---

## 5. Build Order

### Phase 1: Database Foundation
- Create all 4 Supabase tables via migrations
- Build `db.py` with query functions
- Seed Taiwan data by running existing `parse_markdown()` → insert into DB
- Verify Taiwan loads from DB identically

### Phase 2: Generalise Existing Code
- Strip `event_data.py` to dataclass only
- Update `styles.py` with dynamic palette + universal categories
- Update `timeline_component.py` to accept `eras_config`
- Update `map_component.py` to accept `country_config`
- Add `load_country_from_db()` to `data_parser.py`
- **Test:** Taiwan renders identically from DB

### Phase 3: Multi-Country App Shell
- Add country search bar to `app.py`
- Dynamic header, filters, colour key from loaded data
- Loading / error state UIs
- **Test:** Taiwan works via country search

### Phase 4: Data Pipeline
- Build Wikipedia fetch function
- Build Claude extraction prompt + function
- Build storage function with era-width calculation + colour assignment
- Build background thread wrapper
- **Test:** Type "Japan", wait for generation, verify result

### Phase 5: Polish
- Stale-data refresh logic (>14 days → queue background refresh)
- Country name autocomplete from existing DB entries
- Cost tracking in `generation_jobs`
- Update `requirements.txt` (add `anthropic`, `supabase`, `python-dotenv`)
- Update `.gitignore` (add `.env`)

---

## 6. Git & Deployment

### Repository
- Existing repo: `charlierochfordgroup/taiwan-history-timeline` on GitHub
- Consider renaming to `history-timeline` once multi-country is live
- Streamlit Cloud auto-deploys from `main` branch

### Branching Strategy
- Work on `master` locally, push to `main` on GitHub for deployment
- Each phase gets its own commit with a clear message
- Tag releases: `v2.0` for first multi-country release

### Secrets Management
- `.env` file for local development (in `.gitignore`)
- Streamlit Cloud Secrets for production (`SUPABASE_URL`, `SUPABASE_KEY`, `ANTHROPIC_API_KEY`)
- Never commit API keys

### `.gitignore` additions
```
.env
__pycache__/
.claude/
*.pyc
```

### Deployment Checklist (per phase)
1. Test locally with `streamlit run app.py`
2. `git add` changed files (never `git add -A`)
3. Commit with descriptive message
4. `git push origin master:main`
5. Verify on https://taiwan-history-timeline.streamlit.app/
6. Check Streamlit Cloud logs if anything breaks

### Streamlit Cloud Config
- Add secrets via Settings → Secrets in TOML format:
  ```toml
  SUPABASE_URL = "https://xxx.supabase.co"
  SUPABASE_KEY = "eyJ..."
  ANTHROPIC_API_KEY = "sk-ant-..."
  ```
- `requirements.txt` must include all new deps (`anthropic`, `supabase`, `python-dotenv`)

---

## 7. Verification

1. Run locally, type "Taiwan" — should load from DB instantly
2. Type "Japan" — should show "Generating..." UI, complete in 30-60s, then render full timeline
3. Reload page, type "Japan" again — should load from DB instantly
4. Verify all interactions work: timeline click, map click, event list, search, filters
5. Check `generation_jobs` table for token counts and cost
6. Wait 15 days (or manually set `refreshed_at` to old date), reload Japan — should serve stale + queue refresh
7. Deploy to Streamlit Cloud, test with env vars set in Streamlit secrets
