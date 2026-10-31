"""Jeff crunching numbers, seen from above (from Sam's sketch, Oct 30 2026): his back is a big hump with
the curly tail on top, head tipped down over a calculator he's hugging, ears out to the sides, glasses
on, stress lines flicking around him. Same palette and outline style as jeff.py.
Run: python3 jeff_topdown.py  ->  jeff_topdown.gif (+ jeff_topdown_frames.png contact sheet)"""
from PIL import Image, ImageDraw
W, H = 56, 66
C = dict(P="#f6b3c1", p="#e2899c", d="#9e4258", N="#f28ea4", E="#2b1d22", W="#ffffff", B="#f48aa2", G="#5a4636", h="#c9677e",
         calc="#5f6b7a", calcD="#3d4652", key="#eef1f4", keyO="#f0a04b", lcd="#bfe8c8", lcdD="#2b6f4d", spark="#ffd34d", sweat="#9fdcff")
OUT_PIG, OUT_CALC = "#7a3a4c", "#2b1d22"

def rgba(c): return tuple(int(c[i:i+2], 16) for i in (1, 3, 5)) + (255,)
def outline(img, col):
    """dark 1-px outline around every opaque pixel (Stardew-style)"""
    src = img.load(); out = img.copy(); o = out.load(); c = rgba(col)
    for y in range(H):
        for x in range(W):
            if src[x, y][3]: continue
            if any(0 <= x+dx < W and 0 <= y+dy < H and src[x+dx, y+dy][3] for dx, dy in ((1,0),(-1,0),(0,1),(0,-1))): o[x, y] = c
    return out
def layer(): im = Image.new("RGBA", (W, H), (0,0,0,0)); return im, ImageDraw.Draw(im)

DIGITS = ["0", "12", "38", "57", "61", "88", "92", "124"]
def frame(t):
    n = len(DIGITS); tapL, tapR = t % 2 == 0, t % 2 == 1
    bob = [0, 1, 0, 1, 0, 1, 0, 1][t % n]                       # head bobs with each tap
    # --- the back: a big hump behind and above the head, leaning right ---
    back, b = layer()
    b.ellipse([16, 8, 50, 44], fill=C["P"])
    b.chord([16, 8, 50, 44], -60, 60, fill=C["p"])               # shade on the far side
    b.ellipse([20, 11, 46, 40], fill=C["P"])
    b.arc([21, 12, 33, 26], 190, 260, fill=C["W"])               # shine
    back = outline(back, OUT_PIG)
    # --- curly tail on top of the hump, twitching ---
    tail, tl = layer()
    tx = 33 + [0, 1, 1, 0, -1, -1, 0, 1][t % n]
    tl.line([(tx, 11), (tx, 8)], fill=C["h"])                                 # grows out of the top of the back
    tl.arc([tx-3, 2, tx+3, 8], 90, 420 if t % 2 else 380, fill=C["h"])
    tail = outline(tail, OUT_PIG)
    # --- head, tipped down, ears out to the sides ---
    head, d = layer()
    y0 = 22 + bob
    d.polygon([(6, y0+2), (10, y0-6), (18, y0+5)], fill=C["P"]); d.polygon([(8, y0+1), (10, y0-3), (14, y0+3)], fill=C["h"])      # left ear, out and up
    d.polygon([(30, y0+4), (35, y0-6), (40, y0+3)], fill=C["P"]); d.polygon([(33, y0+2), (35, y0-3), (37, y0+2)], fill=C["h"])    # right ear
    d.ellipse([9, y0, 41, y0+26], fill=C["P"])
    d.rectangle([12, y0+14, 15, y0+15], fill=C["B"]); d.rectangle([35, y0+14, 38, y0+15], fill=C["B"])                           # cheeks
    # glasses, slightly askew like the sketch; eyes looking down at the numbers
    d.rectangle([14, y0+8, 21, y0+13], outline=C["G"]); d.rectangle([27, y0+7, 33, y0+13], outline=C["G"])
    d.line([(22, y0+9), (26, y0+8)], fill=C["G"])
    d.rectangle([17, y0+11, 18, y0+12], fill=C["E"]); d.rectangle([29, y0+11, 30, y0+12], fill=C["E"])
    if t % n in (4, 5): d.line([(16, y0+9), (19, y0+10)], fill=C["E"]); d.line([(28, y0+10), (31, y0+9)], fill=C["E"])          # squint on the hard sums
    d.ellipse([18, y0+16, 32, y0+24], fill=C["N"]); d.point((22, y0+20), fill=C["d"]); d.point((28, y0+20), fill=C["d"])        # snout
    d.line([(23, y0+24), (27, y0+24)], fill=C["d"])                                                                                # tiny worried mouth
    head = outline(head, OUT_PIG)
    # --- calculator hugged against the belly ---
    calc, c = layer()
    c.rounded_rectangle([15, 49, 39, 64], 2, fill=C["calc"])
    c.rectangle([18, 51, 36, 54], fill=C["lcd"])
    s = DIGITS[t % n]
    for i, ch in enumerate(s.rjust(4)):                                                                                            # 1-px digits, right-aligned
        if ch == " ": continue
        x = 20 + i*4; v = int(ch)
        c.line([(x, 52), (x+2, 52)], fill=C["lcdD"]); c.line([(x + v % 3, 52), (x + v % 3, 53)], fill=C["lcdD"])
    for row in range(3):
        for k in range(4):
            kx, ky = 18 + k*5, 56 + row*3
            c.rectangle([kx, ky, kx+2, ky+1], fill=C["keyO"] if (row, k) == (2, 3) else C["key"])
    calc = outline(calc, OUT_CALC)
    # --- arms down the sides, trotters taking turns on the keys ---
    arms, a = layer()
    for side, down in ((-1, tapL), (1, tapR)):
        sx = 12 if side < 0 else 38
        hy = 61 if down else 58                                                # trotters on the keys, below the screen
        hx = 19 if side < 0 else 31
        a.line([(sx, 40), (sx + side*0, 47), (hx + 2, hy - 2)], fill=C["P"], width=4)
        a.rounded_rectangle([hx, hy - 3, hx + 5, hy + 1], 1, fill=C["P"]); a.rectangle([hx, hy, hx + 5, hy + 1], fill=C["d"])
    arms = outline(arms, OUT_PIG)
    # --- stress lines and taps ---
    fx, f = layer()
    if t % 2 == 0:
        f.line([(4, 22), (8, 12)], fill=C["E"]); f.line([(8, 24), (10, 18)], fill=C["E"])
        f.line([(46, 10), (49, 15)], fill=C["E"]); f.line([(50, 9), (53, 16)], fill=C["E"])
    else:
        f.line([(3, 20), (7, 10)], fill=C["E"]); f.line([(7, 22), (9, 16)], fill=C["E"])
        f.line([(47, 9), (50, 14)], fill=C["E"]); f.line([(51, 8), (54, 15)], fill=C["E"])
    sx = 21 if tapL else 34                                                                                                         # click sparks
    f.point((sx, 55), fill=C["spark"]); f.point((sx + (-2 if tapL else 2), 54), fill=C["spark"])
    if t % n in (5, 6, 7):                                                                                                          # sweat on the big numbers
        f.polygon([(44, 26), (42, 30), (46, 30)], fill=C["sweat"]); f.ellipse([42, 28, 46, 32], fill=C["sweat"]); f.point((43, 29), fill=C["W"])
    out = Image.new("RGBA", (W, H), (0,0,0,0))
    for L in (tail, back, head, calc, arms, fx): out.alpha_composite(L)
    return out

if __name__ == "__main__":
    sc = 8; frames = []
    for t in range(len(DIGITS)):
        bg = Image.new("RGBA", (W*sc, H*sc), (233, 201, 138, 255))
        bg.alpha_composite(frame(t).resize((W*sc, H*sc), Image.NEAREST)); frames.append(bg.convert("P", palette=Image.ADAPTIVE))
    frames[0].save("jeff_topdown.gif", save_all=True, append_images=frames[1:], duration=120, loop=0, disposal=2)
    strip = Image.new("RGBA", (W*4*4, H*4*2), (233, 201, 138, 255))
    for t in range(len(DIGITS)): strip.alpha_composite(frame(t).resize((W*4, H*4), Image.NEAREST), ((t % 4)*W*4, (t//4)*H*4))
    strip.save("jeff_topdown_frames.png"); print("ok")
