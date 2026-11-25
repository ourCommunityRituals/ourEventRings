"""Write geographies/chicago-sw/corridors.json: the proposed corridor segments.

Chicago's address grid runs on into the south suburbs, so each street is placed
from its grid number: 800 west per mile east-west (Halsted 800 W, Western
2400 W, Cicero 4800 W) and 8 blocks per mile north-south (87th, 95th, 103rd).
The grid is calibrated on Evergreen Park's Census boundary (87th, 103rd,
Western, Pulaski) and is good to about 150 m, well inside one res 7 hexagon.

Why each corridor and node is here is in docs/corridors-chicago-sw.md.
Usage: python tools/chicago_sw_definitions.py
"""
import json
from pathlib import Path

WESTERN, PULASKI = -87.6820, -87.7217
MILE_LNG = (PULASKI - WESTERN) / 2  # 2400 W to 4000 W is two miles
LAT87, LAT103 = 41.7356, 41.7063
MILE_LAT = (LAT87 - LAT103) / 2


def lng(addr_w: int) -> float:
    return round(WESTERN + (addr_w - 2400) / 800 * MILE_LNG, 5)


def lat(street: float) -> float:
    return round(LAT87 - (street - 87) / 8 * MILE_LAT, 5)


def at(addr_w: int, street: float) -> list[float]:
    return [lng(addr_w), lat(street)]


HALSTED, ASHLAND, WESTERN_W, KEDZIE, PULASKI_W, CICERO = 800, 1600, 2400, 3200, 4000, 4800
NORTH, SOUTH = 79, 147


def ns(addr_w, a=NORTH, b=SOUTH):
    return [at(addr_w, a), at(addr_w, b)]


def ew(street, a=HALSTED, b=CICERO):
    return [at(a, street), at(b, street)]


CORRIDORS = [
    # North-south strips
    ("western", "Western Avenue", 1, ns(WESTERN_W, 79, 127),
     "Beverly's main street and the Chicago / Evergreen Park line from 87th to 103rd; studied as one corridor "
     "from 83rd to Vermont St in Blue Island across three governments; Evergreen Plaza and the 95th & Western TIF "
     "face each other across it."),
    ("cicero", "Cicero Avenue", 1, ns(CICERO, 79, 147),
     "The heaviest strip in the box (34,600 vehicles a day at 103rd-111th, 2014 plan); Chicago's west line to 87th, "
     "then Hometown, Oak Lawn and Alsip; retail crossroads at 95th, 103rd and 111th."),
    ("halsted", "Halsted Street", 1, ns(HALSTED, 79, 147),
     "East edge; 95th & Halsted is the busiest bus crossroads by the 95th Red Line terminal; Red Line extension "
     "stations at 103rd, 111th and 130th sit just east; runs on through Calumet Park, Riverdale and Harvey."),
    ("pulaski", "Pulaski Road", 2, ns(PULASKI_W, 79, 147),
     "Evergreen Park / Oak Lawn / Hometown line from 87th to 103rd; Mount Greenwood's west half; Crestwood, Robbins "
     "and Midlothian to the south."),
    ("kedzie", "Kedzie Avenue", 2, ns(KEDZIE, 79, 127),
     "Through Evergreen Park (95th & Kedzie retail), the 111th & Kedzie business district and Merrionette Park, "
     "into Blue Island."),
    ("ashland", "Ashland Avenue", 2, ns(ASHLAND, 87, 131),
     "Calumet Park's own corridor plan runs Ashland from its Metra station to Raceway Park at Vermont."),
    # East-west strips
    ("e79", "79th Street", 2, ew(79), "North edge; long neighbourhood retail strip through Auburn Gresham and Ashburn."),
    ("e87", "87th Street", 2, ew(87),
     "Evergreen Park's north line; Dan Ryan Woods at Western; Hometown / Burbank corner at Cicero."),
    ("e95", "95th Street", 1, ew(95),
     "The spine: Red Line terminal and the 95th Street plan in the east, the 95th St streetscape (Wood to Ashland), "
     "95th & Western, 95th & Kedzie in Evergreen Park, Oak Lawn's 95th & Cicero crossroads in the west."),
    ("e103", "103rd Street", 2, ew(103),
     "Evergreen Park's south line; Beverly / Washington Heights; Red Line extension station near its east end."),
    ("e111", "111th Street", 1, ew(111),
     "Mount Greenwood's business district (111th & Kedzie TIF) and Morgan Park; Oak Lawn / Alsip line at Cicero; "
     "Red Line extension station near its east end."),
    ("e119", "119th Street", 2, ew(119),
     "Chicago's line with Blue Island, Calumet Park and Merrionette Park for most of its length."),
    ("e127", "127th Street", 1, ew(127),
     "Calumet Park's commercial 127th (Winchester to Aberdeen), Blue Island's south side, Alsip, the Cal-Sag "
     "channel close by; meets Western at Blue Island's uptown."),
    ("e147", "147th Street (Sibley Blvd)", 2, ew(147),
     "South edge; Harvey, Dixmoor, Posen, Midlothian, Oak Forest share it."),
]

# Nodes: where corridors cross and commerce clusters, stations, founding venues.
NODES = [
    ("n79-western", "79th & Western", at(WESTERN_W, 79), "crossroads"),
    ("n79-cicero", "79th & Cicero (Ford City nearby)", at(CICERO, 79), "crossroads"),
    ("n87-western", "87th & Western (Dan Ryan Woods)", at(WESTERN_W, 87), "crossroads"),
    ("n87-cicero", "87th & Cicero", at(CICERO, 87), "crossroads"),
    ("n95-halsted", "95th & Halsted (Red Line terminal)", at(HALSTED, 95), "transit"),
    ("n95-ashland", "95th & Ashland", at(ASHLAND, 95), "crossroads"),
    ("n95-western", "95th & Western (Evergreen Plaza)", at(WESTERN_W, 95), "border retail"),
    ("n95-kedzie", "95th & Kedzie", at(KEDZIE, 95), "crossroads"),
    ("n95-pulaski", "95th & Pulaski", at(PULASKI_W, 95), "crossroads"),
    ("n95-cicero", "95th & Cicero (Oak Lawn crossroads)", at(CICERO, 95), "crossroads"),
    ("n103-halsted", "103rd & Halsted (Red Line extension)", at(HALSTED, 103), "transit"),
    ("n103-western", "103rd & Western", at(WESTERN_W, 103), "border retail"),
    ("n103-cicero", "103rd & Cicero", at(CICERO, 103), "crossroads"),
    ("n111-halsted", "111th & Halsted (Red Line extension)", at(HALSTED, 111), "transit"),
    ("n111-western", "111th & Western", at(WESTERN_W, 111), "crossroads"),
    ("n111-kedzie", "111th & Kedzie (Mount Greenwood)", at(KEDZIE, 111), "crossroads"),
    ("n111-pulaski", "111th & Pulaski", at(PULASKI_W, 111), "crossroads"),
    ("n111-cicero", "111th & Cicero (Oak Lawn / Alsip)", at(CICERO, 111), "border retail"),
    ("n119-western", "119th & Western (Blue Island line)", at(WESTERN_W, 119), "border retail"),
    ("n119-ashland", "119th & Ashland", at(ASHLAND, 119), "crossroads"),
    ("n127-halsted", "127th & Halsted", at(HALSTED, 127), "crossroads"),
    ("n127-ashland", "127th & Ashland (Calumet Park)", at(ASHLAND, 127), "crossroads"),
    ("n127-western", "127th & Western (Blue Island uptown)", at(WESTERN_W, 127), "founding"),
    ("n127-kedzie", "127th & Kedzie", at(KEDZIE, 127), "crossroads"),
    ("n127-cicero", "127th & Cicero", at(CICERO, 127), "crossroads"),
    ("n147-halsted", "147th & Halsted", at(HALSTED, 147), "crossroads"),
    ("n147-pulaski", "147th & Pulaski", at(PULASKI_W, 147), "crossroads"),
    ("n147-cicero", "147th & Cicero", at(CICERO, 147), "crossroads"),
    ("n79-pulaski", "79th & Pulaski", at(PULASKI_W, 79), "crossroads"),
    ("n87-halsted", "87th & Halsted", at(HALSTED, 87), "crossroads"),
    ("n87-pulaski", "87th & Pulaski (Evergreen Park / Hometown corner)", at(PULASKI_W, 87), "border retail"),
    ("n103-pulaski", "103rd & Pulaski (Evergreen Park / Oak Lawn corner)", at(PULASKI_W, 103), "border retail"),
    ("n111-ashland", "111th & Ashland (Morgan Park)", at(ASHLAND, 111), "crossroads"),
    ("n119-pulaski", "119th & Pulaski", at(PULASKI_W, 119), "crossroads"),
    ("n127-pulaski", "127th & Pulaski", at(PULASKI_W, 127), "crossroads"),
    ("n147-western", "147th & Western (Posen / Harvey / Dixmoor)", at(WESTERN_W, 147), "border retail"),
]


def main() -> None:
    out = {
        "name": "Chicago southwest side: 79th to 147th, Halsted to Cicero",
        "rules": "segment-rules-v1",
        "lat0": 41.69,
        "strip_m": 150,
        "snap_m": 120,
        "edge_m": 150,
        "corridors": [{"id": i, "name": n, "tier": t, "line": l, "why": w} for i, n, t, l, w in CORRIDORS],
        "nodes": [{"id": i, "name": n, "at": a, "kind": k} for i, n, a, k in NODES],
    }
    path = Path(__file__).resolve().parents[1] / "geographies" / "chicago-sw" / "corridors.json"
    path.write_text(json.dumps(out, indent=1) + "\n")
    print(f"wrote {path}: {len(CORRIDORS)} corridors, {len(NODES)} nodes")


if __name__ == "__main__":
    main()
