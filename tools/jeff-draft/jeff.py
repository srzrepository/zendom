"""Jeff crunching numbers: rump up behind his head, wiggling; front trotters tapping an adding machine."""
from PIL import Image, ImageDraw
W, H = 56, 66
DY = 10                                   # head + desk sit lower so the rump shows above
C = dict(P="#f6b3c1", p="#e2899c", d="#9e4258", N="#f28ea4", E="#2b1d22", W="#ffffff", B="#f48aa2", V="#3f9a6b", v="#2b6f4d",
         G="#5a4636", h="#c9677e", o="#7a3a4c", wood="#c98f5a", woodD="#8a5a32", woodL="#ddaa74", calc="#5f6b7a", calcD="#3d4652",
         key="#eef1f4", keyO="#f0a04b", lcd="#bfe8c8", lcdD="#2b6f4d", paper="#fbf7f2", ink="#7a8794")

def outline(img, col):
    """dark outline around every opaque pixel (Stardew-style)"""
    src = img.load(); out = img.copy(); o = out.load()
    for y in range(H):
        for x in range(W):
            if src[x, y][3]: continue
            if any(0 <= x+dx < W and 0 <= y+dy < H and src[x+dx, y+dy][3] for dx, dy in ((1,0),(-1,0),(0,1),(0,-1))):
                o[x, y] = col + (255,) if isinstance(col, tuple) else tuple(int(col[i:i+2], 16) for i in (1,3,5)) + (255,)
    return out

def layer(): im = Image.new("RGBA", (W, H), (0,0,0,0)); return im, ImageDraw.Draw(im)

def frame(t):
    tapL, tapR = (t % 2 == 0), (t % 2 == 1)                    # trotters take turns
    # --- rump, behind the head ---
    rump, r = layer()
    wig = [0, 2, 3, 3, 2, 0, -2, -3, -3, -2][t % 10]
    cx = 28 + wig
    for sx in (-1, 1):                                                  # back legs up in the air, hooves on top
        lx = cx + sx*9
        r.rounded_rectangle([lx-3, 3, lx+3, 18], 2, fill=C["P"]); r.rectangle([lx-3, 3, lx+3, 5], fill=C["d"]); r.line([(lx, 3), (lx, 4)], fill=C["P"])
    r.ellipse([cx-14, 8, cx+14, 34], fill=C["P"])
    r.line([(cx, 12), (cx, 24)], fill=C["p"])                           # the crease
    r.arc([cx-12, 10, cx-2, 22], 120, 220, fill=C["W"])                 # a bit of shine
    # big curly tail on the back, flipping with the sway
    side = 1 if wig >= 0 else -1; tx = cx + side * 1
    r.arc([tx-4, 4, tx+4, 12], 0, 360, fill=C["h"]); r.arc([tx-2, 6, tx+2, 10], 90, 360, fill=C["h"])
    r.line([(tx, 12), (tx, 14)], fill=C["h"])
    rump = outline(rump, "#7a3a4c")
    # --- head, leaning down over the machine ---
    head, d = layer()
    d.polygon([(16, 17), (19, 12), (22, 18)], fill=C["P"]); d.polygon([(40, 17), (37, 12), (34, 18)], fill=C["P"])     # ears
    d.ellipse([15, 16, 41, 40], fill=C["P"])
    d.pieslice([15, 13, 41, 31], 180, 360, fill=C["V"]); d.rectangle([15, 21, 41, 23], fill=C["v"])                  # green beanie
    d.ellipse([26, 10, 30, 14], fill=C["V"])                                                                        # pompom
    for ex in (21, 31):                                                                                              # glasses, eyes looking down
        d.rectangle([ex, 25, ex+5, 29], outline=C["G"]); d.rectangle([ex+2, 27, ex+3, 29], fill=C["E"])
    d.line([(26, 26), (31, 26)], fill=C["G"])
    d.ellipse([23, 31, 33, 38], fill=C["N"]); d.point((26, 34), fill=C["d"]); d.point((30, 34), fill=C["d"])         # snout
    d.rectangle([17, 31, 19, 32], fill=C["B"]); d.rectangle([37, 31, 39, 32], fill=C["B"])                            # cheeks
    if t % 5 == 0: d.point((20, 20), fill=C["W"]) if False else None
    head = outline(head, "#7a3a4c"); hh = Image.new("RGBA", (W, H), (0,0,0,0)); hh.alpha_composite(head.crop((0, 0, W, H - DY)), (0, DY)); head = hh
    # --- desk + adding machine + trotters (in front) ---
    front, f = layer()
    f.rectangle([0, 44, W-1, H-1], fill=C["wood"]); f.line([(0, 44), (W-1, 44)], fill=C["woodL"]); f.line([(0, 50), (W-1, 50)], fill=C["woodD"])
    f.polygon([(15, 36), (41, 36), (44, 46), (12, 46)], fill=C["calc"])                                              # adding machine
    f.rectangle([19, 37, 37, 40], fill=C["lcd"])
    digits = ["0.00", "12.4", "38.9", "57.0", "61.2", "88.4", "92.0", "124.", "131.", "147."][t % 10]
    for i, ch in enumerate(digits[:4]):                                                                              # tiny 1-px "digits"
        x = 21 + i*4
        if ch == ".": f.point((x+1, 40), fill=C["lcdD"])
        else: f.line([(x, 38), (x+2, 38)], fill=C["lcdD"]); f.line([(x+(int(ch) % 3), 38), (x+(int(ch) % 3), 40)], fill=C["lcdD"])
    for row in range(2):
        for k in range(5):
            kx, ky = 17 + k*5, 42 + row*2
            f.rectangle([kx, ky, kx+2, ky], fill=C["keyO"] if (row, k) == (1, 4) else C["key"])
    # paper tape curling out the back-right, growing
    tl = 4 + (t % 10)
    f.rectangle([42, 36 - tl, 46, 36], fill=C["paper"])
    for yy in range(36 - tl + 1, 36, 2): f.line([(43, yy), (45, yy)], fill=C["ink"])
    # front trotters: the tapping one dips onto the keys
    for (x, down) in ((19, tapL), (33, tapR)):
        y = 39 if down else 36
        f.rounded_rectangle([x, y-3, x+5, y+3], 1, fill=C["P"]); f.rectangle([x, y+2, x+5, y+3], fill=C["d"])
    if tapL or tapR:                                                                                                 # little "click" sparks
        sx = 18 if tapL else 39
        f.point((sx, 36 - (t % 3)), fill="#ffd34d"); f.point((sx + (1 if tapR else -1), 35 - (t % 3)), fill="#ffd34d")
    front = outline(front, "#5a3a24"); ff = Image.new("RGBA", (W, H), (0,0,0,0)); ff.alpha_composite(front.crop((0, 0, W, H - DY)), (0, DY)); front = ff
    # sweat drop on hard frames
    out = Image.new("RGBA", (W, H), (0,0,0,0)); out.alpha_composite(rump); out.alpha_composite(head); out.alpha_composite(front)
    if t % 10 in (3, 4, 5):
        dd = ImageDraw.Draw(out); dd.polygon([(44, 26), (42, 30), (46, 30)], fill="#9fdcff"); dd.ellipse([42, 28, 46, 32], fill="#9fdcff"); dd.point((43, 29), fill="#ffffff")
    return out

if __name__ == "__main__":
    sc = 8; frames = []
    for t in range(10):
        bg = Image.new("RGBA", (W*sc, H*sc), (233, 201, 138, 255))
        fr = frame(t).resize((W*sc, H*sc), Image.NEAREST); bg.alpha_composite(fr); frames.append(bg.convert("P", palette=Image.ADAPTIVE))
    frames[0].save("jeff.gif", save_all=True, append_images=frames[1:], duration=110, loop=0, disposal=2)
    strip = Image.new("RGBA", (W*4*5, H*4*2), (233, 201, 138, 255))
    for t in range(10): strip.alpha_composite(frame(t).resize((W*4, H*4), Image.NEAREST), ((t % 5)*W*4, (t//5)*H*4))
    strip.save("jeff_frames.png"); print("ok")
