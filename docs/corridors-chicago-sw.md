# Proposed corridor segments: Chicago southwest side and Sawyer

Status: proposed for Matt's review, 2026-11-25. Segment rules: `segment-rules-v1`.
Nothing here is fitted to scan data yet. These are the frame the scan layers will be read along.

## The question

The OSE map already cuts the ground into numbered res 7 hexagons (the
hyperlocal areas). The NCR layers need something above them: corridors that
follow where commerce sits and traffic actually moves, so that rings can be
seen forming along them at three sizes. Matt's direction (2026-11-25):

- weight the cut heavily toward commercial strips and real traffic;
- look for retail sited at town lines to draw on a neighbour's tax base, so
  corridors straddle official lines instead of stopping at them;
- the point is to show how places are actually used, which has outgrown the
  jurisdictional map; this makes that gap visible, it does not argue against it;
- never about people: only which events happen where and which corridors
  carry the traffic.

## Words

The doctrine words keep their meaning (OCR_VISION section 9, OSE ADR-009,
`docs/RING-METHODOLOGY.md`):

| Word | Here |
| --- | --- |
| Node | An activation point. Where a crossroads, station or founding venue sits on a corridor; segments are cut there. Venues themselves stay res 9 inside OSE; only res 7 leaves (OCR-docs ADR-011). |
| Corridor | The organic thread connecting nodes. Here: a commercial strip, drawn as a street line widened about one lot deep each side, cut node to node. Scans between hexagons (the existing `connection` layer) say how much each segment carries. |
| Ring | The self-sustaining loop. Read from traffic, never drawn by hand: 3+ hexagons trading both ways season after season (`ncr/compute.py`). Small, medium and large rings are the same test at res 7 (about 5 km²), res 6 (about 36 km²) and res 5 (about 250 km²). The study box holds 36, 8 and 3 hexagons at those sizes. |

## Segment rules v1

1. **A corridor is a commercial strip.** It is on the list only if a plan, a
   TIF or business district, a traffic count, or a transit terminal says
   commerce and traffic concentrate on it. Tier 1 is a primary strip, tier 2 a
   secondary one.
2. **Strip width 150 m each side of the centreline**, about one commercial lot
   plus its parking. Wider would swallow the houses behind the strip.
3. **Cut at nodes, never at town lines.** A segment runs from one node to the
   next (a node within 120 m of the line counts). A town line inside a segment
   is reported, not used as a cut.
4. **Town lines are an overlay.** Each segment reports the share of its strip
   in each municipality and each Chicago community area, and how much of its
   centreline rides within 150 m of a municipal line (`edge_share`). A segment
   **straddles** when two or more towns each hold at least 10% of it.
   Community areas are neighbourhood names, not tax bases, so they never make a
   segment straddle.
5. **Every segment lists the res 7 hexagons it touches**, so scan counts per
   hexagon roll up to segments with no new data.
6. **Rules are versioned.** A change to any number above is a new rules
   version, written here and in each `corridors.json`, so results from two rule
   sets are never compared as if they were one.

The code: `ncr/corridors.py` (rules), `tools/chicago_sw_definitions.py`
(streets and nodes), `python -m ncr corridors --geography geographies/chicago-sw --out DIR`,
`python tools/corridor_map.py geographies/chicago-sw map.png`.

## What the research found

- **Border retail is the rule, not the exception.** Across the CMAP region, 60%
  of sales-tax-rebate deals went to developments on or next to a municipal
  border, and about 47% of all suburban retail sits there; CMAP notes a town
  gains when "more of the service and infrastructure costs may be borne by
  neighboring jurisdictions" (CMAP, 2016, data to 2015).
- **Western Avenue is one corridor across three governments.** The 2024
  application for a Beverly corridor plan defines it as "South Western Avenue
  from Evergreen Park at 83rd Street to Vermont Street in Blue Island" and says
  it "crosses multiple jurisdictions including Evergreen Park, City of Chicago,
  and Blue Island." From 87th to 103rd, Western *is* the Chicago / Evergreen Park
  line: Evergreen Plaza sits on the Evergreen Park side at 95th, and Chicago's
  95th & Western TIF (90th to 96th, Western to Beverly Ave) faces it "to
  reinforce retail activity along the Beverly community's main shopping
  corridors."
- **Cicero Avenue carries the most traffic** in the box: 34,600 vehicles a day
  between 103rd and 111th, rising to 63,400 north of the box (Southwest
  Conference of Mayors, 2014). It is Chicago's west line up to 87th, then
  Hometown (87th to 90th), Oak Lawn (87th to 111th) and Alsip (111th to 127th).
  Oak Lawn's "commercial crossroads" is 95th & Cicero, with more retail at
  103rd and 111th.
- **95th Street is the spine.** The 95th/Dan Ryan Red Line terminal is "the
  busiest station within the CTA system" and 95th & Halsted "sees hundreds of
  buses daily" (95th Street Corridor Plan). West of it: the 95th Street
  streetscape (Wood to Ashland), 95th & Western, 95th & Kedzie in Evergreen
  Park, and Oak Lawn's crossroads at Cicero.
- **The Red Line extension adds four stations** near 103rd, 111th, Michigan Ave
  and 130th (CTA). They sit just east of Halsted, so Halsted's nodes at 103rd,
  111th and 127th are marked as transit nodes.
- **Mount Greenwood's 111th Street** business district (111th & Kedzie TIF,
  Mt. Greenwood Plaza) and **Calumet Park's 127th Street and Ashland Avenue**
  (its own corridor plan: 127th from Winchester to Aberdeen; Ashland from its
  Metra station to Raceway Park at Vermont) complete the tier 1 and 2 strips.
- **Sawyer** is a destination, not a residential corridor (OSE user research
  plan, 2026-10-04). Its businesses cluster downtown and along Red Arrow Highway,
  just off I-94 exit 12 (South County News 2023; Visit Southwest Michigan).

## What the proposal looks like

64 segments on 14 corridors (6 north-south, 8 east-west) and 36 nodes in the
Chicago box; 5 segments on 3 corridors and 6 nodes around Sawyer.

- **27 of 64 segments straddle a town line**: 64 of 136 km of strip.
- **10 segments ride a town line for at least 90% of their length**: Western
  87th to 95th (Chicago / Evergreen Park), Cicero 79th to 87th (Chicago /
  Burbank), Pulaski 87th to 111th in three segments (Evergreen Park, Hometown,
  Oak Lawn, Chicago), 87th Street west of Western in two segments (Chicago /
  Evergreen Park / Hometown), 111th west of Pulaski (Chicago / Oak Lawn), and
  119th from Ashland to Pulaski in two segments (Chicago / Blue Island /
  Calumet Park / Merrionette Park / Alsip).
- Six nodes are marked **border retail**: 95th & Western, 103rd & Western,
  87th & Pulaski, 103rd & Pulaski, 111th & Cicero, 119th & Western, plus 147th
  & Western where Posen, Harvey and Dixmoor meet.

The full table with town shares, edge share and hexagons per segment is what
`python -m ncr corridors` writes (`corridor-segments.csv`, `.geojson`).

## Ring saturation

Built in `ncr/saturation.py`; the admin layer carries it on each ring and
`python -m ncr build` writes `research/ring-saturation-history.csv`. Matt
(2026-11-25) took the street and node list as the starting point, to be
calibrated through practice.

- **Saturation per ring is read from the hexagons inside it**, as the average of
  four shares, each 0 to 1 and each a ratio of scan counts: coverage (hexagons
  inside the ring's outline with traffic at or over the floor), steadiness
  (weeks with traffic, over the ring's core), closure (scans touching the core
  that stay inside it) and reciprocity (how even the two directions of its
  links are).
- **A baseline**, so a number means something: each ring against its own
  history (the same window a year earlier), and against the other rings of the
  same size in the geography. A ring is not called saturated on one season.
- **A confidence measure beside it**, because sparse early data can fake a
  ring: how many weeks of data, how many scans after the floor, and in how many
  seasons the ring held. Low confidence is shown as "forming" whatever the
  saturation reads.
- **No saturation threshold is set in advance.** Matt (2026-11-25): the value
  at which a ring is saturated is not known from theory and can only be found
  through applied practice. So the job measures and records the four shares
  and their average every week, keeps the history, and names no cut point. A
  threshold, if one ever exists, is read off that history once real rings have
  been seen to hold. This is the stance the doctrine already takes: OSE
  `docs/RING-METHODOLOGY.md` Part 2 ("Governing Principle" and section 2.6,
  "Pre-Registration Standard") locks the infrastructure now, collects across
  seasons, fits the model with an academic partner, and pre-registers the
  criteria before any confirmatory test; OSE ADR-009 defers ring thresholds
  the same way. The segment rules here are infrastructure (Part 1 side); the
  saturation threshold is a Part 2 finding.

## Weak spots, said plainly

- **Traffic counts are thin.** The only counts found for the box are Cicero
  (2014 plan) and 99th Street east of Halsted (25,709 vehicles a day, City of
  Chicago counts, 2026). IDOT's AADT map and Chicago's own counts could not be
  read from this session; they should be pulled before tiers are final.
- **Commerce is read from plans, TIFs and business districts**, not from
  parcel zoning or business licences. A zoning pass would confirm the strip
  ends.
- **Street lines are placed from Chicago's address grid**, calibrated on
  Evergreen Park's Census lines, good to about 150 m. Sawyer's lines are placed
  by hand from town centres and need a check on the ground; Sawyer has no Census
  place line of its own (Chikaming Township).
- **Town lines are Census 2019.** Annexations since then are not in them.
- **Diagonal streets are left out** for now: Vincennes Ave, Southwest Highway
  (mostly west of Cicero) and Vermont St in Blue Island's uptown. Vermont St is
  covered by the 127th & Western node.

## Sources

- CMAP, Sales tax rebates (2016): https://www.cmap.illinois.gov/documents/10180/542501/PU-0014_SALES_TAX_REBATES.pdf/e54292d2-d81a-52ca-fd5e-dcc449cf5f3e
- Beverly corridor plan application (2024): https://nita.illinois.gov/uploads/files/general/Communities/2024-Call-for-projects-applications/Beverly-Corridor-Plan.pdf
- 95th & Western TIF: https://www.chicago.gov/city/en/depts/dcd/supp_info/tif/95th_western_tif.html
- Evergreen Plaza redevelopment (Patch, 2015): https://patch.com/illinois/evergreenpark/ghost-mall-no-more-reboot-evergreen-plaza-gets-underway
- Cicero Avenue TOD and transit plan (2014): https://rtams.org/sites/default/files/digital_documents/3337_SWConfMayors_CiceroAve_TOD_TransitImprovementPlan_2014.pdf
- 95th Street Corridor Plan: https://chicago.gov/95th and https://www.chicago.gov/content/dam/city/sites/95th-street/pdfs/presentation_boards_111624.pdf
- Red Line extension: https://transitchicago.com/rle/
- 111th/Kedzie TIF: https://www.chicago.gov/city/en/depts/dcd/supp_info/tif/111th_kedzie_tif.html
- Calumet Park corridor plan: https://engage.cmap.illinois.gov/calumet-park-corridor-plan
- Chicago traffic counts summary (2026): https://keepchicagolandmoving.com/chicago-street-traffic-counts/
- Sawyer: https://southcountynews.org/2023/07/01/on-the-road-again-sawyer/ and https://swmichigan.org/plan-and-stay/towns/sawyer
- Boundaries: Census TIGER 2019 places (via github.com/generalpiston/geojson-us-city-boundaries); City of Chicago community areas; Metra and CTA lines (see `geographies/README.md`).
