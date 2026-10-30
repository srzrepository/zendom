"""Opening zen·dom without internet. Serves the repo on http://localhost (service workers need a real
web address), loads the app once online, then goes offline and reloads.
Run: python3 tests/offline_tests.py /path/to/repo"""
import sys, asyncio, threading, http.server, functools, socketserver
from playwright.async_api import async_playwright
ROOT = sys.argv[1]; results = []
def check(n, ok, d=""): results.append(ok); print(("PASS " if ok else "FAIL ") + n + (f"  [{d}]" if d and not ok else ""))
class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
srv = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=ROOT)); port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f"http://localhost:{port}/index.html"
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); ctx = await b.new_context(viewport={"width": 390, "height": 844})
        await ctx.route("**/fonts.g*/**", lambda r: r.abort())
        await ctx.route(lambda u: "googleapis.com" in u and "fonts" not in u, lambda r: r.abort())   # no real Firebase in tests
        pg = await ctx.new_page(); errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
        await pg.goto(URL); await pg.wait_for_timeout(500)
        ok = await pg.evaluate("navigator.serviceWorker.ready.then(r => !!r.active).catch(() => false)")
        check("the background worker installs", ok)
        await pg.reload(); await pg.wait_for_timeout(500)
        check("it controls the page after a reload", await pg.evaluate("!!navigator.serviceWorker.controller"))
        await pg.evaluate("state.notes.push({id:'off1', text:'written before going offline', color:'mint', pinned:true, author:'sam', created:Date.now(), updated:Date.now(), reactions:[], replies:[]}); save()")
        cached = await pg.evaluate("caches.open('zendom-app-v1').then(c => c.keys()).then(k => k.map(r => new URL(r.url).pathname))")
        check("app files are saved on the phone", all(any(x.endswith(f) for x in cached) for f in ("index.html", "firebase-bundle.js", "manifest.json")), str(cached))
        await ctx.set_offline(True)
        await pg.reload(); await pg.wait_for_timeout(800)
        txt = await pg.evaluate("document.querySelector('#view') ? document.querySelector('#view').innerText : ''")
        check("offline: the app still opens", "Up next for you" in txt, txt[:200])
        check("offline: your data is there", "written before going offline" in txt)
        check("offline: the Offline bar shows", await pg.evaluate("!document.querySelector('#netPill').hidden && document.querySelector('#netPill').textContent.includes('Offline')"))
        await pg.evaluate("ACTIONS.tab('kitchen'); ACTIONS.ktab('grocery')")
        check("offline: other tabs work", "Add an item" in await pg.evaluate("document.querySelector('#view').innerHTML"))
        await ctx.set_offline(False); await pg.wait_for_timeout(300)
        check("back online: the Offline bar goes away", await pg.evaluate("document.querySelector('#netPill').hidden"))
        check("no page errors", not errs, "; ".join(errs[:3]))
        await b.close()
    srv.shutdown(); print(f"\n{sum(results)} of {len(results)} offline checks passed"); sys.exit(0 if all(results) else 1)
asyncio.run(main())
