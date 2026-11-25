"""Draw the proposed corridor segments as stacked layers, for review.

Layers, bottom to top: town lines and Chicago community areas (base), Metra and
CTA lines, the res 7 hexagons (the hyperlocal areas on the OSE map), corridor
strips, nodes. A strip that straddles a town line is drawn in the border colour.

Needs matplotlib. Usage:
  python tools/corridor_map.py GEOGRAPHY_DIR OUT.png [--title TEXT]
"""
import argparse
import json
import sys
from pathlib import Path

import h3
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Polygon as P  # noqa: E402
from shapely.geometry import box, shape  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ncr.corridors import load_definitions, load_jurisdictions, segments  # noqa: E402

INK, QUIET, GRID = "#1f2a33", "#5b6770", "#c3ccd4"
ONE, BORDER, TRANSIT = "#2f6fb0", "#d0731c", "#6b4fa0"
NODE = {"crossroads": "#1f2a33", "border retail": "#d0731c", "transit": "#6b4fa0", "founding": "#1a7f4b",
        "destination": "#1a7f4b"}


def polys(g):
    return getattr(g, "geoms", [g])


def main() -> None:
    a = argparse.ArgumentParser()
    a.add_argument("geo", type=Path)
    a.add_argument("out", type=Path)
    a.add_argument("--title", default="")
    a.add_argument("--size", type=float, nargs=2, default=(11, 13))
    args = a.parse_args()

    defs = load_definitions(args.geo / "corridors.json")
    juris = load_jurisdictions(args.geo / "jurisdictions.geojson")
    segs = segments(defs, juris)
    xs = [p[0] for c in defs["corridors"] for p in c.line] + [n.at[0] for n in defs["nodes"]]
    ys = [p[1] for c in defs["corridors"] for p in c.line] + [n.at[1] for n in defs["nodes"]]
    pad = 0.012
    w, s, e, n = min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad
    frame = box(w, s, e, n)

    fig, ax = plt.subplots(figsize=tuple(args.size), dpi=110)
    fig.patch.set_facecolor("#ffffff")
    ax.set_facecolor("#f6f7f8")
    ax.set_xlim(w, e)
    ax.set_ylim(s, n)
    ax.set_aspect(1 / 0.745)
    ax.set_xticks([])
    ax.set_yticks([])

    # 1. base: towns (solid) and Chicago community areas (dotted), with names
    for name, kind, g in juris:
        g = g.intersection(frame)
        if g.is_empty:
            continue
        for p in polys(g):
            if p.geom_type != "Polygon":
                continue
            ls = "-" if kind == "municipality" else ":"
            lw = 1.1 if kind == "municipality" else 0.6
            ax.add_patch(P(list(p.exterior.coords), fc="none", ec="#8a96a0", lw=lw, ls=ls, zorder=1))
        c = g.representative_point()
        style = dict(fontsize=7.5 if kind == "municipality" else 6.2, color=QUIET,
                     style="normal" if kind == "municipality" else "italic", ha="center", zorder=2)
        ax.text(c.x, c.y, name.upper() if kind == "municipality" else name, **style)

    # 2. transit lines
    tpath = args.geo / "transit.geojson"
    if tpath.exists():
        for f in json.loads(tpath.read_text())["features"]:
            g = shape(f["geometry"])
            for line in getattr(g, "geoms", [g]):
                x, y = line.xy
                ax.plot(x, y, color=TRANSIT, lw=1.2, ls=(0, (6, 2)), alpha=0.7, zorder=2)

    # 3. res 7 hexagons over the frame
    shell = [(s, w), (s, e), (n, e), (n, w)]
    for cell in h3.h3shape_to_cells_experimental(h3.LatLngPoly(shell), 7, contain="overlap"):
        ring = [(lng, lat) for lat, lng in h3.cell_to_boundary(cell)]
        ax.add_patch(P(ring, fc="none", ec=GRID, lw=0.5, zorder=3))

    # 4. corridor strips
    for sg in segs:
        colour = BORDER if sg.straddles else ONE
        alpha = 0.55 if sg.tier == 1 else 0.32
        for p in polys(sg.strip):
            ax.add_patch(P(list(p.exterior.coords), fc=colour, ec=colour, lw=0.4, alpha=alpha, zorder=4))
        mid = sg.line.interpolate(0.5, normalized=True)
        ax.text(mid.x, mid.y, sg.id, fontsize=5.6, color=INK, ha="center", va="center", zorder=6,
                bbox=dict(boxstyle="round,pad=0.12", fc="#ffffff", ec="none", alpha=0.75))

    # 5. nodes
    for nd in defs["nodes"]:
        ax.plot(*nd.at, "o", ms=5.5, color=NODE.get(nd.kind, INK), mec="#ffffff", mew=0.8, zorder=7)

    fig.text(0.04, 0.975, args.title or defs["name"], fontsize=14, weight="bold", color=INK, va="top")
    legend = ("Strips: blue = inside one town; orange = straddles a town line (2+ towns hold 10%+ of it). "
              "Darker = primary strip.\nDots: orange = retail at a town line, purple = transit, green = founding "
              "or destination, black = crossroads.\nGrey hexagons = res 7 areas (the OSE map's numbered "
              "areas). Solid lines = towns, dotted = Chicago community areas, dashed purple = Metra and CTA.")
    fig.text(0.04, 0.945, legend, fontsize=8, color=QUIET, va="top")
    note = defs.get("note", "Street lines placed from the address grid (about 150 m).")
    fig.text(0.04, 0.012, "Proposed segments for review. No scan data is drawn. " + note, fontsize=7.5,
             color="#8a1c1c", va="bottom", wrap=True)
    plt.subplots_adjust(left=0.03, right=0.97, top=0.885, bottom=0.03)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out)
    print(f"wrote {args.out}: {len(segs)} segments")


if __name__ == "__main__":
    main()
