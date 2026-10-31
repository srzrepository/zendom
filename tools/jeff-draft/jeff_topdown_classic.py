"""Jeff crunching numbers in his ORIGINAL style (the app's flat 32px sprite: no outlines, green bucket hat,
brown square glasses), seen from above like Sam's sketch: his back is a hump with the curly tail on top
that sways side to side as he types,
head tipped down over a calculator he's hugging, ears out to the sides, stress lines around him.
Palette letters are the same as PIG in index.html. Run: python3 jeff_topdown_classic.py"""
from PIL import Image, ImageDraw
W, H = 32, 36
PAL = {"P": "#f6b3c1", "p": "#e2899c", "d": "#9e4258", "N": "#f28ea4", "E": "#2b1d22", "W": "#ffffff", "B": "#f48aa2",
       "V": "#3f9a6b", "v": "#2b6f4d", "G": "#5a4636", "C": "#5f6b7a", "c": "#bfe8c8", "K": "#eef1f4", "O": "#f0a04b", "h": "#c9677e", "s": "#9fdcff"}
BG = (233, 201, 138, 255)
rgb = lambda k: tuple(int(PAL[k][i:i+2], 16) for i in (1, 3, 5)) + (255,)

def edge(img, inside, col):
    """paint `col` on `inside`-colored pixels that touch the outside of this layer (the original sprite's soft edge)"""
    a = img.load(); w, h = img.size; ins = rgb(inside); out = []
    for y in range(h):
        for x in range(w):
            if a[x, y] != ins: continue
            if any(not (0 <= x+dx < w and 0 <= y+dy < h) or a[x+dx, y+dy][3] == 0 for dx, dy in ((1,0),(-1,0),(0,1),(0,-1))): out.append((x, y))
    for (x, y) in out: a[x, y] = rgb(col)

def frame(t):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    px = lambda x, y, k: d.point((x, y), fill=rgb(k))
    rect = lambda x0, y0, x1, y1, k: d.rectangle([x0, y0, x1, y1], fill=rgb(k))
    tapL, tapR = t % 2 == 0, t % 2 == 1
    bob = t % 2                                                   # head dips with each tap
    # curly tail on top of the back, twitching left/right
    wig = (0, 2, 3, 2, 0, -2, -3, -2)[t % 8]                     # his butt sways side to side as he types
    tx = 19 + wig + (1 if wig > 0 else -1 if wig < 0 else 0)     # the tail swings a little further than the back
    for (x, y) in ((tx, 4), (tx, 3), (tx - 1, 2), (tx - 1, 1), (tx, 0), (tx + 1, 0), (tx + 2, 1), (tx + 1, 2)): px(x, y, "h")
    back = im; im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d_back = ImageDraw.Draw(back)
    # the back: a big hump behind the head, leaning right (visible above the hat and down the right side)
    d_back.ellipse([7 + wig, 3, 28 + wig, 21], fill=rgb("P"))
    d_back.ellipse([9 + wig // 2, 10, 28 + wig // 2, 22], fill=rgb("P"))        # lower back moves less (it pivots at the shoulders)
    d_back.arc([7 + wig, 3, 28 + wig, 21], -80, 60, fill=rgb("p"))
    for (x, y) in ((12, 6), (13, 5), (14, 5)): d_back.point((x + wig, y), fill=rgb("W"))
    y0 = 9 + bob
    # ears: up and out past the brim corners (the original's ears stick up above the hat)
    for (x, y, k) in ((4, y0-2, "p"), (4, y0-1, "p"), (5, y0-1, "P"), (4, y0, "p"), (5, y0, "P"), (6, y0, "P"), (5, y0+1, "P"), (6, y0+1, "P"), (7, y0+1, "P"), (6, y0+2, "P"), (7, y0+2, "P"), (8, y0+2, "P"),
                      (26, y0-2, "p"), (26, y0-1, "p"), (25, y0-1, "P"), (26, y0, "p"), (25, y0, "P"), (24, y0, "P"), (25, y0+1, "P"), (24, y0+1, "P"), (23, y0+1, "P"), (24, y0+2, "P"), (23, y0+2, "P"), (22, y0+2, "P")):
        px(x, y, k)
    for (x, y) in ((5, y0), (6, y0+1), (5, y0-1), (25, y0), (24, y0+1), (25, y0-1)): px(x, y, "h")   # inside of the ears
    # head, tipped down
    d.ellipse([6, y0+2, 24, y0+18], fill=rgb("P"))
    px(6, y0+10, "p"); px(6, y0+11, "p"); px(24, y0+10, "p"); px(24, y0+11, "p")
    # green bucket hat from above: crown, with the dark brim showing at the front
    d.ellipse([5, y0+2, 25, y0+7], fill=rgb("v"))
    d.ellipse([9, y0, 21, y0+5], fill=rgb("V"))
    # glasses: thick brown squares, eyes looking down at the numbers
    for gx in (8, 16):
        rect(gx, y0+8, gx+6, y0+11, "G"); rect(gx+1, y0+9, gx+5, y0+10, "P")
        px(gx+3, y0+10, "E"); px(gx+4, y0+10, "E")
    rect(15, y0+9, 15, y0+9, "G")
    if t % 8 in (4, 5): rect(9, y0+9, 13, y0+9, "E"); rect(17, y0+9, 21, y0+9, "E")    # squint on the hard sums
    # cheeks and snout
    rect(7, y0+12, 8, y0+12, "B"); rect(22, y0+12, 23, y0+12, "B")
    rect(12, y0+12, 18, y0+15, "N"); rect(11, y0+13, 19, y0+14, "N")
    px(13, y0+13, "d"); px(17, y0+13, "d")
    edge(im, "P", "p")                                              # darker-pink edge where the head meets the back
    back.alpha_composite(im); im = back; d = ImageDraw.Draw(im)
    # calculator hugged against the belly
    rect(10, 27, 21, 35, "C")
    rect(11, 28, 20, 29, "c")
    digits = ["1", "12", "38", "57", "61", "88", "92", "124"][t % 8]
    for i, ch in enumerate(digits.rjust(3)):                       # 1-px "digits" in dark green
        if ch == " ": continue
        x = 14 + i * 2; px(x, 28 + (int(ch) % 2), "v")
    for row in range(2):
        for k in range(4):
            px(11 + k * 3, 31 + row * 2, "O" if (row, k) == (1, 3) else "K")
    # arms from the shoulders down to the calculator; trotters take turns tapping the keys
    body = im; im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for side, down in ((-1, tapL), (1, tapR)):
        sx = 6 if side < 0 else 23; hx = 10 if side < 0 else 19; hy = 33 if down else 31
        d.line([(sx, y0 + 13), (hx + 1, hy - 1)], fill=rgb("P"), width=3)
        rect(hx, hy - 2, hx + 2, hy - 1, "P")
    edge(im, "P", "p")
    for side, down in ((-1, tapL), (1, tapR)):
        hx = 10 if side < 0 else 19; hy = 33 if down else 31; rect(hx, hy, hx + 2, hy, "h")
    body.alpha_composite(im); im = body; d = ImageDraw.Draw(im)
    # stress lines (from the sketch), flicking between two spots
    if t % 2 == 0: lines = [(1, 9), (2, 7), (2, 8), (3, 6), (4, 10), (4, 11), (29, 4), (30, 5), (30, 6), (31, 7), (28, 7), (29, 8)]
    else: lines = [(0, 10), (1, 8), (1, 9), (2, 7), (3, 11), (3, 12), (29, 3), (30, 4), (31, 5), (31, 6), (28, 6), (29, 7)]
    for (x, y) in lines: px(x, y, "E")
    if t % 8 in (5, 6, 7):                                         # sweat drop on the big numbers
        for (x, y) in ((27, 13), (26, 14), (27, 14), (28, 14), (26, 15), (27, 15), (28, 15)): px(x, y, "s")
        px(27, 14, "W")
    return im

if __name__ == "__main__":
    sc = 12; frames = []
    for t in range(8):
        bg = Image.new("RGBA", (W * sc, H * sc), BG); bg.alpha_composite(frame(t).resize((W * sc, H * sc), Image.NEAREST))
        frames.append(bg.convert("P", palette=Image.ADAPTIVE))
    frames[0].save("jeff_topdown_classic.gif", save_all=True, append_images=frames[1:], duration=130, loop=0, disposal=2)
    sheet = Image.new("RGBA", (W * 6 * 4, H * 6 * 2), BG)
    for t in range(8): sheet.alpha_composite(frame(t).resize((W * 6, H * 6), Image.NEAREST), ((t % 4) * W * 6, (t // 4) * H * 6))
    sheet.save("jeff_topdown_classic_frames.png"); print("ok")
