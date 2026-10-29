"""Step 5: sync between phones through Firebase (no stored-data format change; schema stays 8).
Each chore, note, recipe, ... becomes one record "kind~id" holding its JSON. Usage: python3 patch_step5_sync.py file.html"""
import sys
p = sys.argv[1]; s = open(p).read()
def rep(old, new):
    global s
    assert s.count(old) == 1, (s.count(old), old[:90])
    s = s.replace(old, new)

SYNC = r'''
/* ============================================================
   SYNC between phones (Firebase, through window.zdBackend)
   The app always works from this phone's copy. When the website
   version is signed in, every chore, note, recipe, bill… is also a
   record "kind~id" in the shared database, so two phones merge item
   by item. Records are compared by a short hash of their JSON.
   ============================================================ */
const SYNC_KEY = "zendom:sync";                       // this phone only: {last:{key:hash|null}, ever}
const ACCOUNTS = {sam:[], charlie:[]};                // Google emails, lowercase: picks who's using
const SYNC_LISTS = [
  ["chore", st => st.chores], ["note", st => st.notes], ["recipe", st => st.recipes], ["meal", st => st.meals],
  ["grocery", st => st.grocery], ["pantry", st => st.pantry], ["event", st => st.events],
  ["bcat", st => st.budget.categories], ["txn", st => st.budget.txns], ["bill", st => st.budget.bills],
  ["fgoal", st => st.budget.fund.goals], ["fentry", st => st.budget.fund.entries]
];
function syncHash(str){ let h1 = 0xdeadbeef, h2 = 0x41c6ce57; for(let i = 0; i < str.length; i++){ const c = str.charCodeAt(i); h1 = Math.imul(h1 ^ c, 2654435761); h2 = Math.imul(h2 ^ c, 1597334677); }
  h1 = Math.imul(h1 ^ (h1 >>> 16), 2246822507) ^ Math.imul(h2 ^ (h2 >>> 13), 3266489909); h2 = Math.imul(h2 ^ (h2 >>> 16), 2246822507) ^ Math.imul(h1 ^ (h1 >>> 13), 3266489909);
  return (h2 >>> 0).toString(36) + (h1 >>> 0).toString(36); }
function recordsOf(st){
  const m = {};
  SYNC_LISTS.forEach(([k, get]) => get(st).forEach(x => { m[k + "~" + x.id] = x; }));
  PEOPLE.forEach(k => { m["person~" + k] = st.people[k]; });
  m["one~settings"] = st.settings;
  m["one~budget"] = {pigName: st.budget.pigName, venmo: st.budget.venmo};
  m["one~fund"] = {name: st.budget.fund.name};
  Object.entries(st.budget.plan).forEach(([mo, v]) => { m["plan~" + mo] = v; });
  return m;
}
function recordHashes(st){ const m = recordsOf(st), out = {}; for(const k in m) out[k] = syncHash(JSON.stringify(m[k])); return out; }
// data null = deleted. Unknown kinds are ignored (a newer app version may add some).
function applyRecord(st, key, data){
  const i = key.indexOf("~"); if(i < 1) return; const kind = key.slice(0, i), id = key.slice(i + 1);
  const L = SYNC_LISTS.find(x => x[0] === kind);
  if(L){ const arr = L[1](st), j = arr.findIndex(x => x.id === id);
    if(data === null || typeof data !== "object"){ if(j >= 0) arr.splice(j, 1); return; }
    const v = Object.assign({}, data, {id}); if(j >= 0) arr[j] = v; else arr.push(v); return; }
  if(kind === "plan" && /^\d{4}-\d{2}$/.test(id)){ if(data && typeof data === "object") st.budget.plan[id] = data; else delete st.budget.plan[id]; return; }
  if(!data || typeof data !== "object") return;                 // the singletons below are never deleted
  if(kind === "person" && PEOPLE.includes(id)) st.people[id] = data;
  else if(kind === "one" && id === "settings") st.settings = data;
  else if(kind === "one" && id === "budget"){ st.budget.pigName = data.pigName; st.budget.venmo = data.venmo; }
  else if(kind === "one" && id === "fund") st.budget.fund.name = data.name;
}
function emptyHousehold(){
  const d = defaults();
  d.budget.categories = []; d.budget.txns = []; d.budget.bills = []; d.budget.plan = {}; d.budget.fund.goals = []; d.budget.fund.entries = [];
  return d;
}
const sync = {status:"off", user:null, err:"", last:{}, ever:false, unsub:null, timer:0, at:0, pending:0};
function syncLoad(){ try { const o = JSON.parse(lsGet(SYNC_KEY) || "{}"); sync.last = (o.last && typeof o.last === "object") ? o.last : {}; sync.ever = !!o.ever; } catch(e){} }
function syncStore(){ lsSet(SYNC_KEY, JSON.stringify({last:sync.last, ever:sync.ever})); }
function syncSchedule(){ if(sync.status !== "on") return; clearTimeout(sync.timer); sync.timer = setTimeout(syncFlush, 400); }
function syncSetStatus(st, err){ sync.status = st; sync.err = err || ""; if(prefs.tab === "more" && prefs.moreTab === "settings" && !$("#sheetRoot").innerHTML) render(); }
// Push every record that changed since the last sync. Returns the number of writes.
function syncFlush(){
  const be = window.zdBackend; if(!be || sync.status !== "on") return 0;
  const cur = recordsOf(state), writes = [], by = sync.user ? sync.user.email : "";
  for(const k in cur){ const j = JSON.stringify(cur[k]), h = syncHash(j); if(sync.last[k] !== h){ writes.push({id:k, data:{del:false, j, t:Date.now(), by}}); sync.last[k] = h; } }
  for(const k in sync.last){ if(!(k in cur) && sync.last[k] !== null){ writes.push({id:k, data:{del:true, j:"", t:Date.now(), by}}); sync.last[k] = null; } }
  if(!writes.length) return 0;
  syncStore(); sync.pending++;
  be.write(writes).then(() => { sync.pending--; sync.at = Date.now(); if(sync.status === "on") syncSetStatus("on"); })
    .catch(e => { sync.pending--; writes.forEach(w => { if(w.data.del) sync.last[w.id] = "resend"; else delete sync.last[w.id]; }); syncStore(); syncSetStatus("error", syncErrText(e)); });
  return writes.length;
}
function syncErrText(e){
  const c = e && (e.code || ""), m = String(e && e.message || e || "");
  if(/permission/i.test(c + m)) return "This Google account isn't allowed into your zen·dom yet. Sign in with the account you gave Claude, or ask to have this one added.";
  if(/unavailable|offline|network/i.test(c + m)) return "Couldn't reach the internet. Changes are kept on this phone and will sync when you're back online.";
  if(/popup-closed|cancelled-popup/i.test(c + m)) return "Sign-in was closed before it finished.";
  if(/popup-blocked/i.test(c + m)) return "The browser blocked the sign-in window. Allow pop-ups for this site, then tap Sign in again.";
  if(/unauthorized-domain/i.test(c + m)) return "This web address isn't on Firebase's allowed list yet (Authentication → Settings → Authorized domains).";
  return "Sync stopped: " + m.slice(0, 140);
}
// Changes from the other phone. A record this phone changed but hasn't sent yet stays as it is here (it's about to win).
function syncRemote(changes){
  if(sync.status !== "on") return;
  const curH = recordHashes(state), applied = [];
  changes.forEach(c => {
    const h = c.del ? null : syncHash(c.j);
    if(sync.last[c.id] === h) return;                                   // already have it (often our own echo)
    const lastH = sync.last[c.id], localH = curH[c.id];
    const unsent = lastH === undefined ? localH !== undefined : (localH === undefined ? null : localH) !== lastH;
    if(unsent) return;                                                  // this phone's newer edit wins and is about to be sent
    let data = null; if(!c.del){ try { data = JSON.parse(c.j); } catch(e){ return; } }
    applyRecord(state, c.id, data); applied.push(c.id);
  });
  if(!applied.length) return;
  state = normalize(state);
  const after = recordHashes(state);
  applied.forEach(k => { sync.last[k] = k in after ? after[k] : null; });
  syncStore(); lsSet(KEY, JSON.stringify(state)); sync.at = Date.now();
  render();
}
async function syncStart(user){
  const be = window.zdBackend; if(!be) return;
  sync.user = user;
  const who = Object.keys(ACCOUNTS).find(k => ACCOUNTS[k].includes(user.email));
  if(who && prefs.user !== who){ prefs.user = who; savePrefs(); }
  syncSetStatus("connecting");
  try {
    if(!sync.ever){
      const docs = await be.fetchAll();
      if(docs.some(d => !d.del)){
        // someone already set up the shared household: this phone joins it instead of uploading its own copy
        backupRaw("before-first-sync", JSON.stringify(state));
        const st = emptyHousehold();
        docs.forEach(d => { if(d.del) return; try { applyRecord(st, d.id, JSON.parse(d.j)); } catch(e){} });
        state = normalize(st);
        notices.push("This phone now shows your shared household. What was on it before was kept as a safety copy in More → Settings → Backup.");
      }
      const h = recordHashes(state); sync.last = {};
      docs.forEach(d => { sync.last[d.id] = d.del ? null : (h[d.id] || null); });
      sync.ever = true; syncStore(); lsSet(KEY, JSON.stringify(state));
    }
    if(sync.unsub) sync.unsub();
    sync.status = "on";
    sync.unsub = be.listen(syncRemote, e => syncSetStatus("error", syncErrText(e)));
    syncFlush(); sync.at = Date.now(); syncSetStatus("on"); render();
  } catch(e){ syncSetStatus("error", syncErrText(e)); }
}
function syncStopped(){ if(sync.unsub){ sync.unsub(); sync.unsub = null; } clearTimeout(sync.timer); sync.user = null; syncSetStatus("off"); }
function syncSection(){
  const be = window.zdBackend;
  let body;
  if(!be) body = `<p class="small" style="margin:0">Sharing between phones works on the zen·dom website. In this copy, everything stays on this device.</p>`;
  else if(!sync.user) body = `<p class="small" style="margin:0">Sign in with Google on both phones and you'll each see the other's changes. Nothing leaves this phone until you sign in.</p>
    <div class="actions"><button type="button" class="btn small" data-act="syncIn">Sign in with Google</button></div>`;
  else body = `<p class="small" style="margin:0">Signed in as <b>${esc(sync.user.email)}</b>.</p>
    <p class="small" style="margin:0">${sync.status === "on" ? (sync.pending ? "Sending changes…" : `Up to date${sync.at ? " · " + new Date(sync.at).toLocaleTimeString(undefined, {hour:"numeric", minute:"2-digit"}) : ""}`) : sync.status === "connecting" ? "Connecting…" : "Not syncing right now."}</p>
    <div class="actions"><button type="button" class="btn ghost small" data-act="syncOut">Sign out</button></div>`;
  return `<section class="sec"><span class="label">Share between phones</span>
    <div class="card" style="display:flex;flex-direction:column;gap:10px">${body}
      ${sync.err ? `<p class="small" role="alert" style="margin:0;color:var(--late)">${esc(sync.err)}</p>` : ""}
      <p class="small muted" style="margin:0">Recipe photos and PDFs stay on the phone that added them.</p></div></section>`;
}
'''
rep('''/* ---------- boot ---------- */''', SYNC + '''
/* ---------- boot ---------- */''')
# every save also schedules a sync
rep('''function save(){
  if(!lsSet(KEY, JSON.stringify(state))){
    if(!notices.includes(NOSAVE)){ notices.push(NOSAVE); renderBanners(); }
    return false;
  }
  return true;
}''', '''function save(){
  if(!lsSet(KEY, JSON.stringify(state))){
    if(!notices.includes(NOSAVE)){ notices.push(NOSAVE); renderBanners(); }
    if(typeof syncSchedule === "function") syncSchedule();
    return false;
  }
  if(typeof syncSchedule === "function") syncSchedule();
  return true;
}''')
rep('''function viewSettings(){
  return `${lookSection()}''', '''function viewSettings(){
  return `${syncSection()}
  ${lookSection()}''')
rep('''Object.assign(ACTIONS, IMPORT_ACTIONS, { jeffSettings: () => jeffSettingsForm() });''',
'''Object.assign(ACTIONS, IMPORT_ACTIONS, { jeffSettings: () => jeffSettingsForm() });
Object.assign(ACTIONS, {
  syncIn: async () => { const be = window.zdBackend; if(!be) return; sync.err = ""; try { await be.signIn(); } catch(e){ syncSetStatus("off", syncErrText(e)); } },
  syncOut: async () => { const be = window.zdBackend; if(!be) return; try { await be.signOut(); } catch(e){} syncStopped(); toast("Signed out. Everything stays on this phone."); }
});''')
rep('''initKitchenInputs();
load();
render();''', '''initKitchenInputs();
load();
syncLoad();
render();
if(window.zdBackend) window.zdBackend.onUser(u => { if(u) syncStart(u); else syncStopped(); });''')
# a restore from backup replaces everything: push it as the new shared version
rep('''    state = v < SCHEMA ? migrate(parsed, v) : normalize(parsed);
    save(); closeSheet(); render(); toast("Backup restored");''',
'''    state = v < SCHEMA ? migrate(parsed, v) : normalize(parsed);
    save(); closeSheet(); render(); toast(sync.status === "on" ? "Backup restored and shared" : "Backup restored");''')
open(p, 'w').write(s)
print("patched", p)
