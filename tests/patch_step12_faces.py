"""Step 12: Azumanga-style faces for statuses (replaces the emoji picker).
14 expressions per person, drawn as 64x64 pixel portraits. Stored compactly: one base portrait
plus only the pixels each face changes (mock/faces/export.py builds FACES from mock/faces/chibi.py).
Data: status gains `face` (one of the face keys, default "normal"). The old `emoji` field is
left as it is, so older copies of the app still read the record. No schema bump needed.
Usage: python3 patch_step12_faces.py file.html path/to/faces.js"""
import sys
p = sys.argv[1]; s = open(p).read(); FACES_JS = open(sys.argv[2]).read()
def rep(old, new):
    global s
    assert s.count(old) == 1, (s.count(old), old[:90])
    s = s.replace(old, new)

# ---------- CSS: swap the emoji picker for a face picker + speech bubbles ----------
rep(""".who .st{position:absolute;left:16px;top:-3px;font-size:.78rem;line-height:1;filter:drop-shadow(0 1px 0 var(--bg))}""",
""".who .st{position:absolute;left:20px;top:-2px;width:11px;height:8px;border-radius:3px;background:#fffaf0;box-shadow:0 0 0 1.5px var(--ink)}
.who .st::after{content:"";position:absolute;left:1px;bottom:-3px;border:2px solid transparent;border-top-color:var(--ink);border-left-color:var(--ink)}""")
rep(""".emopick{display:flex;flex-wrap:wrap;gap:6px}
.emopick label{width:42px;height:42px;display:grid;place-items:center;font-size:1.3rem;border-radius:4px;box-shadow:inset 0 0 0 2px var(--line);background:var(--surface);cursor:pointer;position:relative}
.emopick input{position:absolute;opacity:0;inset:0;margin:0;width:100%;height:100%;min-height:0;padding:0}
.emopick label:has(input:checked){box-shadow:inset 0 0 0 3px var(--accent);background:var(--bg)}
.emopick label:has(input:focus-visible){outline:3px solid var(--accent);outline-offset:2px}""",
""".facepick{display:grid;grid-template-columns:repeat(auto-fill,minmax(72px,1fr));gap:8px}
.facepick label{display:flex;flex-direction:column;align-items:center;gap:2px;padding:4px 2px 6px;border-radius:4px;box-shadow:inset 0 0 0 2px var(--line);background:var(--surface);cursor:pointer;position:relative;font-size:.72rem;font-weight:600;text-align:center;line-height:1.15}
.facepick input{position:absolute;opacity:0;inset:0;margin:0;width:100%;height:100%;min-height:0;padding:0}
.facepick label:has(input:checked){box-shadow:inset 0 0 0 3px var(--accent);background:var(--bg)}
.facepick label:has(input:focus-visible){outline:3px solid var(--accent);outline-offset:2px}
.face{display:block;width:64px;height:64px;flex:none;background:var(--surface-2);border-radius:4px;box-shadow:inset 0 0 0 2px var(--line)}
.facepick .face{width:56px;height:56px;box-shadow:none;background:transparent}
.face svg{display:block;width:100%;height:100%}
.face .wa{animation:wagA .5s steps(1) infinite}.face .wb{animation:wagB .5s steps(1) infinite}
@keyframes wagA{0%{opacity:1}50%{opacity:0}}@keyframes wagB{0%{opacity:0}50%{opacity:1}}
@media (prefers-reduced-motion:reduce){.face .wa{animation:none}.face .wb{animation:none;opacity:0}}
.bub{position:relative;display:inline-block;max-width:100%;margin-top:4px;background:#fffaf0;color:#3b1f0e;border:2px solid #3b1f0e;border-radius:4px;padding:6px 10px;font-size:.95rem;box-shadow:3px 3px 0 rgba(59,31,14,.25);overflow-wrap:anywhere}
.bub::before{content:"";position:absolute;left:-9px;top:9px;border:7px solid transparent;border-right:9px solid #3b1f0e;border-left:0}
.bub::after{content:"";position:absolute;left:-5px;top:11px;border:5px solid transparent;border-right:6px solid #fffaf0;border-left:0}""")
rep(""".strow{display:flex;align-items:center;gap:10px;width:100%;text-align:left;border:0;background:transparent;padding:2px 0;color:inherit}
.strow .av{width:34px;height:34px;border-radius:10px;overflow:hidden;flex:none;background:var(--surface-2)}
.strow .tx{flex:1;min-width:0}
.strow .tx b{display:block}
.strow .tx span{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}""",
""".strow{display:flex;align-items:flex-start;gap:12px;width:100%;text-align:left;border:0;background:transparent;padding:2px 0;color:inherit}
.strow .tx{flex:1;min-width:0;padding-top:4px}
.strow .tx b{font-family:var(--f-display);font-weight:400;font-size:1.3rem;line-height:1}
.strow .tx .when{font-size:.8rem;color:var(--muted);margin-left:4px}
.strow .tx .hint{display:block;margin-top:6px;color:var(--muted);font-size:.9rem}
.profstatus{display:flex;gap:12px;align-items:flex-start}""")
rep(""".profstatus{margin:4px 0 0;font-size:.95rem}
""", "")

# ---------- data ----------
rep("""      p.status = {emoji: str(st.emoji, 16).trim(), text: str(st.text, 80).trim(), at: Math.max(0, Number(st.at) || 0)}; }""",
"""      p.status = {face: FACE_KEYS.includes(st.face) ? st.face : "normal", emoji: str(st.emoji, 16).trim(), text: str(st.text, 80).trim(), at: Math.max(0, Number(st.at) || 0)}; }""")

# ---------- face data + renderer (placed before normalize so FACE_KEYS exists) ----------
rep("function spriteRects(rows, pal){", FACES_JS + r"""
const FACE_KEYS = FACES.list.map(x => x[0]);
const FACE_LABEL = Object.fromEntries(FACES.list);
const faceCache = {};
function faceRects(grid, pal){
  let out = "";
  grid.forEach((row, y) => { let x = 0;
    while(x < row.length){ const ch = row[x]; if(ch === "_"){ x++; continue; }
      let w = 1; while(x + w < row.length && row[x+w] === ch) w++;
      out += `<rect x="${x}" y="${y}" width="${w}" height="1" fill="${pal[ch]}"/>`; x += w; } });
  return out;
}
function faceLayer(segs){ const g = Array.from({length:64}, () => Array(64).fill("_")); segs.forEach(([y, x, t]) => { for(let i = 0; i < t.length; i++) g[y][x+i] = t[i]; }); return g.map(r => r.join("")); }
// A 64x64 portrait of sam/charlie wearing one of the status faces. Tail wag animates.
function faceSVG(who, key){
  const F = FACES[who]; if(!F) return ""; if(!FACE_KEYS.includes(key)) key = "normal";
  const ck = who + "|" + key; if(faceCache[ck]) return faceCache[ck];
  const g = F.base.map(r => r.split(""));
  (F.d[key] || []).forEach(([y, x, t]) => { for(let i = 0; i < t.length; i++) g[y][x+i] = t[i]; });
  let body = faceRects(g.map(r => r.join("")), F.pal);
  if(key === "wag") body += `<g class="wa">${faceRects(faceLayer(F.d["wag~a"]), F.pal)}</g><g class="wb">${faceRects(faceLayer(F.d["wag~b"]), F.pal)}</g>`;
  return faceCache[ck] = `<svg viewBox="0 0 64 64" shape-rendering="crispEdges" aria-hidden="true">${body}</svg>`;
}
function spriteRects(rows, pal){""")

# ---------- top bar: a little speech bubble when there's something to read ----------
rep("""aria-label="${esc(nameOf(k))}'s profile${st.text || st.emoji ? ": " + esc((st.emoji + " " + st.text).trim()) : ""}"><span class="av">${sprite(k)}</span>${st.emoji ? `<span class="st" aria-hidden="true">${esc(st.emoji)}</span>` : ""}""",
"""aria-label="${esc(nameOf(k))}'s profile${st.text ? ": " + esc(st.text) : ""}"><span class="av">${sprite(k)}</span>${st.text ? `<span class="st" aria-hidden="true"></span>` : ""}""")

# ---------- Family profile ----------
rep("""      ${cat ? "" : `<p class="profstatus">${p.status.text || p.status.emoji ? `${esc(p.status.emoji)} ${esc(p.status.text)} <span class="muted small">· ${esc(sinceText(p.status.at))}</span>` : `<span class="muted small">No status set</span>`}</p>`}
      <button class="link" type="button" data-act="editBasics" style="padding-left:0">Edit details</button>${!cat && k === prefs.user ? ` <button class="link" type="button" data-act="setStatus">Change status</button>` : ""}</div></div>""",
"""      <button class="link" type="button" data-act="editBasics" style="padding-left:0">Edit details</button>${!cat && k === prefs.user ? ` <button class="link" type="button" data-act="setStatus">Change status</button>` : ""}</div></div>
    ${cat ? "" : `<div class="profstatus" style="margin-top:12px"><span class="face">${faceSVG(k, p.status.face)}</span><div style="min-width:0;padding-top:4px"><span class="small muted">${statusSet(p.status) ? `${esc(FACE_LABEL[p.status.face])} · ${esc(sinceText(p.status.at))}` : "No status set"}</span>${p.status.text ? `<br><span class="bub">${esc(p.status.text)}</span>` : ""}</div></div>`}""")

# ---------- status helpers, card and sheet ----------
rep("""const STATUS_EMOJI = ["🙂","😴","🎧","💼","🛒","🍳","🏃","🎮","📚","🤒","🔋","🫠","🎉","❤️","🐱",""];
const STATUS_PRESETS = [["💼","At work"],["🎧","Heads down, focusing"],["😴","Napping"],["🔋","Low battery, need quiet"],["🛒","Out running errands"],["🙂","Free, come say hi"]];""",
"""const STATUS_PRESETS = [["normal","At work"],["squint","Heads down, focusing"],["sleepy","Napping"],["sweat","Low battery, need quiet"],["blank","Out running errands"],["grin","Free, come say hi"]];
const statusSet = st => !!(st && (st.text || (st.face && st.face !== "normal")));""")
rep("""function statusCardHTML(me){
  const row = (k, mine) => { const st = state.people[k].status, has = st.text || st.emoji;
    return `<button type="button" class="strow" data-act="${mine ? "setStatus" : "goFam"}" data-id="${k}"><span class="av">${sprite(k)}</span>
      <span class="tx"><b>${mine ? "You" : esc(nameOf(k))}</b><span class="${has ? "" : "muted"}">${has ? `${esc(st.emoji)} ${esc(st.text)}` : (mine ? "Tap to set a status" : "No status")}</span></span>
      <span class="muted small">${has ? esc(sinceText(st.at)) : ""}</span></button>`; };
  return `<section class="card status-card" aria-label="Statuses">${row(me, true)}${row(other(me), false)}</section>`;
}""",
"""function statusCardHTML(me){
  const row = (k, mine) => { const st = state.people[k].status, has = statusSet(st);
    return `<button type="button" class="strow" data-act="${mine ? "setStatus" : "goFam"}" data-id="${k}" aria-label="${mine ? "Your status" : esc(nameOf(k)) + "'s status"}: ${has ? esc(FACE_LABEL[st.face] + (st.text ? ", " + st.text : "")) : "none"}">
      <span class="face">${faceSVG(k, st.face)}</span>
      <span class="tx"><b>${mine ? "You" : esc(nameOf(k))}</b>${has ? `<span class="when">· ${esc(sinceText(st.at))}</span>` : ""}
        ${st.text ? `<br><span class="bub">${esc(st.text)}</span>` : `<span class="hint">${has ? "" : (mine ? "Tap to pick a face and say something" : "No status yet")}</span>`}</span></button>`; };
  return `<section class="card status-card" aria-label="Statuses">${row(me, true)}${row(other(me), false)}</section>`;
}""")
rep("""    <div class="field"><span class="lab">Pick an emoji</span><div class="emopick" role="radiogroup" aria-label="Emoji">${STATUS_EMOJI.map(e => `<label title="${e || "No emoji"}"><input type="radio" name="semoji" value="${e}" ${st.emoji === e ? "checked" : ""} aria-label="${e || "No emoji"}">${e || "–"}</label>`).join("")}</div></div>
    ${field("stext", "What's up?", `<input id="stext" name="stext" maxlength="80" value="${esc(st.text)}" placeholder="e.g. Heads down until 3" autocomplete="off">`, "Just for fun. It doesn't send a notification.")}
    <div class="seg">${STATUS_PRESETS.map(([e, t]) => `<button type="button" class="chip" data-act="statusPreset" data-emoji="${e}" data-text="${esc(t)}">${e} ${esc(t)}</button>`).join("")}</div>
    <div class="actions">${st.text || st.emoji ? `<button type="button" class="btn ghost small" data-act="clearStatus">Clear status</button>` : "<span></span>"}""",
"""    <div class="field"><span class="lab">Pick a face</span><div class="facepick" role="radiogroup" aria-label="Face">${FACES.list.map(([f, l]) => `<label><input type="radio" name="sface" value="${f}" ${st.face === f ? "checked" : ""} aria-label="${esc(l)}"><span class="face">${faceSVG(k, f)}</span>${esc(l)}</label>`).join("")}</div></div>
    ${field("stext", "Speech bubble", `<input id="stext" name="stext" maxlength="80" value="${esc(st.text)}" placeholder="e.g. Heads down until 3" autocomplete="off">`, "Optional. Just for fun: it doesn't send a notification.")}
    <div class="seg">${STATUS_PRESETS.map(([f, t]) => `<button type="button" class="chip" data-act="statusPreset" data-face="${f}" data-text="${esc(t)}">${esc(t)}</button>`).join("")}</div>
    <div class="actions">${statusSet(st) ? `<button type="button" class="btn ghost small" data-act="clearStatus">Clear status</button>` : "<span></span>"}""")
rep("""    const text = val(form, "stext").slice(0, 80), r = form.querySelector("input[name=semoji]:checked");
    const emoji = r && STATUS_EMOJI.includes(r.value) ? r.value : "";
    if(!text && !emoji) return fail("stext", "Pick an emoji or type a few words, or tap Clear status.");
    state.people[k].status = {emoji, text, at: Date.now()};""",
"""    const text = val(form, "stext").slice(0, 80), r = form.querySelector("input[name=sface]:checked");
    const face = r && FACE_KEYS.includes(r.value) ? r.value : "normal";
    if(!text && face === "normal") return fail("stext", "Pick a face or type a few words, or tap Clear status.");
    state.people[k].status = {face, emoji: "", text, at: Date.now()};""")
rep("""    const r = f.querySelector(`input[name=semoji][value="${CSS.escape(el.dataset.emoji || "")}"]`); if(r) r.checked = true; t.focus(); },
  clearStatus: () => { const p = state.people[prefs.user]; p.status = {emoji:"", text:"", at:Date.now()}; save(); closeSheet(); render(); toast("Status cleared"); },""",
"""    const r = f.querySelector(`input[name=sface][value="${CSS.escape(el.dataset.face || "normal")}"]`); if(r) r.checked = true; t.focus(); },
  clearStatus: () => { const p = state.people[prefs.user]; p.status = {face:"normal", emoji:"", text:"", at:Date.now()}; save(); closeSheet(); render(); toast("Status cleared"); },""")

open(p, "w").write(s)
print("step 12 applied")
