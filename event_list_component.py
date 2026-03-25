"""Clickable event list rendered as a single HTML component."""

import html as html_lib
import streamlit.components.v1 as components
from styles import get_era_color, get_era_short, CATEGORY_COLORS


def render_event_list(events: list, selected_id: int = None, height: int = 500):
    """Render a scrollable list of clickable event cards."""

    cards_html = ""
    for evt in events:
        era_color = get_era_color(evt.era)
        era_short = html_lib.escape(get_era_short(evt.era))
        safe_t = html_lib.escape(evt.title)
        safe_d = html_lib.escape(evt.display_date)
        is_selected = selected_id is not None and selected_id == evt.id

        major_html = ' <span class="major-badge">KEY</span>' if evt.is_major else ""

        cat_tags = ""
        for c in evt.categories:
            c_color = CATEGORY_COLORS.get(c, "#666")
            cat_tags += f'<span class="cat-tag" style="background:{c_color}30;color:{c_color};">{html_lib.escape(c)}</span>'

        selected_cls = " selected" if is_selected else ""

        cards_html += (
            f'<div class="el-card{selected_cls}" data-id="{evt.id}">'
            f'<div class="el-date">{safe_d}</div>'
            f'<div class="el-title">{safe_t}{major_html}</div>'
            f'<div class="el-tags">'
            f'<span class="el-era" style="background:{era_color}35;color:{era_color};">{era_short}</span>'
            f'{cat_tags}'
            f'</div></div>'
        )

    count = len(events)

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            background: transparent;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            color: #e0e0e0;
        }}

        .el-header {{
            font-size: 12px;
            color: #5a6a7a;
            margin-bottom: 6px;
            padding: 0 2px;
        }}

        .el-scroll {{
            overflow-y: auto;
            max-height: {height - 30}px;
            padding-right: 4px;
        }}

        .el-card {{
            background: #1a1e2a;
            border: 1px solid #2a2e3a;
            border-radius: 8px;
            padding: 10px 14px;
            margin-bottom: 6px;
            cursor: pointer;
            transition: border-color 0.15s, background 0.15s;
        }}
        .el-card:hover {{
            border-color: #4fc3f7;
            background: #1e2336;
        }}
        .el-card.selected {{
            border-color: #4fc3f7;
            background: #1a2a3a;
        }}

        .el-date {{
            font-size: 11px;
            color: #8899aa;
            margin-bottom: 2px;
        }}
        .el-title {{
            font-size: 13px;
            color: #e0e0e0;
            font-weight: 500;
            line-height: 1.35;
        }}
        .el-tags {{
            display: flex;
            flex-wrap: wrap;
            gap: 4px;
            margin-top: 5px;
            align-items: center;
        }}
        .el-era {{
            display: inline-block;
            font-size: 10px;
            padding: 1px 7px;
            border-radius: 8px;
            white-space: nowrap;
            line-height: 1.5;
        }}
        .cat-tag {{
            display: inline-block;
            font-size: 10px;
            padding: 1px 6px;
            border-radius: 8px;
            white-space: nowrap;
            line-height: 1.5;
        }}
        .major-badge {{
            display: inline-block;
            font-size: 9px;
            padding: 1px 6px;
            border-radius: 6px;
            background: #4fc3f7;
            color: #0e1117;
            font-weight: 700;
            white-space: nowrap;
            vertical-align: middle;
            margin-left: 4px;
        }}

        .el-scroll::-webkit-scrollbar {{ width: 5px; }}
        .el-scroll::-webkit-scrollbar-track {{ background: transparent; }}
        .el-scroll::-webkit-scrollbar-thumb {{ background: #333; border-radius: 3px; }}
        .el-scroll::-webkit-scrollbar-thumb:hover {{ background: #555; }}
    </style>
    </head>
    <body>
        <div class="el-header">{count} event{"s" if count != 1 else ""}</div>
        <div class="el-scroll">{cards_html}</div>

        <script>
            document.querySelectorAll('.el-card').forEach(card => {{
                card.addEventListener('click', () => {{
                    const eventId = card.getAttribute('data-id');

                    // Visual feedback immediately
                    document.querySelectorAll('.el-card.selected').forEach(c => c.classList.remove('selected'));
                    card.classList.add('selected');

                    // Navigate parent to trigger Streamlit rerun with selected param
                    const url = new URL(window.parent.location);
                    url.searchParams.set('selected', eventId);
                    window.parent.location.href = url.toString();
                }});
            }});

            // Scroll selected card into view
            const selected = document.querySelector('.el-card.selected');
            if (selected) {{
                selected.scrollIntoView({{ block: 'center', behavior: 'smooth' }});
            }}
        </script>
    </body>
    </html>
    """

    components.html(html, height=height, scrolling=False)
