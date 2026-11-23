"""What the job writes.

- public layer: shapes only, no numbers (Matt's ruling, 2026-11-23). Busy
  cells with a 1-3 level, connection lines with their direction, ring
  outlines. No count, no event type, no date finer than the week it is as of.
- admin layer: the same shapes with counts, each a sum of rows already floored
  and rounded, published through rows.publish (under 5 is withheld, never 0).
- research tables (CSV): corridors, cells, rings and corridor-by-event-type
  totals for the internal, named readers ADR-026 rule A allows.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import h3
from shapely.geometry import MultiPolygon, Polygon, mapping
from shapely.ops import unary_union

from .compute import Result
from .rows import publish

PUBLIC_KEYS = {"layer", "level", "direction", "role", "label", "status", "pattern", "ring", "ends"}


def hex_polygon(cell: str) -> Polygon:
    return Polygon([(lng, lat) for lat, lng in h3.cell_to_boundary(cell)])


def centre(cell: str) -> list[float]:
    lat, lng = h3.cell_to_latlng(cell)
    return [round(lng, 5), round(lat, 5)]


def ring_outline(cells: list[str]) -> Polygon | MultiPolygon:
    """The ring's core as one soft shape: the hull around its cells, so it
    crosses zip, town and city lines where the traffic does."""
    return unary_union([hex_polygon(c) for c in cells]).convex_hull


def _round_geom(g) -> dict:
    m = mapping(g)

    def r(x):
        if isinstance(x, (list, tuple)):
            return [r(i) for i in x]
        return round(x, 5)

    return {"type": m["type"], "coordinates": r(m["coordinates"])}


def _label(labels: dict[str, str], cells: list[str]) -> str:
    names = [labels[c] for c in cells if c in labels]
    return ", ".join(names)


def features(result: Result, labels: dict[str, str], with_numbers: bool) -> list[dict]:
    out: list[dict] = []
    for c in sorted(result.cells.values(), key=lambda c: c.cell):
        if c.level == 0:
            continue
        props = {"layer": "busy", "level": c.level, "status": c.status, "pattern": c.pattern,
                 "label": labels.get(c.cell, "")}
        if with_numbers:
            props |= {"cell": c.cell, "scans": publish(c.total), "local": publish(c.local),
                      "outbound": publish(c.outbound), "inbound": publish(c.inbound),
                      "saturation": round(c.saturation, 2), "potential": c.potential}
        out.append({"type": "Feature", "geometry": _round_geom(hex_polygon(c.cell)), "properties": props})

    drawn_links = [l for l in result.links.values() if l.validated and l.direction in ("one", "both")]
    ranked = sorted(drawn_links, key=lambda l: (l.total, l.a, l.b))
    for i, l in enumerate(ranked):
        level = 1 + (3 * i) // max(len(ranked), 1)
        props = {"layer": "connection", "level": level, "direction": l.direction, "status": l.status,
                 "pattern": l.pattern, "ends": [labels.get(l.from_cell, ""), labels.get(l.to_cell, "")]}
        if with_numbers:
            props |= {"from_cell": l.from_cell, "to_cell": l.to_cell,
                      "scans_from_to": publish(max(l.ab, l.ba)), "scans_to_from": publish(min(l.ab, l.ba)),
                      "seasons_seen": l.seasons_seen, "temporal": l.temporal,
                      "trend_quarter": None if l.trend_short is None else round(l.trend_short, 2),
                      "growth_year": None if l.growth is None else round(l.growth, 2)}
        geom = {"type": "LineString", "coordinates": [centre(l.from_cell), centre(l.to_cell)]}
        out.append({"type": "Feature", "geometry": geom, "properties": props})

    for ring in result.rings:
        props = {"layer": "ring", "role": "core", "ring": ring.ring_id, "label": _label(labels, ring.core)}
        if with_numbers:
            props |= {"core_cells": ring.core, "periphery_cells": ring.periphery,
                      "seasons_seen": ring.seasons_seen, "temporal": ring.temporal}
        out.append({"type": "Feature", "geometry": _round_geom(ring_outline(ring.core)), "properties": props})
        for p in ring.periphery:
            pprops = {"layer": "ring", "role": "periphery", "ring": ring.ring_id, "label": labels.get(p, "")}
            out.append({"type": "Feature", "geometry": _round_geom(hex_polygon(p)), "properties": pprops})
    return out


def collection(result: Result, labels: dict[str, str], with_numbers: bool) -> dict:
    return {
        "type": "FeatureCollection",
        "as_of": result.as_of.isoformat(),
        "provisional": result.settings.provisional,
        "unit": "scans on posters" if with_numbers else None,
        "features": features(result, labels, with_numbers),
    }


def check_public(fc: dict) -> None:
    """The public layer may carry shapes and words, never a count (2026-11-23)."""
    for f in fc["features"]:
        extra = set(f["properties"]) - PUBLIC_KEYS
        if extra:
            raise ValueError(f"public layer feature carries {sorted(extra)}")
        for k, v in f["properties"].items():
            if isinstance(v, (int, float)) and not isinstance(v, bool) and k != "level":
                raise ValueError(f"public layer feature carries a number in {k}")
            if k == "level" and v not in (1, 2, 3):
                raise ValueError(f"level must be 1, 2 or 3, got {v}")
    if fc.get("unit") is not None:
        raise ValueError("public layer must not name a unit of count")


def write_all(result: Result, labels: dict[str, str], out: Path) -> dict[str, Path]:
    out.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    public = collection(result, labels, with_numbers=False)
    check_public(public)
    paths["public"] = out / "layer-public.geojson"
    paths["public"].write_text(json.dumps(public, indent=1, sort_keys=True))
    paths["admin"] = out / "layer-admin.geojson"
    paths["admin"].write_text(json.dumps(collection(result, labels, with_numbers=True), indent=1, sort_keys=True))

    rdir = out / "research"
    rdir.mkdir(exist_ok=True)
    with (rdir / "corridors.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["from_cell", "to_cell", "from_label", "to_label", "direction", "scans_from_to", "scans_to_from",
                    "validated", "seasons_seen", "temporal", "trend_quarter", "trend_year", "growth_year",
                    "status", "pattern", "first_week", "last_week"])
        for l in sorted(result.links.values(), key=lambda l: (-l.total, l.a, l.b)):
            w.writerow([l.from_cell, l.to_cell, labels.get(l.from_cell, ""), labels.get(l.to_cell, ""),
                        l.direction, publish(max(l.ab, l.ba)), publish(min(l.ab, l.ba)), l.validated,
                        l.seasons_seen, l.temporal,
                        None if l.trend_short is None else round(l.trend_short, 3),
                        None if l.trend_long is None else round(l.trend_long, 3),
                        None if l.growth is None else round(l.growth, 3), l.status, l.pattern,
                        l.first, l.last])
    with (rdir / "corridor_types.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["cell_a", "cell_b", "uec_code", "scans"])
        for l in sorted(result.links.values(), key=lambda l: (l.a, l.b)):
            for uec, n in sorted(l.by_type.items()):
                if publish(n) is not None:
                    w.writerow([l.a, l.b, uec, publish(n)])
    with (rdir / "cells.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["cell", "label", "scans", "local", "outbound", "inbound", "saturation",
                    "saturation_quarter_before", "trend_quarter", "status", "potential", "pattern", "level"])
        for c in sorted(result.cells.values(), key=lambda c: (-c.total, c.cell)):
            w.writerow([c.cell, labels.get(c.cell, ""), publish(c.total), publish(c.local), publish(c.outbound),
                        publish(c.inbound), round(c.saturation, 3), round(c.saturation_before, 3),
                        None if c.trend_short is None else round(c.trend_short, 3), c.status, c.potential,
                        c.pattern, c.level])
    with (rdir / "rings.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ring_id", "resolution", "core", "periphery", "seasons_seen", "temporal"])
        for r in result.rings:
            w.writerow([r.ring_id, r.resolution, " ".join(r.core), " ".join(r.periphery), r.seasons_seen,
                        r.temporal])
        for res, n in sorted(result.fractal.items()):
            w.writerow([f"fractal-count-r{res}", res, "", "", n, ""])
    paths["research"] = rdir
    return paths
