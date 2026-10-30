"""Step 18: bedtime in the room.
11 pm-midnight: the sofa becomes a bed; Sam is up on her phone (face lit by the screen), Charlie is
asleep with Paprika curled up on him. Midnight-6 am: both asleep, moonlight only.
The room checks the hour while it's on screen, so it changes on its own at 11 and at midnight.
No data change. Usage: python3 patch_step18_bedtime.py file.html"""
import sys
p = sys.argv[1]; s = open(p).read()
def rep(old, new):
    global s
    assert s.count(old) == 1, (s.count(old), old[:90])
    s = s.replace(old, new)

# which scene: "" (day/evening), "phone" (11pm), "asleep" (midnight-6am)
rep("""  return {season:look.season, mood, mess, overdue, goal: g === undefined ? 0 : Math.max(0, Math.min(1, g)), hour:new Date().getHours(), palette:document.documentElement.dataset.palette || "sage"};""",
"""  const hour = new Date().getHours();
  return {season:look.season, mood, mess, overdue, goal: g === undefined ? 0 : Math.max(0, Math.min(1, g)), hour, bed: hour === 23 ? "phone" : hour < 6 ? "asleep" : "", palette:document.documentElement.dataset.palette || "sage"};""")

# heads lying on pillows, made from the sitting sprites' heads
rep("""/* ---------- people and Paprika (redrawn every frame) ---------- */""",
"""/* ---------- bedtime ---------- */
const RM_PHONE = {pal:{k:"#1d1d24", L:"#bfe3ff", l:"#8cc7f0", S:"#e2b28c"}, rows:["kkkkk", "kLLLk", "kLlLk", "kLLLk", "kLLLk", "SkkkS"]};
function rmHead(key, awake){
  const sp = RM_PEOPLE[key], rows = sp.rows.slice(0, key === "sam" ? 10 : 11);
  return rows.map(r => awake ? r : r.replace(/E/g, "s").replace(/g/g, "S").replace(/i/g, "s"));   // asleep: eyes shut, glasses off
}
function rmBed(B, F, pal, opts, wood, woodD, woodL){
  const quilt = rc(pal.sofa), quiltD = rc(pal.sofaD), quiltT = rc(pal.sofaT), sheet = rc("#f4efe6"), sheetD = rc("#ddd4c4");
  rmBox(B, {x:40, y:0, z:0, w:54, d:3, h:24, outline:"#7a4b2a", top:woodL, right:woodD, left:(u, v) => v > 21 || u < 2 || u > 52 ? woodD : wood});   // headboard
  rmBox(B, {x:40, y:3, z:0, w:54, d:31, h:8, outline:"#a89a86", top:sheet, right:sheetD, left:(u, v) => v < 2 ? woodD : sheet});                       // mattress
  [[44, 21], [70, 21]].forEach(([x, w]) => rmBox(B, {x, y:4, z:8, w, d:8, h:3, outline:"#cfc4b2", top:rc("#fffaf2"), right:sheetD, left:sheet}));       // pillows
  const awake = opts.bed === "phone";
  rmSprite(B, rmHead("sam", awake), RM_PEOPLE.sam.pal, 55, 8, 11);
  rmSprite(B, rmHead("charlie", false), RM_PEOPLE.charlie.pal, 81, 8, 11);
  if(!awake) [[49, 12], [61, 12]].forEach(([x, y]) => rmBox(B, {x, y, z:10, w:2, d:2, h:2, top:rc("#4a3026"), left:rc("#4a3026"), right:rc("#3a261c")}));  // hair spread on the pillow
  const patch = (u, v) => (Math.floor(u / 6) + Math.floor(v / 6)) % 2 ? quiltT : rcMix(quiltT, .93);
  rmBox(F, {x:40, y:13, z:8, w:54, d:21, h:3, outline:pal.sofaD, top:(u, v) => v < 3 ? sheet : patch(u, v), right:quiltD, left:(u, v) => v > 1 ? quilt : quiltD});  // the quilt, folded back at the top
  [[45, 18], [71, 18]].forEach(([x, w]) => rmBox(F, {x, y:16, z:11, w, d:14, h:2, top:(u, v) => patch(u + x, v + 16), right:quiltD, left:quilt}));          // two shapes under it
  if(awake) rmSprite(F, RM_PHONE.rows, RM_PHONE.pal, 55, 15, 15);
  return {sam:rmIso(55, 8, 18), charlie:rmIso(81, 8, 18), phone:rmIso(55, 15, 18)};
}

/* ---------- people and Paprika (redrawn every frame) ---------- */""")

# sofa -> bed at bedtime
rep("""  // sofa: back and seat go behind the people; arms and blanket go in front
  const S = {x:40, w:54}, sofa = rc(pal.sofa), sofaD = rc(pal.sofaD), sofaT = rc(pal.sofaT);""",
"""  const bedAt = opts.bed ? rmBed(B, F, pal, opts, wood, woodD, woodL) : null;
  // sofa: back and seat go behind the people; arms and blanket go in front
  const S = {x:40, w:54}, sofa = rc(pal.sofa), sofaD = rc(pal.sofaD), sofaT = rc(pal.sofaT);
  if(!opts.bed){""")
rep("""  rmBox(F, {x:S.x + S.w, y:2, z:0, w:5, d:19, h:12, outline:pal.sofaD, top:sofaT, right:sofaD, left:sofa});
""",
"""  rmBox(F, {x:S.x + S.w, y:2, z:0, w:5, d:19, h:12, outline:pal.sofaD, top:sofaT, right:sofaD, left:sofa});
  }
""")
rep("""  return {B, F, night: !!sky.night};
}""", """  return {B, F, night: !!sky.night, bed: opts.bed || "", bedAt};
}""")

# each frame: people on the sofa, or the bedtime version
rep("""  // people: breathe (1px) and blink now and then
  [["sam", 58, 22, 0], ["charlie", 79, 22, 700]].forEach(([k, x, y, ph]) => {""",
"""  if(R.base.bed){ roomBedFrame(B, ms); return; }
  // people: breathe (1px) and blink now and then
  [["sam", 58, 22, 0], ["charlie", 79, 22, 700]].forEach(([k, x, y, ph]) => {""")
rep("""function roomMount(){""",
"""function roomBedFrame(B, ms){
  const R = RM_RT, ctx = R.cv.getContext("2d"), at = R.base.bedAt, asleep = R.base.bed === "asleep";
  const F = R.base.F.d; for(let i = 0; i < F.length; i++) if(F[i]) B.d[i] = F[i];
  // Paprika curled up on Charlie, breathing
  let pr = RM_PAP.sleep; if(Math.floor(ms / 1400) % 2) pr = pr.map((r, i) => i === 0 ? "......KKKOOO......." : i === 1 ? "....KKKKKOOOOO....." : r);
  rmSprite(B, pr, RM_PAP.pal, 82, 24, 13);
  R.papBox = (() => { const [x, y] = rmIso(82, 24, 13); return [x - 10, y - 9, x + 10, y + 1]; })();
  if(ms < R.heartUntil) rmSprite(B, RM_BUBBLE.heart, RM_BUB_PAL, 86, 20, 26 + Math.floor((R.heartUntil - ms) / 300));
  // Zzz over whoever is asleep, drifting up and down
  const z = (who, ph) => { const [x, y] = at[who], up = Math.floor((ms + ph) / 600) % 3;
    RM_BUBBLE.z.forEach((row, r) => row.split("").forEach((ch, c) => { if(ch !== ".") rmSet(B, x + 5 + c, y - 6 - up + r, rc(RM_BUB_PAL.z)); })); };
  z("charlie", 0); if(asleep) z("sam", 900);
  // lights out: a cool, dark room; the phone screen lights Sam's face, or the moon through the window
  const [gx, gy] = asleep ? rmIso(80, 2, 30) : at.phone, flick = asleep ? 0 : (Math.floor(ms / 2300) % 3 === 0 ? .05 : 0);
  for(let yy = 0; yy < RM.H; yy++) for(let xx = 0; xx < RM.W; xx++){ const i = yy * RM.W + xx, c = B.d[i]; if(!c) continue;
    const d2 = (xx - gx) ** 2 + ((yy - gy) * 1.2) ** 2, glow = Math.max(0, 1 - d2 / (asleep ? 2600 : 900));
    B.d[i] = asleep ? rcMix(c, .42 + .22 * glow, [.85, .92, 1.25]) : rcMix(c, .45 + (.55 + flick) * glow, [.9 - .05 * glow, .97, 1.2 + .15 * glow]); }
  const img = ctx.createImageData(RM.W, RM.H); new Uint32Array(img.data.buffer).set(B.d); ctx.putImageData(img, 0, 0);
}
function roomMount(){""")
# rebuild when the hour changes while the room is on screen
rep("""    if(document.hidden) return;
    roomFrame(performance.now() - R.start);""",
"""    if(document.hidden) return;
    const h = new Date().getHours(); if(R.hour !== undefined && h !== R.hour){ R.hour = h; const i2 = roomInfo(), k2 = JSON.stringify(i2); if(k2 !== R.key){ R.base = rmStatic(i2); R.key = k2; R.plan = rmPapPlan(i2.mood); } }
    R.hour = h;
    roomFrame(performance.now() - R.start);""")
# screen-reader label
rep("""  const label = `Our pixel home: ${nameOf("sam")} and ${nameOf("charlie")} on the sofa,""",
"""  const label = i.bed ? `Our pixel home at night: ${i.bed === "phone" ? `${nameOf("sam")} up on her phone, ${nameOf("charlie")} asleep` : `${nameOf("sam")} and ${nameOf("charlie")} asleep`} with Paprika curled up on ${nameOf("charlie")}` : `Our pixel home: ${nameOf("sam")} and ${nameOf("charlie")} on the sofa,""")

open(p, "w").write(s)
print("step 18 applied")
