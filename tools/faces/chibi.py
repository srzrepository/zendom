from PIL import Image, ImageDraw, ImageFont
N = 64
PAL = {
 "sam": dict(skin="#d9a47c", shade="#bd8763", blush="#e8907c", hair="#3b271d", hair2="#5a3b2a", end="#b07d4d", end2="#d0a066",
             frame="#c08a2c", eye="#2b1a12", top="#9a9ea3", top2="#7c8086", tee="#f5f2ed", mouth="#7a3328", tongue="#e07a6a", brow="#3b271d"),
 "charlie": dict(skin="#f1c6aa", shade="#d9a68a", blush="#f0a08e", hair="#33241b", hair2="#57402f", end="#33241b", end2="#57402f",
             frame="#7d8792", eye="#2a2a33", top="#2d3b5b", top2="#3f5079", tee="#2d3b5b", mouth="#8a4a40", tongue="#e88a7a", brow="#33241b"),
}
FX = dict(sweat="#9fdcff", sweat2="#3f86c4", vein="#e0453a", star="#ffd23f", heart="#ff6f9c", white="#ffffff", tear="#8fd0ff", dark="#4a1f1a")
LE, RE = (24, 33), (40, 33)   # eye centres

def base(k):
    p = PAL[k]; im = Image.new("RGBA", (N, N), (0,0,0,0)); d = ImageDraw.Draw(im)
    # shoulders / clothes
    if k == "sam":
        d.rounded_rectangle([6, 54, 57, 70], 10, fill=p["top"]); d.polygon([(24,54),(40,54),(36,64),(28,64)], fill=p["tee"])
        d.line([(23,55),(27,64)], fill=p["top2"]); d.line([(40,55),(36,64)], fill=p["top2"])
    else:
        d.rounded_rectangle([6, 54, 57, 70], 10, fill=p["top"]); d.polygon([(26,54),(38,54),(32,59)], fill=p["skin"]); d.line([(26,54),(32,59),(38,54)], fill=p["top2"])
    d.rectangle([28, 47, 35, 55], fill=p["shade"])           # neck
    # back hair (Sam's long hair falls behind the shoulders)
    if k == "sam":
        d.ellipse([8, 6, 55, 50], fill=p["hair"])
        d.rectangle([8, 26, 55, 56], fill=p["hair"])
        for x0 in (8, 46):                                   # lighter ends, wavy
            d.rectangle([x0, 44, x0+9, 58], fill=p["end"]); d.rectangle([x0+2, 52, x0+7, 60], fill=p["end2"])
            d.rectangle([x0, 40, x0+9, 43], fill=p["hair2"])
            d.line([(x0+1, 47), (x0+4, 50), (x0+1, 54)], fill=p["end2"]); d.line([(x0+8, 46), (x0+6, 50), (x0+8, 55)], fill=p["hair2"])
    # face
    d.ellipse([13, 12, 50, 52], fill=p["skin"])
    d.ellipse([16, 34, 47, 52], fill=p["skin"])
    # ears
    d.rectangle([11, 31, 13, 37], fill=p["skin"]); d.rectangle([50, 31, 52, 37], fill=p["skin"])
    # front hair
    if k == "sam":
        d.pieslice([10, 4, 53, 34], 180, 360, fill=p["hair"])
        # centre part: two curtains sweeping out to the sides, forehead showing
        d.polygon([(31,11),(24,15),(17,20),(13,27),(12,36),(16,30),(21,23),(28,18)], fill=p["hair"])
        d.polygon([(32,11),(39,15),(46,20),(50,27),(51,36),(47,30),(42,23),(35,18)], fill=p["hair"])
        d.line([(31,6),(31,12)], fill=p["skin"])
        d.line([(24,9),(18,18)], fill=p["hair2"]); d.line([(39,9),(45,18)], fill=p["hair2"]); d.line([(15,24),(14,32)], fill=p["hair2"]); d.line([(48,24),(49,32)], fill=p["hair2"])
        d.rectangle([10, 22, 13, 46], fill=p["hair"]); d.rectangle([50, 22, 53, 46], fill=p["hair"])
    else:
        d.pieslice([11, 5, 52, 38], 180, 360, fill=p["hair"])
        d.polygon([(12,22),(52,22),(50,26),(44,23),(38,27),(33,22),(27,26),(21,22),(15,27)], fill=p["hair"])
        for x, y in ((18,5),(25,2),(31,4),(37,1),(44,5)):   # tousled tufts
            d.polygon([(x-3,y+7),(x,y),(x+3,y+7)], fill=p["hair"])
        d.line([(24,9),(28,16)], fill=p["hair2"]); d.line([(38,8),(35,15)], fill=p["hair2"]); d.line([(45,12),(47,18)], fill=p["hair2"])
        d.rectangle([12, 22, 14, 33], fill=p["hair"]); d.rectangle([49, 22, 51, 33], fill=p["hair"])
    return im, d, p

def glasses(d, p, k):
    if k == "sam":
        for cx, cy in (LE, RE): d.ellipse([cx-6, cy-6, cx+6, cy+6], outline=p["frame"])
    else:
        for cx, cy in (LE, RE): d.rounded_rectangle([cx-7, cy-5, cx+7, cy+5], 2, outline=p["frame"])
    d.line([(LE[0]+(6 if k=="sam" else 7), 32), (RE[0]-(6 if k=="sam" else 7), 32)], fill=p["frame"])
    d.line([(LE[0]-7, 31), (13, 30)], fill=p["frame"]); d.line([(RE[0]+7, 31), (50, 30)], fill=p["frame"])

def brows(d, p, kind="norm"):
    for cx, s in ((LE[0], -1), (RE[0], 1)):
        y = 25
        if kind == "norm": d.line([(cx-3, y), (cx+3, y)], fill=p["brow"])
        if kind == "up":   d.line([(cx-3, y-1), (cx+3, y-1)], fill=p["brow"])
        if kind == "angry": d.line([(cx-3*s*-1, y-1), (cx+3*s*-1, y+1)], fill=p["brow"]) if False else d.line([(cx - 3, y - (1 if s < 0 else -1)), (cx + 3, y + (1 if s < 0 else -1))], fill=p["brow"])
        if kind == "sad":  d.line([(cx - 3, y + (1 if s < 0 else -1)), (cx + 3, y - (1 if s < 0 else -1))], fill=p["brow"])

def blush(d, p, strong=False):
    for cx in (LE[0]-1, RE[0]+1):
        d.rectangle([cx-3, 41, cx+3, 42], fill=p["blush"])
        if strong: d.line([(cx-3, 43), (cx-1, 41)], fill=p["shade"]); d.line([(cx+1, 43), (cx+3, 41)], fill=p["shade"])

def eye_open(d, p, cx, cy):
    d.rectangle([cx-2, cy-3, cx+2, cy+3], fill=p["eye"]); d.rectangle([cx-1, cy-2, cx, cy-1], fill=FX["white"])
def eye_arc_up(d, p, cx, cy):   # ^
    d.line([(cx-3, cy+1), (cx, cy-2), (cx+3, cy+1)], fill=p["eye"])
def eye_line(d, p, cx, cy):
    d.line([(cx-3, cy), (cx+3, cy)], fill=p["eye"])
def eye_arc_down(d, p, cx, cy): # u (closed, content)
    d.line([(cx-3, cy-1), (cx, cy+1), (cx+3, cy-1)], fill=p["eye"])

E = {}
def expr(key, label):
    def w(f): E[key] = (label, f); return f
    return w

@expr("normal", "Normal style")
def _(d, p):
    brows(d, p); [eye_open(d, p, *c) for c in (LE, RE)]
    d.line([(29, 44), (34, 44)], fill=p["mouth"]); d.point((28, 43), fill=p["mouth"]); d.point((35, 43), fill=p["mouth"]); blush(d, p)
@expr("grin", "Big grin")
def _(d, p):
    brows(d, p, "up"); [eye_arc_up(d, p, *c) for c in (LE, RE)]
    d.pieslice([25, 38, 38, 50], 0, 180, fill=p["mouth"]); d.pieslice([28, 44, 35, 50], 0, 180, fill=p["tongue"]); blush(d, p)
@expr("cat", "Mischief :3")
def _(d, p):
    d.line([(LE[0]-3,24),(LE[0]+3,25)], fill=p["brow"]); d.line([(RE[0]-3,23),(RE[0]+3,22)], fill=p["brow"])
    for cx, cy in (LE, RE):    # half-lidded, looking sideways
        d.line([(cx-3, cy-1), (cx+3, cy-1)], fill=p["eye"]); d.rectangle([cx, cy, cx+2, cy+2], fill=p["eye"])
    d.line([(27, 43), (29, 45), (31, 43), (32, 43), (34, 45), (36, 43)], fill=p["mouth"]); blush(d, p)
@expr("squint", ">_<")
def _(d, p):
    brows(d, p, "angry")
    cx, cy = LE; d.line([(cx-3, cy-3), (cx+2, cy), (cx-3, cy+3)], fill=p["eye"])
    cx, cy = RE; d.line([(cx+3, cy-3), (cx-2, cy), (cx+3, cy+3)], fill=p["eye"])
    d.line([(28, 45), (35, 45)], fill=p["mouth"]); d.line([(29, 44), (34, 44)], fill=p["mouth"]); blush(d, p, True)
@expr("blank", "Spaced out")
def _(d, p):
    for cx, cy in (LE, RE): d.rectangle([cx, cy, cx+1, cy+1], fill=p["eye"])
    d.rectangle([31, 44, 32, 45], fill=p["mouth"])
@expr("sweat", "Sweat drop")
def _(d, p):
    brows(d, p, "sad"); [eye_open(d, p, *c) for c in (LE, RE)]
    d.line([(28, 45), (30, 44), (32, 45), (34, 44), (36, 45)], fill=p["mouth"])
    d.polygon([(53, 14), (50, 21), (56, 21)], fill=FX["sweat"]); d.ellipse([50, 18, 56, 24], fill=FX["sweat"]); d.point((51, 20), fill=FX["white"])
    d.line([(53, 14), (50, 20)], fill=FX["sweat2"]); d.arc([50, 18, 56, 24], 300, 180, fill=FX["sweat2"])
@expr("grumpy", "Grumpy")
def _(d, p):
    brows(d, p, "angry")
    for cx, cy in (LE, RE): d.line([(cx-3, cy-1), (cx+3, cy-1)], fill=p["eye"]); d.rectangle([cx-1, cy, cx+1, cy+2], fill=p["eye"])
    d.arc([28, 44, 36, 50], 200, 340, fill=p["mouth"])
    vx, vy = 47, 12
    for a, b in (((vx, vy), (vx+2, vy+2)), ((vx+6, vy), (vx+4, vy+2)), ((vx, vy+6), (vx+2, vy+4)), ((vx+6, vy+6), (vx+4, vy+4))):
        d.line([a, b], fill=FX["vein"], width=2)
@expr("cry", "T_T")
def _(d, p):
    brows(d, p, "sad")
    for cx, cy in (LE, RE):
        d.line([(cx-3, cy-2), (cx+3, cy-2)], fill=p["eye"]); d.line([(cx, cy-2), (cx, cy+1)], fill=p["eye"])
        d.rectangle([cx-1, cy+2, cx+1, cy+12], fill=FX["tear"])
    d.arc([28, 42, 36, 50], 200, 340, fill=p["mouth"])
@expr("sleepy", "Sleepy")
def _(d, p):
    brows(d, p)
    [eye_arc_down(d, p, *c) for c in (LE, RE)]
    d.ellipse([30, 43, 33, 46], fill=p["mouth"]); blush(d, p)
    d.line([(31, 47), (31, 49)], fill=FX["tear"])                   # tiny drool
@expr("shock", "Shocked")
def _(d, p):
    brows(d, p, "up")
    for cx, cy in (LE, RE): d.ellipse([cx-3, cy-3, cx+3, cy+3], fill=FX["white"], outline=p["eye"]); d.point((cx, cy), fill=p["eye"])
    d.ellipse([29, 42, 34, 48], fill=p["mouth"])
    for x in (4, 58): d.line([(x, 20), (x, 26)], fill=p["eye"]); d.line([(x+(-2 if x<30 else 2), 23), (x, 26)], fill=p["eye"]) if False else None
    d.line([(6, 16), (9, 21)], fill=p["eye"]); d.line([(3, 24), (8, 25)], fill=p["eye"]); d.line([(57, 16), (54, 21)], fill=p["eye"]); d.line([(60, 24), (55, 25)], fill=p["eye"])
@expr("sparkle", "Sparkly")
def _(d, p):
    brows(d, p, "up")
    for cx, cy in (LE, RE):
        d.rectangle([cx-3, cy-4, cx+3, cy+4], fill=p["eye"]); d.rectangle([cx-2, cy-3, cx-1, cy-2], fill=FX["white"]); d.point((cx+1, cy+2), fill=FX["white"]); d.point((cx+2, cy+1), fill=FX["white"])
    d.pieslice([27, 40, 36, 48], 0, 180, fill=p["mouth"]); blush(d, p)
    for sx, sy in ((5, 10), (56, 6), (59, 28)):
        d.line([(sx-2, sy), (sx+2, sy)], fill=FX["star"]); d.line([(sx, sy-2), (sx, sy+2)], fill=FX["star"])
@expr("love", "In love")
def _(d, p):
    for cx, cy in (LE, RE):
        d.polygon([(cx-3, cy-1), (cx, cy+3), (cx+3, cy-1)], fill=FX["heart"]); d.rectangle([cx-3, cy-2, cx-1, cy-1], fill=FX["heart"]); d.rectangle([cx+1, cy-2, cx+3, cy-1], fill=FX["heart"])
    d.line([(27, 43), (29, 45), (31, 43), (32, 43), (34, 45), (36, 43)], fill=p["mouth"]); blush(d, p, True)
    for hx, hy in ((52, 8), (57, 15)):
        d.rectangle([hx, hy, hx+1, hy+1], fill=FX["heart"]); d.rectangle([hx+3, hy, hx+4, hy+1], fill=FX["heart"]); d.polygon([(hx, hy+2), (hx+2, hy+4), (hx+4, hy+2)], fill=FX["heart"])

def face(k, key):
    im, d, p = base(k); E[key][1](d, p); glasses(d, p, k); return im

# ---- three more faces ----
@expr("ahoge", "Idiot hair")
def _(d, p):
    # one silly strand sticking up out of the top of the head, plus a happy dopey look
    brows(d, p, "up")
    for cx, cy in (LE, RE): d.rectangle([cx-1, cy-1, cx+1, cy+1], fill=p["eye"])
    d.pieslice([28, 41, 36, 48], 0, 180, fill=p["mouth"]); blush(d, p)
@expr("burger", "Hamburger")
def _(d, p):
    brows(d, p, "up")
    for cx, cy in (LE, RE):
        d.rectangle([cx-3, cy-4, cx+3, cy+4], fill=p["eye"]); d.rectangle([cx-2, cy-3, cx-1, cy-2], fill=FX["white"]); d.point((cx+1, cy+2), fill=FX["white"])
    d.ellipse([26, 40, 37, 50], fill=FX["dark"]); d.rectangle([28, 46, 35, 49], fill=p["tongue"])   # big open mouth
    d.line([(35, 48), (35, 55)], fill=FX["tear"]); d.rectangle([34, 55, 36, 57], fill=FX["tear"])   # drool
    # a little floating burger
    bx, by = 49, 5
    d.pieslice([bx, by, bx+12, by+8], 180, 360, fill="#d9963e"); d.point((bx+4, by+2), fill="#fff3c4"); d.point((bx+8, by+1), fill="#fff3c4")
    d.rectangle([bx, by+4, bx+12, by+5], fill="#5bbf4a"); d.rectangle([bx, by+6, bx+12, by+7], fill="#6b3a1f"); d.rectangle([bx, by+8, bx+12, by+9], fill="#d9963e")
@expr("mask", "Muggin'")
def _(d, p):
    K, K2 = "#1b1b1f", "#2f2f36"
    d.ellipse([10, 3, 53, 52], fill=K); d.rectangle([12, 30, 51, 54], fill=K)          # balaclava over the head
    d.line([(20, 8), (16, 20)], fill=K2); d.line([(43, 8), (47, 20)], fill=K2); d.line([(31, 4), (31, 10)], fill=K2)
    d.rounded_rectangle([15, 27, 48, 38], 3, fill=p["skin"])                            # eye hole
    d.ellipse([27, 40, 36, 48], fill=p["skin"])                                         # mouth hole
    d.line([(LE[0]-3, 29), (LE[0]+3, 30)], fill=p["brow"]); d.line([(RE[0]-3, 30), (RE[0]+3, 29)], fill=p["brow"])
    for cx, cy in (LE, RE): d.line([(cx-3, cy-1), (cx+3, cy-1)], fill=p["eye"]); d.rectangle([cx-1, cy, cx+1, cy+2], fill=p["eye"])
    d.line([(29, 44), (34, 45)], fill=p["mouth"])

# ---- filters ----
DOG = dict(ear="#8a5a34", ear2="#6b4325", inner="#e8a3a3", snout="#f2d2ae", nose="#1e1410", tongue="#ff7f96", tail="#8a5a34", tail2="#b07a4c")
def dog_tail(d, frame):
    # tail sticking out behind the right shoulder; two frames for the wag
    pts = [(48, 58), (54, 52), (58, 44), (60, 38)] if frame == 0 else [(48, 58), (55, 54), (61, 50), (63, 45)]
    for i in range(len(pts) - 1): d.line([pts[i], pts[i+1]], fill=DOG["tail"], width=4)
    x, y = pts[-1]; d.ellipse([x-3, y-3, x+2, y+2], fill=DOG["tail2"])
@expr("dog", "Tail wag")
def _(d, p):
    brows(d, p, "up"); [eye_open(d, p, *c) for c in (LE, RE)]
    for x0, flip in ((8, 1), (44, -1)):          # floppy ears over the hair
        d.polygon([(x0+6, 6), (x0+12, 4), (x0+14, 10), (x0+10, 24), (x0+3, 26), (x0, 18)] if flip == 1 else
                  [(x0+6, 4), (x0+12, 6), (x0+18, 18), (x0+15, 26), (x0+8, 24), (x0+4, 10)], fill=DOG["ear"])
        d.polygon([(x0+5, 10), (x0+9, 9), (x0+8, 20), (x0+4, 21)] if flip == 1 else [(x0+11, 9), (x0+15, 10), (x0+16, 21), (x0+12, 20)], fill=DOG["ear2"])
    d.ellipse([24, 36, 39, 47], fill=DOG["ear2"]); d.ellipse([25, 37, 38, 46], fill=DOG["tail2"])   # brown muzzle
    d.rounded_rectangle([28, 37, 35, 41], 2, fill=DOG["nose"]); d.point((30, 38), fill=FX["white"]); d.point((29, 38), fill="#5a4a44")
    d.line([(31, 41), (31, 43)], fill=DOG["nose"]); d.line([(28, 44), (31, 43), (34, 44)], fill=DOG["nose"])
    d.rounded_rectangle([29, 44, 34, 51], 2, fill=DOG["tongue"]); d.line([(31, 45), (31, 49)], fill="#e0566f")
    blush(d, p)
@expr("cat2", "Doggy world")
def _(d, p):
    d.line([(LE[0]-3,24),(LE[0]+3,25)], fill=p["brow"]); d.line([(RE[0]-3,25),(RE[0]+3,24)], fill=p["brow"])
    for cx, cy in (LE, RE):
        d.ellipse([cx-4, cy-4, cx+4, cy+4], fill="#ffd23f", outline="#b8860b")
        d.line([(cx, cy-4), (cx, cy+4)], fill="#111111"); d.line([(cx+1, cy-2), (cx+1, cy+2)], fill="#111111")
        d.point((cx-2, cy-2), fill=FX["white"])
    d.line([(27, 43), (29, 45), (31, 43), (32, 43), (34, 45), (36, 43)], fill=FX["dark"])
    d.line([(28, 46), (28, 47)], fill=FX["white"]); d.line([(35, 46), (35, 47)], fill=FX["white"]); d.point((29, 46), fill=FX["white"]); d.point((34, 46), fill=FX["white"])
    for s in (-1, 1):                                # whisker marks on the cheeks
        x = 32 + s*14
        d.line([(x, 40), (x + s*4, 39)], fill=p["shade"]); d.line([(x, 42), (x + s*4, 42)], fill=p["shade"])
    blush(d, p)

_face_plain = face
def face(k, key, frame=0):
    if key == "ahoge":   # shift down to make room, then the silly strand sticks up out of the head
        im = _face_plain(k, key); out = Image.new("RGBA", (N, N), (0,0,0,0)); out.alpha_composite(im, (0, 6))
        d = ImageDraw.Draw(out); hair = PAL[k]["hair"]
        d.line([(31, 14), (29, 8), (30, 3), (34, 1), (39, 2), (42, 5), (42, 9)], fill=hair, width=2)
        return out
    if key != "dog": return _face_plain(k, key)
    back = Image.new("RGBA", (N, N), (0,0,0,0)); dog_tail(ImageDraw.Draw(back), frame)
    front = _face_plain(k, key); back.alpha_composite(front); return back

if __name__ == "__main__":
    sc, keys = 4, list(E); cell = N*sc
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
    sheet = Image.new("RGB", (6*(cell+16)+16, 4*(cell+46)+16), "#f3dca6"); dr = ImageDraw.Draw(sheet)
    for r, k in enumerate(["sam", "charlie"]):
        for i, key in enumerate(keys):
            row = r*2 + i//6; col = i % 6
            x, y = 16 + col*(cell+16), 16 + row*(cell+46)
            dr.rectangle([x, y, x+cell-1, y+cell-1], fill="#e9c98a")
            f = face(k, key).resize((cell, cell), Image.NEAREST); sheet.paste(f, (x, y), f)
            dr.text((x+cell//2, y+cell+22), E[key][0], fill="#4a2610", font=font, anchor="mm")
    sheet.save("chibi.png"); print(sheet.size)

