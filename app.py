"""Taiwan History Timeline — Interactive Streamlit App."""

import html as html_lib
import subprocess
import streamlit as st
from pathlib import Path


def _get_version() -> str:
    """Derive version from git commit count (auto-increments on each push)."""
    try:
        count = subprocess.check_output(
            ["git", "rev-list", "--count", "HEAD"],
            stderr=subprocess.DEVNULL,
            cwd=Path(__file__).parent,
        ).decode().strip()
        short_hash = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
            cwd=Path(__file__).parent,
        ).decode().strip()
        return f"v1.{count} ({short_hash})"
    except Exception:
        return "v1.0"

from data_parser import parse_markdown, filter_events
from timeline_component import render_timeline
from map_component import render_map
from styles import inject_styles, get_era_color, get_era_short, CATEGORY_COLORS

# --- Page config ---
st.set_page_config(
    page_title="Taiwan History Timeline",
    page_icon="🏝️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

inject_styles()

# --- Load data ---
DATA_FILE = Path(__file__).parent / "taiwan_timeline.md"


@st.cache_data
def load_events():
    return parse_markdown(str(DATA_FILE))


all_events = load_events()

# --- Session state ---
if "selected_id" not in st.session_state:
    st.session_state.selected_id = None



def select_event(eid: int):
    st.session_state.selected_id = eid


# --- Header ---
st.markdown(
    '<div style="display:flex;align-items:baseline;gap:16px;margin-bottom:4px;">'
    '<h1 style="margin:0;font-size:1.8rem;color:#f0f0f0;">Taiwan History Timeline</h1>'
    '<span style="color:#5a6a7a;font-size:0.85rem;">'
    f'450,000 years ago — present &nbsp;|&nbsp; {len(all_events)} events'
    '</span></div>',
    unsafe_allow_html=True,
)

# --- Filters ---
eras = ["All"] + sorted(
    list(set(e.era for e in all_events)),
    key=lambda x: min(e.sort_year for e in all_events if e.era == x),
)
all_categories = sorted(list(set(c for e in all_events for c in e.categories)))

col_search, col_era, col_cats, col_key = st.columns([3, 2, 3, 1.5])

with col_search:
    search_query = st.text_input(
        "Search events",
        placeholder="Search by keyword...",
        label_visibility="collapsed",
    )

with col_era:
    selected_era = st.selectbox("Era", eras, label_visibility="collapsed")

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
timeline_clicked = render_timeline(filtered, st.session_state.selected_id, height=160)
if timeline_clicked is not None and timeline_clicked != st.session_state.selected_id:
    st.session_state.selected_id = timeline_clicked
    st.rerun()

# --- Colour Key ---
from styles import ERA_COLORS, ERA_SHORT_NAMES

legend_items = ""
for era_full, color in ERA_COLORS.items():
    short = ERA_SHORT_NAMES.get(era_full, era_full)
    legend_items += (
        f'<span style="display:inline-flex;align-items:center;gap:5px;margin-right:14px;">'
        f'<span style="width:10px;height:10px;border-radius:50%;background:{color};display:inline-block;"></span>'
        f'<span style="color:#8899aa;font-size:0.75rem;">{html_lib.escape(short)}</span>'
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
    clicked_event_id = render_map(filtered, st.session_state.selected_id, height=500)
    if clicked_event_id is not None and clicked_event_id != st.session_state.selected_id:
        st.session_state.selected_id = clicked_event_id
        st.rerun()

# --- Event List (using fragment for fast button reruns) ---
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

            # Compact inline button
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
            '<div style="font-size:2.5rem;margin-bottom:12px;">🏝️</div>'
            '<h2 style="color:#5a6a7a !important;">Select an event</h2>'
            '<p style="color:#4a5a6a;font-size:0.9rem;">'
            'Click an event in the list, a dot on the timeline, or a marker on the map.'
            '</p></div>',
            unsafe_allow_html=True,
        )

# --- Version footer ---
st.markdown(
    f'<div style="position:fixed;bottom:8px;left:12px;color:#3a4a5a;font-size:0.65rem;'
    f'font-family:monospace;z-index:9999;opacity:0.7;">{_get_version()}</div>',
    unsafe_allow_html=True,
)
