"""History Timeline — Interactive Streamlit App."""

import html as html_lib
import os
import subprocess
import streamlit as st
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

from data_parser import parse_markdown, filter_events
from timeline_component import render_timeline
from map_component import render_map
from styles import inject_styles, get_era_color, get_era_short, set_era_config, CATEGORY_COLORS


def _get_version() -> str:
    """Derive version from git commit count (auto-increments on each push)."""
    try:
        count = subprocess.check_output(
            ["git", "rev-list", "--count", "HEAD"],
            stderr=subprocess.DEVNULL,
            cwd=Path(__file__).parent,
        ).decode().strip()
        return f"v2.{count}"
    except Exception:
        return "v2.0"


# --- Page config ---
st.set_page_config(
    page_title="History Timeline",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

inject_styles()

# --- Session state ---
if "selected_id" not in st.session_state:
    st.session_state.selected_id = None
if "country_name" not in st.session_state:
    st.session_state.country_name = ""


def select_event(eid: int):
    st.session_state.selected_id = eid


# --- Country Search ---
def _on_country_change():
    st.session_state.selected_id = None

col_title, col_search_bar = st.columns([4, 6])
with col_title:
    st.markdown(
        '<h1 style="margin:0;font-size:1.8rem;color:#f0f0f0;">History Timeline</h1>',
        unsafe_allow_html=True,
    )
with col_search_bar:
    country_input = st.text_input(
        "Country",
        value=st.session_state.country_name,
        placeholder="Type a country name (e.g. Taiwan, Japan, France)...",
        label_visibility="collapsed",
        on_change=_on_country_change,
        key="country_input",
    )

country_name = country_input.strip()
if country_name:
    st.session_state.country_name = country_name

# --- Load data for selected country ---
all_events = []
eras_config = []
country_config = None

if country_name:
    try:
        from db import load_country_data, get_country, create_country
        events_db, eras_db, country_db = load_country_data(country_name)

        if events_db is not None:
            # Country exists and is ready
            all_events = events_db
            eras_config = eras_db
            country_config = country_db
            set_era_config(eras_config)
        elif country_db and country_db.get("status") == "generating":
            # Country is being generated
            st.info(f"**{country_name}** is being generated... This takes 30-60 seconds.", icon="⏳")
            import time
            time.sleep(5)
            st.rerun()
        elif country_db and country_db.get("status") == "failed":
            st.error(f"Failed to generate timeline for **{country_name}**. Try again?")
            if st.button("Retry generation"):
                from db import update_country
                update_country(country_db["id"], status="generating")
                from worker import generate_in_background
                generate_in_background(country_name)
                st.rerun()
        else:
            # Country not in DB — offer to generate
            st.warning(f"No timeline found for **{country_name}**.")
            if st.button(f"Generate timeline for {country_name}", type="primary"):
                try:
                    record = create_country(country_name)
                    from worker import generate_in_background
                    generate_in_background(country_name)
                    st.rerun()
                except Exception as ex:
                    st.error(f"Error: {ex}")
    except Exception as ex:
        # DB not available — fall back to local Taiwan file
        if country_name.lower() == "taiwan":
            DATA_FILE = Path(__file__).parent / "taiwan_timeline.md"
            all_events = parse_markdown(str(DATA_FILE))
            # Load hardcoded Taiwan eras config as fallback
            from timeline_component import _match_era
            eras_config = _build_taiwan_fallback_eras()
            country_config = {"name": "Taiwan", "center_lat": 23.7, "center_lng": 121.0, "default_zoom": 7}
            set_era_config(eras_config)
        else:
            st.error(f"Database unavailable: {ex}")
else:
    # No country selected — show welcome
    st.markdown(
        '<div style="text-align:center;padding:120px 24px;">'
        '<div style="font-size:3rem;margin-bottom:16px;">🌍</div>'
        '<h2 style="color:#5a6a7a !important;">Explore History</h2>'
        '<p style="color:#4a5a6a;font-size:1rem;">'
        'Type a country name above to explore its interactive historical timeline.'
        '</p></div>',
        unsafe_allow_html=True,
    )

# --- Only render timeline UI if we have data ---
if all_events and eras_config:
    # Subtitle
    date_range = ""
    if eras_config:
        first_label = eras_config[0].get("date_label", "")
        last_era = eras_config[-1]
        date_range = f"{first_label} — present"

    display_name = country_config["name"] if country_config else country_name
    st.markdown(
        f'<span style="color:#5a6a7a;font-size:0.85rem;">'
        f'{display_name} &nbsp;|&nbsp; {date_range} &nbsp;|&nbsp; {len(all_events)} events'
        f'</span>',
        unsafe_allow_html=True,
    )

    # --- Filters ---
    eras_list = ["All"] + [ec["name"] for ec in eras_config]
    all_categories = sorted(list(set(c for e in all_events for c in e.categories)))

    col_search, col_era, col_cats, col_key = st.columns([3, 2, 3, 1.5])

    with col_search:
        search_query = st.text_input(
            "Search events",
            placeholder="Search by keyword...",
            label_visibility="collapsed",
        )

    with col_era:
        selected_era = st.selectbox("Era", eras_list, label_visibility="collapsed")

    with col_cats:
        selected_cats = st.multiselect(
            "Categories",
            all_categories,
            placeholder="Filter by category...",
            label_visibility="collapsed",
        )

    with col_key:
        key_only = st.toggle("Key events", value=False)

    # Apply filters
    filtered = filter_events(all_events, search_query, selected_era, selected_cats)
    if key_only:
        filtered = [e for e in filtered if e.is_major]

    # --- Timeline ---
    timeline_clicked = render_timeline(filtered, st.session_state.selected_id, height=160, eras_config=eras_config)
    if timeline_clicked is not None and timeline_clicked != st.session_state.selected_id:
        st.session_state.selected_id = timeline_clicked
        st.rerun()

    # --- Colour Key ---
    legend_items = ""
    for ec in eras_config:
        short = html_lib.escape(ec.get("short_name", ec["name"]))
        color = ec.get("color", "#666")
        legend_items += (
            f'<span style="display:inline-flex;align-items:center;gap:5px;margin-right:14px;">'
            f'<span style="width:10px;height:10px;border-radius:50%;background:{color};display:inline-block;"></span>'
            f'<span style="color:#8899aa;font-size:0.75rem;">{short}</span>'
            f'</span>'
        )
    legend_items += (
        '<span style="display:inline-flex;align-items:center;gap:5px;margin-right:14px;">'
        '<span style="width:12px;height:12px;border-radius:50%;background:#4fc3f7;display:inline-block;"></span>'
        '<span style="color:#8899aa;font-size:0.75rem;">Key event</span>'
        '</span>'
    )

    st.markdown(
        f'<div style="display:flex;flex-wrap:wrap;align-items:center;padding:4px 0 8px;gap:2px;">{legend_items}</div>',
        unsafe_allow_html=True,
    )

    # --- Main content: Map + Event List + Detail Panel ---
    col_map, col_list, col_detail = st.columns([3, 3, 4])

    # --- Map ---
    with col_map:
        clicked_event_id = render_map(filtered, st.session_state.selected_id, height=500, country_config=country_config)
        if clicked_event_id is not None and clicked_event_id != st.session_state.selected_id:
            st.session_state.selected_id = clicked_event_id
            st.rerun()

    # --- Event List ---
    with col_list:
        st.markdown(
            f'<p style="color:#5a6a7a;font-size:0.8rem;margin:0 0 4px;">'
            f'{len(filtered)} event{"s" if len(filtered) != 1 else ""}</p>',
            unsafe_allow_html=True,
        )

        list_container = st.container(height=470)
        with list_container:
            for evt in filtered:
                era_color = get_era_color(evt.era)
                era_short = html_lib.escape(get_era_short(evt.era))
                safe_t = html_lib.escape(evt.title)
                safe_d = html_lib.escape(evt.display_date)
                is_selected = st.session_state.selected_id == evt.id

                major_html = ' <span class="major-badge">KEY</span>' if evt.is_major else ""

                cat_tags = ""
                for c in evt.categories:
                    c_color = CATEGORY_COLORS.get(c, "#666")
                    cat_tags += f'<span class="cat-tag" style="background:{c_color}30;color:{c_color};">{html_lib.escape(c)}</span>'

                border_style = "border-color:#4fc3f7;background:#1a2a3a;" if is_selected else ""

                card_html = (
                    f'<div class="event-card" style="{border_style}">'
                    f'<div class="event-date">{safe_d}</div>'
                    f'<div class="event-title">{safe_t}{major_html}</div>'
                    f'<div class="tags-row">'
                    f'<span class="era-tag" style="background:{era_color}35;color:{era_color};">{era_short}</span>'
                    f'{cat_tags}'
                    f'</div></div>'
                )
                st.markdown(card_html, unsafe_allow_html=True)

                st.button(
                    f"{'✓ Selected' if is_selected else 'View details →'}",
                    key=f"evt_{evt.id}",
                    on_click=select_event,
                    args=(evt.id,),
                    type="tertiary" if not is_selected else "primary",
                )

    # --- Detail Panel ---
    with col_detail:
        if st.session_state.selected_id is not None:
            selected_evt = None
            for e in all_events:
                if e.id == st.session_state.selected_id:
                    selected_evt = e
                    break

            if selected_evt:
                era_color = get_era_color(selected_evt.era)
                era_short = html_lib.escape(get_era_short(selected_evt.era))
                safe_title = html_lib.escape(selected_evt.title)
                safe_desc = html_lib.escape(selected_evt.description)
                safe_date = html_lib.escape(selected_evt.display_date)

                major_html = '<span class="major-badge">PIVOTAL EVENT</span>' if selected_evt.is_major else ""

                cat_html = ""
                for c in selected_evt.categories:
                    c_color = CATEGORY_COLORS.get(c, "#666")
                    cat_html += f'<span class="cat-tag" style="background:{c_color}30;color:{c_color};">{html_lib.escape(c)}</span>'

                st.markdown(
                    f'<div class="detail-panel">'
                    f'<div class="detail-date">{safe_date}</div>'
                    f'<h2>{safe_title}</h2>'
                    f'<div class="tags-row">'
                    f'<span class="era-tag" style="background:{era_color}35;color:{era_color};">{era_short}</span>'
                    f'{cat_html}'
                    f'{major_html}'
                    f'</div>'
                    f'<div class="detail-body">{safe_desc}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

                if st.button("Clear selection", type="tertiary"):
                    st.session_state.selected_id = None
                    st.rerun()
            else:
                st.session_state.selected_id = None
                st.rerun()
        else:
            st.markdown(
                '<div class="detail-panel" style="text-align:center;padding:80px 24px;">'
                '<div style="font-size:2.5rem;margin-bottom:12px;">🌍</div>'
                '<h2 style="color:#5a6a7a !important;">Select an event</h2>'
                '<p style="color:#4a5a6a;font-size:0.9rem;">'
                'Click an event in the list, a dot on the timeline, or a marker on the map.'
                '</p></div>',
                unsafe_allow_html=True,
            )

# --- Version footer ---
st.markdown(
    f'<div style="color:#3a4a5a;font-size:0.65rem;'
    f'font-family:monospace;opacity:0.7;padding:24px 0 8px 4px;">{_get_version()}</div>',
    unsafe_allow_html=True,
)


def _build_taiwan_fallback_eras() -> list[dict]:
    """Build eras config for Taiwan from the legacy hardcoded data (offline fallback)."""
    from timeline_component import _match_era
    from styles import ERA_PALETTE

    era_names = [
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
    year_ranges = {
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
    short_names = {
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
    date_labels = {
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
    widths = {
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
    colors = [
        "#5a8a9a", "#6a8a5a", "#c49a2a", "#b06040", "#7a5aaa",
        "#2aaa7a", "#c04040", "#707070", "#3a7abb", "#40a870",
    ]

    result = []
    for i, name in enumerate(era_names):
        ys, ye = year_ranges[name]
        result.append({
            "name": name,
            "short_name": short_names[name],
            "sort_order": i,
            "year_start": ys,
            "year_end": ye,
            "date_label": date_labels[name],
            "width_pct": widths[name],
            "color": colors[i],
        })
    return result
