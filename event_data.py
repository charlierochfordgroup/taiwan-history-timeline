"""Data structures and reference data for Taiwan timeline events."""

from dataclasses import dataclass, field
import re


@dataclass
class TimelineEvent:
    id: int
    raw_date: str
    sort_year: float
    display_date: str
    title: str
    description: str
    era: str
    categories: list = field(default_factory=list)
    coordinates: tuple = None
    is_major: bool = False


# --- Location coordinates (lat, lng) for known Taiwan places ---

LOCATION_COORDS = {
    "fort zeelandia": (22.9908, 120.1603),
    "anping": (22.9908, 120.1603),
    "tainan": (22.9999, 120.2269),
    "chikan": (22.9999, 120.2023),
    "sakam": (22.9908, 120.1603),
    "tayowan": (22.9908, 120.1603),
    "keelung": (25.1283, 121.7419),
    "san salvador": (25.1283, 121.7419),
    "taipei": (25.0330, 121.5654),
    "tamsui": (25.1697, 121.4408),
    "santo domingo": (25.1697, 121.4408),
    "penghu": (23.5711, 119.5793),
    "kaohsiung": (22.6273, 120.3014),
    "changhua": (24.0752, 120.5414),
    "hsinchu": (24.8138, 120.9675),
    "taitung": (22.7583, 121.1444),
    "kinmen": (24.4488, 118.3769),
    "sun moon lake": (23.8581, 120.9169),
    "yunlin": (23.7092, 120.4313),
    "zuojhen": (23.0584, 120.4477),
    "eluanbi": (21.9009, 120.8560),
    "matsu": (26.1606, 119.9498),
    "musha": (24.0208, 121.1336),
    "wushe": (24.0208, 121.1336),
    "beipu": (24.6972, 121.0594),
    "liuqiu": (22.3420, 120.3714),
    "nanjing": (32.0603, 118.7969),
    "xiamen": (24.4798, 118.0894),
    "quanzhou": (24.8741, 118.6757),
    "mazu": (26.1606, 119.9498),
    "aoli": (25.0977, 121.7869),
    "changbin": (23.2928, 121.3591),
    "tapani": (23.2577, 120.5895),
}

# --- Category keyword matching ---

CATEGORY_KEYWORDS = {
    "Military": [
        "war", "battle", "troops", "army", "invasion", "siege", "killed",
        "massacre", "rebellion", "uprising", "fleet", "soldiers", "military",
        "shelling", "missile", "navy", "naval", "bombed", "cavalry",
        "musketeers", "attack", "fought", "fighting", "executed", "weapon",
        "infantry", "suppress", "defeat", "routed", "casualties", "garrison",
        "warship", "blockade", "artillery", "fortif",
    ],
    "Political": [
        "election", "president", "governor", "party", "government",
        "martial law", "constitution", "independence", "treaty", "democratic",
        "KMT", "DPP", "legislature", "parliament", "republic", "regime",
        "inaugurated", "declared", "sovereignty", "administration", "reform",
        "political", "opposition", "vote", "inaugurated", "TPP",
    ],
    "Economic": [
        "trade", "economy", "GDP", "export", "sugar", "rice", "land reform",
        "aid", "inflation", "semiconductor", "TSMC", "tax", "merchant",
        "commerce", "monopoly", "price", "plantation", "agriculture",
        "industrial", "railway", "telegraph", "banking", "currency",
    ],
    "Aboriginal": [
        "aborigi", "indigenous", "Seediq", "Paiwan", "Saisiyat", "tribal",
        "Musha", "Austronesian", "Dapenkeng", "native", "Formosan language",
        "Mattau", "Favorolang", "Sinkan", "Baccluan", "Mona Rudao",
    ],
    "Foreign Relations": [
        "United States", "Japan", "Dutch", "Spanish", "Portuguese", "British",
        "French", "Beijing", "United Nations", "US ", "American",
        "diplomatic", "Communiqu", "recogni", "derecogni", "Shanghai",
        "Nixon", "Truman", "Pelosi", "carrier", "7th Fleet",
    ],
    "Cultural": [
        "language", "education", "school", "cultural", "religion",
        "Christianity", "newspaper", "same-sex marriage", "Confucian",
        "romanised", "curriculum", "literary", "academy", "university",
        "Sunflower", "women",
    ],
}

# --- Major events (sort_year, title keyword fragment) ---

MAJOR_EVENT_MARKERS = [
    (-450000, "jawbone"),
    (-3000, "Dapenkeng"),
    (1624, "Fort Zeelandia"),
    (1661, "Koxinga launches"),
    (1662, "Fort Zeelandia surrenders"),
    (1684, "annex"),
    (1786, "Lin Shuangwen"),
    (1895, "Treaty of Shimonoseki"),
    (1895.4, "Taiwan Republic"),  # May 1895
    (1898, "Goto Shimpei"),
    (1930, "Musha"),
    (1947, "February 28"),
    (1949, "Chiang Kai-shek formally moves"),
    (1950, "Korean War"),
    (1987, "Martial law lifted"),
    (1996, "First direct presidential"),
    (2000, "DPP candidate Chen Shui-bian wins"),
    (2019, "same-sex marriage"),
    (2024, "William Lai"),
]


def assign_categories(text: str) -> list:
    """Auto-tag an event with categories based on keyword matching."""
    cats = []
    text_lower = text.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in text_lower:
                cats.append(category)
                break
    return cats


def assign_coordinates(text: str) -> tuple:
    """Find the first matching location keyword and return its coordinates."""
    text_lower = text.lower()
    for location, coords in LOCATION_COORDS.items():
        if location in text_lower:
            return coords
    return None


def check_is_major(sort_year: float, title: str, description: str) -> bool:
    """Check if an event matches one of the hardcoded major event markers."""
    full_text = f"{title} {description}"
    for marker_year, keyword in MAJOR_EVENT_MARKERS:
        year_close = abs(sort_year - marker_year) < 2
        if year_close and keyword.lower() in full_text.lower():
            return True
    return False
