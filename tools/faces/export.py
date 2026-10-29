import json, sys
src = open('chibi.py').read().split('if __name__ == "__main__":')
exec(src[0] + src[1].split('\n# ---- filters ----')[1])
KEYS = {"normal":"normal","grin":"grin","cat":"smug","squint":"squint","blank":"blank","sweat":"sweat","grumpy":"grumpy","cry":"cry","sleepy":"sleepy","shock":"shock","sparkle":"sparkle","love":"love","dog":"wag","cat2":"slit"}
CH = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789#$%&*+-=?@^~"
def px(im): 
    a = im.load(); return [[None if a[x,y][3] == 0 else '#%02x%02x%02x' % a[x,y][:3] for x in range(N)] for y in range(N)]
def plain(k):
    im, d, p = base(k); glasses(d, p, k); return im
out = {"list": [[KEYS[k], E[k][0]] for k in E]}
for who in ("sam", "charlie"):
    renders = {"base": px(plain(who))}
    for k in E: renders[KEYS[k]] = px(face(who, k, 0))
    t1 = px(face(who, "dog", 1))
    cols = sorted({c for g in list(renders.values()) + [t1] for row in g for c in row if c})
    assert len(cols) <= len(CH), len(cols)
    pal = {CH[i]: c for i, c in enumerate(cols)}; rev = {c: ch for ch, c in pal.items()}
    enc = lambda c: rev[c] if c else '_'
    b = renders["base"]
    def diff(g, mask=None):
        segs = []
        for y in range(N):
            x = 0
            while x < N:
                if (mask and not mask[y][x]) or (not mask and g[y][x] == b[y][x]): x += 1; continue
                x0 = x; sstr = ""
                while x < N and ((mask and mask[y][x]) or (not mask and g[y][x] != b[y][x])): sstr += enc(g[y][x]); x += 1
                segs.append([y, x0, sstr])
        return segs
    wag0 = renders["wag"]; moving = [[wag0[y][x] != t1[y][x] for x in range(N)] for y in range(N)]
    still = [[wag0[y][x] if not moving[y][x] else b[y][x] for x in range(N)] for y in range(N)]
    d = {k: diff(g) for k, g in renders.items() if k not in ("base", "wag")}
    d["wag"] = diff(still); d["wag~a"] = diff(wag0, moving); d["wag~b"] = diff(t1, moving)
    out[who] = {"pal": pal, "base": ["".join(enc(c) for c in row) for row in b], "d": d}
js = "const FACES = " + json.dumps(out, ensure_ascii=False, separators=(",", ":")) + ";"
open("faces.js", "w").write(js); print(len(js))
