"""Write the data file the NCR Layer Map prototype draws (one JSON, already projected).

Each place is projected to a flat plane in units of 100 m around its centre and
written as SVG path strings, so the page draws with no map library. Layers:
streets, towns, Chicago community areas, Metra and CTA, res 7/6/5 hexagons,
corridor segments, nodes, and, for Chicago, the practice busy places and rings
with their saturation history (made-up practice data, labelled so on the page).

Usage: python tools/prototype_data.py OUT.json
"""
import json
import math
import sys
from pathlib import Path

import h3
from shapely.geometry import box, shape

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ncr.compute import compute, run  # noqa: E402
from ncr.corridors import load_definitions, load_jurisdictions, segments  # noqa: E402
from ncr.layers import ring_outline  # noqa: E402
from ncr.practice import generate, labels  # noqa: E402
from ncr.saturation import SIZES, history, ring_saturation  # noqa: E402


class Plane:
    def __init__(self, lat0, lng0):
        self.lat0, self.lng0, self.c = lat0, lng0, math.cos(math.radians(lat0))

    def p(self, lng, lat):
        return ((lng - self.lng0) * self.c * 1113.2, -(lat - self.lat0) * 1105.74)

    def ring(self, coords):
        return "M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in (self.p(*q) for q in coords)) + "Z"

    def line(self, coords):
        return "M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in (self.p(*q) for q in coords))

    def geom(self, g):
        if g.is_empty:
            return ""
        t = g.geom_type
        if t == "Polygon":
            return self.ring(g.exterior.coords) + "".join(self.ring(i.coords) for i in g.interiors)
        if t == "LineString":
            return self.line(g.coords)
        if t.startswith("Multi") or t == "GeometryCollection":
            return "".join(self.geom(x) for x in g.geoms)
        return ""

    def hexagon(self, cell):
        return self.ring([(lng, lat) for lat, lng in h3.cell_to_boundary(cell)])


def place(geo, lat0, lng0, frame):
    pl = Plane(lat0, lng0)
    F = box(*frame)
    gdir = ROOT / "geographies" / geo
    defs = load_definitions(gdir / "corridors.json")
    jur = load_jurisdictions(gdir / "jurisdictions.geojson")
    out = {"name": defs["name"], "towns": [], "areas": [], "transit": [], "streets": [], "hex": {}, "segments": [],
           "nodes": [], "busy": [], "rings": []}
    for name, kind, g in jur:
        g2 = g.intersection(F).simplify(0.0002)
        if g2.is_empty:
            continue
        x, y = pl.p(*g2.representative_point().coords[0])
        item = {"name": name, "d": pl.geom(g2), "at": [round(x, 1), round(y, 1)], "area": round(g2.area * 1e4, 2)}
        out["towns" if kind == "municipality" else "areas"].append(item)
    for fname, key in (("transit.geojson", "transit"), ("streets.geojson", "streets")):
        path = gdir / fname
        if path.exists():
            for f in json.loads(path.read_text())["features"]:
                g = shape(f["geometry"]).intersection(F)
                if not g.is_empty:
                    out[key].append({"name": f["properties"]["name"],
                                     "kind": f["properties"].get("class") or f["properties"].get("kind"),
                                     "d": pl.geom(g)})
    w, s, e, n = frame
    shell = h3.LatLngPoly([(s, w), (s, e), (n, e), (n, w)])
    for res in (7, 6, 5):
        cells = h3.h3shape_to_cells_experimental(shell, res, contain="overlap")
        out["hex"][res] = [{"id": c, "d": pl.hexagon(c)} for c in sorted(cells)]
    for sg in segments(defs, jur):
        mx, my = pl.p(*sg.line.interpolate(0.5, normalized=True).coords[0])
        out["segments"].append({"id": sg.id, "name": sg.name, "tier": sg.tier, "from": sg.start, "to": sg.end,
                                "km": sg.length_km, "towns": sg.municipalities, "hoods": sg.neighbourhoods,
                                "edge": sg.edge_share, "straddles": sg.straddles, "hexes": len(sg.hexagons),
                                "d": pl.geom(sg.strip.simplify(0.00005)), "mid": [round(mx, 1), round(my, 1)]})
    out["why"] = {c.id: c.why for c in defs["corridors"]}
    for nd in defs["nodes"]:
        x, y = pl.p(*nd.at)
        out["nodes"].append({"id": nd.id, "name": nd.name, "kind": nd.kind, "at": [round(x, 1), round(y, 1)]})
    x0, y0 = pl.p(w, n)
    x1, y1 = pl.p(e, s)
    out["box"] = [round(x0, 1), round(y0, 1), round(x1 - x0, 1), round(y1 - y0, 1)]
    return out, pl


def practice(out, pl):
    rows = generate()
    lab = labels()
    res7 = run(rows)
    inside = {h["id"] for h in out["hex"][7]}
    for c in res7.cells.values():
        if c.level and c.cell in inside:
            out["busy"].append({"id": c.cell, "level": c.level, "label": lab.get(c.cell, ""), "d": pl.hexagon(c.cell)})
    hist = history(rows, step_weeks=4)
    for res in (7, 6, 5):
        result = res7 if res == 7 else compute(rows, None, res7.as_of, res)
        for ring in result.rings:
            sat = ring_saturation(result, ring)
            names = sorted({lab[c] for c in lab if (c if res == 7 else h3.cell_to_parent(c, res)) in ring.core})
            series = [[r["as_of"], r["saturation"], r["confidence"]] for r in hist
                      if r["resolution"] == res and set(r["core"].split()) & set(ring.core)]
            out["rings"].append({
                "id": ring.ring_id, "size": SIZES[res], "res": res, "places": names,
                "d": pl.geom(ring_outline(ring.core)),
                "periphery": [pl.hexagon(p) for p in ring.periphery] if res == 7 else [],
                "sat": {k: getattr(sat, k) for k in ("saturation", "coverage", "steadiness", "closure",
                                                     "reciprocity", "confidence", "hexagons", "active",
                                                     "weeks_observed", "seasons_seen")},
                "series": series, "as_of": res7.as_of.isoformat()})


def main():
    chi, pl = place("chicago-sw", 41.69, -87.69, (-87.77, 41.605, -87.615, 41.765))
    practice(chi, pl)
    saw, _ = place("sawyer-mi", 41.88, -86.60, (-86.64, 41.79, -86.545, 41.955))
    Path(sys.argv[1]).write_text(json.dumps({"chicago": chi, "sawyer": saw}, separators=(",", ":")))
    print(f"wrote {sys.argv[1]}: {len(chi['segments'])} + {len(saw['segments'])} segments, "
          f"{len(chi['streets'])} streets, {len(chi['rings'])} practice rings")


if __name__ == "__main__":
    main()
