"""Draw the public layer as three phone-sized pictures, for review only.

Needs matplotlib (pip install matplotlib). It has no street map: each picture says
so. On /map (OSE-2217) the layers sit see-through over the street map.
Usage: python tools/preview.py OUT_DIR_OF_BUILD PICTURE_DIR
"""
import json, sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as P, FancyArrowPatch

src = Path(sys.argv[1]); out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
fc = json.loads((src / "layer-public.geojson").read_text())
feats = fc["features"]
INK="#1f2a33"; QUIET="#5b6770"; SHADE={1:"#9ec5e8",2:"#4f93cf",3:"#1d5f9e"}; RING="#7a4fb3"
def frame(title, sentence):
    fig, ax = plt.subplots(figsize=(3.9, 5.6), dpi=200)
    fig.patch.set_facecolor("#ffffff"); ax.set_facecolor("#f1f3f5")
    ax.set_xlim(-87.80, -87.46); ax.set_ylim(41.55, 41.86)
    ax.set_aspect(1/0.745, adjustable="box"); ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values(): s.set_color("#c9d1d8")
    fig.text(0.05, 0.965, title, fontsize=13, weight="bold", color=INK, va="top")
    fig.text(0.05, 0.925, sentence, fontsize=8.2, color=QUIET, va="top", wrap=True)
    fig.text(0.05, 0.035, "PRACTICE DATA. NO STREET MAP IN THIS PICTURE:\nthis computer cannot reach street tiles. On /map these\nshapes sit see-through over the street map.",
             fontsize=7, color="#8a1c1c", weight="bold", va="bottom")
    plt.subplots_adjust(left=0.04, right=0.96, top=0.84, bottom=0.13)
    return fig, ax
OFF={"Beverly":(0.02,0.02,"left"),"Evergreen Park":(-0.02,0.025,"right"),"Blue Island":(0.02,-0.012,"left"),
     "Mount Greenwood":(-0.025,-0.006,"right"),"Morgan Park":(0.025,-0.01,"left"),"Oak Lawn":(-0.02,0.012,"right"),
     "Hammond":(0.02,-0.01,"left"),"Bronzeville":(0.02,0.006,"left"),"Hyde Park":(0.02,-0.01,"left")}
def label(ax, f):
    lab=f["properties"].get("label")
    if not lab or lab not in OFF: return
    g=f["geometry"]["coordinates"][0]; x=sum(p[0] for p in g)/len(g); y=sum(p[1] for p in g)/len(g)
    dx,dy,ha=OFF[lab]
    ax.annotate(lab,(x,y),(x+dx,y+dy),fontsize=6.5,color=INK,ha=ha,va="center",weight="bold",
                arrowprops=dict(arrowstyle="-",color=QUIET,lw=0.4))
def sawyer_note(ax):
    ax.text(-87.47, 41.735, "Sawyer, Michigan\n(off the map, 60 km east)", fontsize=6.3, color=INK, ha="right", va="center")

fig, ax = frame("Busy places", "Darker areas had more scans on their posters.\nNo numbers are shown.")
for f in feats:
    if f["properties"]["layer"]=="busy":
        ax.add_patch(P(f["geometry"]["coordinates"][0], fc=SHADE[f["properties"]["level"]], ec=INK, lw=0.5, alpha=0.75)); label(ax,f)
fig.savefig(out/"1-busy-places.png"); plt.close(fig)

fig, ax = frame("Connections", "Lines show scans on posters in one area for\nevents in another. An arrow means one way.")
for f in feats:
    p=f["properties"]
    if p["layer"]=="busy":
        ax.add_patch(P(f["geometry"]["coordinates"][0], fc="#ffffff", ec="#9aa5ae", lw=0.4, alpha=0.6)); label(ax,f)
for f in feats:
    p=f["properties"]
    if p["layer"]=="connection":
        (x1,y1),(x2,y2)=f["geometry"]["coordinates"]; w={1:1.2,2:2.4,3:3.8}[p["level"]]
        style="-|>" if p["direction"]=="one" else "-"
        if x1>-87.46: x1,y1=-87.47+0.001,y1+(y2-y1)*((x1+87.47)/(x1-x2))
        ax.add_patch(FancyArrowPatch((x1,y1),(x2,y2),arrowstyle=style,mutation_scale=10,lw=w,color="#1d5f9e",alpha=0.85,shrinkA=4,shrinkB=4))
sawyer_note(ax); fig.savefig(out/"2-connections.png"); plt.close(fig)

fig, ax = frame("Rings", "A ring is three or more areas that send scans\nboth ways, season after season. Dotted: tied in.")
for f in feats:
    p=f["properties"]
    if p["layer"]=="ring" and p["role"]=="core":
        ax.add_patch(P(f["geometry"]["coordinates"][0], fc=RING, ec=RING, lw=1.6, alpha=0.22))
        ax.text(-87.78, 41.845, "Ring: "+p["label"].replace(", ",",\n"), fontsize=7.5, color=RING, weight="bold", va="top")
    if p["layer"]=="ring" and p["role"]=="periphery":
        ax.add_patch(P(f["geometry"]["coordinates"][0], fc="none", ec=RING, lw=1.0, ls=":")); label(ax,f)
for f in feats:
    if f["properties"]["layer"]=="busy" and f["properties"]["label"] in ("Beverly","Evergreen Park","Blue Island"):
        ax.add_patch(P(f["geometry"]["coordinates"][0], fc="none", ec=RING, lw=0.8)); label(ax,f)
ax.text(-87.47, 41.718, "dotted when tied in by summer trips", fontsize=6, color=QUIET, ha="right", va="top")
sawyer_note(ax); fig.savefig(out/"3-rings.png"); plt.close(fig)
print("ok")
