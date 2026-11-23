"""A made-up practice data set in the exact shape of the OSE export (OSE-2216).

It is not real traffic. Places are real towns on Chicago's south side and in
Indiana and Michigan so the layers can be checked by eye; every number is
generated from a fixed seed. Each row is floored and rounded down to 5 the way
OSE will do it, so rows under 5 simply never appear.
"""
from __future__ import annotations

import random
from datetime import date, timedelta

import h3

from .rows import FlowRow, check_row, round_down

PLACES = {
    # key: (label, lat, lon) -- town centres, for the practice set only
    "beverly": ("Beverly", 41.7136, -87.6770),
    "evergreen": ("Evergreen Park", 41.7206, -87.7017),
    "blue_island": ("Blue Island", 41.6573, -87.6800),
    "hammond": ("Hammond", 41.5834, -87.5000),
    "sawyer": ("Sawyer, Michigan", 41.8848, -86.5945),
    "mt_greenwood": ("Mount Greenwood", 41.6976, -87.7081),
    "morgan_park": ("Morgan Park", 41.6903, -87.6667),
    "oak_lawn": ("Oak Lawn", 41.7108, -87.7581),
    "bronzeville": ("Bronzeville", 41.8169, -87.6176),
    "hyde_park": ("Hyde Park", 41.7943, -87.5907),
}

START = date(2025, 1, 6)  # a Monday
END = date(2026, 11, 16)  # a Monday: the practice "as of" week

SUMMER = {6, 7, 8}


def cell(key: str) -> str:
    _, lat, lon = PLACES[key]
    return h3.latlng_to_cell(lat, lon, 7)


# (from, to, weekly scans, event types, first week, last week, shape)
EDGES = [
    # The core: Beverly, Evergreen Park and Blue Island send scans both ways all year.
    ("beverly", "evergreen", 30, ["REC-BOCCE-001", "ART-MUSIC-001"], START, END, "steady"),
    ("evergreen", "beverly", 25, ["REC-BOCCE-001", "ART-MUSIC-001"], START, END, "steady"),
    ("evergreen", "blue_island", 22, ["REC-SOFTBALL-001", "VOL-FOODDRIVE-001"], START, END, "steady"),
    ("blue_island", "evergreen", 20, ["REC-SOFTBALL-001", "VOL-FOODDRIVE-001"], START, END, "steady"),
    ("blue_island", "beverly", 28, ["ART-MUSIC-001", "REC-BOCCE-001"], START, END, "rising"),
    ("beverly", "blue_island", 24, ["ART-MUSIC-001", "REC-BOCCE-001"], START, END, "rising"),
    # Hammond trades both ways with Beverly only, and sends one way to Blue Island (fading).
    ("hammond", "beverly", 14, ["REC-BOCCE-001"], START, END, "steady"),
    ("beverly", "hammond", 12, ["REC-BOCCE-001"], START, END, "steady"),
    ("hammond", "blue_island", 18, ["ART-GALLERY-001"], START, END, "falling"),
    # Sawyer, Michigan: summer only, one way, two summers running (seasonal periphery).
    ("sawyer", "beverly", 20, ["ART-MUSIC-001"], START, END, "summer"),
    # Beverly spreads to three newer corridors from September 2025 (SPIDERWEB).
    ("beverly", "mt_greenwood", 10, ["REC-SOFTBALL-001"], date(2025, 9, 1), END, "rising"),
    ("beverly", "morgan_park", 10, ["VOL-FOODDRIVE-001"], date(2025, 9, 8), END, "rising"),
    ("beverly", "oak_lawn", 10, ["ART-GALLERY-001"], date(2025, 9, 15), END, "rising"),
    # Bronzeville and Hyde Park: both ways, but only since spring 2026, and only two of them.
    ("bronzeville", "hyde_park", 15, ["ART-MUSIC-001"], date(2026, 3, 2), END, "steady"),
    ("hyde_park", "bronzeville", 15, ["ART-MUSIC-001"], date(2026, 3, 2), END, "steady"),
    # A trickle under the floor: almost every week of it is withheld before export.
    ("bronzeville", "beverly", 3, ["ART-MUSIC-001"], START, END, "steady"),
]

LOCAL = {"beverly": 40, "evergreen": 20, "blue_island": 25, "hammond": 15, "bronzeville": 20,
         "hyde_park": 15, "oak_lawn": 5, "mt_greenwood": 5, "morgan_park": 5, "sawyer": 10}


def _level(shape: str, week: date, first: date) -> float:
    age = (week - first).days / 7
    if shape == "rising":
        return 0.5 + age / 80
    if shape == "falling":
        return max(0.2, 1.3 - age / 70)
    if shape == "summer":
        return 1.0 if week.month in SUMMER else 0.0
    return 1.0


def generate(seed: int = 20261123) -> list[FlowRow]:
    rnd = random.Random(seed)
    rows: list[FlowRow] = []
    week = START
    while week <= END:
        for src, dst, base, types, first, last, shape in EDGES:
            if not (first <= week <= last):
                continue
            weekly = base * _level(shape, week, first) * rnd.uniform(0.7, 1.3)
            for i, uec in enumerate(types):
                share = 0.6 if (len(types) > 1 and i == 0) else (0.4 if len(types) > 1 else 1.0)
                n = round_down(int(weekly * share))
                if n >= 5:
                    rows.append(check_row(FlowRow(week, cell(src), cell(dst), uec, n)))
        for key, base in LOCAL.items():
            n = round_down(int(base * rnd.uniform(0.7, 1.4)))
            if n >= 5:
                rows.append(check_row(FlowRow(week, cell(key), cell(key), "REC-BOCCE-001", n)))
        week += timedelta(weeks=1)
    return rows


def labels() -> dict[str, str]:
    return {cell(k): v[0] for k, v in PLACES.items()}
