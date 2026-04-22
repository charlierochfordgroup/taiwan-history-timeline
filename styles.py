"""Dark theme CSS for the History Timeline Streamlit app."""

import streamlit as st

# 15-colour palette for dynamically assigning era colours (dark-theme friendly)
ERA_PALETTE = [
    "#5a8a9a", "#6a8a5a", "#c49a2a", "#b06040", "#7a5aaa",
    "#2aaa7a", "#c04040", "#707070", "#3a7abb", "#40a870",
    "#aa5a8a", "#8a6a3a", "#5a5aaa", "#aa8a2a", "#3a8a8a",
]

CATEGORY_COLORS = {
    "Military": "#e05555",
    "Political": "#5588dd",
    "Economic": "#44bb77",
    "Indigenous": "#cc8844",
    "Aboriginal": "#cc8844",  # legacy alias
    "Foreign Relations": "#9966cc",
    "Cultural": "#dd6699",
    "Social": "#55aacc",
    "Scientific": "#88bb55",
    "Religious": "#cc7744",
}

# --- Runtime era colour/name lookups (populated from DB data) ---

_era_color_map: dict[str, str] = {}
_era_short_map: dict[str, str] = {}


def set_era_config(eras_config: list[dict]):
    """Load era colours and short names from DB-provided eras config."""
    global _era_color_map, _era_short_map
    _era_color_map = {e["name"]: e.get("color", "#666666") for e in eras_config}
    _era_short_map = {e["name"]: e.get("short_name", e["name"]) for e in eras_config}


def assign_era_colors(n_eras: int) -> list[str]:
    """Return a list of n distinct colours from the palette."""
    return [ERA_PALETTE[i % len(ERA_PALETTE)] for i in range(n_eras)]


def get_era_color(era_name: str) -> str:
    """Look up era colour from runtime config."""
    if _era_color_map:
        if era_name in _era_color_map:
            return _era_color_map[era_name]
        # Fuzzy fallback
        era_lower = era_name.lower()
        for key, color in _era_color_map.items():
            if key.lower() in era_lower or era_lower in key.lower():
                return color
    return "#666666"


def get_era_short(era_name: str) -> str:
    """Look up short era name from runtime config."""
    if _era_short_map:
        if era_name in _era_short_map:
            return _era_short_map[era_name]
        era_lower = era_name.lower()
        for key, short in _era_short_map.items():
            if key.lower() in era_lower or era_lower in key.lower():
                return short
    return era_name


DARK_CSS = """
<style>
    /* Main app background */
    .stApp {
        background-color: #0e1117;
        color: #e0e0e0;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #151820;
    }

    /* Headers */
    h1, h2, h3 {
        color: #f0f0f0 !important;
        font-weight: 600 !important;
    }

    h1 {
        font-size: 2rem !important;
        letter-spacing: -0.5px;
    }

    /* Event list items */
    .event-card {
        background: #1a1e2a;
        border: 1px solid #2a2e3a;
        border-radius: 8px;
        padding: 10px 14px;
        margin-bottom: 6px;
        cursor: pointer;
        transition: border-color 0.2s, background 0.2s;
    }
    .event-card:hover {
        border-color: #4fc3f7;
        background: #1e2336;
    }
    .event-card .event-date {
        font-size: 0.75rem;
        color: #8899aa;
        margin-bottom: 2px;
    }
    .event-card .event-title {
        font-size: 0.9rem;
        color: #e0e0e0;
        font-weight: 500;
        line-height: 1.3;
    }

    /* Tags row in cards and detail */
    .tags-row {
        display: flex;
        flex-wrap: wrap;
        gap: 4px;
        margin-top: 6px;
        align-items: center;
    }

    /* Era tag */
    .era-tag {
        display: inline-block;
        font-size: 0.65rem;
        padding: 2px 8px;
        border-radius: 10px;
        color: #fff;
        white-space: nowrap;
        line-height: 1.4;
    }

    /* Major event indicator */
    .major-badge {
        display: inline-block;
        font-size: 0.6rem;
        padding: 2px 7px;
        border-radius: 8px;
        background: #4fc3f7;
        color: #0e1117;
        font-weight: 700;
        white-space: nowrap;
        line-height: 1.4;
        vertical-align: middle;
    }

    /* Category tags */
    .cat-tag {
        display: inline-block;
        font-size: 0.6rem;
        padding: 2px 7px;
        border-radius: 8px;
        white-space: nowrap;
        line-height: 1.4;
    }

    /* Detail panel */
    .detail-panel {
        background: #151820;
        border: 1px solid #2a2e3a;
        border-radius: 10px;
        padding: 20px 24px;
    }
    .detail-panel h2 {
        margin-top: 0;
        font-size: 1.3rem !important;
        line-height: 1.35;
    }
    .detail-panel .detail-date {
        font-size: 1rem;
        color: #8899aa;
        margin-bottom: 8px;
    }
    .detail-panel .detail-body {
        font-size: 0.95rem;
        line-height: 1.65;
        color: #ccc;
        margin-top: 16px;
    }
    .detail-panel .tags-row {
        margin-top: 10px;
        gap: 6px;
    }
    .detail-panel .era-tag {
        font-size: 0.7rem;
        padding: 3px 10px;
    }
    .detail-panel .cat-tag {
        font-size: 0.65rem;
        padding: 3px 8px;
    }
    .detail-panel .major-badge {
        font-size: 0.65rem;
        padding: 3px 9px;
    }

    /* Streamlit widget overrides */
    .stTextInput > div > div > input {
        background: #1a1e2a !important;
        color: #e0e0e0 !important;
        border-color: #2a2e3a !important;
    }
    .stSelectbox > div > div {
        background: #1a1e2a !important;
        color: #e0e0e0 !important;
    }
    .stMultiSelect > div > div {
        background: #1a1e2a !important;
        color: #e0e0e0 !important;
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Scrollbar styling */
    ::-webkit-scrollbar {
        width: 6px;
        height: 6px;
    }
    ::-webkit-scrollbar-track {
        background: #0e1117;
    }
    ::-webkit-scrollbar-thumb {
        background: #333;
        border-radius: 3px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #555;
    }
</style>
"""


def inject_styles():
    """Inject the dark theme CSS into the Streamlit app."""
    st.markdown(DARK_CSS, unsafe_allow_html=True)
