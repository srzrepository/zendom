"""Turn jeff_topdown_classic.py's frames into the JEFF_ANIM2 data the app draws (palette letters, "_" = clear).
Run: python3 export_topdown.py > /tmp/jeff_anim2.json"""
import json
from jeff_topdown_classic import frame, PAL, W, H
inv = {tuple(int(v[i:i+2], 16) for i in (1, 3, 5)): k for k, v in PAL.items()}
frames = []
for t in range(8):
    im = frame(t).load(); rows = []
    for y in range(H):
        rows.append("".join("_" if im[x, y][3] == 0 else inv[im[x, y][:3]] for x in range(W)))
    frames.append(rows)
used = sorted({ch for f in frames for r in f for ch in r} - {"_"})
print(json.dumps({"w": W, "h": H, "pal": {k: PAL[k] for k in used}, "frames": frames}, separators=(",", ":")))
