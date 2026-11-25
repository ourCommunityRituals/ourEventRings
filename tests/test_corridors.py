import csv
import json
from pathlib import Path

import h3
import pytest
from shapely.geometry import box

from ncr.corridors import (Corridor, Node, Projector, hexagons_of, load_definitions, load_jurisdictions, segments,
                           to_geojson, write_segments)

ROOT = Path(__file__).resolve().parents[1]

# Two towns side by side, split at longitude -87.70; a street runs east-west across both.
WEST = ("Westville", "municipality", box(-87.74, 41.68, -87.70, 41.72))
EAST = ("Eastville", "municipality", box(-87.70, 41.68, -87.66, 41.72))
HOOD = ("Hood", "chicago_community_area", box(-87.70, 41.68, -87.66, 41.72))
ACROSS = Corridor("main", "Main Street", 1, [(-87.73, 41.70), (-87.67, 41.70)])
ALONG = Corridor("line", "Line Road", 2, [(-87.70, 41.685), (-87.70, 41.715)])  # on the town line itself
INSIDE = Corridor("east", "East Road", 2, [(-87.68, 41.685), (-87.68, 41.715)])  # well inside Eastville


def defs(corridors, nodes=()):
    return {"name": "test", "lat0": 41.7, "strip_m": 150, "snap_m": 120, "edge_m": 150,
            "corridors": list(corridors), "nodes": list(nodes)}


def test_a_town_line_never_cuts_a_corridor():
    segs = segments(defs([ACROSS]), [WEST, EAST])
    assert len(segs) == 1
    s = segs[0]
    assert s.straddles
    assert set(s.municipalities) == {"Westville", "Eastville"}
    assert s.municipalities["Westville"] == pytest.approx(0.5, abs=0.05)


def test_nodes_on_the_line_cut_it_in_order_and_far_nodes_do_not():
    nodes = [Node("b", "B", (-87.69, 41.7005), "crossroads"), Node("a", "A", (-87.71, 41.6995), "crossroads"),
             Node("far", "Far", (-87.70, 41.71), "crossroads")]
    segs = segments(defs([ACROSS], nodes), [WEST, EAST])
    assert [(s.start, s.end) for s in segs] == [("line end", "A"), ("A", "B"), ("B", "line end")]
    assert [s.id for s in segs] == ["main-1", "main-2", "main-3"]
    total = sum(s.length_km for s in segs)
    assert total == pytest.approx(5.0, abs=0.1)  # 0.06 degrees of longitude at 41.7 N


def test_a_node_just_past_the_snap_distance_does_not_cut():
    p = Projector(41.7)
    off = 130 / p.ky  # 130 m north of the line, snap is 120 m
    segs = segments(defs([ACROSS], [Node("x", "X", (-87.70, 41.70 + off), "crossroads")]), [WEST, EAST])
    assert len(segs) == 1


def test_edge_share_reads_how_much_of_a_strip_rides_a_town_line():
    along, inside = segments(defs([ALONG, INSIDE]), [WEST, EAST])
    assert along.edge_share == 1.0
    assert inside.edge_share == 0.0
    assert not inside.straddles
    assert inside.municipalities == {"Eastville": 1.0}


def test_neighbourhoods_are_an_overlay_not_a_town():
    (s,) = segments(defs([INSIDE]), [EAST, HOOD])
    assert s.neighbourhoods == {"Hood": 1.0}
    assert s.municipalities == {"Eastville": 1.0}
    assert not s.straddles


def test_a_sliver_under_two_percent_is_not_listed():
    sliver = ("Sliver", "municipality", box(-87.6815, 41.684, -87.6785, 41.6845))
    (s,) = segments(defs([INSIDE]), [EAST, sliver])
    assert "Sliver" not in s.municipalities


def test_straddling_needs_two_towns_with_a_tenth_each():
    small = ("Small", "municipality", box(-87.6815, 41.684, -87.6785, 41.690))  # about 15% of the strip
    tiny = ("Tiny", "municipality", box(-87.6815, 41.684, -87.6785, 41.6875))  # about 8%
    (s,) = segments(defs([INSIDE]), [EAST, small])
    assert s.straddles
    (t,) = segments(defs([INSIDE]), [EAST, tiny])
    assert not t.straddles


def test_hexagons_are_res_7_and_cover_the_strip():
    (s,) = segments(defs([ACROSS]), [WEST, EAST])
    assert s.hexagons and all(h3.get_resolution(c) == 7 for c in s.hexagons)
    for lng in (-87.73, -87.70, -87.67):
        assert h3.latlng_to_cell(41.70, lng, 7) in s.hexagons
    assert s.hexagons == sorted(s.hexagons)
    assert h3.latlng_to_cell(41.70, -87.70, 7) in hexagons_of(box(-87.701, 41.699, -87.699, 41.701))


def test_outputs_carry_segments_and_nodes(tmp_path):
    d = defs([ACROSS], [Node("a", "A", (-87.71, 41.70), "border retail")])
    segs = segments(d, [WEST, EAST])
    fc = to_geojson(d, segs)
    layers = [f["properties"]["layer"] for f in fc["features"]]
    assert layers == ["corridor", "corridor", "node"]
    assert fc["provisional"] is True
    node = fc["features"][-1]["properties"]
    assert node["hexagon"] == h3.latlng_to_cell(41.70, -87.71, 7)
    paths = write_segments(d, segs, tmp_path)
    rows = list(csv.DictReader(paths["table"].open()))
    assert [r["segment"] for r in rows] == ["main-1", "main-2"]
    assert rows[0]["straddles"] == "False" and rows[0]["municipalities"] == "Westville 100%"
    assert json.loads(paths["geojson"].read_text())["geography"] == "test"


@pytest.mark.parametrize(("geo", "longest_km"), [("chicago-sw", 5.0), ("sawyer-mi", 10.0)])
def test_each_committed_geography_builds_and_every_node_sits_on_a_corridor(geo, longest_km):
    d = load_definitions(ROOT / "geographies" / geo / "corridors.json")
    j = load_jurisdictions(ROOT / "geographies" / geo / "jurisdictions.geojson")
    segs = segments(d, j)
    used = {s.start for s in segs} | {s.end for s in segs}
    assert {n.name for n in d["nodes"]} <= used
    assert all(s.length_km <= longest_km for s in segs)
    assert len({s.id for s in segs}) == len(segs)


def test_the_chicago_definitions_file_is_what_the_generator_writes(tmp_path, monkeypatch):
    import importlib.util

    spec = importlib.util.spec_from_file_location("gen", ROOT / "tools" / "chicago_sw_definitions.py")
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)
    committed = json.loads((ROOT / "geographies" / "chicago-sw" / "corridors.json").read_text())
    assert [c["id"] for c in committed["corridors"]] == [c[0] for c in gen.CORRIDORS]
    assert [n["at"] for n in committed["nodes"]] == [n[2] for n in gen.NODES]
    # The grid is calibrated on Evergreen Park's Census lines: 87th & Western, 103rd & Pulaski.
    assert gen.at(2400, 87) == [-87.682, 41.7356]
    assert gen.at(4000, 103) == [-87.7217, 41.7063]
