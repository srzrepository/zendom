"""Bigger Stardew-style sprites (64x116): real shoulders, waist, tapered limbs, hands and faces."""
from render2 import *
SKIN = {"sam": "#c98e66", "charlie": "#efc0a0"}
HAIR = {"sam": "#3a261c", "charlie": "#2f2119"}
def mirror(pts): return [(63 - x, y) for x, y in pts]

# body landmarks (left side; the right side is mirrored)
ARM_UP = [(16, 47), (21, 48), (19, 56), (16, 65), (10, 64), (12, 54)]
ARM_LO = [(10, 64), (16, 65), (15, 73), (14, 80), (9, 80), (9, 72)]
LEG = [(20, 72), (31, 72), (31, 76), (30, 78), (29, 88), (28, 100), (22, 100), (21, 88), (20, 80)]
TORSO = [(20, 45), (43, 45), (46, 48), (45, 57), (42, 66), (44, 72), (19, 72), (21, 66), (18, 57), (17, 48)]

def person(k, o):
    s = Sprite(); skin, hair = SKIN[k], HAIR[k]
    top, tc = o["top"]; bot, bc = o["bottom"]; shoe, sc = o["shoes"]; hat, hc = o.get("hat", ("none", ""))
    short = top in ("tee", "dress"); long = top in ("labcoat", "raincoat")
    if k == "sam":   # long wavy hair behind the shoulders
        s.part("hairback", hair, lambda d: (d.ellipse([15, 5, 48, 40]), d.polygon([(15, 22), (48, 22), (50, 46), (47, 56), (16, 56), (13, 46)])))
        s.part("hairends", "#9c6b40", lambda d: (d.polygon([(13, 46), (20, 46), (20, 55), (17, 59), (14, 55)]), d.polygon(mirror([(13, 46), (20, 46), (20, 55), (17, 59), (14, 55)]))), cyl=False)
    if top in ("hoodie", "raincoat"): s.part("hood", tc, lambda d: d.ellipse([20, 38, 43, 52]))
    # legs + bottoms
    if top == "dress" or bot in ("shorts", "skirt"):
        s.part("legs", skin, lambda d: (d.polygon(LEG), d.polygon(mirror(LEG))))
    if top != "dress":
        if bot == "shorts": s.part("pants", bc, lambda d: (d.polygon([(19, 70), (44, 70), (45, 86), (33, 86), (32, 78), (31, 86), (19, 86)])))
        elif bot == "skirt": s.part("pants", bc, lambda d: d.polygon([(19, 70), (44, 70), (49, 88), (14, 88)]))
        else:
            s.part("pants", bc, lambda d: (d.polygon(LEG), d.polygon(mirror(LEG)), d.rectangle([19, 70, 44, 76])))
            if bot == "jeans": s.part("detail", "#c9a35a", lambda d: (d.line([(24, 82), (24, 98)]), d.line([(39, 82), (39, 98)])), flat=True) if False else None
            if bot == "sweats": s.part("pants", bc, lambda d: (d.rectangle([22, 95, 30, 100]), d.rectangle([33, 95, 41, 100])), cyl=False)
    # shoes
    FOOT = [(21, 99), (30, 99), (31, 104), (29, 107), (18, 107), (18, 104)]
    if shoe == "boots": s.part("shoes", sc, lambda d: (d.polygon([(21, 90), (30, 90)] + FOOT[1:] + [(18, 104), (21, 99)]), d.polygon(mirror([(21, 90), (30, 90)] + FOOT[1:] + [(18, 104), (21, 99)]))))
    elif shoe == "slippers": s.part("shoes", sc, lambda d: (d.ellipse([15, 99, 31, 109]), d.ellipse([32, 99, 48, 109])), cyl=False)
    else: s.part("shoes", sc, lambda d: (d.polygon(FOOT), d.polygon(mirror(FOOT))))
    if shoe == "sneakers": s.part("detail", "#f6f3ec", lambda d: (d.line([(18, 106), (30, 106)]), d.line([(33, 106), (45, 106)]), d.line([(19, 105), (30, 105)]), d.line([(33, 105), (44, 105)])), flat=True)
    # neck + torso
    s.part("neck", skin, lambda d: d.polygon([(27, 38), (36, 38), (36, 48), (27, 48)]), cyl=False)
    if top == "dress":
        s.part("top", tc, lambda d: d.polygon(TORSO[:5] + [(43, 66), (52, 92), (11, 92), (20, 66)] + TORSO[8:]))
    elif long:
        s.part("top", tc, lambda d: d.polygon(TORSO[:5] + [(44, 72), (47, 96), (16, 96), (19, 72)] + TORSO[8:]))
    else:
        s.part("top", tc, lambda d: d.polygon(TORSO[:6] + [(44, 75), (19, 75)] + TORSO[7:]))
    # top details
    if top == "fleece":
        s.part("detail", "#f3f0e8", lambda d: d.polygon([(28, 46), (35, 46), (34, 75), (29, 75)]), cyl=False)
        s.part("detail", "#7b7f86", lambda d: (d.line([(28, 47), (29, 75)]), d.line([(35, 47), (34, 75)]), d.polygon([(21, 46), (28, 46), (28, 52)]), d.polygon([(42, 46), (35, 46), (35, 52)])), flat=True)
    if top == "labcoat":
        s.part("detail", "#7f8fa8", lambda d: d.polygon([(28, 46), (35, 46), (34, 74), (29, 74)]), cyl=False)
        s.part("detail", "#c9ccd1", lambda d: (d.line([(28, 47), (27, 95)]), d.line([(35, 47), (36, 95)]), d.rectangle([38, 60, 43, 66], outline=1), d.polygon([(21, 46), (28, 46), (28, 56)]), d.polygon([(42, 46), (35, 46), (35, 56)])), flat=True)
        s.part("detail", "#3f86c4", lambda d: d.line([(40, 57), (40, 61)]), flat=True)
    if top == "hoodie":
        s.part("detail", "#f2efe8", lambda d: (d.line([(29, 49), (29, 57)]), d.line([(34, 49), (34, 57)])), flat=True)
        s.part("detail", ramp(tc)["sh"] and tc, lambda d: d.polygon([(24, 62), (39, 62), (41, 71), (22, 71)]), cyl=False)
    if top in ("tee", "dress"): s.part("detail", skin, lambda d: d.polygon([(27, 46), (36, 46), (33, 51), (30, 51)]), cyl=False)
    if top == "shirt":
        s.part("detail", "#f6f3ec", lambda d: (d.polygon([(26, 45), (31, 45), (29, 51)]), d.polygon([(32, 45), (37, 45), (34, 51)])), flat=True)
        s.part("detail", "#f6f3ec", lambda d: [d.point((32, y)) for y in (55, 61, 67, 73)], flat=True)
    if top == "sweater": s.part("detail", "#e8d9b0", lambda d: (d.line([(18, 56), (45, 56)]), d.line([(18, 58), (45, 58)])), flat=True)
    if top == "raincoat":
        s.part("detail", "#6b5328", lambda d: [d.rectangle([33, y, 34, y+1]) for y in (54, 64, 74, 84)], flat=True)
        s.part("detail", "#c79a1e", lambda d: (d.line([(31, 48), (31, 95)]), d.rectangle([21, 76, 27, 80], outline=1), d.rectangle([36, 76, 42, 80], outline=1)), flat=True)
    if top == "pajamas":
        s.part("detail", "#f2f2ff", lambda d: [d.line([(14, y), (49, y)]) for y in range(50, 76, 5)], flat=True)
    if top == "dress":
        s.part("detail", "#fff3c4", lambda d: [d.point(p) for p in ((22, 80), (30, 86), (38, 78), (44, 88), (26, 70), (35, 70), (17, 88))], flat=True)
    # arms (sleeves), forearms, hands
    s.part("arms", tc, lambda d: (d.polygon(ARM_UP), d.polygon(mirror(ARM_UP))))
    s.part("arms" if not short else "arms2", tc if not short else skin, lambda d: (d.polygon(ARM_LO), d.polygon(mirror(ARM_LO))))
    if short: s.part("arms", tc, lambda d: (d.polygon([(16, 47), (21, 48), (20, 55), (11, 56), (12, 51)]), d.polygon(mirror([(16, 47), (21, 48), (20, 55), (11, 56), (12, 51)]))))
    if top == "pajamas": s.part("detail", "#f2f2ff", lambda d: [d.line([(12, y), (22, y)]) or d.line([(41, y), (51, y)]) for y in range(55, 80, 5)], flat=True) if False else None
    HAND = [(9, 79), (15, 79), (16, 84), (14, 87), (10, 87), (8, 84)]
    s.part("hands", skin, lambda d: (d.polygon(HAND), d.polygon(mirror(HAND))), cyl=False)
    # head
    s.part("ears", skin, lambda d: (d.ellipse([16, 24, 21, 31]), d.ellipse([42, 24, 47, 31])), cyl=False)
    s.part("face", skin, lambda d: (d.ellipse([18, 9, 45, 40]), d.polygon([(21, 30), (42, 30), (38, 39), (32, 42), (25, 39)])))
    if k == "sam":
        s.part("hair", hair, lambda d: (d.pieslice([15, 4, 48, 26], 180, 360),
               d.polygon([(31, 6), (24, 10), (19, 16), (17, 24), (16, 34), (19, 28), (22, 19), (27, 13), (31, 11)]),
               d.polygon(mirror([(31, 6), (24, 10), (19, 16), (17, 24), (16, 34), (19, 28), (22, 19), (27, 13), (31, 11)])),
               d.polygon([(14, 16), (19, 16), (21, 40), (22, 52), (20, 58), (15, 58), (13, 48)]), d.polygon(mirror([(14, 16), (19, 16), (21, 40), (22, 52), (20, 58), (15, 58), (13, 48)]))))
        s.part("hairtips", "#9c6b40", lambda d: (d.polygon([(13, 50), (22, 50), (21, 58), (18, 62), (15, 59)]), d.polygon(mirror([(13, 50), (22, 50), (21, 58), (18, 62), (15, 59)]))))
        s.part("detail", "#c08a55", lambda d: (d.line([(16, 53), (17, 59)]), d.line([(47, 53), (46, 59)])), flat=True)
        s.part("detail", "#5a3b2a", lambda d: (d.line([(24, 8), (19, 16)]), d.line([(39, 8), (44, 16)]), d.line([(16, 28), (15, 40)]), d.line([(47, 28), (48, 40)]), d.line([(28, 6), (25, 10)]), d.line([(35, 6), (38, 10)])), flat=True)
        s.part("detail", skin, lambda d: d.line([(31, 6), (31, 10)]), flat=True)
    else:
        tufts = [(20, 10, 18, 3, 25, 8), (25, 7, 26, 0, 31, 6), (30, 6, 33, 0, 36, 6), (35, 6, 40, 1, 41, 8), (40, 8, 46, 5, 45, 12)]
        s.part("hair", hair, lambda d: (d.pieslice([16, 4, 47, 30], 180, 360), d.polygon([(16, 17), (47, 17), (46, 22), (42, 19), (38, 23), (34, 19), (29, 23), (25, 19), (21, 23), (17, 24)]),
               d.rectangle([16, 16, 19, 27]), d.rectangle([44, 16, 47, 27]), *[d.polygon([(a, b), (c, e), (f, g)]) for a, b, c, e, f, g in tufts]))
        s.part("detail", "#4a3628", lambda d: (d.line([(24, 9), (27, 15)]), d.line([(37, 8), (35, 15)]), d.line([(42, 11), (44, 17)])), flat=True)
    # face details
    eye = "#2a1810" if k == "sam" else "#2a2a33"
    s.part("brow", hair, lambda d: (d.line([(23, 22), (28, 21)]), d.line([(35, 21), (40, 22)])), flat=True)
    s.part("eyewhite", "#fbf6ee", lambda d: (d.rectangle([24, 25, 28, 28]), d.rectangle([35, 25, 39, 28])), flat=True)
    s.part("eye", eye, lambda d: (d.rectangle([26, 25, 28, 28]), d.rectangle([35, 25, 37, 28])), flat=True)
    s.part("shine", "#ffffff", lambda d: (d.point((27, 25)), d.point((36, 25))), flat=True)
    if k == "sam":
        s.part("glass", "#a87526", lambda d: (d.ellipse([21, 22, 30, 31], outline=1), d.ellipse([33, 22, 42, 31], outline=1), d.line([(31, 26), (32, 26)]), d.line([(19, 25), (21, 25)]), d.line([(42, 25), (44, 25)])), flat=True)
    else:
        s.part("glass", "#6d7783", lambda d: (d.rectangle([21, 23, 30, 30], outline=1), d.rectangle([33, 23, 42, 30], outline=1), d.line([(31, 25), (32, 25)]), d.line([(18, 25), (21, 25)]), d.line([(42, 25), (45, 25)])), flat=True)
    s.part("nose", ramp(skin)["sh"] and skin, lambda d: None)
    s.part("blush", "#e48a76" if k == "sam" else "#f29a88", lambda d: (d.rectangle([21, 32, 24, 33]), d.rectangle([39, 32, 42, 33])), flat=True)
    s.part("nosedot", "#a8705a" if k == "sam" else "#d79c86", lambda d: d.point((32, 31)), flat=True)
    s.part("mouth", "#8a4436", lambda d: (d.line([(30, 35), (33, 35)]), d.point((29, 34)), d.point((34, 34))), flat=True)
    # hats
    if hat == "beanie":
        s.part("hat", hc, lambda d: d.ellipse([14, 0, 49, 22]))
        s.part("hat", hc, lambda d: d.rectangle([14, 13, 49, 18]), cyl=False)
        s.part("pom", "#f4efe6", lambda d: d.ellipse([28, -4, 35, 3]), cyl=False)
    if hat == "cap":
        s.part("hat", hc, lambda d: (d.pieslice([15, 3, 48, 26], 180, 360), d.polygon([(30, 13), (58, 13), (58, 16), (30, 16)])))
    if hat == "frog":
        s.part("hat", hc, lambda d: (d.pieslice([12, 1, 51, 30], 180, 360), d.ellipse([16, -3, 27, 7]), d.ellipse([36, -3, 47, 7])))
        s.part("detail", "#ffffff", lambda d: (d.ellipse([18, -1, 25, 5]), d.ellipse([38, -1, 45, 5])), flat=True)
        s.part("detail", "#1b1b1f", lambda d: (d.rectangle([21, 0, 22, 3]), d.rectangle([41, 0, 42, 3]), d.line([(26, 11), (29, 13), (34, 13), (37, 11)])), flat=True)
    if hat == "catears":
        s.part("hat", hc, lambda d: (d.polygon([(16, 12), (17, -1), (27, 7)]), d.polygon(mirror([(16, 12), (17, -1), (27, 7)]))))
        s.part("detail", "#ff9cb8", lambda d: (d.polygon([(19, 9), (19, 3), (24, 7)]), d.polygon(mirror([(19, 9), (19, 3), (24, 7)]))), flat=True)
    if hat == "bow":
        s.part("hat", hc, lambda d: (d.polygon([(38, 6), (47, 0), (47, 13)]), d.polygon([(38, 6), (30, 0), (30, 13)])))
        s.part("detail", ramp(hc)["sh"] and "#b23b55", lambda d: d.rectangle([36, 4, 40, 9]), flat=True)
    return s.render()

from sd import LOOKS
if __name__ == "__main__":
    from PIL import ImageFont
    sc = 4; cw, ch = W*sc, H*sc
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
    sheet = Image.new("RGB", (5*(cw+16)+16, 2*(ch+46)+16), "#f3dca6"); dr = ImageDraw.Draw(sheet)
    for i, (k, label, o) in enumerate(LOOKS):
        r, c = divmod(i, 5); x, y = 16 + c*(cw+16), 16 + r*(ch+46)
        dr.rectangle([x, y, x+cw-1, y+ch-1], fill="#e9c98a"); dr.rectangle([x, y+ch-60, x+cw-1, y+ch-1], fill="#c99a5c")
        f = person(k, o).resize((cw, ch), Image.NEAREST); sheet.paste(f, (x, y), f)
        dr.text((x+cw//2, y+ch+22), label, fill="#4a2610", font=font, anchor="mm")
    sheet.save("sd2.png"); print(sheet.size)
