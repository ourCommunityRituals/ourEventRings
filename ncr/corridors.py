"""Corridor segments: the commercial strips the NCR layers are read along.

A corridor here is a street or strip where commerce sits and traffic flows,
drawn as a line and widened into a strip about one lot deep on each side. It is
cut into segments at its nodes (crossroads where commerce clusters, stations,
founding venues), never at a town line: corridors follow how places are used,
and the jurisdictions they cross are reported as an overlay, so the gap between
the two maps is visible instead of hidden.

Input is a definitions file (one per geography) and the jurisdictions of that
geography (municipal lines, and named neighbourhoods such as Chicago's community
areas). Nothing here reads traffic, scans or people: the segments are the frame
the scan layers are read against.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import h3
from shapely.geometry import LineString, Point, mapping, shape
import numpy as np
import shapely
from shapely.ops import substring, unary_union

from .rows import CORRIDOR_RES

LAT0 = 41.7  # projection centre; overridden per definitions file


@dataclass
class Node:
    id: str
    name: str
    at: tuple[float, float]  # lng, lat
    kind: str
    note: str = ""


@dataclass
class Corridor:
    id: str
    name: str
    tier: int  # 1 primary strip, 2 secondary
    line: list[tuple[float, float]]
    why: str = ""


@dataclass
class Segment:
    id: str
    corridor: str
    name: str
    tier: int
    start: str
    end: str
    line: LineString  # lng/lat
    strip: object  # lng/lat polygon
    length_km: float = 0.0
    municipalities: dict = field(default_factory=dict)  # name -> share of strip area
    neighbourhoods: dict = field(default_factory=dict)
    edge_share: float = 0.0  # share of the centreline within edge_m of a municipal line
    straddles: bool = False
    hexagons: list = field(default_factory=list)


class Projector:
    """Metres on a flat plane around the geography's centre; plenty for a few dozen km."""

    def __init__(self, lat0: float):
        self.kx = 111_320 * math.cos(math.radians(lat0))
        self.ky = 110_574

    def to_m(self, g):
        return shapely.transform(g, lambda a: a * np.array([self.kx, self.ky]))

    def to_deg(self, g):
        return shapely.transform(g, lambda a: a / np.array([self.kx, self.ky]))


def load_definitions(path: Path) -> dict:
    raw = json.loads(Path(path).read_text())
    raw["nodes"] = [Node(n["id"], n["name"], tuple(n["at"]), n["kind"], n.get("note", "")) for n in raw["nodes"]]
    raw["corridors"] = [Corridor(c["id"], c["name"], c["tier"], [tuple(p) for p in c["line"]], c.get("why", ""))
                        for c in raw["corridors"]]
    return raw


def load_jurisdictions(path: Path) -> list[tuple[str, str, object]]:
    fc = json.loads(Path(path).read_text())
    return [(f["properties"]["name"], f["properties"]["kind"], shape(f["geometry"])) for f in fc["features"]]


def _shares(strip_m, juris_m, kind: str) -> dict[str, float]:
    total = strip_m.area
    out = {}
    for name, k, g in juris_m:
        if k != kind:
            continue
        a = strip_m.intersection(g).area
        if a / total >= 0.02:
            out[name] = round(a / total, 2)
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))


def hexagons_of(strip_deg) -> list[str]:
    cells = set()
    for poly in getattr(strip_deg, "geoms", [strip_deg]):
        shell = [(lat, lng) for lng, lat in poly.exterior.coords]
        cells |= set(h3.h3shape_to_cells_experimental(h3.LatLngPoly(shell), CORRIDOR_RES, contain="overlap"))
    return sorted(cells)


def segments(defs: dict, jurisdictions: list[tuple[str, str, object]]) -> list[Segment]:
    p = Projector(defs.get("lat0", LAT0))
    strip_m = defs.get("strip_m", 150)
    snap_m = defs.get("snap_m", 120)
    edge_m = defs.get("edge_m", 150)
    juris_m = [(n, k, p.to_m(g).buffer(0)) for n, k, g in jurisdictions]
    muni_lines = unary_union([g.boundary for n, k, g in juris_m if k == "municipality"])
    near_line = muni_lines.buffer(edge_m)
    nodes_m = [(n, p.to_m(Point(n.at))) for n in defs["nodes"]]

    out: list[Segment] = []
    for c in defs["corridors"]:
        line_m = p.to_m(LineString(c.line))
        # Cut points: every node within snap_m of the line, in order along it.
        cuts = sorted({(line_m.project(pt), n.id) for n, pt in nodes_m if line_m.distance(pt) <= snap_m})
        end_gap = snap_m  # a node this close to an end names that end instead of cutting
        first = next((nid for d, nid in cuts if d <= end_gap), "start")
        last = next((nid for d, nid in reversed(cuts) if d >= line_m.length - end_gap), "end")
        inner = [x for x in cuts if end_gap < x[0] < line_m.length - end_gap]
        stops = [(0.0, first)] + inner + [(line_m.length, last)]
        names = {n.id: n.name for n in defs["nodes"]}
        for i in range(len(stops) - 1):
            (d0, a), (d1, b) = stops[i], stops[i + 1]
            if d1 - d0 < 50:
                continue
            seg_m = substring(line_m, d0, d1)
            strip = seg_m.buffer(strip_m, cap_style="flat")
            near_edge = seg_m.intersection(near_line).length / seg_m.length if seg_m.length else 0
            munis = _shares(strip, juris_m, "municipality")
            s = Segment(
                id=f"{c.id}-{i + 1}", corridor=c.id, name=c.name, tier=c.tier,
                start=names.get(a, "line end"), end=names.get(b, "line end"),
                line=p.to_deg(seg_m), strip=p.to_deg(strip), length_km=round(seg_m.length / 1000, 2),
                municipalities=munis, neighbourhoods=_shares(strip, juris_m, "chicago_community_area"),
                edge_share=round(near_edge, 2),
            )
            s.straddles = sum(1 for v in munis.values() if v >= 0.10) >= 2
            s.hexagons = hexagons_of(s.strip)
            out.append(s)
    return out


def _round(g) -> dict:
    m = mapping(g)

    def r(x):
        return [r(i) for i in x] if isinstance(x, (list, tuple)) else round(x, 5)

    return {"type": m["type"], "coordinates": r(m["coordinates"])}


def to_geojson(defs: dict, segs: list[Segment]) -> dict:
    feats = []
    for s in segs:
        props = {"layer": "corridor", "segment": s.id, "corridor": s.corridor, "name": s.name, "tier": s.tier,
                 "from": s.start, "to": s.end, "length_km": s.length_km, "municipalities": s.municipalities,
                 "neighbourhoods": s.neighbourhoods, "edge_share": s.edge_share, "straddles": s.straddles,
                 "hexagons": s.hexagons}
        feats.append({"type": "Feature", "geometry": _round(s.strip), "properties": props})
    for n in defs["nodes"]:
        feats.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": list(n.at)},
                      "properties": {"layer": "node", "id": n.id, "name": n.name, "kind": n.kind,
                                     "hexagon": h3.latlng_to_cell(n.at[1], n.at[0], CORRIDOR_RES)}})
    return {"type": "FeatureCollection", "geography": defs["name"], "rules": defs.get("rules"), "provisional": True,
            "features": feats}


SEGMENT_COLUMNS = ("segment", "corridor", "name", "tier", "from", "to", "length_km", "municipalities",
                   "neighbourhoods", "edge_share", "straddles", "hexagons")


def write_segments(defs: dict, segs: list[Segment], out: Path) -> dict[str, Path]:
    import csv

    out.mkdir(parents=True, exist_ok=True)
    gj = out / "corridor-segments.geojson"
    gj.write_text(json.dumps(to_geojson(defs, segs), indent=1, sort_keys=True))
    table = out / "corridor-segments.csv"
    with table.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(SEGMENT_COLUMNS)
        for s in segs:
            w.writerow([s.id, s.corridor, s.name, s.tier, s.start, s.end, s.length_km,
                        "; ".join(f"{k} {round(v * 100)}%" for k, v in s.municipalities.items()),
                        "; ".join(f"{k} {round(v * 100)}%" for k, v in s.neighbourhoods.items()),
                        s.edge_share, s.straddles, " ".join(s.hexagons)])
    return {"geojson": gj, "table": table}
