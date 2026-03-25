"""Dark theme CSS for the Taiwan Timeline Streamlit app."""

import streamlit as st

# Era color palette — muted tones for dark theme
ERA_COLORS = {
    "Prehistory & Early Settlement": "#5a8a9a",
    "Chinese Contact & Early Settlement": "#6a8a5a",
    "Dutch & Spanish Colonial Period": "#c49a2a",
    "Koxinga & the Kingdom of Tungning": "#b06040",
    "Qing Dynasty Rule": "#7a5aaa",
    "Republic of Formosa": "#2aaa7a",
    "Japanese Colonial Rule": "#c04040",
    "Return of Chinese Rule & the White Terror": "#707070",
    "Democratisation": "#3a7abb",
    "Modern Taiwan": "#40a870",
}

# Short era names for tags
ERA_SHORT_NAMES = {
    "Prehistory & Early Settlement": "Prehistory",
    "Chinese Contact & Early Settlement (~230 AD \u2013 1620s)": "Early Chinese",
    "Chinese Contact & Early Settlement": "Early Chinese",
    "Dutch & Spanish Colonial Period (1624\u20131662)": "Dutch & Spanish",
    "Dutch & Spanish Colonial Period": "Dutch & Spanish",
    "Koxinga & the Kingdom of Tungning (1661\u20131683)": "Koxinga",
    "Koxinga & the Kingdom of Tungning": "Koxinga",
    "Qing Dynasty Rule (1683\u20131895)": "Qing Dynasty",
    "Qing Dynasty Rule": "Qing Dynasty",
    "Republic of Formosa (May\u2013October 1895)": "Rep. Formosa",
    "Republic of Formosa": "Rep. Formosa",
    "Japanese Colonial Rule (1895\u20131945)": "Japanese Rule",
    "Japanese Colonial Rule": "Japanese Rule",
    "Return of Chinese Rule & the White Terror (1945\u20131987)": "White Terror",
    "Return of Chinese Rule & the White Terror": "White Terror",
    "Democratisation (1971\u20132000)": "Democratisation",
    "Democratisation": "Democratisation",
    "Modern Taiwan (2000\u2013present)": "Modern",
    "Modern Taiwan": "Modern",
}

CATEGORY_COLORS = {
    "Military": "#e05555",
    "Political": "#5588dd",
    "Economic": "#44bb77",
    "Aboriginal": "#cc8844",
    "Foreign Relations": "#9966cc",
    "Cultural": "#dd6699",
}


def get_era_color(era_name: str) -> str:
    """Get the color for an era, with fuzzy matching on partial names."""
    for key, color in ERA_COLORS.items():
        if key.lower() in era_name.lower() or era_name.lower() in key.lower():
            return color
    era_words = era_name.lower().split()
    for key, color in ERA_COLORS.items():
        for word in era_words:
            if len(word) > 3 and word in key.lower():
                return color
    return "#666666"


def get_era_short(era_name: str) -> str:
    """Get a short display name for an era."""
    if era_name in ERA_SHORT_NAMES:
        return ERA_SHORT_NAMES[era_name]
    for key, short in ERA_SHORT_NAMES.items():
        if key.lower() in era_name.lower() or era_name.lower() in key.lower():
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
