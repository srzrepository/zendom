"""Stardew-style full-body sprites: parts are flat masks; shading and outlines are added automatically
(light from the top-left, a darker ramp on the right/bottom edges, dark coloured outlines)."""
from PIL import Image, ImageDraw
W, H, TOP = 64, 122, 6

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
                    wdt = x1 - x0 + 1; t = (x - x0) / max(1, wdt - 1)
                    if cyl and wdt >= 4:
                        if t > .68: c = r["sh"]
                        if t > .88 and wdt >= 8: c = r["sh2"]
                        if t < .16 and wdt >= 8: c = r["hi"]
                    if get(x, y+1) != i and get(x, y+1) != -1 and get(x, y+1) < i: pass
                    if get(x, y-1) != i and wdt >= 4 and name not in ("face", "hands", "neck", "legs", "arms2", "ears"): c = r["hi"]
                    if name == "face" and t > .8: c = r["sh"]
                    elif get(x, y-1) > i and not s.parts[get(x, y-1)][4] and s.parts[get(x, y-1)][0] != "ears": c = r["sh2"]    # cast shadow under something in front
                # inner outline where this part overlaps a part behind it (selective outline)
                OCC = {"hairtips", "arms", "arms2", "hands", "hair", "top", "hat", "shoes", "jacket"}
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

