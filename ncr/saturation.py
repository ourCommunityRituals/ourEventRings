"""How far a ring has filled in, measured from the hexagons inside it.

A ring (compute.py) is 3 or more cells whose links run both ways, season after
season. Saturation is the plain average of four shares, each 0 to 1 and each a
ratio of scan counts on posters (never of people), so anyone can check one by
hand:

- coverage:    of the hexagons inside the ring's outline, the share with
               traffic at or over the floor;
- steadiness:  of the weeks in the window, the share with traffic, averaged
               over the ring's core cells;
- closure:     of the scans that touch the core, the share that stay inside it;
- reciprocity: across the core's links, the smaller direction over the larger,
               averaged.

No threshold is set (Matt, 2026-11-25; OSE RING-METHODOLOGY Part 2): the value
at which a ring is saturated is found through practice. So the job only
measures, and keeps each measure beside what it should be read against:

- confidence:  how much evidence sits under the number (weeks of data in the
               window, and seasons the ring has held), so a young, thin ring is
               not mistaken for a full one;
- baseline:    the same ring a year earlier, and the median of the other rings
               of the same size at the same date (history()).

The same test runs at three sizes: res 7 (small, about 5 km²), res 6 (medium,
about 36 km²) and res 5 (large, about 250 km²).
"""
from __future__ import annotations

import statistics
from dataclasses import asdict, dataclass
from datetime import timedelta

import h3
from shapely.geometry import mapping

from .compute import Result, Ring, Settings, compute
from .rows import K, FlowRow

SIZES = {7: "small", 6: "medium", 5: "large"}
FULL_SEASONS = 4  # a ring seen in all four seasons has a full year of evidence behind it


@dataclass(frozen=True)
class RingSaturation:
    ring_id: str
    resolution: int
    size: str
    hexagons: int  # hexagons inside the ring's outline, core cells included
    active: int  # of those, hexagons with traffic at or over the floor
    coverage: float
    steadiness: float
    closure: float
    reciprocity: float
    saturation: float
    weeks_observed: int  # weeks in the window with any traffic on the core
    seasons_seen: int
    confidence: float


def ring_hexagons(ring: Ring) -> set[str]:
    """The hexagons, at the ring's own size, that its outline covers; its core cells always among them."""
    from .layers import ring_outline  # the outline the map draws

    cells = set(ring.core)
    outline = mapping(ring_outline(ring.core))
    if outline["type"] == "Polygon":
        shell = [(lat, lng) for lng, lat in outline["coordinates"][0]]
        cells |= set(h3.polygon_to_cells(h3.LatLngPoly(shell), ring.resolution))
    return cells


def ring_saturation(result: Result, ring: Ring) -> RingSaturation:
    s = result.settings
    core = set(ring.core)
    hexes = ring_hexagons(ring)
    active = sum(1 for h in hexes if h in result.cells and result.cells[h].total >= K)
    coverage = active / len(hexes)
    steadiness = sum(result.cells[c].saturation for c in core) / len(core)

    inside = sum(result.cells[c].local for c in core)
    touching = inside
    balance: list[float] = []
    for (a, b), link in result.links.items():
        ends_in = (a in core) + (b in core)
        if ends_in == 0:
            continue
        touching += link.total
        if ends_in == 2:
            inside += link.total
            if link.total:
                balance.append(min(link.ab, link.ba) / max(link.ab, link.ba))
    closure = inside / touching if touching else 0.0
    reciprocity = sum(balance) / len(balance) if balance else 0.0

    window_start = result.as_of - timedelta(weeks=s.window_weeks - 1)
    weeks = {w for c in core for w, n in result.cells[c].weekly.items() if n and w >= window_start}
    week_share = len(weeks) / s.window_weeks
    confidence = (week_share + min(ring.seasons_seen, FULL_SEASONS) / FULL_SEASONS) / 2

    value = (coverage + steadiness + closure + reciprocity) / 4
    return RingSaturation(ring.ring_id, ring.resolution, SIZES.get(ring.resolution, f"res {ring.resolution}"),
                          len(hexes), active, round(coverage, 3), round(steadiness, 3), round(closure, 3),
                          round(reciprocity, 3), round(value, 3), len(weeks), ring.seasons_seen,
                          round(confidence, 3))


def history(rows: list[FlowRow], settings: Settings | None = None, step_weeks: int = 4,
            resolutions: tuple[int, ...] = (7, 6, 5)) -> list[dict]:
    """Ring saturation as the weeks layer up, at each size, with its baselines.

    The job is run as of every step_weeks from the first week of data to the
    last, as if it had run on that day. A ring keeps the id it was first seen
    with while its core overlaps the core it had at its last step, so one ring
    that grows reads as one line. Each row carries the same ring's saturation a
    year earlier (if it existed then) and the median of the other rings of the
    same size that day (if there are any).
    """
    s = settings or Settings()
    weeks = sorted({r.week for r in rows})
    steps = []
    d = weeks[-1]
    while d >= weeks[0]:
        steps.append(d)
        d -= timedelta(weeks=step_weeks)
    steps.reverse()

    out: list[dict] = []
    for res in resolutions:
        seen: dict[str, frozenset[str]] = {}
        past: dict[str, list] = {}  # stable id -> [(as_of, saturation)]
        for as_of in steps:
            result = compute([r for r in rows if r.week <= as_of], s, as_of, res)
            today = []
            for ring in result.rings:
                core = frozenset(ring.core)
                stable = next((sid for sid, prev in seen.items() if prev & core), ring.ring_id)
                seen[stable] = core
                today.append((stable, ring, ring_saturation(result, ring)))
            for stable, ring, sat in today:
                peers = [x.saturation for sid, _, x in today if sid != stable]
                year = as_of - timedelta(weeks=52)
                year_ago = next((v for d, v in reversed(past.get(stable, []))
                                 if year - timedelta(weeks=step_weeks) < d <= year), None)
                past.setdefault(stable, []).append((as_of, sat.saturation))
                row = {"as_of": as_of.isoformat(), "ring": stable, **asdict(sat), "core": " ".join(ring.core),
                       "year_ago": year_ago,
                       "peer_median": round(statistics.median(peers), 3) if peers else None}
                row.pop("ring_id")
                out.append(row)
    return out


HISTORY_COLUMNS = ("as_of", "resolution", "size", "ring", "core", "hexagons", "active", "coverage", "steadiness",
                   "closure", "reciprocity", "saturation", "weeks_observed", "seasons_seen", "confidence",
                   "year_ago", "peer_median")
