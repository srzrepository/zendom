"""Deletes across two phones (step 37): an entry deleted on one phone stays deleted, including when the
other phone was closed, on an older app version, or updates afterwards.
Run:  python3 tests/sync_delete_tests.py path/to/index.html path/to/older-index.html
(older build, e.g.: git show e931ce3:index.html > /tmp/old.html)

Two-phone sync checks against a stand-in server (the real Firebase can't be reached from the test machine).
Run:  python3 tests/sync_tests.py path/to/index.html
Each "phone" is its own browser context (separate storage). The stand-in replaces window.zdBackend with
the same five calls the Firebase bundle provides, backed by one shared Python dict."""
import sys, json, asyncio
from playwright.async_api import async_playwright

PAGE = sys.argv[1]; OLD = sys.argv[2]
results = []
def check(name, ok, detail=""):
    results.append((name, bool(ok))); print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail and not ok else ""))

ALLOWED = {"sam@example.com", "charliepurdomva@gmail.com"}
class Server:
    def __init__(self): self.recs = {}; self.ver = {}; self.log = []; self.writes = 0; self.down = False; self.devices = {}; self.notified = []
    def all(self): return [dict(id=k, **{x: v[x] for x in ("del", "j")}) for k, v in self.recs.items()]
    def write(self, lst, email):
        if self.down: raise Exception("unavailable: network down")
        if email not in ALLOWED: raise Exception("permission-denied: Missing or insufficient permissions.")
        for w in lst:   # like firestore.rules: only these fields may be written
            extra = set(w["data"]) - {"del", "j", "t", "by", "ts"}
            if extra: raise Exception("permission-denied: Missing or insufficient permissions. (extra fields: " + ",".join(sorted(extra)) + ")")
        for w in lst:
            self.ver[w["id"]] = self.ver.get(w["id"], 0) + 1
            self.recs[w["id"]] = {"del": w["data"]["del"], "j": w["data"]["j"], "by": email}
            self.log.append(w["id"]); self.writes += 1
    def since(self, cur):
        ids = list(dict.fromkeys(self.log[cur:]))
        return {"cur": len(self.log), "changes": [{"id": i, "del": self.recs[i]["del"], "j": self.recs[i]["j"]} for i in ids]}

FAKE = """
window.zdBackend = {
  _u: null, _cbs: [],
  onUser(cb){ this._cbs.push(cb); setTimeout(() => cb(this._u), 0); return () => {}; },
  async signIn(){ const u = {email: window.__email, name: ""}; this._u = u; this._cbs.forEach(c => c(u)); },
  async signOut(){ this._u = null; this._cbs.forEach(c => c(null)); },
  async fetchAll(){ return await window.__srvAll(); },
  async write(list){ await window.__srvWrite(list, this._u ? this._u.email : ""); },
  // like Firestore's transaction: read the server's copy, let the app merge, write the result
  async writeMerged(list, merge){ if(window.__noTx) { await this.write(list); return list.map(w => ({id: w.id, data: w.data})); }
    if(!navigator.onLine) throw Object.assign(new Error("unavailable: offline"), {code: "unavailable"});
    for(let tries = 0; tries < 8; tries++){
      const cur = await window.__srvGet(list.map(w => w.id)); const out = list.map(w => ({id: w.id, data: merge(w, cur[w.id] || null)}));
      const vers = {}; list.forEach(w => { vers[w.id] = cur[w.id] ? cur[w.id].v : 0; });
      if(await window.__srvWriteIf(out, this._u ? this._u.email : "", vers)) return out;    // someone wrote in between: read again
    }
    throw Object.assign(new Error("aborted: too much contention"), {code: "aborted"}); },
  async idToken(){ return this._u ? "tok-" + this._u.email : null; },
  push: {
    _perm: "default",
    async supported(){ return true; },
    permission(){ return this._perm; },
    async enable(v){ window.__enableCalls = (window.__enableCalls || 0) + 1; if(window.__deny){ const e = new Error("no"); e.code = "denied"; throw e; } this._perm = "granted"; return "fcm-" + window.__email; },
    async disable(){ window.__disabled = (window.__disabled || 0) + 1; },
    async saveDevice(id, d){ await window.__srvDevice(id, d); },
    async removeDevice(id){ await window.__srvDevice(id, null); },
    onForeground(){ return () => {}; }
  },
  listen(cb){ let cur = 0, busy = false; const t = setInterval(async () => { if(busy) return; busy = true;
      try { const r = await window.__srvSince(cur); cur = r.cur; if(r.changes.length) cb(r.changes); } finally { busy = false; } }, 100);
    return () => clearInterval(t); }
};
"""

async def phone(browser, srv, email, clock="2026-10-29T10:00:00-07:00", ua=None, page=None, ctx=None):
    if ctx is not None:
        pg = await ctx.new_page(); pg.errors = []; pg.ctx = ctx; pg.on("pageerror", lambda e: pg.errors.append(str(e)))
        await pg.goto("file://" + (page or PAGE)); await pg.wait_for_timeout(300); return pg
    ctx = await browser.new_context(viewport={"width": 390, "height": 844}, **({"user_agent": ua} if ua else {}))
    await ctx.route("**/fonts.g*/**", lambda r: r.abort())
    await ctx.expose_function("__srvAll", lambda: srv.all())
    def _w(lst, em):
        srv.write(lst, em)
    await ctx.expose_function("__srvWrite", _w)
    await ctx.expose_function("__srvSince", lambda cur: srv.since(cur))
    await ctx.expose_function("__srvGet", lambda ids: {i: {"del": srv.recs[i]["del"], "j": srv.recs[i]["j"], "v": srv.ver.get(i, 0)} for i in ids if i in srv.recs})
    def _wif(lst, em, vers):
        if any(srv.ver.get(i, 0) != v for i, v in vers.items()): return False
        srv.write(lst, em); return True
    await ctx.expose_function("__srvWriteIf", _wif)
    def _dev(i, d):
        if d is None: srv.devices.pop(i, None)
        else: srv.devices[i] = d
    await ctx.expose_function("__srvDevice", _dev)
    async def _notify(route):
        b = json.loads(route.request.post_data or "{}"); b["_ct"] = route.request.headers.get("content-type", ""); srv.notified.append(b)
        await route.fulfill(status=200, content_type="application/json", body=json.dumps({"sent": 1, "gone": 0}))
    await ctx.route("https://notify.test/**", _notify)
    await ctx.add_init_script(f"window.__email = {json.dumps(email)};" + FAKE)
    pg = await ctx.new_page(); pg.errors = []; pg.ctx = ctx
    pg.on("pageerror", lambda e: pg.errors.append(str(e)))
    await pg.goto("file://" + (page or PAGE)); await pg.wait_for_timeout(300)
    return pg

async def ev(pg, js): return await pg.evaluate(js)
async def settle(*pgs, ms=900):
    for pg in pgs: await pg.wait_for_timeout(ms // len(pgs))


SEED = """(() => { state.budget.txns.push(
  {id:'keep', kind:'expense', amount:360000, date:'2026-10-30', categoryId:null, paidBy:'charlie', shared:true, note:'Rent & utilities', billId:null},
  {id:'dupe', kind:'expense', amount:360000, date:'2026-10-30', categoryId:null, paidBy:'charlie', shared:false, note:'Rent', billId:null}); save(); })()"""
async def scenario(b, name, a_page, b_page, b_reopen_page, b_closed):
    srv = Server()
    A = await phone(b, srv, "sam@example.com", page=a_page)
    await ev(A, "ACTIONS.syncIn()"); await settle(A)
    await ev(A, SEED); await settle(A)
    B = await phone(b, srv, "charliepurdomva@gmail.com", page=b_page)
    await ev(B, "ACTIONS.syncIn()"); await settle(A, B, ms=1600)
    ok0 = await ev(B, "state.budget.txns.some(t => t.id === 'dupe')")
    ctxB = B.ctx
    if b_closed: await B.close()
    await ev(A, "removeBy(state.budget.txns, 'dupe'); save()"); await settle(A, ms=1200)
    if b_closed:
        B = await phone(b, srv, "charliepurdomva@gmail.com", page=b_reopen_page, ctx=ctxB)
        await ev(B, "ACTIONS.syncIn()")
    await settle(A, B, ms=2500)
    srv_del = srv.recs.get("txn~dupe", {}).get("del")
    a_has = await ev(A, "state.budget.txns.some(t => t.id === 'dupe')"); b_has = await ev(B, "state.budget.txns.some(t => t.id === 'dupe')")
    check(f"deleted entry stays deleted: {name}", ok0 and srv_del and not a_has and not b_has and not A.errors and not B.errors, f"server del={srv_del} sam={a_has} charlie={b_has}")
    await A.ctx.close(); await ctxB.close()

async def both_editing(b):
    srv = Server()
    A = await phone(b, srv, "sam@example.com"); await ev(A, "ACTIONS.syncIn()"); await settle(A)
    await ev(A, "state.budget.txns.push({id:'x', kind:'expense', amount:5000, date:'2026-10-29', categoryId:null, paidBy:'sam', shared:true, note:'Groceries', billId:null}); state.chores.push({id:'cx', title:'Vacuum', owner:'sam', freq:'weekly', everyDays:null, start:'2026-10-29', lastDone:null, history:[], done:false, standard:'', cpe:{c:'',p:'',e:''}, example:false}); save()"); await settle(A)
    B = await phone(b, srv, "charliepurdomva@gmail.com"); await ev(B, "ACTIONS.syncIn()"); await settle(A, B, ms=1600)
    # Sam opens the entry; Charlie changes the amount; Sam changes only the note and saves
    await ev(A, "ACTIONS.tab('budget'); ACTIONS.editTxn('x')")
    await ev(B, "state.budget.txns.find(t => t.id === 'x').amount = 9900; save()"); await settle(A, B, ms=1500)
    await ev(A, "document.querySelector('#tnote').value = 'Groceries + wine'; document.querySelector('#sheetForm').requestSubmit()"); await settle(A, B, ms=2400)
    a = await ev(A, "JSON.stringify(state.budget.txns.find(t => t.id === 'x'), ['note','amount'])"); bb = await ev(B, "JSON.stringify(state.budget.txns.find(t => t.id === 'x'), ['note','amount'])")
    check("both editing: an open form keeps the other person's change (note from Sam, amount from Charlie)", a == bb == '{"note":"Groceries + wine","amount":9900}', f"{a} {bb}")
    # both change the same field: the one who saves last wins, and is told
    await ev(A, "ACTIONS.editTxn('x')")
    await ev(B, "state.budget.txns.find(t => t.id === 'x').note = 'Charlie note'; save()"); await settle(A, B, ms=1500)
    await ev(A, "document.querySelector('#tnote').value = 'Sam note'; document.querySelector('#sheetForm').requestSubmit()"); await settle(A, B, ms=2600)
    check("both editing: same field changed on both: the later save is kept everywhere", await ev(B, "state.budget.txns.find(t => t.id === 'x').note") == "Sam note")
    check("both editing: and the person saving is told the other had changed it", "had changed this too" in await ev(A, "document.body.innerText"))
    # a chore form open while the other ticks it off: the tick stays
    await ev(A, "ACTIONS.tab('chores'); ACTIONS.editChore('cx')")
    await ev(B, "toggleChore('cx')"); await settle(A, B, ms=1500)
    await ev(A, "document.querySelector('#sheetForm #title').value = 'Vacuum the rug'; document.querySelector('#sheetForm').requestSubmit()"); await settle(A, B, ms=2400)
    c = await ev(B, "JSON.stringify(state.chores.find(c => c.id === 'cx'), ['title','lastDone'])")
    check("both editing: renaming a chore keeps the other person's tick", '"title":"Vacuum the rug"' in c and '"lastDone":"2026-10-' in c, c)
    check("both editing: no page errors", not A.errors and not B.errors, "; ".join(A.errors + B.errors))
    await A.ctx.close(); await B.ctx.close()

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        await scenario(b, "both open, new build", PAGE, PAGE, None, False)
        await scenario(b, "Charlie's app closed, reopens", PAGE, PAGE, PAGE, True)
        await scenario(b, "Charlie on old build, reopens old", PAGE, OLD, OLD, True)
        await scenario(b, "Charlie on old build, reopens NEW build", PAGE, OLD, PAGE, True)
        await scenario(b, "Sam on old build deletes, Charlie new", OLD, PAGE, PAGE, True)
        await both_editing(b)
        await b.close()
    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)} of {len(results)} two-phone checks passed"); sys.exit(1 if failed else 0)
asyncio.run(main())
