"""Nodes, corridors and rings, computed from FlowRows.

Words, as the NCR documents use them (OCR_VISION section 9, OSE ADR-009):
- a corridor cell is an H3 res 7 cell, the unit that crosses the boundary;
- a link is a pair of corridor cells joined by scans on posters in one for
  events in the other; its direction is a fact about where posters hang, not
  about anyone who scanned them;
- a ring is 3 or more corridor cells in a cycle whose links run both ways
  (the core), seen in 2 or more seasons, plus cells tied to the core by a
  validated link (the periphery). Spokes to one hub are corridors, not rings.

ADR-009 leaves the ring thresholds to be fitted from real data, so every number
that decides a status lives in Settings and is reported as provisional.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta

import h3
import networkx as nx
import numpy as np

from .rows import K, FlowRow, publish

SEASONS = {12: "winter", 1: "winter", 2: "winter", 3: "spring", 4: "spring", 5: "spring",
           6: "summer", 7: "summer", 8: "summer", 9: "autumn", 10: "autumn", 11: "autumn"}


@dataclass(frozen=True)
class Settings:
    """Provisional thresholds (ADR-009: to be fitted once a year of real data exists)."""

    window_weeks: int = 52
    short_weeks: int = 13
    both_ways_ratio: float = 1 / 3  # the smaller direction is at least a third of the larger
    min_seasons: int = 2  # ADR-009 temporal requirement
    trend_band: float = 0.10  # +/- 10% a quarter counts as growing / fading
    spiderweb_min_links: int = 3
    provisional: bool = True


def season_of(d: date) -> tuple[int, str]:
    # December belongs to the winter that runs into the next year.
    year = d.year + 1 if d.month == 12 else d.year
    return (year, SEASONS[d.month])


def pair_key(a: str, b: str) -> tuple[str, str]:
    return (a, b) if a <= b else (b, a)


def weekly_series(totals: dict[date, int], end: date, weeks: int) -> np.ndarray:
    start = end - timedelta(weeks=weeks - 1)
    return np.array([totals.get(start + timedelta(weeks=i), 0) for i in range(weeks)], dtype=float)


def trend(series: np.ndarray) -> float | None:
    """Slope of a straight line through weekly totals, as a share of the mean per week."""
    if series.sum() < K or len(series) < 4:
        return None
    slope = np.polyfit(np.arange(len(series)), series, 1)[0]
    # The line's rise over one quarter (13 weeks), as a share of the average week.
    return float(slope * 13 / series.mean())


def status_of(t: float | None, s: Settings) -> str:
    if t is None:
        return "new"
    if t > s.trend_band:
        return "growing"
    if t < -s.trend_band:
        return "fading"
    return "steady"


def _link_status(link: "Link", as_of: date, s: Settings) -> str:
    if link.temporal == "SEASONAL":
        return "seasonal"  # a summer-only link is not fading in November
    if link.first and link.first > as_of - timedelta(weeks=s.short_weeks):
        return "new"
    if link.trend_short is None:
        return "fading"  # traffic inside the window, none worth a line lately
    return status_of(link.trend_short, s)


@dataclass
class Link:
    a: str
    b: str
    ab: int = 0  # scans on posters in a for events in b, inside the window
    ba: int = 0
    weekly: dict = field(default_factory=lambda: defaultdict(int))  # both directions, all time
    by_type: dict = field(default_factory=lambda: defaultdict(int))  # inside the window
    seasons_ab: set = field(default_factory=set)
    seasons_ba: set = field(default_factory=set)
    first: date | None = None
    last: date | None = None
    # filled by compute()
    direction: str = ""
    seasons_seen: int = 0
    validated: bool = False
    temporal: str = ""
    trend_short: float | None = None
    trend_long: float | None = None
    growth: float | None = None
    status: str = ""
    pattern: str = ""

    @property
    def total(self) -> int:
        return self.ab + self.ba

    @property
    def from_cell(self) -> str:
        return self.a if self.ab >= self.ba else self.b

    @property
    def to_cell(self) -> str:
        return self.b if self.ab >= self.ba else self.a


@dataclass
class Cell:
    cell: str
    local: int = 0  # posters here for events here
    outbound: int = 0
    inbound: int = 0
    weekly: dict = field(default_factory=lambda: defaultdict(int))
    first: date | None = None
    saturation: float = 0.0  # share of weeks in the window with traffic
    saturation_before: float = 0.0  # the same share, the quarter before the last one
    trend_short: float | None = None
    status: str = ""
    potential: bool = False
    pattern: str = ""
    level: int = 0  # 1 quiet, 2 busier, 3 busiest, ranked among drawn cells

    @property
    def total(self) -> int:
        return self.local + self.outbound + self.inbound


@dataclass
class Ring:
    ring_id: str
    core: list[str]
    periphery: list[str]
    resolution: int
    seasons_seen: int
    temporal: str


@dataclass
class Result:
    as_of: date
    settings: Settings
    cells: dict[str, Cell]
    links: dict[tuple[str, str], Link]
    rings: list[Ring]
    fractal: dict[int, int]  # resolution -> number of rings found there


def _season_count(seasons: set) -> tuple[int, str]:
    names = {s for (_, s) in seasons}
    temporal = "UNKNOWN" if len(seasons) < 2 else ("SEASONAL" if len(names) == 1 else "STRUCTURAL")
    return len(seasons), temporal


def compute(rows: list[FlowRow], settings: Settings | None = None, as_of: date | None = None,
            resolution: int = 7) -> Result:
    s = settings or Settings()
    if not rows:
        raise ValueError("no rows")
    as_of = as_of or max(r.week for r in rows)
    win_start = as_of - timedelta(weeks=s.window_weeks - 1)

    def cell_at(c: str) -> str:
        return c if resolution == 7 else h3.cell_to_parent(c, resolution)

    cells: dict[str, Cell] = {}
    links: dict[tuple[str, str], Link] = {}

    for r in rows:
        if r.week > as_of:
            continue
        src, dst = cell_at(r.source_cell), cell_at(r.destination_cell)
        for c in {src, dst}:
            cell = cells.setdefault(c, Cell(c))
            cell.weekly[r.week] += r.scans
            cell.first = r.week if cell.first is None else min(cell.first, r.week)
        in_window = r.week >= win_start
        if src == dst:
            if in_window:
                cells[src].local += r.scans
            continue
        key = pair_key(src, dst)
        link = links.setdefault(key, Link(*key))
        link.weekly[r.week] += r.scans
        link.first = r.week if link.first is None else min(link.first, r.week)
        link.last = r.week if link.last is None else max(link.last, r.week)
        forward = src == link.a
        (link.seasons_ab if forward else link.seasons_ba).add(season_of(r.week))
        if in_window:
            if forward:
                link.ab += r.scans
            else:
                link.ba += r.scans
            link.by_type[r.uec_code] += r.scans
            cells[src].outbound += r.scans
            cells[dst].inbound += r.scans

    # A seasonal count per direction needs K scans in that season; rows are each
    # >= K, so any row in a season is enough. Seasons are counted all-time, as
    # ADR-009's "2+ distinct time windows" asks.
    for link in links.values():
        both = link.ab >= K and link.ba >= K and min(link.ab, link.ba) >= s.both_ways_ratio * max(link.ab, link.ba)
        link.direction = "both" if both else ("one" if link.total >= K else "none")
        seen = (link.seasons_ab & link.seasons_ba) if both else (link.seasons_ab | link.seasons_ba)
        link.seasons_seen, link.temporal = _season_count(seen)
        link.validated = link.total >= K and link.seasons_seen >= s.min_seasons
        link.trend_short = trend(weekly_series(link.weekly, as_of, s.short_weeks))
        link.trend_long = trend(weekly_series(link.weekly, as_of, s.window_weeks))
        last_q = weekly_series(link.weekly, as_of, s.short_weeks).sum()
        year_ago = weekly_series(link.weekly, as_of - timedelta(weeks=52), s.short_weeks).sum()
        link.growth = None if year_ago < K else float(last_q / year_ago - 1)
        link.status = _link_status(link, as_of, s)
        # REVERB (ADR-009): signal both ways that keeps compounding, so it needs
        # a year-on-year rise, not only a young link's climb from zero.
        if link.direction == "both" and link.validated and (link.growth or 0) > s.trend_band:
            link.pattern = "REVERB"

    for cell in cells.values():
        recent = weekly_series(cell.weekly, as_of, s.window_weeks)
        cell.saturation = float((recent > 0).mean())
        q_now = weekly_series(cell.weekly, as_of, s.short_weeks)
        q_before = weekly_series(cell.weekly, as_of - timedelta(weeks=s.short_weeks), s.short_weeks)
        cell.saturation_before = float((q_before > 0).mean())
        cell.trend_short = trend(q_now)
        cell.status = status_of(cell.trend_short, s)
        # Potential: posters here send scans to events elsewhere, but little
        # comes back here. Events placed here would have an audience nearby.
        cell.potential = cell.outbound >= K and cell.inbound < s.both_ways_ratio * cell.outbound

    # SPIDERWEB: one cell feeding 3+ validated links that are newer than it.
    for c, cell in cells.items():
        newer = [l for l in links.values() if l.validated and l.from_cell == c and l.first and cell.first
                 and l.first >= cell.first + timedelta(weeks=8)]
        if len(newer) >= s.spiderweb_min_links:
            cell.pattern = "SPIDERWEB"

    drawn = sorted((c for c in cells.values() if c.total >= K), key=lambda c: (c.total, c.cell))
    for i, c in enumerate(drawn):
        c.level = 1 + (3 * i) // max(len(drawn), 1)

    rings = find_rings(cells, links, s, resolution)
    result = Result(as_of, s, cells, links, rings, {})
    return result


def find_rings(cells: dict[str, Cell], links: dict[tuple[str, str], Link], s: Settings,
               resolution: int) -> list[Ring]:
    core_graph = nx.Graph()
    for (a, b), l in links.items():
        if l.direction == "both" and l.validated:
            core_graph.add_edge(a, b)
    rings: list[Ring] = []
    for comp in nx.biconnected_components(core_graph):
        if len(comp) < 3:  # a pair, or a spoke: a corridor, not a ring
            continue
        core = sorted(comp)
        periphery = sorted(
            {
                (l.b if l.a in comp else l.a)
                for l in links.values()
                if l.validated and ((l.a in comp) != (l.b in comp))
            }
        )
        core_links = [l for (a, b), l in links.items() if a in comp and b in comp and l.direction == "both"]
        seasons = set.intersection(*[l.seasons_ab & l.seasons_ba for l in core_links]) if core_links else set()
        n, temporal = _season_count(seasons)
        if n < s.min_seasons:
            continue
        rings.append(Ring(f"ring-r{resolution}-{core[0]}", core, periphery, resolution, n, temporal))
    rings.sort(key=lambda r: r.ring_id)
    return rings


def run(rows: list[FlowRow], settings: Settings | None = None, as_of: date | None = None) -> Result:
    """Compute at res 7, and count rings at res 6 and 5 too (FRACTAL, ADR-009)."""
    base = compute(rows, settings, as_of, 7)
    base.fractal[7] = len(base.rings)
    for res in (6, 5):
        base.fractal[res] = len(compute(rows, settings, base.as_of, res).rings)
    return base


__all__ = ["Settings", "Result", "Cell", "Link", "Ring", "compute", "run", "publish"]
