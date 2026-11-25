"""tools/prototype_data.py: the layer-map prototype's town tints and page template."""
import importlib.util
from pathlib import Path

from shapely.geometry import box

from ncr.corridors import load_jurisdictions

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("prototype_data", ROOT / "tools" / "prototype_data.py")
proto = importlib.util.module_from_spec(spec)
spec.loader.exec_module(proto)


def test_touching_towns_get_different_tints_and_apart_towns_may_share():
    towns = {"big": box(0, 0, 0.02, 0.02), "east": box(0.02, 0, 0.03, 0.01),
             "north": box(0, 0.02, 0.01, 0.03), "far": box(0.5, 0.5, 0.51, 0.51)}
    t = proto.town_tints(towns)
    assert t["big"] != t["east"] and t["big"] != t["north"]
    assert t["far"] == t["big"] == 0  # largest first takes tint 0; a town touching nothing reuses it
    assert all(0 <= v < proto.TINTS for v in t.values())


def test_no_two_neighbouring_towns_share_a_tint_on_the_chicago_sw_map():
    towns = {n: g for n, k, g in load_jurisdictions(ROOT / "geographies/chicago-sw/jurisdictions.geojson")
             if k == "municipality"}
    t = proto.town_tints(towns)
    pad = 50 / 111_000
    for a in towns:
        for b in towns:
            if a < b and towns[a].buffer(pad).intersects(towns[b].buffer(pad)):
                assert t[a] != t[b], (a, b)


def test_template_has_one_data_slot_and_the_layer_order():
    page = proto.TEMPLATE.read_text()
    assert page.count("__NCR_DATA__") == 1
    order = [page.index(f"g('{g}')") for g in ("towns", "streets", "hex7", "strips", "nodes", "rings")]
    assert order == sorted(order), "base, hexagons, corridors, nodes, then rings on top"
    for step in ("'base'", "'hex'", "'corridors'", "'rings'"):
        assert f"id:{step}" in page
