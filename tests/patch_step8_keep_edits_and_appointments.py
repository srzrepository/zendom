"""Step 8:
(a) Changes from the other phone no longer replace the objects an open form is editing, so a Save made while
    the other person is busy is kept (it used to be silently lost).
(b) Checkups can have a booked next appointment: book, reschedule, mark as done, cancel, add to calendar.
Schema v8 -> v9 (checkup.next is new and optional). Usage: python3 patch_step8_keep_edits_and_appointments.py file.html"""
import sys
p = sys.argv[1]; s = open(p).read()
def rep(old, new):
    global s
    assert s.count(old) == 1, (s.count(old), old[:90])
    s = s.replace(old, new)

# ---------- (a) keep object identity when applying remote changes ----------
rep('''  if(!applied.length) return;
  state = normalize(state);
  const after = recordHashes(state);''', '''  if(!applied.length) return;
  state = keepIdentity(state, normalize(state), new Set(applied));
  const after = recordHashes(state);''')
rep('''    const v = Object.assign({}, data, {id}); if(j >= 0) arr[j] = v; else arr.push(v); return; }''',
    '''    const v = Object.assign({}, data, {id}); if(j >= 0) refill(arr[j], v); else arr.push(v); return; }''')
rep('''  if(kind === "person" && PEOPLE.includes(id)) st.people[id] = data;''',
    '''  if(kind === "person" && PEOPLE.includes(id)){ if(st.people[id] && typeof st.people[id] === "object") refill(st.people[id], data); else st.people[id] = data; }''')
rep('''function emptyHousehold(){''', '''// After a remote change, reuse this phone's existing objects so anything holding them (an open edit form) stays live.
// Changed records are updated in place; untouched ones are kept exactly as they were.
function refill(o, n){ Object.keys(o).forEach(k => { if(!(k in n)) delete o[k]; }); return Object.assign(o, n); }
function keepIdentity(oldS, newS, applied){
  SYNC_LISTS.forEach(([kind, get]) => {
    const oldMap = new Map(get(oldS).map(x => [x.id, x])), arr = get(newS);
    const merged = arr.map(n => { const o = oldMap.get(n.id); if(!o) return n; return applied.has(kind + "~" + n.id) ? refill(o, n) : o; });
    arr.splice(0, arr.length, ...merged);
  });
  PEOPLE.forEach(k => { const o = oldS.people[k]; if(o) newS.people[k] = applied.has("person~" + k) ? refill(o, newS.people[k]) : o; });
  return newS;
}
function emptyHousehold(){''')

# ---------- (b) appointments on checkups ----------
rep('const SCHEMA = 8;', 'const SCHEMA = 9;')
rep('''  7: d => Object.assign({}, d, {version: 8})    // v8 lets a note hold a drawing; old notes are unchanged''',
    '''  7: d => Object.assign({}, d, {version: 8}),   // v8 lets a note hold a drawing; old notes are unchanged
  8: d => Object.assign({}, d, {version: 9})    // v9 lets a checkup hold a booked next appointment; old checkups have none''')
rep('''    p.checkups = objs(p.checkups).map(c => Object.assign(c, {name:str(c.name,80), months: clampInt(c.months,1,120,12), last: isDate(c.last)?c.last:"", provider:str(c.provider,80)})).filter(c => c.name.trim());''',
    '''    p.checkups = objs(p.checkups).map(c => Object.assign(c, {name:str(c.name,80), months: clampInt(c.months,1,120,12), last: isDate(c.last)?c.last:"", provider:str(c.provider,80),
      next: c.next && typeof c.next === "object" && isDate(c.next.date) ? {date:c.next.date, time: /^([01]\\d|2[0-3]):[0-5]\\d$/.test(String(c.next.time || "")) ? c.next.time : "", where: str(c.next.where, 120)} : null})).filter(c => c.name.trim());''')
rep('''function checkupInfo(c){
  if(!c.last) return {cls:"", text:"No visit logged yet", due:null};''', '''function checkupInfo(c){
  if(c.next){
    const n = diffDays(todayStr(), c.next.date), at = c.next.time ? " · " + fmtTime(c.next.time) : "";
    if(n < 0) return {cls:"late", text:`Was booked for ${niceDate(c.next.date)}. Did it happen?`, due:c.next.date, n, booked:true};
    if(n === 0) return {cls:"today", text:"Today" + at, due:c.next.date, n, booked:true};
    return {cls: n <= 7 ? "soon" : "ok", text:`Booked ${niceDate(c.next.date)}${at}`, due:c.next.date, n, booked:true};
  }
  if(!c.last) return {cls:"", text:"No visit logged yet", due:null};''')
rep('''    p.checkups.forEach(c => { const i = checkupInfo(c); if(i.cls === "late" || i.cls === "soon") out.push({k, what:c.name, i, sort:i.n}); });''',
    '''    p.checkups.forEach(c => { const i = checkupInfo(c); if(i.cls === "late" || i.cls === "soon" || i.cls === "today") out.push({k, what:c.name, i, sort:i.n}); });''')
rep('''    p.checkups.forEach(c => { const i = checkupInfo(c); if(i.due) push(i.due < t ? t : i.due, {type:"health", title:`${p.name}: ${c.name}`, who: HUMANS.includes(k) ? k : "", act:"goFam", id:k, flag: i.due < t ? "overdue" : ""}); });''',
    '''    p.checkups.forEach(c => { const i = checkupInfo(c); if(i.due) push(i.due < t ? t : i.due, {type:"health", title:`${p.name}: ${c.name}${i.booked ? "" : " (due)"}`, who: HUMANS.includes(k) ? k : "", act:"goFam", id:k, time: i.booked && i.due >= t ? c.next.time : "", flag: i.due < t ? "overdue" : ""}); });''')

# checkup form: a "Next appointment" section
rep('''  const d = c || {name: presetName || "", months:12, last:"", provider:""};''',
    '''  const d = c || {name: presetName || "", months:12, last:"", provider:"", next:null};
  const nx = d.next || {date:"", time:"", where:""};''')
rep('''    ${field("provider","Provider", `<input id="provider" name="provider" maxlength="80" value="${esc(d.provider)}" placeholder="Optional">`)}
    ${footer(c ? "delCheckup:" + c.id : "")}`,''', '''    ${field("provider","Provider", `<input id="provider" name="provider" maxlength="80" value="${esc(d.provider)}" placeholder="Optional">`)}
    <div class="appt"><span class="lab">Next appointment</span>
      <div class="two">${field("ndate","Date", `<input id="ndate" name="ndate" type="date" value="${esc(nx.date)}">`)}
      ${field("ntime","Time", `<input id="ntime" name="ntime" type="time" value="${esc(nx.time)}">`, "Optional")}</div>
      ${field("nwhere","Where or notes", `<input id="nwhere" name="nwhere" maxlength="120" value="${esc(nx.where)}" placeholder="e.g. Dr. Lee, 2nd floor">`)}
      <span class="hint">${c && c.next ? "To reschedule, change the date or time and tap Save." : "Leave the date blank if nothing is booked yet."}</span>
      ${c && c.next ? `<div class="actions" style="justify-content:flex-start"><button type="button" class="btn small" data-act="apptDone" data-id="${c.id}">${diffDays(todayStr(), c.next.date) > 0 ? "It happened early" : "Mark as done"}</button><button type="button" class="btn ghost small" data-act="apptCancel" data-id="${c.id}">Cancel appointment</button></div>
        ${calLinksHTML(apptEvent(p, c))}` : ""}
    </div>
    ${footer(c ? "delCheckup:" + c.id : "")}`,''')
rep('''    if(last && last > todayStr()) return fail("last","A past visit can't be in the future. Leave it blank until it happens.");
    const data = {name, months:+months, last, provider:val(form,"provider")};''', '''    if(last && last > todayStr()) return fail("last","A past visit can't be in the future. Leave it blank until it happens.");
    const nd = val(form,"ndate"), nt = val(form,"ntime");
    if(nd && !isDate(nd)) return fail("ndate","Pick a valid date or leave it blank.");
    if(nd && nd < todayStr() && !(c && c.next && c.next.date === nd)) return fail("ndate","That date has passed. If the visit already happened, put it under Last visit instead.");
    if(nt && !nd) return fail("ndate","Add the date for this time.");
    if(nt && !/^([01]\\d|2[0-3]):[0-5]\\d$/.test(nt)) return fail("ntime","Pick a valid time or leave it blank.");
    const was = c && c.next ? c.next.date + c.next.time : "";
    const data = {name, months:+months, last, provider:val(form,"provider"), next: nd ? {date:nd, time:nt, where:val(form,"nwhere")} : null};''')
rep('''    save(); closeSheet(); render(); toast("Checkup saved");''',
    '''    save(); closeSheet(); render();
    toast(data.next ? (c && c.next && was !== data.next.date + data.next.time ? `Rescheduled to ${niceDate(data.next.date)}` : c && c.next ? "Checkup saved" : `Booked for ${niceDate(data.next.date)}`) : "Checkup saved");''')

# calendar links for an appointment reuse the event ones
rep('''function calLinksHTML(e){''', '''function apptEvent(p, c){ return {id:"appt~" + c.id, title:`${p.name}: ${c.name}`, date:c.next.date, time:c.next.time, repeat:"none", note:[c.next.where, c.provider].filter(Boolean).join(" · ")}; }
function calEventById(id){
  if(!String(id).startsWith("appt~")) return state.events.find(x => x.id === id) || null;
  const cid = id.slice(5);
  for(const k of PEOPLE){ const c = state.people[k].checkups.find(x => x.id === cid); if(c && c.next) return apptEvent(state.people[k], c); }
  return null;
}
function calLinksHTML(e){''')
rep('''  icsFile: id => { const e = state.events.find(x => x.id === id); if(!e) return;''', '''  icsFile: id => { const e = calEventById(id); if(!e) return;''')
rep('''  editVaccine: id => vaccineForm(id || null),''', '''  editVaccine: id => vaccineForm(id || null),
  apptDone: id => { const p = state.people[prefs.fam], c = p.checkups.find(x => x.id === id); if(!c || !c.next) return;
    const before = JSON.parse(JSON.stringify(c)), t = todayStr();
    c.last = c.next.date <= t ? c.next.date : t; c.next = null; save(); closeSheet(); render();
    toast(`Logged ${c.name} · next due around ${niceDate(addMonths(c.last, c.months))}`, () => { const x = p.checkups.find(y => y.id === id); if(x){ refill(x, before); save(); render(); } }); },
  apptCancel: id => { const p = state.people[prefs.fam], c = p.checkups.find(x => x.id === id); if(!c || !c.next) return;
    const was = c.next; c.next = null; save(); closeSheet(); render();
    toast("Appointment cancelled", () => { const x = p.checkups.find(y => y.id === id); if(x){ x.next = was; save(); render(); } }); },''')
rep('\n</style>\n', '''
.appt{display:flex;flex-direction:column;gap:10px;background:var(--surface-2);border-radius:var(--r-card,6px);padding:12px;box-shadow:inset 0 0 0 2px var(--line)}
.appt > .lab{font-weight:600;font-size:.9rem}
</style>\n''')
open(p, 'w').write(s)
print("patched", p)
