"""Two-phone sync checks against a stand-in server (the real Firebase can't be reached from the test machine).
Run:  python3 tests/sync_tests.py path/to/index.html
Each "phone" is its own browser context (separate storage). The stand-in replaces window.zdBackend with
the same five calls the Firebase bundle provides, backed by one shared Python dict."""
import sys, json, asyncio
from playwright.async_api import async_playwright

PAGE = sys.argv[1]
results = []
def check(name, ok, detail=""):
    results.append((name, bool(ok))); print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail and not ok else ""))

ALLOWED = {"sam@example.com", "charliepurdomva@gmail.com"}
class Server:
    def __init__(self): self.recs = {}; self.log = []; self.writes = 0; self.down = False
    def all(self): return [dict(id=k, **{x: v[x] for x in ("del", "j")}) for k, v in self.recs.items()]
    def write(self, lst, email):
        if self.down: raise Exception("unavailable: network down")
        if email not in ALLOWED: raise Exception("permission-denied: Missing or insufficient permissions.")
        for w in lst:
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
  listen(cb){ let cur = 0, busy = false; const t = setInterval(async () => { if(busy) return; busy = true;
      try { const r = await window.__srvSince(cur); cur = r.cur; if(r.changes.length) cb(r.changes); } finally { busy = false; } }, 100);
    return () => clearInterval(t); }
};
"""

async def phone(browser, srv, email, clock="2026-10-29T10:00:00-07:00"):
    ctx = await browser.new_context(viewport={"width": 390, "height": 844})
    await ctx.route("**/fonts.g*/**", lambda r: r.abort())
    await ctx.expose_function("__srvAll", lambda: srv.all())
    def _w(lst, em):
        srv.write(lst, em)
    await ctx.expose_function("__srvWrite", _w)
    await ctx.expose_function("__srvSince", lambda cur: srv.since(cur))
    await ctx.add_init_script(f"window.__email = {json.dumps(email)};" + FAKE)
    pg = await ctx.new_page(); pg.errors = []
    pg.on("pageerror", lambda e: pg.errors.append(str(e)))
    await pg.goto("file://" + PAGE); await pg.wait_for_timeout(300)
    return pg

async def ev(pg, js): return await pg.evaluate(js)
async def settle(*pgs, ms=900):
    for pg in pgs: await pg.wait_for_timeout(ms // len(pgs))

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        srv = Server()
        A = await phone(b, srv, "sam@example.com")
        check("no account yet: nothing uploaded", srv.writes == 0)
        await ev(A, "ACTIONS.tab('more'); ACTIONS.mtab('settings')")
        check("settings offers Google sign-in", await ev(A, "!!document.querySelector('[data-act=syncIn]')"))
        await ev(A, "ACTIONS.syncIn()"); await settle(A)
        n = len(await ev(A, "Object.keys(recordsOf(state))"))
        check("first phone uploads its household", len(srv.recs) == n and n > 10, f"{len(srv.recs)} vs {n}")
        check("settings shows the signed-in account", "sam@example.com" in await ev(A, "document.querySelector('#view').innerText"))

        B = await phone(b, srv, "charliepurdomva@gmail.com")
        await ev(B, "prefs.user = 'sam'")
        b_own = await ev(B, "state.chores.map(c => c.id)")
        await ev(B, "ACTIONS.syncIn()"); await settle(A, B)
        a_ids = sorted(await ev(A, "state.chores.map(c => c.id)")); b_ids = sorted(await ev(B, "state.chores.map(c => c.id)"))
        check("second phone joins the shared household instead of uploading its examples", a_ids == b_ids and not set(b_own) & set(a_ids), f"{a_ids} {b_ids}")
        check("second phone keeps its old data as a safety copy", any(k.startswith("zendom:backup:before-first-sync") for k in await ev(B, "Object.keys(localStorage)")))
        check("Charlie's Google account switches the app to Charlie", await ev(B, "prefs.user") == "charlie")
        check("second phone explains what happened", "shared household" in await ev(B, "document.querySelector('#banners').innerText"))
        check("no duplicate budget categories", len(await ev(B, "state.budget.categories")) == len(await ev(A, "state.budget.categories")))

        # add, tick, delete across phones
        await ev(A, "state.chores.push({id:'shared1', title:'Descale the kettle', owner:'charlie', freq:'monthly', everyDays:null, start:'2026-10-29', lastDone:null, history:[], done:false, standard:'', cpe:{c:'',p:'',e:''}, example:false}); save(); render()")
        await settle(A, B)
        check("a chore added on Sam's phone shows on Charlie's", await ev(B, "state.chores.some(c => c.id === 'shared1')"))
        await ev(B, "ACTIONS.tab('chores'); ACTIONS.filter('all'); toggleChore('shared1')"); await settle(A, B)
        check("Charlie ticks it off and Sam sees it", await ev(A, "state.chores.find(c => c.id === 'shared1').lastDone") == "2026-10-29")
        check("Sam's screen updates without a reload", await ev(A, "ACTIONS.tab('chores'); ACTIONS.filter('all'); !!document.querySelector('[data-act=toggle][data-id=shared1][aria-pressed=true]')"))
        nid = await ev(A, "state.notes[0].id")
        await ev(A, f"removeBy(state.notes, '{nid}'); save()"); await settle(A, B)
        check("a deleted note disappears on the other phone", not await ev(B, f"state.notes.some(n => n.id === '{nid}')"))

        # different items edited at the same moment: both kept
        c1, c2 = (await ev(A, "state.chores.map(c => c.id)"))[:2]
        await ev(A, f"state.chores.find(c => c.id === '{c1}').title = 'Edited on Sam'; save()")
        await ev(B, f"state.chores.find(c => c.id === '{c2}').title = 'Edited on Charlie'; save()")
        await settle(A, B, ms=1400)
        for X, nm in ((A, "Sam"), (B, "Charlie")):
            t = await ev(X, f"[state.chores.find(c => c.id === '{c1}').title, state.chores.find(c => c.id === '{c2}').title]")
            check(f"simultaneous edits to different chores both kept ({nm}'s phone)", t == ["Edited on Sam", "Edited on Charlie"], str(t))
        # same item at the same moment: phones end up agreeing
        await ev(A, f"state.chores.find(c => c.id === '{c1}').title = 'Sam wins?'; save()")
        await ev(B, f"state.chores.find(c => c.id === '{c1}').title = 'Charlie wins?'; save()")
        await settle(A, B, ms=1600)
        ta = await ev(A, f"state.chores.find(c => c.id === '{c1}').title"); tb = await ev(B, f"state.chores.find(c => c.id === '{c1}').title")
        check("same chore edited on both phones: they end up agreeing", ta == tb and ta in ("Sam wins?", "Charlie wins?"), f"{ta} / {tb}")

        # drawings and budget travel too
        await ev(B, "state.notes.push({id:'dr1', text:'', drawing:{strokes:[{c:'#4f7fc4', w:10, p:[10,10,500,400]}]}, color:'mint', pinned:true, author:'charlie', created:1, updated:1, reactions:[], replies:[]}); save()")
        await ev(A, "state.budget.fund.entries.push({id:'fe1', kind:'in', amount:2500, who:'sam', place:'Cash jar', date:'2026-10-29', note:'', goalId:'', toPlace:'', created:1}); save()")
        await settle(A, B)
        check("a drawn note syncs", await ev(A, "(state.notes.find(n => n.id === 'dr1') || {drawing:null}).drawing?.strokes?.length") == 1)
        check("Fun Fund money syncs", await ev(B, "fundTotal()") == 2500)

        # offline, then back
        srv.down = True
        await ev(A, "state.grocery.push({id:'g-off', name:'Oat milk', qty:'', aisle:'Dairy & eggs', checked:false, recipeId:null, added:1}); save()")
        await A.wait_for_timeout(700)
        check("offline: the phone says it will catch up", "back online" in await ev(A, "sync.err"), await ev(A, "sync.err"))
        check("offline: the change is still on Sam's phone", await ev(A, "state.grocery.some(g => g.id === 'g-off')"))
        srv.down = False
        await ev(A, "sync.status = 'on'; sync.err = ''; state.grocery.push({id:'g-on', name:'Basil', qty:'', aisle:'Produce', checked:false, recipeId:null, added:2}); save()")
        await settle(A, B)
        check("back online: the change made offline reaches Charlie", await ev(B, "state.grocery.some(g => g.id === 'g-off') && state.grocery.some(g => g.id === 'g-on')"))

        # reload: no re-upload, nothing lost
        before = srv.writes
        await A.reload(); await A.wait_for_timeout(300); await ev(A, "ACTIONS.syncIn()"); await settle(A)
        check("reopening the app doesn't re-send everything", srv.writes - before <= 1, f"{srv.writes - before} writes")
        check("reopening keeps the shared data", await ev(A, "state.notes.some(n => n.id === 'dr1') && fundTotal() === 2500"))

        # someone else's Google account
        C = await phone(b, Server(), "stranger@example.com")
        srvC = None
        await ev(C, "ACTIONS.syncIn()"); await C.wait_for_timeout(700)
        check("an account that isn't yours gets a clear message", "isn't allowed" in await ev(C, "sync.err"), await ev(C, "sync.err"))

        # sign out keeps data local
        await ev(B, "ACTIONS.syncOut()"); await B.wait_for_timeout(200)
        check("signing out stops syncing and keeps the data", await ev(B, "sync.status") == "off" and await ev(B, "state.chores.some(c => c.id === 'shared1')"))
        for X, nm in ((A, "Sam"), (B, "Charlie"), (C, "stranger")):
            check(f"no page errors ({nm})", not X.errors, "; ".join(X.errors)[:300])

        # without the website's backend: honest note, no sign-in button
        ctx = await b.new_context(); pg = await ctx.new_page(); await pg.goto("file://" + PAGE); await pg.wait_for_timeout(300)
        await pg.evaluate("delete window.zdBackend; ACTIONS.tab('more'); ACTIONS.mtab('settings')")
        check("copy without sync says so plainly", "works on the zen·dom website" in await pg.evaluate("document.querySelector('#view').innerText"))
        await b.close()
    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)} of {len(results)} sync checks passed"); sys.exit(1 if failed else 0)

asyncio.run(main())
