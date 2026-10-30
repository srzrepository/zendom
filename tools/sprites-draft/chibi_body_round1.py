"""Full-body chibi sprites with swappable clothes. Head = the status-face portrait (chibi.py)."""
from PIL import Image, ImageDraw, ImageFont
import chibi
from chibi import PAL, _face_plain, E, FX
W, H, HY = 64, 128, 8          # canvas; head drawn 8px down to leave room for hats / idiot hair

def shade(hexc, f):
    r, g, b = int(hexc[1:3], 16), int(hexc[3:5], 16), int(hexc[5:7], 16)
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(c * f))) for c in (r, g, b))

TOPS = {}      # name -> draw(d, p, c, back) ; back=True for parts behind the head (hoods)
def top(name, long=False):
    def w(f): TOPS[name] = (f, long); return f
    return w
def torso(d, c, y1=93): d.rounded_rectangle([19, 61+HY-8, 44, y1+HY-8], 4, fill=c)
def sleeves(d, p, c, short=False):
    for x0 in (13, 44):
        d.rounded_rectangle([x0, 63, x0+6, 86 if not short else 72], 2, fill=c)
        if short: d.rectangle([x0+1, 72, x0+5, 86], fill=p["skin"])
        d.rectangle([x0+1, 86, x0+5, 90], fill=p["skin"])                      # hands
@top("tee")
def _(d, p, c, back):
    if back: return
    sleeves(d, p, c, short=True); torso(d, c); d.polygon([(28, 61), (36, 61), (32, 66)], fill=p["skin"])
@top("fleece")
def _(d, p, c, back):
    if back: return
    sleeves(d, p, c); torso(d, c); d.rectangle([28, 61, 35, 93], fill="#f5f2ed")
    d.line([(28, 61), (28, 93)], fill=shade(c, .8)); d.line([(35, 61), (35, 93)], fill=shade(c, .8))
    d.rectangle([20, 61, 26, 64], fill=shade(c, 1.1)); d.rectangle([37, 61, 43, 64], fill=shade(c, 1.1))   # collar
@top("hoodie")
def _(d, p, c, back):
    if back: d.ellipse([18, 52, 45, 66], fill=shade(c, .85)); return
    sleeves(d, p, c); torso(d, c)
    d.rounded_rectangle([24, 78, 39, 88], 2, fill=shade(c, .88)); d.line([(29, 62), (29, 72)], fill="#f5f2ed"); d.line([(34, 62), (34, 72)], fill="#f5f2ed")
    d.rectangle([19, 90, 44, 93], fill=shade(c, .85)); d.rectangle([13, 84, 19, 86], fill=shade(c, .85)); d.rectangle([44, 84, 50, 86], fill=shade(c, .85))
@top("sweater")
def _(d, p, c, back):
    if back: return
    sleeves(d, p, c); torso(d, c); d.rectangle([26, 61, 37, 63], fill=shade(c, .85))
    for x in range(20, 44, 3): d.line([(x, 90), (x, 93)], fill=shade(c, .85))
    for y in (68, 76): d.line([(21, y), (42, y)], fill=shade(c, 1.12))           # stripes
@top("shirt")
def _(d, p, c, back):
    if back: return
    sleeves(d, p, c); torso(d, c); d.line([(32, 63), (32, 93)], fill=shade(c, .8))
    for y in (68, 75, 82, 89): d.point((33, y), fill="#ffffff")
    d.polygon([(26, 61), (32, 61), (29, 66)], fill="#ffffff"); d.polygon([(32, 61), (38, 61), (35, 66)], fill="#ffffff")
@top("labcoat", long=True)
def _(d, p, c, back):
    if back: return
    sleeves(d, p, "#fbfbf8"); d.rounded_rectangle([18, 61, 45, 106], 3, fill="#fbfbf8")
    d.rectangle([27, 61, 36, 106], fill=c)                                       # the top underneath
    d.line([(27, 61), (27, 106)], fill="#c9ccd1"); d.line([(36, 61), (36, 106)], fill="#c9ccd1")
    d.polygon([(22, 61), (27, 61), (27, 70)], fill="#e3e5e8"); d.polygon([(41, 61), (36, 61), (36, 70)], fill="#e3e5e8")
    d.rectangle([38, 70, 43, 76], outline="#c9ccd1"); d.line([(40, 68), (40, 72)], fill="#3f86c4")   # pocket + pen
@top("raincoat", long=True)
def _(d, p, c, back):
    if back: d.ellipse([17, 51, 46, 66], fill=shade(c, .85)); return
    sleeves(d, p, c); d.rounded_rectangle([18, 61, 45, 104], 3, fill=c); d.line([(32, 62), (32, 104)], fill=shade(c, .75))
    for y in (70, 80, 90): d.rectangle([33, y, 34, y+1], fill="#5a4a2a")
    d.rectangle([22, 84, 27, 88], outline=shade(c, .75)); d.rectangle([37, 84, 42, 88], outline=shade(c, .75))
@top("dress", long=True)
def _(d, p, c, back):
    if back: return
    sleeves(d, p, c, short=True); torso(d, c, 88)
    d.polygon([(19, 86), (44, 86), (49, 106), (14, 106)], fill=c); d.line([(15, 105), (48, 105)], fill=shade(c, .82))
    d.polygon([(28, 61), (36, 61), (32, 65)], fill=p["skin"])
    for x, y in ((24, 96), (36, 99), (30, 90), (41, 92), (20, 101)): d.point((x, y), fill="#fff3c4")   # little flowers
@top("pajamas")
def _(d, p, c, back):
    if back: return
    sleeves(d, p, c); torso(d, c)
    for y in range(64, 93, 4): d.line([(19, y), (44, y)], fill="#ffffff")
    for y in range(64, 86, 4): d.line([(13, y), (19, y)], fill="#ffffff"); d.line([(44, y), (50, y)], fill="#ffffff")
    d.polygon([(27, 61), (37, 61), (32, 67)], fill=shade(c, .8))

BOTTOMS = {}
def bottom(name):
    def w(f): BOTTOMS[name] = f; return f
    return w
def legs(d, c, y0=92, y1=118):
    d.rectangle([21, y0, 30, y1], fill=c); d.rectangle([33, y0, 42, y1], fill=c); d.rectangle([21, y0, 42, y0+4], fill=c)
@bottom("jeans")
def _(d, p, c):
    legs(d, c); d.line([(25, 98), (25, 118)], fill=shade(c, 1.15)); d.line([(38, 98), (38, 118)], fill=shade(c, 1.15))
    d.rectangle([21, 92, 42, 93], fill=shade(c, .8)); d.point((32, 93), fill="#d9b25a")
@bottom("pants")
def _(d, p, c):
    legs(d, c); d.line([(31, 96), (31, 118)], fill=shade(c, .85)); d.line([(32, 96), (32, 118)], fill=shade(c, .85)); d.rectangle([21, 92, 42, 93], fill=shade(c, .8))
@bottom("sweats")
def _(d, p, c):
    legs(d, c); d.rectangle([21, 115, 30, 118], fill=shade(c, .82)); d.rectangle([33, 115, 42, 118], fill=shade(c, .82)); d.line([(29, 93), (29, 98)], fill="#ffffff"); d.line([(34, 93), (34, 98)], fill="#ffffff")
@bottom("shorts")
def _(d, p, c):
    legs(d, p["skin"], 100, 118); d.rectangle([21, 92, 30, 104], fill=c); d.rectangle([33, 92, 42, 104], fill=c); d.rectangle([21, 92, 42, 96], fill=c)
@bottom("skirt")
def _(d, p, c):
    legs(d, p["skin"], 100, 118); d.polygon([(21, 91), (42, 91), (46, 106), (17, 106)], fill=c); d.line([(18, 105), (45, 105)], fill=shade(c, .82))
@bottom("pjpants")
def _(d, p, c):
    legs(d, c)
    for y in range(95, 118, 4): d.line([(21, y), (30, y)], fill="#ffffff"); d.line([(33, y), (42, y)], fill="#ffffff")

SHOES = {}
def shoe(name):
    def w(f): SHOES[name] = f; return f
    return w
def feet(d, c, y0=117):
    d.rounded_rectangle([19, y0, 31, 123], 2, fill=c); d.rounded_rectangle([32, y0, 44, 123], 2, fill=c)
@shoe("sneakers")
def _(d, c):
    feet(d, "#f4f4f2"); d.line([(20, 121), (30, 121)], fill=c); d.line([(33, 121), (43, 121)], fill=c); d.line([(19, 123), (31, 123)], fill="#bdbdbd"); d.line([(32, 123), (44, 123)], fill="#bdbdbd")
@shoe("boots")
def _(d, c):
    d.rectangle([21, 110, 30, 118], fill=c); d.rectangle([33, 110, 42, 118], fill=c); feet(d, c); d.line([(19, 123), (44, 123)], fill=shade(c, .6))
@shoe("loafers")
def _(d, c):
    feet(d, c, 118); d.line([(22, 119), (28, 119)], fill=shade(c, 1.3)); d.line([(35, 119), (41, 119)], fill=shade(c, 1.3))
@shoe("slippers")
def _(d, c):
    d.ellipse([17, 115, 32, 125], fill=c); d.ellipse([31, 115, 46, 125], fill=c)
    for x in (21, 26, 35, 40): d.point((x, 118), fill="#ffffff")

HATS = {}
def hat(name):
    def w(f): HATS[name] = f; return f
    return w
@hat("none")
def _(d, c): pass
@hat("beanie")
def _(d, c):
    d.pieslice([11, 3+HY, 52, 40+HY], 180, 360, fill=c); d.rectangle([11, 20+HY, 52, 24+HY], fill=shade(c, .82)); d.ellipse([28, HY-4, 35, HY+3], fill=shade(c, 1.15))
@hat("cap")
def _(d, c):
    d.pieslice([12, 3+HY, 51, 36+HY], 180, 360, fill=c); d.rectangle([30, 17+HY, 56, 20+HY], fill=shade(c, .8)); d.point((31, 4+HY), fill=shade(c, .7))
@hat("frog")
def _(d, c):
    d.pieslice([9, 2+HY, 54, 40+HY], 180, 360, fill=c); d.rectangle([9, 19+HY, 54, 22+HY], fill=shade(c, .85))
    for ex in (18, 38):
        d.ellipse([ex, HY-6, ex+9, HY+3], fill=c); d.ellipse([ex+2, HY-4, ex+7, HY+1], fill="#ffffff"); d.rectangle([ex+4, HY-3, ex+5, HY], fill="#1b1b1f")
    d.line([(26, 14+HY), (29, 16+HY), (34, 16+HY), (37, 14+HY)], fill=shade(c, .6))
@hat("catears")
def _(d, c):
    d.arc([11, 4+HY, 52, 40+HY], 190, 350, fill=c)
    for x0 in (14, 40):
        d.polygon([(x0, 12+HY), (x0+5, HY-2), (x0+10, 10+HY)], fill=c); d.polygon([(x0+3, 10+HY), (x0+5, HY+3), (x0+7, 10+HY)], fill="#ff9cb8")
@hat("bow")
def _(d, c):
    d.polygon([(38, 6+HY), (46, 2+HY), (46, 14+HY)], fill=c); d.polygon([(54, 6+HY), (46, 2+HY), (46, 14+HY)], fill=c) if False else d.polygon([(47, 8+HY), (55, 3+HY), (55, 15+HY)], fill=c)
    d.rectangle([44, 6+HY, 48, 10+HY], fill=shade(c, .8))

DEFAULT = {
    "sam": dict(top=("fleece", "#9a9ea3"), bottom=("jeans", "#4a6a9a"), shoes=("sneakers", "#e07a5f"), hat=("none", "")),
    "charlie": dict(top=("tee", "#2d3b5b"), bottom=("pants", "#b8a07a"), shoes=("loafers", "#6b4325"), hat=("none", "")),
}

def sam_back_hair(d, p):
    d.ellipse([8, 6+HY, 55, 50+HY], fill=p["hair"]); d.rectangle([9, 26+HY, 54, 70], fill=p["hair"])
    for x0 in (9, 45):
        d.rectangle([x0, 58, x0+9, 74], fill=p["end"]); d.rectangle([x0+2, 68, x0+7, 77], fill=p["end2"])
        d.rectangle([x0, 54, x0+9, 57], fill=p["hair2"]); d.line([(x0+1, 61), (x0+4, 65), (x0+1, 70)], fill=p["end2"])

def body(k, outfit=None, key="normal", frame=0):
    o = dict(DEFAULT[k]); o.update(outfit or {}); p = PAL[k]
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    tname, tcol = o["top"]; tf, long = TOPS[tname]
    if key == "wag": chibi.dog_tail(d, frame) if False else None
    if key in ("dog",):
        tail = Image.new("RGBA", (64, 64), (0,0,0,0)); chibi.dog_tail(ImageDraw.Draw(tail), frame); im.alpha_composite(tail, (-14, 40))
    if k == "sam": sam_back_hair(d, p)
    tf(d, p, tcol, True)
    if tname == "dress": legs(d, p["skin"], 100, 118)
    elif not long or tname in ("labcoat", "raincoat"):
        bname, bcol = o["bottom"]; BOTTOMS[bname](d, p, bcol)
    SHOES[o["shoes"][0]](d, o["shoes"][1])
    d.rectangle([28, 54, 35, 62], fill=p["shade"])                        # neck
    tf(d, p, tcol, False)
    head = _face_plain(k, key, shoulders=False, backhair=False)
    im.alpha_composite(head, (0, HY))
    d = ImageDraw.Draw(im)
    if key == "ahoge": d.line([(31, 12), (29, 6), (30, 1), (34, 0), (39, 1), (42, 4), (42, 8)], fill=p["hair"], width=2)
    HATS[o["hat"][0]](d, o["hat"][1])
    return im

if __name__ == "__main__":
    LOOKS = [
        ("sam", "Everyday", {}),
        ("sam", "Lab day", dict(top=("labcoat", "#f5f2ed"), shoes=("sneakers", "#3f86c4"))),
        ("sam", "Cozy", dict(top=("hoodie", "#f2a7c3"), bottom=("sweats", "#9a9ea3"), shoes=("slippers", "#ffd1dc"), hat=("catears", "#3b271d"))),
        ("sam", "Rainy day", dict(top=("raincoat", "#f2c230"), shoes=("boots", "#7a4a2a"))),
        ("sam", "Picnic", dict(top=("dress", "#6fae6a"), shoes=("loafers", "#a0522d"), hat=("bow", "#e85d75"))),
        ("charlie", "Everyday", {}),
        ("charlie", "Weekend", dict(top=("hoodie", "#5f8f5a"), bottom=("jeans", "#4a6a9a"), shoes=("sneakers", "#d64545"), hat=("beanie", "#d9883e"))),
        ("charlie", "Dinner out", dict(top=("shirt", "#7aa3cc"), bottom=("pants", "#3a3a44"))),
        ("charlie", "Pajamas", dict(top=("pajamas", "#5c7fc2"), bottom=("pjpants", "#5c7fc2"), shoes=("slippers", "#c9a27a"), hat=("frog", "#6cbf4f"))),
        ("charlie", "Sweater weather", dict(top=("sweater", "#b5473a"), bottom=("jeans", "#33475e"), shoes=("boots", "#6b4325"), hat=("cap", "#2d3b5b"))),
    ]
    sc = 4; cw, ch = W*sc, H*sc
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
    sheet = Image.new("RGB", (5*(cw+16)+16, 2*(ch+50)+16), "#f3dca6"); dr = ImageDraw.Draw(sheet)
    for i, (k, label, o) in enumerate(LOOKS):
        r, c = divmod(i, 5); x, y = 16 + c*(cw+16), 16 + r*(ch+50)
        dr.rectangle([x, y, x+cw-1, y+ch-1], fill="#e9c98a")
        f = body(k, o).resize((cw, ch), Image.NEAREST); sheet.paste(f, (x, y), f)
        dr.text((x+cw//2, y+ch+24), label, fill="#4a2610", font=font, anchor="mm")
    sheet.save("bodies.png"); print(sheet.size)
