# Geographies

One folder per place the NCR layers are read in. Each holds:

- `corridors.json`: the corridor strips and nodes, and the segment rules version
  they follow (`docs/corridors-chicago-sw.md` explains rules v1);
- `jurisdictions.geojson`: municipal lines (`kind: municipality`) and named
  neighbourhoods (`kind: chicago_community_area`), clipped to the area and
  simplified to about 10 m;
- `transit.geojson` (optional): rail lines drawn under the strips on previews.

To add a place: write its `corridors.json` (streets as lng/lat lines, nodes as
points), add its jurisdictions, run `python -m ncr corridors --geography DIR --out OUT`
and `python tools/corridor_map.py DIR map.png`.

## Sources

| Folder | File | Source |
| --- | --- | --- |
| chicago-sw | jurisdictions.geojson | Census TIGER 2019 places (public domain), via github.com/generalpiston/geojson-us-city-boundaries; City of Chicago community areas (City of Chicago data portal), via github.com/Crains-Chicago/where-to-buy |
| chicago-sw | transit.geojson | Metra lines via github.com/noumanmkhan/layers.city; CTA rail lines (City of Chicago, 2023) via github.com/YizhouWang19 (Urban Data Science project) |
| chicago-sw | corridors.json | written by `tools/chicago_sw_definitions.py` from Chicago's address grid |
| sawyer-mi | jurisdictions.geojson | Census TIGER 2019 places, as above |
| sawyer-mi | corridors.json | hand-placed from town centres; needs a ground check |
