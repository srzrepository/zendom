import json
from jeff import frame, W, H
CH = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789#$%&*+-=?@^~"
frs = []
for t in range(10):
    a = frame(t).load(); frs.append([[None if a[x, y][3] == 0 else '#%02x%02x%02x' % a[x, y][:3] for x in range(W)] for y in range(H)])
cols = sorted({c for f in frs for r in f for c in r if c}); assert len(cols) <= len(CH), len(cols)
pal = {CH[i]: c for i, c in enumerate(cols)}; rev = {c: k for k, c in pal.items()}
enc = lambda c: rev[c] if c else "_"
base = frs[0]
def diff(f):
    segs = []
    for y in range(H):
        x = 0
        while x < W:
            if f[y][x] == base[y][x]: x += 1; continue
            x0 = x; s = ""
            while x < W and f[y][x] != base[y][x]: s += enc(f[y][x]); x += 1
            segs.append([y, x0, s])
    return segs
out = {"w": W, "h": H, "pal": pal, "base": ["".join(enc(c) for c in r) for r in base], "d": [diff(f) for f in frs[1:]]}
js = "const JEFF_ANIM = " + json.dumps(out, separators=(",", ":")) + ";"
open("jeff_anim.js", "w").write(js); print(len(js))
