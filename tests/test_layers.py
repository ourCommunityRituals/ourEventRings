import json

import pytest

from ncr.compute import run
from ncr.layers import check_public, collection, write_all
from ncr.practice import generate, labels


@pytest.fixture(scope="module")
def result():
    return run(generate())


def test_public_layer_has_shapes_and_no_numbers(result):
    fc = collection(result, labels(), with_numbers=False)
    check_public(fc)
    text = json.dumps([f["properties"] for f in fc["features"]])
    for word in ("scans", "inbound", "outbound", "saturation", "cell", "uec"):
        assert word not in text


def test_check_public_refuses_a_count():
    fc = {"unit": None, "features": [{"properties": {"layer": "busy", "level": 2, "scans": 40}}]}
    with pytest.raises(ValueError):
        check_public(fc)


def test_admin_numbers_are_rounded_to_five_and_never_under_five(result):
    fc = collection(result, labels(), with_numbers=True)
    for f in fc["features"]:
        for k in ("scans", "local", "outbound", "inbound", "scans_from_to", "scans_to_from"):
            v = f["properties"].get(k)
            if v is not None:
                assert v >= 5 and v % 5 == 0, (k, v)


def test_every_layer_is_drawn(result, tmp_path):
    paths = write_all(result, labels(), tmp_path)
    fc = json.loads(paths["public"].read_text())
    kinds = {f["properties"]["layer"] for f in fc["features"]}
    assert kinds == {"busy", "connection", "ring"}
    assert (paths["research"] / "corridors.csv").exists()
