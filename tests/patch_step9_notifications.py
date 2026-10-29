"""Step 9: opt-in notifications (instant updates from the other person + morning summary).
Nothing is sent or asked until someone turns a switch on in More -> Settings, on that phone.
No household-data change (devices live in their own Firestore collection). Usage: python3 patch_step9_notifications.py file.html"""
import sys
p = sys.argv[1]; s = open(p).read()
def rep(old, new):
    global s
    assert s.count(old) == 1, (s.count(old), old[:90])
    s = s.replace(old, new)

CODE = r'''
/* ============================================================
   NOTIFICATIONS (opt in, per phone)
   Instant: after this phone sends changes, it describes them in a
   few words and asks the zen·dom notifier (a small Cloudflare
   Worker) to tell the other person's opted-in phones.
   Morning summary: a scheduled GitHub job; this file only stores
   the choice. Health and money changes are described vaguely.
   ============================================================ */
const NOTIFY = {url:"https://zendom-notify.samzenteno.workers.dev", vapid:"BPVl07O4Ja1gqAK0P9tMrbb7cS2QSea97_PkE5JGfHl3gDuVO5DSdn0jy9QMWFMPOjHFMXE2qMDyisX_H6LCNr4"};                    // filled in once setup is finished
const PUSH_KEY = "zendom:push";                       // this phone only: {id, token, instant, morning}
const pushState = {supported:null, busy:false, err:"", note:""};
const IS_IOS = /iPad|iPhone|iPod/.test(navigator.userAgent) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
const IS_STANDALONE = (window.matchMedia && matchMedia("(display-mode: standalone)").matches) || navigator.standalone === true;
function pushLoad(){ try { const o = JSON.parse(lsGet(PUSH_KEY) || "null"); return o && typeof o === "object" ? o : null; } catch(e){ return null; } }
function pushStore(o){ if(o) lsSet(PUSH_KEY, JSON.stringify(o)); else { try { localStorage.removeItem(PUSH_KEY); } catch(e){} } }
const clip = (t, n) => { const a = Array.from(String(t || "").trim()); return a.length > n ? a.slice(0, n - 1).join("") + "…" : a.join(""); };
// A few words about one changed record, or null if it isn't worth a notification.
function describeChange(key, o, n){
  const i = key.indexOf("~"), kind = key.slice(0, i), t = todayStr();
  if(kind === "chore"){
    if(!n) return o ? `removed the chore “${clip(o.title, 40)}”` : null;
    if(!o) return `added a chore: ${clip(n.title, 40)}`;
    if((n.lastDone === t && o.lastDone !== t) || (n.done && !o.done)) return `finished “${clip(n.title, 40)}”`;
    if(o.lastDone === t && n.lastDone !== t) return null;                       // un-ticked
    if(n.owner && n.owner !== o.owner) return `handed “${clip(n.title, 40)}” to ${nameOf(n.owner)}`;
    return null;
  }
  if(kind === "note"){
    if(!n || !o){ if(!n) return null; return n.drawing && !n.text ? "drew you a note" : `left a note: “${clip(n.text, 60)}”`; }
    if((n.replies || []).length > (o.replies || []).length){ const r = n.replies[n.replies.length - 1]; return `replied to a note: “${clip(r && r.text, 50)}”`; }
    if((n.reactions || []).length > (o.reactions || []).length){ const r = n.reactions[n.reactions.length - 1]; return `reacted ${r ? r.emoji : ""} to a note`.replace("  ", " "); }
    return null;
  }
  if(kind === "grocery"){ if(!n) return null; if(!o) return `added ${clip(n.name, 30)} to the grocery list`; if(n.checked && !o.checked) return `got ${clip(n.name, 30)}`; return null; }
  if(kind === "meal"){ if(!n || o) return null; const d = parse(n.date).toLocaleDateString(undefined, {weekday:"long"}); return `planned ${SLOTS[n.slot].toLowerCase()} for ${d}: ${clip(mealLabel(n), 30)}`; }
  if(kind === "event"){
    if(!n) return o ? `removed “${clip(o.title, 40)}” from the calendar` : null;
    if(!o) return `added “${clip(n.title, 40)}” on ${niceDate(n.date)}`;
    if(n.date !== o.date || n.time !== o.time) return `moved “${clip(n.title, 40)}” to ${niceDate(n.date)}${n.time ? " · " + fmtTime(n.time) : ""}`;
    return null;
  }
  if(kind === "recipe"){ if(!n) return null; if(!o) return `added a recipe: ${clip(n.title, 40)}`; if((n.cooked || []).length > (o.cooked || []).length) return `made ${clip(n.title, 40)}`; return null; }
  if(kind === "txn"){ if(!n || o) return null; return n.kind === "settle" ? "settled up" : n.kind === "income" ? "logged income" : "logged spending"; }
  if(kind === "bill"){ if(!n) return null; if(!o) return `added a bill: ${clip(n.name, 30)}`; if(n.nextDue > o.nextDue) return `paid ${clip(n.name, 30)}`; return null; }
  if(kind === "fentry"){ if(!n || o) return null; return n.kind === "in" ? "added money to the Fun Fund" : n.kind === "out" ? "took money out of the Fun Fund" : null; }
  if(kind === "fgoal"){ if(!n || o) return null; return `started a Fun Fund goal: ${clip(n.name, 30)}`; }
  if(kind === "person"){ if(!n || !o || JSON.stringify(n) === JSON.stringify(o)) return null; return `updated ${n.name}'s profile`; }
  return null;
}
const notifyQ = {items:[], timer:0};
// Notes go out right away; anything else offers a small "Tell Charlie?" pop-up and only sends if tapped.
function notifyCollect(writes, cur){
  if(!sync.shadow) return;
  const nudges = [];
  writes.forEach(w => {
    const before = sync.shadow[w.id];
    let o = null; try { o = before ? JSON.parse(before) : null; } catch(e){}
    const n = w.data.del ? null : cur[w.id];
    const d = NOTIFY.url && sync.user ? describeChange(w.id, o, n) : null;
    if(d){ if(w.id.startsWith("note~")) notifyQ.items.push(d); else nudges.push(d); }
    if(w.data.del) delete sync.shadow[w.id]; else sync.shadow[w.id] = w.data.j;
  });
  if(notifyQ.items.length){ clearTimeout(notifyQ.timer); notifyQ.timer = setTimeout(() => notifySend(false), 1500); }
  if(nudges.length) showNudge(nudges);
}
let nudgeTimer;
function showNudge(items){
  notifyQ.nudge = (notifyQ.nudge && $("#nudgeRoot").innerHTML ? notifyQ.nudge : []).concat(items);
  const other = nameOf(other_(sync.who || prefs.user));
  $("#nudgeRoot").innerHTML = `<div class="nudge" role="status"><span>Tell ${esc(other)}?</span><button type="button" class="btn small" data-act="nudgeSend">Notify</button><button type="button" class="nx" data-act="nudgeClose" aria-label="No, don't tell ${esc(other)}">✕</button></div>`;
  clearTimeout(nudgeTimer); nudgeTimer = setTimeout(() => { $("#nudgeRoot").innerHTML = ""; notifyQ.nudge = null; }, 9000);
}
function notifyBody(items){
  const who = nameOf(sync.who || prefs.user), u = [...new Set(items)];
  return clip(u.length === 1 ? `${who} ${u[0]}` : `${who} ${u[0]}, and ${u.length - 1} more`, 178);
}
async function notifySend(leaving, items){
  if(!items){ clearTimeout(notifyQ.timer); items = notifyQ.items; notifyQ.items = []; }
  if(!items.length || !NOTIFY.url || !sync.user) return null;
  const body = notifyBody(items);
  try {
    const idToken = sync.idTok || await window.zdBackend.idToken(); if(!idToken) return;
    // text/plain keeps this a simple request, so it still goes out when the app is being closed
    const r = await fetch(NOTIFY.url.replace(/\/$/, "") + "/notify", {method:"POST", keepalive: !!leaving, headers:{"Content-Type":"text/plain"}, body: JSON.stringify({idToken, title:"zen·dom", body})});
    return await r.json().catch(() => ({}));
  } catch(e){ return null; }
}
document.addEventListener("visibilitychange", () => { if(document.visibilityState === "hidden") notifySend(true); });
async function pushPrepare(){
  const be = window.zdBackend; if(!be || !be.push) return;
  if(pushState.supported === null){ pushState.supported = await be.push.supported(); if(prefs.tab === "more" && prefs.moreTab === "settings") render(); }
  const pu = pushLoad();
  if(pu && sync.user && NOTIFY.vapid && be.push.permission() === "granted"){
    try {   // tokens can change: keep the saved one current
      const token = await be.push.enable(NOTIFY.vapid);
      if(token && token !== pu.token){ try { await be.push.removeDevice(pu.id); } catch(e){}
        const id = syncHash(token) + syncHash(token.split("").reverse().join(""));
        await be.push.saveDevice(id, {owner:sync.user.email, token, instant:!!pu.instant, morning:!!pu.morning, kind: IS_IOS ? "iPhone" : "other"});
        pushStore(Object.assign({}, pu, {id, token})); }
    } catch(e){}
    be.push.onForeground(m => { const n = m && (m.notification || m.data) || {}; if(n.body) toast(n.body); });
  }
}
// Turn one switch on or off for this phone. Called straight from the tap so iPhone shows its prompt.
async function pushSet(which, on){
  const be = window.zdBackend; if(!be || !be.push || pushState.busy) return;
  const pu = pushLoad() || {instant:false, morning:false};
  const next = Object.assign({}, pu, {[which]: !!on});
  pushState.busy = true; pushState.err = ""; pushState.note = "";
  try {
    if(next.instant || next.morning){
      let token = next.token, id = next.id;
      if(!token){ token = await be.push.enable(NOTIFY.vapid); id = syncHash(token) + syncHash(token.split("").reverse().join("")); }
      await be.push.saveDevice(id, {owner:sync.user.email, token, instant:!!next.instant, morning:!!next.morning, kind: IS_IOS ? "iPhone" : "other"});
      pushStore({id, token, instant:!!next.instant, morning:!!next.morning});
      pushState.note = on ? "On for this phone." : "Saved.";
    } else {
      if(next.id){ try { await be.push.removeDevice(next.id); } catch(e){} }
      await be.push.disable(); pushStore(null); pushState.note = "Notifications are off for this phone.";
    }
  } catch(e){
    pushState.err = e && e.code === "denied"
      ? (IS_IOS ? "Notifications are blocked for zen·dom. To allow them: iPhone Settings → Notifications → zen·dom." : "Notifications are blocked for this site. Allow them in the browser's site settings, then try again.")
      : "Couldn't turn that on: " + clip(e && e.message || e, 120);
  }
  pushState.busy = false; render();
}
async function pushTest(){
  const be = window.zdBackend; if(!be || !NOTIFY.url) return;
  try {
    const idToken = await be.idToken();
    const r = await fetch(NOTIFY.url.replace(/\/$/, "") + "/notify", {method:"POST", headers:{"Content-Type":"text/plain"}, body: JSON.stringify({idToken, test:true, title:"zen·dom", body:"Test: notifications work on this phone."})});
    const j = await r.json().catch(() => ({}));
    toast(r.ok ? (j.sent ? "Test sent. It should arrive in a few seconds." : "The notifier found no phones of yours to send to.") : "The notifier said no: " + clip(j.error || r.status, 60));
  } catch(e){ toast("Couldn't reach the notifier."); }
}
function notifySection(){
  const be = window.zdBackend;
  if(!be || !be.push) return "";
  const pu = pushLoad() || {}, other = nameOf(other_(sync.who || prefs.user));
  let body;
  if(!NOTIFY.vapid || !NOTIFY.url) body = `<p class="small" style="margin:0">Notifications are almost ready. They can be switched on here once setup is finished.</p>`;
  else if(!sync.user) body = `<p class="small" style="margin:0">Sign in above first. Notifications go to the phones you choose.</p>`;
  else if(IS_IOS && !IS_STANDALONE) body = `<p class="small" style="margin:0">On iPhone, notifications only work in the Home Screen app. Open zen·dom from its icon and turn them on there.</p>`;
  else if(pushState.supported === false) body = `<p class="small" style="margin:0">This browser can't show notifications.</p>`;
  else body = `
    <label class="setrow" style="cursor:pointer"><span><b>Notes and nudges from ${esc(other)}</b><span class="small muted" style="display:block">New notes and replies right away, plus anything ${esc(other)} taps “Notify” on.</span></span>
      <input type="checkbox" data-change="pushPref" data-id="instant" ${pu.instant ? "checked" : ""} ${pushState.busy ? "disabled" : ""} style="width:26px;height:26px;accent-color:var(--accent)"></label>
    <label class="setrow" style="cursor:pointer"><span><b>Morning reminders</b><span class="small muted" style="display:block">Around 8:30 am: what's due today for both of you, and anything overdue.</span></span>
      <input type="checkbox" data-change="pushPref" data-id="morning" ${pu.morning ? "checked" : ""} ${pushState.busy ? "disabled" : ""} style="width:26px;height:26px;accent-color:var(--accent)"></label>
    <p class="small muted" style="margin:0">Both are off until you turn them on, and only for this phone. ${esc(other)} chooses for theirs.</p>
    ${pu.id ? `<div class="actions" style="justify-content:flex-start"><button type="button" class="btn ghost small" data-act="pushTest">Send a test</button></div>` : ""}`;
  return `<section class="sec"><span class="label">Notifications</span>
    <div class="card" style="display:flex;flex-direction:column;gap:12px">${body}
      ${pushState.note && !pushState.err ? `<p class="small" role="status" style="margin:0">${esc(pushState.note)}</p>` : ""}
      ${pushState.err ? `<p class="small" role="alert" style="margin:0;color:var(--late)">${esc(pushState.err)}</p>` : ""}</div></section>`;
}
const other_ = k => k === "charlie" ? "sam" : "charlie";
'''
rep('''/* ---------- boot ---------- */''', CODE + '''
/* ---------- boot ---------- */''')
rep('''function viewSettings(){
  return `${syncSection()}''', '''function viewSettings(){
  return `${syncSection()}
  ${notifySection()}''')
rep('''<div id="toastRoot"></div>''', '''<div id="toastRoot"></div>
<div id="nudgeRoot"></div>''')
rep('''\n</style>\n''', '''
.nudge{position:fixed;left:50%;transform:translateX(-50%);bottom:calc(205px + env(safe-area-inset-bottom,0px));z-index:31;display:flex;align-items:center;gap:10px;
  background:var(--surface);color:var(--ink);border:3px solid var(--wood-dark,#4a2610);border-radius:6px;box-shadow:4px 4px 0 rgba(0,0,0,.25);padding:8px 8px 8px 14px;font-weight:600;white-space:nowrap}
.nudge .nx{border:0;background:transparent;color:var(--muted);width:36px;height:36px;font-size:1rem}
</style>
''')
# remember what was last sent, so changes can be described
rep('''  if(!writes.length) return 0;
  syncStore(); sync.pending++;''', '''  if(!writes.length) return 0;
  if(typeof notifyCollect === "function") notifyCollect(writes, cur);
  syncStore(); sync.pending++;''')
rep('''  applied.forEach(k => { sync.last[k] = k in after ? after[k] : null; });''',
    '''  applied.forEach(k => { sync.last[k] = k in after ? after[k] : null; });
  if(sync.shadow){ const cur = recordsOf(state); applied.forEach(k => { if(k in cur) sync.shadow[k] = JSON.stringify(cur[k]); else delete sync.shadow[k]; }); }''')
rep('''    if(sync.unsub) sync.unsub();
    sync.status = "on";''', '''    if(sync.unsub) sync.unsub();
    sync.who = who || null;
    { const cur = recordsOf(state); sync.shadow = {}; for(const k in cur) sync.shadow[k] = JSON.stringify(cur[k]); }
    try { sync.idTok = await be.idToken(); } catch(e){}
    sync.status = "on";''')
rep('''    syncFlush(); sync.at = Date.now(); syncSetStatus("on"); render();''',
    '''    syncFlush(); sync.at = Date.now(); syncSetStatus("on"); render();
    pushPrepare();''')
rep('''  syncOut: async () => { const be = window.zdBackend; if(!be) return; try { await be.signOut(); } catch(e){} syncStopped(); toast("Signed out. Everything stays on this phone."); }''',
    '''  syncOut: async () => { const be = window.zdBackend; if(!be) return;
    const pu = pushLoad(); if(pu && pu.id && be.push){ try { await be.push.removeDevice(pu.id); await be.push.disable(); } catch(e){} pushStore(null); }
    try { await be.signOut(); } catch(e){} syncStopped(); toast("Signed out. Everything stays on this phone."); },
  pushTest: () => pushTest(),
  nudgeClose: () => { clearTimeout(nudgeTimer); $("#nudgeRoot").innerHTML = ""; notifyQ.nudge = null; },
  nudgeSend: async () => { const items = notifyQ.nudge || []; clearTimeout(nudgeTimer); $("#nudgeRoot").innerHTML = ""; notifyQ.nudge = null;
    const other = nameOf(other_(sync.who || prefs.user)), r = await notifySend(false, items);
    toast(!r ? "Couldn't reach the notifier." : r.sent ? `${other} was notified` : `${other} hasn't turned on notifications yet`); }''')
rep('''  if(el.dataset.change === "rsort"){ ACTIONS.rsort(el.value); }''', '''  if(el.dataset.change === "rsort"){ ACTIONS.rsort(el.value); }
  if(el.dataset.change === "pushPref" && (el.dataset.id === "instant" || el.dataset.id === "morning")) pushSet(el.dataset.id, el.checked);''')
# id tokens expire after an hour: refresh quietly
rep('''if(window.zdBackend) window.zdBackend.onUser(u => { if(u) syncStart(u); else syncStopped(); });''',
    '''if(window.zdBackend) window.zdBackend.onUser(u => { if(u) syncStart(u); else syncStopped(); });
setInterval(async () => { if(sync.user && window.zdBackend){ try { sync.idTok = await window.zdBackend.idToken(); } catch(e){} } }, 20 * 60000);
if(window.zdBackend && window.zdBackend.push) pushPrepare();''')
open(p, 'w').write(s)
print("patched", p)
