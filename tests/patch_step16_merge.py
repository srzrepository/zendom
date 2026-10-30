"""Step 16: edits made at the same time are combined instead of one overwriting the other,
and offline edits wait on the phone and go out (combined) when it's back online.

How: each phone keeps the last version of every record it sent or received (its "base", stored in
zendom:base). Saving reads the server's copy inside a transaction (zdBackend.writeMerged). If the server
still has our base, our version goes in as before. If someone else changed it meanwhile, we merge:
- fields only one side changed: that side's value
- lists of items with ids (replies, comments, reactions, meds, checkups, ...): merged item by item
  (new items from both kept, an item deleted on one side stays deleted, sorted by time if timed)
- the same plain field changed on both phones: this phone's edit wins (what happened before)
The merged version is shown here right away and is what the server stores.
Offline: nothing is sent; changes stay on this phone (they already survive a reload) and go out
when the browser says it's back online, or on a retry every 30 s. The top bar shows "Offline".
No household-data change. Usage: python3 patch_step16_merge.py file.html"""
import sys
p = sys.argv[1]; s = open(p).read()
def rep(old, new):
    global s
    assert s.count(old) == 1, (s.count(old), old[:90])
    s = s.replace(old, new)

# ---------- merge helpers + persistent base ----------
rep("""const sync = {status:"off", user:null, err:"", last:{}, ever:false, unsub:null, timer:0, at:0, pending:0};
function syncLoad(){ try { const o = JSON.parse(lsGet(SYNC_KEY) || "{}"); sync.last = (o.last && typeof o.last === "object") ? o.last : {}; sync.ever = !!o.ever; } catch(e){} }
function syncStore(){ lsSet(SYNC_KEY, JSON.stringify({last:sync.last, ever:sync.ever})); }""",
"""const sync = {status:"off", user:null, err:"", last:{}, ever:false, unsub:null, timer:0, at:0, pending:0, offline:false, retry:0};
const BASE_KEY = "zendom:base";                       // this phone only: last version of each record sent/received
function syncLoad(){ try { const o = JSON.parse(lsGet(SYNC_KEY) || "{}"); sync.last = (o.last && typeof o.last === "object") ? o.last : {}; sync.ever = !!o.ever; } catch(e){}
  try { const b = JSON.parse(lsGet(BASE_KEY) || "null"); if(b && typeof b === "object") sync.base = b; } catch(e){} }
function syncStore(){ lsSet(SYNC_KEY, JSON.stringify({last:sync.last, ever:sync.ever})); if(sync.shadow) lsSet(BASE_KEY, JSON.stringify(sync.shadow)); }

/* ---- combining two versions of one record (see step 16 notes) ---- */
const jeq = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const itemKey = x => x && typeof x === "object" && !Array.isArray(x)
  ? (x.id != null ? "id:" + x.id : (typeof x.by === "string" && typeof x.emoji === "string" ? "re:" + x.by + "|" + x.emoji : null)) : null;
function mergeList(b, l, r){
  const keyed = a => Array.isArray(a) && a.every(x => itemKey(x) !== null);
  if(!keyed(l) || !keyed(r) || (b !== undefined && !keyed(b))) return undefined;
  const bm = new Map((b || []).map(x => [itemKey(x), x])), lm = new Map(l.map(x => [itemKey(x), x])), rm = new Map(r.map(x => [itemKey(x), x]));
  const out = [];
  l.forEach(x => { const k = itemKey(x);
    if(rm.has(k)) out.push(merge3(bm.get(k), x, rm.get(k)));
    else if(!(bm.has(k) && jeq(bm.get(k), x))) out.push(x); });          // missing there + unchanged here = they deleted it
  r.forEach(x => { const k = itemKey(x);
    if(lm.has(k)) return;
    if(!(bm.has(k) && jeq(bm.get(k), x))) out.push(x); });               // missing here + unchanged there = we deleted it
  if(out.length && out.every(x => typeof x.at === "number")) out.sort((a, c) => a.at - c.at);
  return out;
}
function merge3(b, l, r){
  if(jeq(l, r)) return l;
  if(b !== undefined && jeq(l, b)) return r;
  if(b !== undefined && jeq(r, b)) return l;
  if(Array.isArray(l) && Array.isArray(r)){ const m = mergeList(b, l, r); return m === undefined ? l : m; }
  if(l && r && typeof l === "object" && typeof r === "object" && !Array.isArray(l) && !Array.isArray(r)){
    const bo = b && typeof b === "object" && !Array.isArray(b) ? b : undefined, o = {};
    new Set([...Object.keys(l), ...Object.keys(r)]).forEach(k => {
      const bk = bo ? bo[k] : undefined;
      if(!(k in l)){ if(!(bo && (k in bo) && jeq(bk, r[k]))) o[k] = r[k]; return; }
      if(!(k in r)){ if(!(bo && (k in bo) && jeq(bk, l[k]))) o[k] = l[k]; return; }
      o[k] = merge3(bo ? bk : undefined, l[k], r[k]);
    });
    return o;
  }
  return l;                                                              // the same value changed on both: this phone wins
}
// Called inside the save transaction: what should the server store for this write?
function mergeWrite(w, server){
  if(w.data.del || !server || server.del) return w.data;
  const baseJ = sync.shadow ? sync.shadow[w.id] : undefined;
  if(server.j === w.data.j || (baseJ !== undefined && server.j === baseJ)) return w.data;     // nobody else changed it
  let b, l, r; try { l = JSON.parse(w.data.j); r = JSON.parse(server.j); b = baseJ !== undefined ? JSON.parse(baseJ) : undefined; } catch(e){ return w.data; }
  return Object.assign({}, w.data, {j: JSON.stringify(merge3(b, l, r)), merged: true});
}""")

# ---------- flush: offline-aware, transactional when available ----------
rep("""function syncFlush(){
  const be = window.zdBackend; if(!be || sync.status !== "on") return 0;""",
"""function syncOffline(on){
  if(sync.offline === on) return; sync.offline = on; renderNetPill();
  clearInterval(sync.retry); sync.retry = on ? setInterval(() => { if(navigator.onLine !== false) syncFlush(); }, 30000) : 0;
  if(prefs.tab === "more" && prefs.moreTab === "settings" && !$("#sheetRoot").innerHTML) render();
}
function syncFlush(){
  const be = window.zdBackend; if(!be || sync.status !== "on") return 0;
  if(navigator.onLine === false){ syncOffline(true); return 0; }       // keep changes here; they go out when back online""")
rep("""  syncStore(); sync.pending++;
  be.write(writes).then(() => { sync.pending--; sync.at = Date.now(); if(sync.status === "on") syncSetStatus("on"); })
    .catch(e => { sync.pending--; writes.forEach(w => { if(w.data.del) sync.last[w.id] = "resend"; else delete sync.last[w.id]; }); syncStore(); syncSetStatus("error", syncErrText(e)); });
  return writes.length;""",
"""  syncStore(); sync.pending++;
  if(sync.shadow) writes.forEach(w => { if(base0[w.id] !== undefined) sync.shadow[w.id] = base0[w.id]; else delete sync.shadow[w.id]; });   // merge against what we had before this send
  const send = be.writeMerged ? be.writeMerged(writes, mergeWrite) : be.write(writes).then(() => writes.map(w => ({id:w.id, data:w.data})));
  send.then(res => {
    sync.pending--; sync.at = Date.now(); syncOffline(false);
    const merged = (res || []).filter(x => x.data && x.data.merged);
    (res || []).forEach(x => { if(!sync.shadow) return; if(x.data.del) delete sync.shadow[x.id]; else sync.shadow[x.id] = x.data.j; });
    if(merged.length){                                                   // show the combined version here too
      merged.forEach(x => { try { applyRecord(state, x.id, JSON.parse(x.data.j)); } catch(e){} });
      state = keepIdentity(state, normalize(state), new Set(merged.map(x => x.id)));
      merged.forEach(x => { sync.last[x.id] = syncHash(x.data.j); });
      lsSet(KEY, JSON.stringify(state)); render(); syncSchedule();      // if tidying changed anything, it goes out next
    }
    syncStore(); if(sync.status === "on") syncSetStatus("on");
  }).catch(e => {
    sync.pending--; writes.forEach(w => { if(w.data.del) sync.last[w.id] = "resend"; else delete sync.last[w.id]; });
    if(sync.shadow) writes.forEach(w => { if(base0[w.id] !== undefined) sync.shadow[w.id] = base0[w.id]; });
    syncStore();
    const c = String((e && (e.code || e.message)) || e);
    if(navigator.onLine === false || /unavailable|offline|network|failed-precondition|deadline/i.test(c)) syncOffline(true);
    else syncSetStatus("error", syncErrText(e));
  });
  return writes.length;""")

rep("""  if(!writes.length) return 0;
  if(typeof notifyCollect === "function") notifyCollect(writes, cur);""",
"""  if(!writes.length) return 0;
  const base0 = {}; writes.forEach(w => { base0[w.id] = sync.shadow ? sync.shadow[w.id] : undefined; });   // before notifyCollect moves it on
  if(typeof notifyCollect === "function") notifyCollect(writes, cur);""")
# notifyCollect stamped the base with what we were about to send; the flush now restores the true base
# before sending (above), so notification wording still compares against the pre-send version.

# ---------- start: keep the base across reloads ----------
rep("""    { const cur = recordsOf(state); sync.shadow = {}; for(const k in cur) sync.shadow[k] = JSON.stringify(cur[k]); }""",
"""    { const cur = recordsOf(state), saved = sync.base || {}; sync.shadow = {};
      // a record with a change not yet sent keeps its saved base (so the change can still be merged); others start from what's here
      for(const k in cur){ const j = JSON.stringify(cur[k]), unsent = sync.last[k] !== syncHash(j);
        if(unsent){ if(saved[k] !== undefined) sync.shadow[k] = saved[k]; } else sync.shadow[k] = j; }
      for(const k in saved) if(!(k in cur) && sync.last[k] !== null && saved[k] !== undefined) sync.shadow[k] = saved[k]; }""")

# ---------- the "Offline" pill + online/offline events ----------
rep("""const navKey = () =>""",
"""function renderNetPill(){
  const el = $("#netPill"); if(!el) return;
  const off = navigator.onLine === false || sync.offline;
  el.hidden = !off;
  el.textContent = "";
  if(off) el.innerHTML = `<span class="dot" aria-hidden="true"></span>Offline${sync.status === "on" ? " · saving on this phone" : ""}`;
}
window.addEventListener("online", () => { renderNetPill(); if(sync.status === "on") setTimeout(syncFlush, 300); });
window.addEventListener("offline", () => { syncOffline(true); renderNetPill(); });
const navKey = () =>""")
rep("""<div class="who" role="group" aria-label="Profiles" id="who"></div>""",
"""<div class="who" role="group" aria-label="Profiles" id="who"></div>
    <div class="netpill" id="netPill" role="status" hidden></div>""")
rep(""".who{display:flex;background:var(--surface-2);border-radius:var(--r-pill);padding:3px;gap:2px}""",
""".who{display:flex;background:var(--surface-2);border-radius:var(--r-pill);padding:3px;gap:2px}
.top{flex-wrap:wrap}
.netpill{flex-basis:100%;order:3;display:flex;align-items:center;justify-content:center;gap:8px;margin-top:2px;padding:5px 10px;border-radius:4px;
  background:#3b2a1e;color:#ffe9c4;font-size:.85rem;font-weight:600;box-shadow:inset 0 0 0 2px #6b4a2e}
.netpill .dot{width:8px;height:8px;border-radius:2px;background:#e8a23a;box-shadow:0 0 0 2px rgba(232,162,58,.3)}
.netpill[hidden]{display:none}""")
rep("""  applyLook();""", """  applyLook(); renderNetPill();""")

# ---------- Settings sync line ----------
rep("""${sync.status === "on" ? (sync.pending ? "Sending changes…" : `Up to date""",
    """${sync.status === "on" && sync.offline ? "Offline. Changes are saved on this phone and will sync when you're back online." : sync.status === "on" ? (sync.pending ? "Sending changes…" : `Up to date""")

open(p, "w").write(s)
print("step 16 applied")
