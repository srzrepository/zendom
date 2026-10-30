"""Stardew-style full-body sprites: parts are flat masks; shading and outlines are added automatically
(light from the top-left, a darker ramp on the right/bottom edges, dark coloured outlines)."""
from PIL import Image, ImageDraw
W, H, TOP = 32, 56, 4      # TOP: headroom so hair tufts and hats fit

def hx(c): return tuple(int(c[i:i+2], 16) for i in (1, 3, 5))
def mix(a, b, t): return tuple(round(a[i] + (b[i]-a[i])*t) for i in range(3))
def ramp(base, warm=(255, 236, 200), cool=(40, 20, 50)):
    b = hx(base)
    return {"hi": mix(b, warm, .28), "base": b, "sh": mix(b, cool, .28), "sh2": mix(b, cool, .45), "out": mix(b, (25, 12, 18), .68)}

class Pen:
    """ImageDraw for masks: shapes are filled unless outline=1 is asked for; everything moves down TOP px."""
    def __init__(s, m): s.d = ImageDraw.Draw(m)
    def _xy(s, xy): return [(p[0], p[1] + TOP) for p in xy] if isinstance(xy[0], (tuple, list)) else [v + (TOP if i % 2 else 0) for i, v in enumerate(xy)]
    def _shape(s, fn, xy, *a, outline=None, **k):
        if outline: getattr(s.d, fn)(s._xy(xy), *a, outline=1, **k)
        else: getattr(s.d, fn)(s._xy(xy), *a, fill=1, **k)
    def rectangle(s, xy, **k): s._shape("rectangle", xy, **k)
    def ellipse(s, xy, **k): s._shape("ellipse", xy, **k)
    def polygon(s, xy, **k): s._shape("polygon", xy, **k)
    def pieslice(s, xy, a, b, **k): s._shape("pieslice", xy, a, b, **k)
    def line(s, xy, **k): s.d.line(s._xy(xy), fill=1, **k)
    def point(s, xy): s.d.point(s._xy([xy]), fill=1)

class Sprite:
    def __init__(s): s.parts = []           # (name, ramp, mask image, cyl) in draw order
    def part(s, name, color, draw, cyl=True, flat=False):
        m = Image.new("1", (W, H), 0); draw(Pen(m)); s.parts.append((name, ramp(color) if isinstance(color, str) else color, m, cyl, flat)); return s
    def render(s):
        idg = [[-1]*W for _ in range(H)]
        for i, (_, _, m, _, _) in enumerate(s.parts):
            px = m.load()
            for y in range(H):
                for x in range(W):
                    if px[x, y]: idg[y][x] = i
        out = Image.new("RGBA", (W, H), (0, 0, 0, 0)); o = out.load()
        get = lambda x, y: idg[y][x] if 0 <= x < W and 0 <= y < H else -1
        for y in range(H):
            for x in range(W):
                i = idg[y][x]
                if i < 0: continue
                name, r, m, cyl, flat = s.parts[i]
                c = r["base"]
                if not flat:
                    # where this part's own shape ends: shadow on the right/bottom, highlight on the top-left
                    xs = [xx for xx in range(W) if idg[y][xx] == i]; x0, x1 = min(xs), max(xs)
                    wdt = x1 - x0 + 1
                    if cyl and wdt >= 3 and x >= x1 - max(0, wdt // 4): c = r["sh"]
                    if get(x, y+1) != i and get(x, y+1) != -1 and get(x, y+1) < i: pass
                    if get(x, y-1) != i and get(x-1, y) != i and wdt >= 4 and name not in ("face", "hands", "neck", "legs", "arms2"): c = r["hi"]
                    if name == "face" and get(x+1, y) != i: c = r["sh"]
                    elif get(x, y-1) > i and not s.parts[get(x, y-1)][4] and s.parts[get(x, y-1)][0] != "ears": c = r["sh2"]    # cast shadow under something in front
                # inner outline where this part overlaps a part behind it (selective outline)
                OCC = {"arms", "arms2", "hands", "hair", "top", "hat", "shoes"}
                if name in OCC:
                    for dx, dy in ((1, 0), (-1, 0), (0, 1)):
                        j = get(x+dx, y+dy)
                        if j >= 0 and j < i and s.parts[j][0] not in (name, "detail") and s.parts[j][0] != "hairback":
                            c = r["out"]; break
                o[x, y] = c + (255,)
        # outer outline: transparent pixels touching the sprite take the dark of their neighbour
        cp = out.copy(); q = cp.load()
        for y in range(H):
            for x in range(W):
                if q[x, y][3]: continue
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    j = get(x+dx, y+dy)
                    if j >= 0:
                        o[x, y] = s.parts[j][1]["out"] + (255,); break
        return out

SKIN = {"sam": "#c98e66", "charlie": "#efc0a0"}
HAIR = {"sam": "#3a261c", "charlie": "#2f2119"}

def person(k, o):
    s = Sprite(); skin, hair = SKIN[k], HAIR[k]
    top, tc = o["top"]; bot, bc = o["bottom"]; shoe, sc = o["shoes"]; hat, hc = o.get("hat", ("none", ""))
    if k == "sam":   # long hair behind everything
        s.part("hairback", hair, lambda d: (d.ellipse([8, 3, 23, 18]), d.rectangle([8, 10, 23, 29])))
        s.part("hairends", "#a8784a", lambda d: (d.rectangle([8, 24, 11, 31]), d.rectangle([20, 24, 23, 31])), cyl=False)
    if top in ("hoodie", "raincoat"): s.part("hood", tc, lambda d: d.ellipse([10, 16, 21, 22]))
    # legs
    if top == "dress" or bot in ("shorts", "skirt"):
        s.part("legs", skin, lambda d: (d.rectangle([11, 36, 14, 46]), d.rectangle([17, 36, 20, 46])))
    if top != "dress":
        if bot == "shorts": s.part("pants", bc, lambda d: (d.polygon([(10, 32), (21, 32), (21, 38), (16, 38), (15, 35), (14, 38), (10, 38)])))
        elif bot == "skirt": s.part("pants", bc, lambda d: d.polygon([(10, 32), (21, 32), (23, 39), (8, 39)]))
        else: s.part("pants", bc, lambda d: (d.polygon([(10, 32), (21, 32), (21, 46), (17, 46), (16, 36), (15, 36), (14, 46), (10, 46)])))
    # shoes
    if shoe == "boots": s.part("shoes", sc, lambda d: (d.rectangle([10, 42, 14, 48]), d.rectangle([17, 42, 21, 48]), d.rectangle([9, 47, 14, 48]), d.rectangle([17, 47, 22, 48])))
    elif shoe == "slippers": s.part("shoes", sc, lambda d: (d.ellipse([8, 45, 15, 49]), d.ellipse([16, 45, 23, 49])), cyl=False)
    else: s.part("shoes", sc, lambda d: (d.rectangle([9, 46, 14, 48]), d.rectangle([17, 46, 22, 48])), cyl=False)
    if shoe == "sneakers": s.part("detail", "#f4f1ea", lambda d: (d.line([(9, 48), (14, 48)]), d.line([(17, 48), (22, 48)])), flat=True)
    # torso
    long = top in ("labcoat", "raincoat", "dress")
    s.part("neck", skin, lambda d: d.rectangle([14, 17, 17, 20]), cyl=False)
    if top == "dress":
        s.part("top", tc, lambda d: d.polygon([(10, 20), (21, 20), (21, 30), (24, 38), (7, 38), (10, 30)]))
    elif long:
        s.part("top", tc, lambda d: d.polygon([(9, 20), (22, 20), (22, 31), (23, 41), (8, 41), (9, 31)]))
    else:
        s.part("top", tc, lambda d: d.polygon([(9, 20), (22, 20), (22, 31), (21, 33), (10, 33), (9, 31)]))
    if top == "fleece": s.part("detail", "#f2efe8", lambda d: d.rectangle([14, 20, 17, 32]), cyl=False)
    if top == "labcoat": s.part("detail", "#7f8fa8", lambda d: d.rectangle([14, 20, 17, 30]), cyl=False)
    if top == "hoodie": s.part("detail", "#f2efe8", lambda d: (d.line([(14, 21), (14, 24)]), d.line([(17, 21), (17, 24)])), flat=True)
    if top in ("tee", "dress"): s.part("detail", skin, lambda d: d.polygon([(14, 20), (17, 20), (16, 22), (15, 22)]), flat=True)
    if top == "shirt": s.part("detail", "#f4f1ea", lambda d: (d.polygon([(13, 20), (15, 20), (14, 22)]), d.polygon([(16, 20), (18, 20), (17, 22)])), flat=True)
    if top == "sweater": s.part("detail", tc, lambda d: d.line([(10, 26), (21, 26)]), flat=False)
    if top == "raincoat": s.part("detail", "#6b5328", lambda d: (d.point((16, 24)), d.point((16, 28)), d.point((16, 32)), d.point((16, 36))), flat=True)
    if top == "pajamas":
        s.part("detail", "#f2f2ff", lambda d: [d.line([(9, y), (22, y)]) for y in range(22, 33, 3)], flat=True)
    # arms: relaxed, a little bent, slightly away from the body
    short = top in ("tee", "dress")
    arm = lambda d: (d.polygon([(9, 20), (6, 22), (5, 30), (7, 31), (8, 24), (9, 23)]), d.polygon([(22, 20), (25, 22), (26, 30), (24, 31), (23, 24), (22, 23)]))
    s.part("arms", tc, arm)
    if short: s.part("arms2", skin, lambda d: (d.polygon([(6, 25), (5, 30), (7, 31), (8, 25)]), d.polygon([(25, 25), (26, 30), (24, 31), (23, 25)])))
    s.part("hands", skin, lambda d: (d.rectangle([5, 31, 7, 33]), d.rectangle([24, 31, 26, 33])), cyl=False)
    # head
    s.part("face", skin, lambda d: (d.ellipse([9, 5, 22, 19])), cyl=False)
    s.part("ears", skin, lambda d: (d.point((9, 12)), d.point((22, 12)), d.point((9, 13)), d.point((22, 13))), cyl=False)
    if k == "sam":
        s.part("hair", hair, lambda d: (d.pieslice([8, 1, 23, 11], 180, 360), d.polygon([(15, 3), (11, 6), (9, 10), (8, 17), (10, 12), (12, 8), (15, 6)]),
                                        d.polygon([(16, 3), (20, 6), (22, 10), (23, 17), (21, 12), (19, 8), (16, 6)]), d.rectangle([8, 9, 9, 22]), d.rectangle([22, 9, 23, 22])))
    else:
        s.part("hair", hair, lambda d: (d.pieslice([8, 2, 23, 16], 180, 360), d.polygon([(8, 9), (23, 9), (22, 11), (19, 9), (17, 11), (15, 9), (12, 11), (10, 9), (9, 12)]),
                                        d.polygon([(10, 4), (11, 0), (13, 3)]), d.polygon([(13, 3), (15, -1), (17, 2)]), d.polygon([(17, 2), (20, 0), (20, 4)]),
                                        d.rectangle([8, 9, 9, 12]), d.rectangle([22, 9, 23, 12])))
    # face details
    eye = "#2a1810" if k == "sam" else "#26262e"
    s.part("glass", "#8a5f1e" if k == "sam" else "#5d6773", (lambda d: [d.line(seg) for x0 in (11, 17) for seg in ([(x0+1, 11), (x0+2, 11)], [(x0+1, 14), (x0+2, 14)], [(x0, 12), (x0, 13)], [(x0+3, 12), (x0+3, 13)])] + [d.line([(15, 12), (16, 12)])]) if k == "sam" else
                 (lambda d: (d.rectangle([11, 11, 14, 14], outline=1), d.rectangle([17, 11, 20, 14], outline=1), d.line([(15, 12), (16, 12)]))), flat=True)
    s.part("eye", eye, lambda d: (d.line([(13, 12), (13, 13)]), d.line([(18, 12), (18, 13)])), flat=True)
    s.part("blush", "#e8907c" if k == "sam" else "#f2a090", lambda d: (d.point((12, 15)), d.point((19, 15))), flat=True)
    s.part("mouth", "#8a4436", lambda d: d.point((15, 17)), flat=True)
    # hats
    if hat == "beanie":
        s.part("hat", hc, lambda d: d.ellipse([8, 0, 23, 9]))
        s.part("hat", hc, lambda d: d.rectangle([8, 6, 23, 8]), cyl=False)
        s.part("pom", "#f4efe6", lambda d: d.ellipse([14, -3, 17, 0]), cyl=False)
    if hat == "cap": s.part("hat", hc, lambda d: (d.pieslice([8, 1, 23, 13], 180, 360), d.rectangle([15, 6, 27, 7])))
    if hat == "frog":
        s.part("hat", hc, lambda d: (d.pieslice([7, 0, 24, 15], 180, 360), d.ellipse([9, -2, 13, 2]), d.ellipse([18, -2, 22, 2])))
        s.part("detail", "#ffffff", lambda d: (d.point((11, 0)), d.point((20, 0))), flat=True)
    if hat == "catears":
        s.part("hat", hc, lambda d: (d.polygon([(8, 5), (9, -2), (14, 3)]), d.polygon([(17, 3), (22, -2), (23, 5)])))
        s.part("detail", "#ff9cb8", lambda d: (d.line([(10, 1), (10, 3)]), d.line([(21, 1), (21, 3)])), flat=True)
    if hat == "bow": s.part("hat", hc, lambda d: (d.polygon([(19, 2), (23, 0), (23, 5)]), d.polygon([(19, 2), (16, 0), (16, 5)])))
    return s.render()

LOOKS = [
    ("sam", "Everyday", dict(top=("fleece", "#9a9ea3"), bottom=("jeans", "#4a6a9a"), shoes=("sneakers", "#e07a5f"))),
    ("sam", "Lab day", dict(top=("labcoat", "#f3f3ee"), bottom=("jeans", "#4a6a9a"), shoes=("sneakers", "#3f86c4"))),
    ("sam", "Cozy", dict(top=("hoodie", "#f2a7c3"), bottom=("sweats", "#9a9ea3"), shoes=("slippers", "#ffd1dc"), hat=("catears", "#3a261c"))),
    ("sam", "Rainy day", dict(top=("raincoat", "#f2c230"), bottom=("jeans", "#4a6a9a"), shoes=("boots", "#7a4a2a"))),
    ("sam", "Picnic", dict(top=("dress", "#6fae6a"), bottom=("jeans", "#4a6a9a"), shoes=("loafers", "#a0522d"), hat=("bow", "#e85d75"))),
    ("charlie", "Everyday", dict(top=("tee", "#2d3b5b"), bottom=("pants", "#b8a07a"), shoes=("loafers", "#6b4325"))),
    ("charlie", "Weekend", dict(top=("hoodie", "#5f8f5a"), bottom=("jeans", "#4a6a9a"), shoes=("sneakers", "#d64545"), hat=("beanie", "#d9883e"))),
    ("charlie", "Dinner out", dict(top=("shirt", "#7aa3cc"), bottom=("pants", "#3a3a44"), shoes=("loafers", "#4a2a1a"))),
    ("charlie", "Pajamas", dict(top=("pajamas", "#5c7fc2"), bottom=("pants", "#5c7fc2"), shoes=("slippers", "#c9a27a"), hat=("frog", "#6cbf4f"))),
    ("charlie", "Sweater weather", dict(top=("sweater", "#b5473a"), bottom=("jeans", "#33475e"), shoes=("boots", "#6b4325"), hat=("cap", "#2d3b5b"))),
]
if __name__ == "__main__":
    from PIL import ImageFont
    sc = 6; cw, ch = W*sc, H*sc
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
    sheet = Image.new("RGB", (5*(cw+20)+20, 2*(ch+50)+20), "#f3dca6"); dr = ImageDraw.Draw(sheet)
    for i, (k, label, o) in enumerate(LOOKS):
        r, c = divmod(i, 5); x, y = 20 + c*(cw+20), 20 + r*(ch+50)
        dr.rectangle([x, y, x+cw-1, y+ch-1], fill="#e9c98a"); dr.rectangle([x, y+ch-40, x+cw-1, y+ch-1], fill="#c99a5c")
        f = person(k, o).resize((cw, ch), Image.NEAREST); sheet.paste(f, (x, y), f)
        dr.text((x+cw//2, y+ch+24), label, fill="#4a2610", font=font, anchor="mm")
    sheet.save("sd.png"); print(sheet.size)
