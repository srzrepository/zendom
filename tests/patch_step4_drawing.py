"""Step 4: drawings on notes (schema v7 -> v8).
A note may now hold a drawing as compact vector strokes: note.drawing = {strokes:[{c, w, p:[x,y,x,y,...]}]}
on a 1000 x 750 canvas. A note needs text or a drawing. Usage: python3 patch_step4_drawing.py file.html"""
import sys
p = sys.argv[1]; s = open(p).read()
def rep(old, new):
    global s
    assert s.count(old) == 1, (s.count(old), old[:90])
    s = s.replace(old, new)

# ---------- data ----------
rep('const SCHEMA = 7;', 'const SCHEMA = 8;')
rep('''  6: d => Object.assign({}, d, {version: 7})    // v7 gives each bill a fixed day of the month (anchorDay); normalize takes it from the current due date''',
'''  6: d => Object.assign({}, d, {version: 7}),   // v7 gives each bill a fixed day of the month (anchorDay); normalize takes it from the current due date
  7: d => Object.assign({}, d, {version: 8})    // v8 lets a note hold a drawing; old notes are unchanged''')
rep('''const REACTIONS = [''', '''// Drawings: strokes on a 1000 x 750 page, colors from this fixed set
const DRAW_W = 1000, DRAW_H = 750;
const INKS = [["#3a2214","Walnut"],["#e0705a","Peach"],["#4f7fc4","Denim"],["#4f8f4a","Leaf"],["#e0a020","Honey"],["#8a5fc4","Plum"]];
const PENS = [[10,"Fine"],[24,"Thick"]];
const DRAW_LIMITS = {strokes:400, points:2000, total:30000};
function cleanDrawing(raw){
  if(!raw || typeof raw !== "object" || !Array.isArray(raw.strokes)) return null;
  let total = 0; const strokes = [];
  for(const st of raw.strokes.slice(0, DRAW_LIMITS.strokes)){
    if(!st || typeof st !== "object" || !Array.isArray(st.p)) continue;
    const c = INKS.some(i => i[0] === st.c) ? st.c : INKS[0][0];
    const w = PENS.some(x => x[0] === st.w) ? st.w : PENS[0][0];
    const pts = [];
    for(let i = 0; i + 1 < st.p.length && pts.length < DRAW_LIMITS.points * 2; i += 2){
      const x = Math.round(Number(st.p[i])), y = Math.round(Number(st.p[i+1]));
      if(Number.isFinite(x) && Number.isFinite(y)) pts.push(Math.min(DRAW_W, Math.max(0, x)), Math.min(DRAW_H, Math.max(0, y)));
    }
    if(!pts.length || total + pts.length / 2 > DRAW_LIMITS.total) continue;
    total += pts.length / 2; strokes.push({c, w, p:pts});
  }
  return strokes.length ? {strokes} : null;
}
function strokePath(st){
  const p = st.p; if(p.length === 2) return `M${p[0]} ${p[1]}l0.1 0`;
  let d = `M${p[0]} ${p[1]}`; for(let i = 2; i < p.length; i += 2) d += `L${p[i]} ${p[i+1]}`; return d;
}
function drawingSvg(dr, label){
  if(!dr) return "";
  return `<svg class="drawing" viewBox="0 0 ${DRAW_W} ${DRAW_H}" role="img" aria-label="${esc(label || "Drawing")}">${dr.strokes.map(st => `<path d="${strokePath(st)}" stroke="${st.c}" stroke-width="${st.w}" fill="none" stroke-linecap="round" stroke-linejoin="round"/>`).join("")}</svg>`;
}
const REACTIONS = [''')
rep('''  out.notes = (Array.isArray(d.notes) ? d.notes : []).filter(n => n && typeof n === "object" && str(n.text).trim()).map(n => Object.assign({}, n, {
    id: n.id ? String(n.id) : uid(), text: str(n.text, 1000), color: NOTE_COLORS.includes(n.color) ? n.color : "butter",''',
'''  out.notes = (Array.isArray(d.notes) ? d.notes : []).filter(n => n && typeof n === "object" && (str(n.text).trim() || cleanDrawing(n.drawing))).map(n => Object.assign({}, n, {
    id: n.id ? String(n.id) : uid(), text: str(n.text, 1000), drawing: cleanDrawing(n.drawing), color: NOTE_COLORS.includes(n.color) ? n.color : "butter",''')

# ---------- note card, detail ----------
rep('''aria-label="Note from ${esc(nameOf(n.author))}: ${esc(n.text.slice(0,60))}"><p>${esc(n.text)}</p>${''',
'''aria-label="Note from ${esc(nameOf(n.author))}: ${esc((n.text || (n.drawing ? "a drawing" : "")).slice(0,60))}">${n.drawing ? `<span class="paper">${drawingSvg(n.drawing, "Drawing by " + nameOf(n.author))}</span>` : ""}${n.text ? `<p>${esc(n.text)}</p>` : ""}${''')
rep('''    <div class="notebig n-${n.color}">${esc(n.text)}</div>''',
'''    <div class="notebig n-${n.color}">${n.drawing ? `<span class="paper">${drawingSvg(n.drawing, "Drawing by " + nameOf(n.author))}</span>` : ""}${n.text ? esc(n.text) : ""}</div>''')

# ---------- note form: text + drawing pad ----------
rep('''  openSheet(n ? "Edit note" : "New note", `
    ${field("text","Note", `<textarea id="text" name="text" maxlength="1000" placeholder="Write something for both of you">${esc(d.text)}</textarea>`)}''',
'''  drawPad.strokes = n && n.drawing ? JSON.parse(JSON.stringify(n.drawing.strokes)) : []; drawPad.undo = []; drawPad.mode = "pen";
  const startDrawing = !!(n && n.drawing) || opts === "draw";
  openSheet(n ? "Edit note" : (opts === "draw" ? "New drawing" : "New note"), `
    ${field("text","Note", `<textarea id="text" name="text" maxlength="1000" placeholder="${startDrawing ? "Add words if you like (optional)" : "Write something for both of you"}">${esc(d.text)}</textarea>`)}
    <div class="field" id="f-draw"><span class="lab">Drawing</span>
      <div id="drawWrap" ${startDrawing ? "" : "hidden"}>${drawPadHTML()}</div>
      <button type="button" class="btn ghost small" id="drawOpen" data-act="drawOpen" style="align-self:flex-start" ${startDrawing ? "hidden" : ""}>Add a drawing</button></div>''')
rep('''function noteForm(id){
  const n = id ? state.notes.find(x => x.id === id) : null; if(id && !n) return;
  const d = n || {text:"", color:"butter", pinned:false};''',
'''function noteForm(id, opts){
  const n = id ? state.notes.find(x => x.id === id) : null; if(id && !n) return;
  const d = n || {text:"", color:"butter", pinned:false};''')
rep('''    const text = form.elements.text.value.trim();
    if(!text) return fail("text","A note needs some words.");
    const color = (form.querySelector("input[name=color]:checked") || {}).value || "butter";
    const pinned = form.elements.pinned.checked;
    if(n) Object.assign(n, {text, color, pinned, updated:Date.now()});
    else state.notes.push({id:uid(), text, color, pinned, author:prefs.user, created:Date.now(), updated:Date.now(), reactions:[], replies:[]});''',
'''    const text = form.elements.text.value.trim();
    const drawing = $("#drawWrap") && !$("#drawWrap").hidden ? cleanDrawing({strokes: drawPad.strokes}) : null;
    if(!text && !drawing) return fail("text", $("#drawWrap") && !$("#drawWrap").hidden ? "Draw something or write a few words." : "A note needs some words or a drawing.");
    const color = (form.querySelector("input[name=color]:checked") || {}).value || "butter";
    const pinned = form.elements.pinned.checked;
    if(n) Object.assign(n, {text, drawing, color, pinned, updated:Date.now()});
    else state.notes.push({id:uid(), text, drawing, color, pinned, author:prefs.user, created:Date.now(), updated:Date.now(), reactions:[], replies:[]});''')
rep('''    save(); closeSheet(); render(); toast(n ? "Note saved" : "Note added");
  });
}''', '''    save(); closeSheet(); render(); toast(n ? "Note saved" : "Note added");
  });
  initDrawPad();
}

/* ---------- drawing pad ---------- */
const drawPad = {strokes:[], undo:[], mode:"pen", ink:INKS[0][0], pen:PENS[0][0], cur:null};
function drawPadHTML(){
  return `<div class="drawpad">
    <canvas id="drawCanvas" width="${DRAW_W}" height="${DRAW_H}" aria-label="Drawing pad. Draw with your finger, a mouse or a stylus."></canvas>
    <div class="drawtools">
      <div class="inks" role="radiogroup" aria-label="Ink color">${INKS.map(([c,l]) => `<button type="button" class="ink" data-act="drawInk" data-id="${c}" aria-label="${l} ink" aria-pressed="${drawPad.mode === "pen" && drawPad.ink === c}" style="--c:${c}"></button>`).join("")}</div>
      <div class="seg">${PENS.map(([w,l]) => `<button type="button" class="chip" data-act="drawPen" data-id="${w}" aria-pressed="${drawPad.mode === "pen" && drawPad.pen === w}">${l}</button>`).join("")}
        <button type="button" class="chip" data-act="drawEraser" aria-pressed="${drawPad.mode === "erase"}">Eraser</button></div>
      <div class="seg"><button type="button" class="chip" data-act="drawUndo" ${drawPad.undo.length ? "" : "disabled"}>Undo</button>
        <button type="button" class="chip" data-act="drawClear" ${drawPad.strokes.length ? "" : "disabled"}>Clear</button></div>
    </div></div>`;
}
function drawRefreshTools(){ const w = $("#drawWrap"); if(!w || w.hidden) return; const tools = w.querySelector(".drawtools"); const tmp = document.createElement("div"); tmp.innerHTML = drawPadHTML(); tools.replaceWith(tmp.querySelector(".drawtools")); }
function drawRepaint(){
  const cv = $("#drawCanvas"); if(!cv) return; const g = cv.getContext("2d");
  g.clearRect(0, 0, DRAW_W, DRAW_H); g.lineCap = "round"; g.lineJoin = "round";
  drawPad.strokes.concat(drawPad.cur ? [drawPad.cur] : []).forEach(st => {
    g.strokeStyle = st.c; g.lineWidth = st.w; g.beginPath(); g.moveTo(st.p[0], st.p[1]);
    if(st.p.length === 2) g.lineTo(st.p[0] + .1, st.p[1]); else for(let i = 2; i < st.p.length; i += 2) g.lineTo(st.p[i], st.p[i+1]);
    g.stroke();
  });
}
function drawPoint(cv, e){ const r = cv.getBoundingClientRect(); return [Math.round((e.clientX - r.left) / r.width * DRAW_W), Math.round((e.clientY - r.top) / r.height * DRAW_H)]; }
function eraseAt(x, y){
  const hit = drawPad.strokes.findIndex(st => { for(let i = 0; i < st.p.length; i += 2){ const dx = st.p[i] - x, dy = st.p[i+1] - y; if(dx*dx + dy*dy <= (st.w / 2 + 22) ** 2) return true; } return false; });
  if(hit < 0) return false;
  drawPad.undo.push({kind:"erase", at:hit, st:drawPad.strokes[hit]}); drawPad.strokes.splice(hit, 1); return true;
}
function initDrawPad(){
  const cv = $("#drawCanvas"); if(!cv) return;
  drawRepaint();
  cv.addEventListener("pointerdown", e => {
    e.preventDefault(); cv.setPointerCapture(e.pointerId);
    const [x, y] = drawPoint(cv, e);
    if(drawPad.mode === "erase"){ if(eraseAt(x, y)){ drawRepaint(); drawRefreshTools(); } drawPad.cur = {erasing:true}; return; }
    if(drawPad.strokes.length >= DRAW_LIMITS.strokes){ toast("This drawing is full. Undo or clear to keep going."); return; }
    drawPad.cur = {c:drawPad.ink, w:drawPad.pen, p:[x, y]}; drawRepaint();
  });
  cv.addEventListener("pointermove", e => {
    if(!drawPad.cur) return; const [x, y] = drawPoint(cv, e);
    if(drawPad.cur.erasing){ if(eraseAt(x, y)){ drawRepaint(); drawRefreshTools(); } return; }
    const p = drawPad.cur.p, lx = p[p.length - 2], ly = p[p.length - 1];
    if((x - lx) ** 2 + (y - ly) ** 2 < 16 || p.length >= DRAW_LIMITS.points * 2) return;   // skip tiny moves
    p.push(x, y); drawRepaint();
  });
  const end = () => { const c = drawPad.cur; drawPad.cur = null; if(!c || c.erasing) return;
    drawPad.strokes.push(c); drawPad.undo.push({kind:"add"}); drawRepaint(); drawRefreshTools(); };
  cv.addEventListener("pointerup", end); cv.addEventListener("pointercancel", end);
}''')
rep('''  newNote: () => noteForm(null),''', '''  newNote: () => noteForm(null),
  newDrawing: () => noteForm(null, "draw"),
  drawOpen: () => { const w = $("#drawWrap"), b = $("#drawOpen"); if(!w) return; w.hidden = false; if(b) b.hidden = true; initDrawPad(); },
  drawInk: id => { if(!INKS.some(i => i[0] === id)) return; drawPad.ink = id; drawPad.mode = "pen"; drawRefreshTools(); },
  drawPen: id => { const w = +id; if(!PENS.some(x => x[0] === w)) return; drawPad.pen = w; drawPad.mode = "pen"; drawRefreshTools(); },
  drawEraser: () => { drawPad.mode = drawPad.mode === "erase" ? "pen" : "erase"; drawRefreshTools(); },
  drawUndo: () => { const u = drawPad.undo.pop(); if(!u) return;
    if(u.kind === "add") drawPad.strokes.pop(); else if(u.kind === "erase") drawPad.strokes.splice(u.at, 0, u.st); else if(u.kind === "clear") drawPad.strokes = u.strokes;
    drawRepaint(); drawRefreshTools(); },
  drawClear: () => { if(!drawPad.strokes.length) return; drawPad.undo.push({kind:"clear", strokes:drawPad.strokes}); drawPad.strokes = []; drawRepaint(); drawRefreshTools(); toast("Cleared. Tap Undo to bring it back."); },''')

# empty board: offer both
rep('''<button class="btn" type="button" data-act="newNote">${IC.plus} Write a note</button></div>`}''',
    '''<div class="actions" style="justify-content:center"><button class="btn" type="button" data-act="newNote">${IC.plus} Write a note</button><button class="btn ghost" type="button" data-act="newDrawing">Draw one</button></div></div>`}''')
rep('''    <div class="sec-head"><h2>Note board</h2><span class="muted small">${notes.length} ${notes.length===1?"note":"notes"}</span></div>''',
    '''    <div class="sec-head"><h2>Note board</h2><div style="display:flex;gap:8px;align-items:center"><span class="muted small">${notes.length} ${notes.length===1?"note":"notes"}</span>${notes.length ? `<button type="button" class="btn ghost small" data-act="newDrawing">Draw</button>` : ""}</div></div>''')

# ---------- styles ----------
rep('</style>', '''
/* drawings */
.paper{display:block;background:#fffaf0;border-radius:4px;box-shadow:inset 0 0 0 2px rgba(74,38,16,.25);overflow:hidden}
.paper .drawing{display:block;width:100%;height:auto;aspect-ratio:4/3}
.note .paper{margin:-2px -2px 2px}
.notebig .paper{margin-bottom:8px}
.drawpad{display:flex;flex-direction:column;gap:8px}
#drawCanvas{display:block;width:100%;height:auto;aspect-ratio:4/3;max-width:100%;background:#fffaf0;border-radius:4px;box-shadow:inset 0 0 0 3px var(--frame,#8b5a2b);touch-action:none;cursor:crosshair}
.drawtools{display:flex;flex-direction:column;gap:8px}
.inks{display:flex;gap:8px;flex-wrap:wrap}
.ink{width:40px;height:40px;border-radius:4px;border:3px solid var(--surface);background:var(--c);box-shadow:0 0 0 2px var(--line)}
.ink[aria-pressed="true"]{box-shadow:0 0 0 3px var(--ink)}
.chip:disabled{opacity:.45}
</style>''')
open(p, 'w').write(s)
print("patched", p)
