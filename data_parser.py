"""Parse the Taiwan timeline markdown file into structured TimelineEvent objects."""

import re
from pathlib import Path
from event_data import (
    TimelineEvent,
    assign_categories,
    assign_coordinates,
    check_is_major,
)


def parse_sort_year(raw_date: str, era_year_hint: float) -> tuple:
    """Parse a date string into (sort_year: float, display_date: str).

    Handles formats like:
        "450,000-190,000 years ago"
        "~20,000-30,000 years ago"
        "~3,000 BC"
        "~400 AD"
        "230 AD"
        "1624"
        "Early 1400s"
        "Late 1500s"
        "May 16, 1895"
        "February 28, 1947"
        "April 1975"
        "June 25, 1950"
        "1895-1902"
        "1624-25"
        "January 2024"
    """
    cleaned = raw_date.strip().replace(",", "")

    # "X years ago" pattern
    m = re.match(r"~?(\d+)[\s\-–]+[\d,]*\s*years?\s*ago", cleaned, re.IGNORECASE)
    if m:
        return -int(m.group(1)), raw_date.strip()

    m = re.match(r"~?(\d+)\s*years?\s*ago", cleaned, re.IGNORECASE)
    if m:
        return -int(m.group(1)), raw_date.strip()

    # "X BC" pattern
    m = re.match(r"~?(\d+)\s*BC", cleaned, re.IGNORECASE)
    if m:
        return -int(m.group(1)), raw_date.strip()

    # "X AD" pattern
    m = re.match(r"~?(\d+)\s*AD", cleaned, re.IGNORECASE)
    if m:
        return int(m.group(1)), raw_date.strip()

    # "Early Xth century" or "Early X00s"
    m = re.match(r"(Early|Late|Mid)\s+(\d+)(?:th|st|nd|rd)?\s*century", cleaned, re.IGNORECASE)
    if m:
        century = int(m.group(2))
        prefix = m.group(1).lower()
        base = (century - 1) * 100
        offset = {"early": 10, "mid": 50, "late": 90}.get(prefix, 50)
        year = base + offset
        return year, raw_date.strip()

    m = re.match(r"(Early|Late|Mid)\s+(\d{3,4})s", cleaned, re.IGNORECASE)
    if m:
        prefix = m.group(1).lower()
        decade_start = int(m.group(2))
        offset = {"early": 0, "mid": 5, "late": 8}.get(prefix, 5)
        return decade_start + offset, raw_date.strip()

    # Full date: "Month Day, Year" or "Month Year"
    m = re.match(
        r"(January|February|March|April|May|June|July|August|September|October|November|December)"
        r"\s+(\d{1,2})?,?\s*(\d{4})",
        cleaned,
        re.IGNORECASE,
    )
    if m:
        month_name = m.group(1)
        year = int(m.group(3))
        months = [
            "january", "february", "march", "april", "may", "june",
            "july", "august", "september", "october", "november", "december",
        ]
        month_num = months.index(month_name.lower()) + 1
        sort_year = year + (month_num - 1) / 12
        return sort_year, raw_date.strip()

    # "Month Day" without year — use era hint
    m = re.match(
        r"(January|February|March|April|May|June|July|August|September|October|November|December)"
        r"\s+(\d{1,2})",
        cleaned,
        re.IGNORECASE,
    )
    if m:
        month_name = m.group(1)
        months = [
            "january", "february", "march", "april", "may", "june",
            "july", "august", "september", "october", "november", "december",
        ]
        month_num = months.index(month_name.lower()) + 1
        sort_year = era_year_hint + (month_num - 1) / 12
        return sort_year, raw_date.strip()

    # Year range: "1895-1902" or "1895–1902"
    m = re.match(r"(\d{4})\s*[–\-]\s*(\d{2,4})", cleaned)
    if m:
        return int(m.group(1)), raw_date.strip()

    # Plain 4-digit year
    m = re.match(r"~?(\d{4})", cleaned)
    if m:
        return int(m.group(1)), raw_date.strip()

    # Plain 3-digit year (e.g. "230")
    m = re.match(r"~?(\d{3})", cleaned)
    if m:
        return int(m.group(1)), raw_date.strip()

    # "Post-X BC" / "By Xth century"
    m = re.search(r"(\d{3,4})\s*BC", cleaned, re.IGNORECASE)
    if m:
        return -int(m.group(1)), raw_date.strip()

    m = re.search(r"(\d{4})", cleaned)
    if m:
        return int(m.group(1)), raw_date.strip()

    # Fallback: use era hint
    return era_year_hint, raw_date.strip()


def extract_era_year_hint(era_heading: str) -> float:
    """Extract a representative year from an era heading like 'Qing Dynasty Rule (1683-1895)'."""
    m = re.search(r"\((\d{3,4})", era_heading)
    if m:
        return float(m.group(1))
    m = re.search(r"(\d{4})", era_heading)
    if m:
        return float(m.group(1))
    return 0


def extract_title(description: str, max_words: int = 12) -> str:
    """Extract a short title from the first sentence/clause of a description."""
    # Take text up to the first period, semicolon, or colon
    for sep in [".", ";", ":"]:
        idx = description.find(sep)
        if idx != -1 and idx < 200:
            fragment = description[:idx].strip()
            words = fragment.split()
            if len(words) <= max_words:
                return fragment
            return " ".join(words[:max_words]) + "..."
    words = description.split()
    if len(words) <= max_words:
        return description.strip()
    return " ".join(words[:max_words]) + "..."


def parse_markdown(filepath: str) -> list:
    """Parse the timeline markdown file into a list of TimelineEvent objects."""
    text = Path(filepath).read_text(encoding="utf-8")

    # Split into sections by ## headings
    sections = re.split(r"^## ", text, flags=re.MULTILINE)

    events = []
    event_id = 0

    for section in sections:
        if not section.strip():
            continue

        # Extract era name from the first line
        lines = section.split("\n", 1)
        era_heading = lines[0].strip()

        # Skip the "Key Themes" section
        if "Key Themes" in era_heading:
            continue

        # Clean era name (remove trailing ---)
        era_name = re.sub(r"\s*-+\s*$", "", era_heading).strip()

        era_year_hint = extract_era_year_hint(era_heading)

        if len(lines) < 2:
            continue
        body = lines[1]

        # Also handle ### sub-sections — fold them into the parent era
        # but extract sub-heading for context
        sub_sections = re.split(r"^### ", body, flags=re.MULTILINE)

        for sub in sub_sections:
            if not sub.strip():
                continue

            # Extract bullets: lines starting with "- **"
            # Pattern 1: "- **date** – description" (date with dash separator)
            # Pattern 2: "- **label** description" (label without dash, e.g. topic headers)
            bullet_pattern = re.compile(
                r"^- \*\*(.+?)\*\*\s*(?:[–\-—]+\s*)?(.+?)(?=\n- \*\*|\n###|\n---|\n## |\Z)",
                re.MULTILINE | re.DOTALL,
            )

            last_known_year = era_year_hint

            for match in bullet_pattern.finditer(sub):
                raw_date = match.group(1).strip()
                description = match.group(2).strip()

                # Clean up multi-line descriptions
                description = re.sub(r"\n\s*", " ", description)
                description = description.strip()

                # Check if the bold text is actually a date or a topic label
                has_year = bool(re.search(r"\d{3,}", raw_date)) or "years ago" in raw_date.lower() or "BC" in raw_date
                if not has_year:
                    # Bold text is a label, not a date — use it as title prefix
                    description = f"{raw_date}: {description}"
                    raw_date = f"c. {int(last_known_year)}"

                sort_year, display_date = parse_sort_year(raw_date, era_year_hint)

                # Track the last known year for context
                if has_year and sort_year < 5000:
                    last_known_year = sort_year

                title = extract_title(description)
                full_text = f"{raw_date} {description}"
                categories = assign_categories(full_text)
                coordinates = assign_coordinates(full_text)
                is_major = check_is_major(sort_year, title, description)

                events.append(
                    TimelineEvent(
                        id=event_id,
                        raw_date=raw_date,
                        sort_year=sort_year,
                        display_date=display_date,
                        title=title,
                        description=description,
                        era=era_name,
                        categories=categories,
                        coordinates=coordinates,
                        is_major=is_major,
                    )
                )
                event_id += 1

    # Sort by sort_year
    events.sort(key=lambda e: e.sort_year)
    return events


def filter_events(
    events: list,
    search: str = "",
    era: str = "All",
    categories: list = None,
) -> list:
    """Filter events by search text, era, and categories."""
    filtered = events
    if search:
        q = search.lower()
        filtered = [
            e for e in filtered
            if q in e.title.lower() or q in e.description.lower() or q in e.display_date.lower()
        ]
    if era and era != "All":
        filtered = [e for e in filtered if e.era == era]
    if categories:
        filtered = [
            e for e in filtered
            if any(c in e.categories for c in categories)
        ]
    return filtered


if __name__ == "__main__":
    # Quick test
    import sys
    fp = sys.argv[1] if len(sys.argv) > 1 else "taiwan_timeline.md"
    evts = parse_markdown(fp)
    print(f"Parsed {len(evts)} events")
    for e in evts[:5]:
        print(f"  [{e.sort_year}] {e.display_date}: {e.title} | era={e.era} | cats={e.categories} | major={e.is_major} | coords={e.coordinates}")
    print("...")
    for e in evts[-5:]:
        print(f"  [{e.sort_year}] {e.display_date}: {e.title} | era={e.era} | cats={e.categories} | major={e.is_major} | coords={e.coordinates}")
    majors = [e for e in evts if e.is_major]
    print(f"\nMajor events: {len(majors)}")
    for e in majors:
        print(f"  [{e.sort_year}] {e.title}")
    with_coords = [e for e in evts if e.coordinates]
    print(f"\nEvents with coordinates: {len(with_coords)}")
