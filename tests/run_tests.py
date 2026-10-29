"""zen·dom end-to-end checks.

Run:  python3 tests/run_tests.py path/to/index.html
Drives the real page in headless Chromium at phone size (390x844), clicks the
same buttons a person would, and reads the saved data back. Every check prints
PASS/FAIL; the script exits non-zero if anything failed.
"""
import sys, json, asyncio
from playwright.async_api import async_playwright

PAGE = sys.argv[1] if len(sys.argv) > 1 else "index.html"
results = []

def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail and not ok else ""))

async def new_page(browser, storage=None, clock=None):
    ctx = await browser.new_context(viewport={"width": 390, "height": 844})
    # block the Google Fonts request (no network in the test sandbox)
    await ctx.route("**/fonts.googleapis.com/**", lambda r: r.abort())
    await ctx.route("**/fonts.gstatic.com/**", lambda r: r.abort())
    pg = await ctx.new_page()
    pg.errors = []
    pg.on("pageerror", lambda e: pg.errors.append(str(e)))
    if clock:
        await pg.clock.set_fixed_time(clock)
    await pg.goto("file://" + PAGE)
    if storage is not None:
        # seed localStorage once, then reload so the app boots from it
        await pg.evaluate("s => { localStorage.clear(); for (const k in s) localStorage.setItem(k, s[k]); }", storage)
        await pg.reload()
    await pg.wait_for_timeout(300)
    return pg

async def act(pg, name, id=None, nth=0):
    sel = f'[data-act="{name}"]' + (f'[data-id="{id}"]' if id is not None else "")
    loc = pg.locator(sel)
    await loc.nth(nth).click()
    await pg.wait_for_timeout(60)

async def ev(pg, js):
    return await pg.evaluate(js)

async def fill(pg, fields):
    for k, v in fields.items():
        el = pg.locator(f'#sheetForm [name="{k}"]').first
        tag = await el.evaluate("e => e.tagName + ':' + (e.type || '')")
        if tag.startswith("SELECT"):
            await el.select_option(v)
        else:
            await el.fill(v)

async def submit(pg):
    await pg.locator('#sheetForm button[type="submit"]').click()
    await pg.wait_for_timeout(80)

async def sheet_open(pg):
    return await ev(pg, "!!document.querySelector('#sheetForm')")

async def err_text(pg):
    return await ev(pg, "[...document.querySelectorAll('#sheetForm .err')].map(e=>e.textContent).join(' | ')")

async def stored(pg):
    return await ev(pg, "JSON.parse(localStorage.getItem('zendom:data'))")

async def confirm_delete(pg):
    await act(pg, "askDelete")
    await pg.locator('#confirmBox [data-act*=":"]').click()
    await pg.wait_for_timeout(80)


async def test_tabs(pg):
    for tab in ["today", "chores", "kitchen", "family", "more"]:
        await act(pg, "tab", tab)
        cur = await ev(pg, "document.querySelector('#nav [aria-current=page]').dataset.id")
        body = await ev(pg, "document.querySelector('#view').innerText.trim().length")
        check(f"tab {tab} renders", cur == tab and body > 0, f"cur={cur} len={body}")
    await act(pg, "tab", "today")
    for v in ["today", "week", "month"]:
        await act(pg, "tview", v)
        check(f"today sub-view {v} renders", await ev(pg, f"document.querySelector('[data-act=tview][data-id={v}]').getAttribute('aria-selected')") == "true")
    await act(pg, "tview", "today")
    await act(pg, "tab", "kitchen")
    for k in ["recipes", "plan", "grocery", "pantry"]:
        await act(pg, "ktab", k)
        check(f"kitchen sub-tab {k} renders", await ev(pg, f"document.querySelector('[data-act=ktab][data-id={k}]').getAttribute('aria-selected')") == "true")
    await act(pg, "tab", "more")
    for k in ["notes", "budget", "settings"]:
        await act(pg, "mtab", k)
        check(f"more sub-tab {k} renders", await ev(pg, f"document.querySelector('[data-act=mtab][data-id={k}]').getAttribute('aria-selected')") == "true")
    await act(pg, "mtab", "budget")
    for k in ["spending", "plan", "fund"]:
        await act(pg, "btab", k)
        check(f"budget sub-tab {k} renders", await ev(pg, f"document.querySelector('[data-act=btab][data-id={k}]').getAttribute('aria-pressed')") == "true")
    await act(pg, "btab", "spending")
    await act(pg, "mtab", "notes")
    await act(pg, "tab", "family")
    for k in ["sam", "charlie", "paprika"]:
        await act(pg, "fam", k)
        check(f"family profile {k} renders", await ev(pg, f"document.querySelector('[data-act=fam][data-id={k}]').getAttribute('aria-pressed')") == "true")


async def test_chores(pg):
    await act(pg, "tab", "chores")
    await act(pg, "filter", "all")
    n0 = await ev(pg, "state.chores.length")
    await act(pg, "newChore")
    await submit(pg)
    check("chore: empty title rejected", await sheet_open(pg) and "name" in (await err_text(pg)), await err_text(pg))
    await fill(pg, {"title": "Test vacuum", "freq": "custom", "everyDays": "0"})
    await submit(pg)
    check("chore: custom days 0 rejected", "1 to 365" in (await err_text(pg)), await err_text(pg))
    await fill(pg, {"everyDays": "3"})
    await submit(pg)
    s = await stored(pg)
    c = [x for x in s["chores"] if x["title"] == "Test vacuum"]
    check("chore: add saves", not await sheet_open(pg) and len(c) == 1 and c[0]["everyDays"] == 3 and len(s["chores"]) == n0 + 1)
    cid = c[0]["id"]
    await act(pg, "editChore", cid)
    await fill(pg, {"title": "Test vacuum rugs"})
    await submit(pg)
    check("chore: edit saves", any(x["title"] == "Test vacuum rugs" for x in (await stored(pg))["chores"]))
    await act(pg, "toggle", cid)
    s = await stored(pg)
    today = await ev(pg, "todayStr()")
    check("chore: toggle done", next(x for x in s["chores"] if x["id"] == cid)["lastDone"] == today)
    check("chore: done shows pressed", await ev(pg, f"document.querySelector('[data-act=toggle][data-id=\"{cid}\"]').getAttribute('aria-pressed')") == "true")
    await act(pg, "toggle", cid)
    s = await stored(pg)
    check("chore: toggle back to not done", next(x for x in s["chores"] if x["id"] == cid)["lastDone"] is None)
    await act(pg, "toggle", cid)
    await act(pg, "undo")
    s = await stored(pg)
    check("chore: undo toast reverts", next(x for x in s["chores"] if x["id"] == cid)["lastDone"] is None)
    # one-time chore
    await act(pg, "newChore")
    await fill(pg, {"title": "One-off test", "freq": "once"})
    await submit(pg)
    oid = next(x["id"] for x in (await stored(pg))["chores"] if x["title"] == "One-off test")
    await act(pg, "toggle", oid)
    check("chore: one-time toggle done", next(x for x in (await stored(pg))["chores"] if x["id"] == oid)["done"] is True)
    await act(pg, "editChore", cid)
    await confirm_delete(pg)
    check("chore: delete", not any(x["id"] == cid for x in (await stored(pg))["chores"]))
    await act(pg, "editChore", oid)
    await confirm_delete(pg)
    for f in ["me", "them", "none", "all"]:
        await act(pg, "filter", f)
    check("chore: filters cycle without errors", not pg.errors, "; ".join(pg.errors))


async def test_notes(pg):
    await act(pg, "tab", "more")
    await act(pg, "mtab", "notes")
    await act(pg, "newNote")
    await submit(pg)
    check("note: empty rejected", await sheet_open(pg) and await err_text(pg))
    await fill(pg, {"text": "Buy cat litter <b>bold?</b>"})
    await submit(pg)
    s = await stored(pg)
    n = [x for x in s["notes"] if x["text"].startswith("Buy cat litter")]
    check("note: add saves", len(n) == 1)
    check("note: text is escaped in the board", await ev(pg, "!document.querySelector('#view b') || ![...document.querySelectorAll('#view .note b')].length"))
    nid = n[0]["id"]
    await act(pg, "openNote", nid)
    await pg.locator('[data-act=react]').first.click()
    await pg.wait_for_timeout(60)
    check("note: reaction saved", len(next(x for x in (await stored(pg))["notes"] if x["id"] == nid)["reactions"]) == 1)
    await submit(pg)
    check("note: empty reply rejected", "Write something" in (await err_text(pg)))
    await fill(pg, {"reply": "On it"})
    await submit(pg)
    check("note: reply saved", len(next(x for x in (await stored(pg))["notes"] if x["id"] == nid)["replies"]) == 1)
    await act(pg, "editNote", nid)
    await fill(pg, {"text": "Buy cat litter (edited)"})
    await submit(pg)
    check("note: edit saves", next(x for x in (await stored(pg))["notes"] if x["id"] == nid)["text"] == "Buy cat litter (edited)")
    await act(pg, "openNote", nid)
    await act(pg, "editNote", nid)
    await confirm_delete(pg)
    check("note: delete", not any(x["id"] == nid for x in (await stored(pg))["notes"]))


async def test_family(pg):
    await act(pg, "tab", "family")
    await act(pg, "fam", "sam")
    await act(pg, "addAllergy")
    await submit(pg)
    check("family: empty allergy rejected", await err_text(pg))
    await fill(pg, {"allergy": "Penicillin"})
    await submit(pg)
    check("family: allergy added", "Penicillin" in (await stored(pg))["people"]["sam"]["allergies"])
    await act(pg, "addAllergy")
    await fill(pg, {"allergy": "penicillin"})
    await submit(pg)
    check("family: duplicate allergy rejected", "already" in (await err_text(pg)))
    await act(pg, "closeSheet")
    await act(pg, "delAllergy", "0")
    check("family: allergy removed", "Penicillin" not in (await stored(pg))["people"]["sam"]["allergies"])
    await act(pg, "editMed")
    await fill(pg, {"mname": "Vitamin D", "dose": "1000 IU"})
    await submit(pg)
    meds = (await stored(pg))["people"]["sam"]["meds"]
    check("family: med added", len(meds) == 1)
    await act(pg, "editMed", meds[0]["id"])
    await confirm_delete(pg)
    check("family: med deleted", not (await stored(pg))["people"]["sam"]["meds"])
    await act(pg, "editCheckup")
    await fill(pg, {"cname": "Dentist", "months": "0"})
    await submit(pg)
    check("family: bad checkup months rejected", "whole number" in (await err_text(pg)))
    await fill(pg, {"months": "6", "last": "2099-01-01"})
    await submit(pg)
    check("family: future last visit rejected", "future" in (await err_text(pg)))
    await fill(pg, {"last": "2026-01-15"})
    await submit(pg)
    cks = (await stored(pg))["people"]["sam"]["checkups"]
    check("family: checkup added", len(cks) == 1 and cks[0]["months"] == 6)
    await act(pg, "editVaccine")
    await fill(pg, {"vname": "Flu", "vdate": "2026-10-01", "vnext": "2026-09-01"})
    await submit(pg)
    check("family: vaccine next-before-given rejected", "after" in (await err_text(pg)))
    await fill(pg, {"vnext": "2027-10-01"})
    await submit(pg)
    check("family: vaccine added", len((await stored(pg))["people"]["sam"]["vaccines"]) == 1)
    await act(pg, "fam", "paprika")
    await act(pg, "editBasics")
    await fill(pg, {"name": ""})
    await submit(pg)
    check("family: empty name rejected", await err_text(pg))
    await fill(pg, {"name": "Paprika", "breed": "Orange tabby"})
    await submit(pg)
    check("family: basics saved", (await stored(pg))["people"]["paprika"]["breed"] == "Orange tabby")


async def test_kitchen(pg):
    await act(pg, "tab", "kitchen")
    await act(pg, "ktab", "recipes")
    await act(pg, "newRecipe")
    await submit(pg)
    check("recipe: empty title rejected", await err_text(pg))
    await fill(pg, {"rtitle": "Test pasta", "servings": "2", "ings": "200 g spaghetti\n2 cloves garlic\n1 tbsp olive oil", "steps": "Boil.\nToss."})
    await submit(pg)
    r = [x for x in (await stored(pg))["recipes"] if x["title"] == "Test pasta"]
    check("recipe: add saves", len(r) == 1 and len(r[0]["ingredients"]) == 3)
    rid = r[0]["id"]
    await act(pg, "openRecipe", rid)
    await act(pg, "editRecipe", rid)
    await fill(pg, {"servings": "200"})
    await submit(pg)
    check("recipe: servings 200 rejected", "1 to 99" in (await err_text(pg)))
    await fill(pg, {"servings": "3"})
    await submit(pg)
    check("recipe: edit saves", next(x for x in (await stored(pg))["recipes"] if x["id"] == rid)["servings"] == 3)
    await ev(pg, "document.querySelector('#sheetRoot').innerHTML && closeSheet()")
    # meal plan + week navigation
    await act(pg, "ktab", "plan")
    wk0 = await ev(pg, "curWeek()")
    await act(pg, "week", "1")
    wk1 = await ev(pg, "curWeek()")
    await act(pg, "week", "-1")
    await act(pg, "week", "-1")
    wkm1 = await ev(pg, "curWeek()")
    await act(pg, "week", "0")
    check("meal plan: week navigation", wk1 == await ev(pg, f"addDays('{wk0}',7)") and wkm1 == await ev(pg, f"addDays('{wk0}',-7)") and await ev(pg, "curWeek()") == wk0)
    await act(pg, "addMeal", nth=0)
    await submit(pg)
    check("meal: needs recipe or note", "recipe or write" in (await err_text(pg)))
    await fill(pg, {"mrecipe": rid})
    await submit(pg)
    meals = [m for m in (await stored(pg))["meals"] if m["recipeId"] == rid]
    check("meal: add saves", len(meals) == 1)
    await act(pg, "editMeal", meals[0]["id"])
    await confirm_delete(pg)
    check("meal: delete", not any(m["recipeId"] == rid for m in (await stored(pg))["meals"]))
    # grocery
    await act(pg, "ktab", "grocery")
    await pg.locator("#gadd button[type=submit]").click()
    check("grocery: empty add rejected", "Type an item" in await ev(pg, "document.querySelector('#gerr').textContent"))
    await pg.fill("#gname", "Oat milk")
    await pg.locator("#gadd button[type=submit]").click()
    await pg.wait_for_timeout(60)
    g = [x for x in (await stored(pg))["grocery"] if x["name"] == "Oat milk"]
    check("grocery: add saves", len(g) == 1)
    await pg.fill("#gname", "oat milk")
    await pg.locator("#gadd button[type=submit]").click()
    check("grocery: duplicate rejected", "already" in await ev(pg, "document.querySelector('#gerr').textContent"))
    gid = g[0]["id"]
    await act(pg, "editGrocery", gid)
    await fill(pg, {"gqty": "2 cartons"})
    await submit(pg)
    check("grocery: edit saves", next(x for x in (await stored(pg))["grocery"] if x["id"] == gid)["qty"] == "2 cartons")
    await act(pg, "gcheck", gid)
    check("grocery: check off", next(x for x in (await stored(pg))["grocery"] if x["id"] == gid)["checked"])
    await act(pg, "gcheck", gid)
    check("grocery: uncheck", not next(x for x in (await stored(pg))["grocery"] if x["id"] == gid)["checked"])
    await act(pg, "gcheck", gid)
    pn = len((await stored(pg))["pantry"])
    await act(pg, "putAway")
    s = await stored(pg)
    check("grocery: put away moves to pantry", not any(x["id"] == gid for x in s["grocery"]) and len(s["pantry"]) == pn + 1)
    # pantry room switching
    await act(pg, "ktab", "pantry")
    for room in ["fridge", "freezer", "pantry", "spices"]:
        await act(pg, "room", room)
        check(f"pantry: switch to {room}", await ev(pg, f"document.querySelector('[data-act=room][data-id={room}]').getAttribute('aria-pressed')") == "true" and await ev(pg, "prefs.pantryRoom") == room)
    await act(pg, "room", "freezer")
    await act(pg, "newPantry")
    await fill(pg, {"pname": ""})
    await submit(pg)
    check("pantry: empty name rejected", await err_text(pg))
    await fill(pg, {"pname": "Test edamame", "pexp": "2026-12-01"})
    await submit(pg)
    p = [x for x in (await stored(pg))["pantry"] if x["name"] == "Test edamame"]
    check("pantry: add saves in current room", len(p) == 1 and p[0]["room"] == "freezer")
    await act(pg, "editPantry", p[0]["id"])
    await fill(pg, {"proom": "fridge"})
    await submit(pg)
    check("pantry: edit moves room and follows it", next(x for x in (await stored(pg))["pantry"] if x["id"] == p[0]["id"])["room"] == "fridge" and await ev(pg, "prefs.pantryRoom") == "fridge")
    await act(pg, "editPantry", p[0]["id"])
    await confirm_delete(pg)
    check("pantry: delete", not any(x["id"] == p[0]["id"] for x in (await stored(pg))["pantry"]))
    await act(pg, "ktab", "recipes")
    await act(pg, "openRecipe", rid)
    await act(pg, "editRecipe", rid)
    await confirm_delete(pg)
    check("recipe: delete", not any(x["id"] == rid for x in (await stored(pg))["recipes"]))


async def test_calendar(pg):
    await act(pg, "tab", "today")
    await act(pg, "tview", "week")
    t = await ev(pg, "todayStr()")
    await act(pg, "calWeekNav", "1")
    a = await ev(pg, "curCalWeek()")
    await act(pg, "calWeekNav", "-1")
    await act(pg, "calWeekNav", "-1")
    b = await ev(pg, "curCalWeek()")
    await act(pg, "calWeekNav", "0")
    check("calendar: week navigation", a == await ev(pg, f"addDays('{t}',7)") and b == await ev(pg, f"addDays('{t}',-7)") and await ev(pg, "curCalWeek()") == t)
    await act(pg, "tview", "month")
    m0 = await ev(pg, "curCalMonth()")
    await act(pg, "calMonthNav", "1")
    m1 = await ev(pg, "curCalMonth()")
    for _ in range(14):
        await act(pg, "calMonthNav", "-1")
    m13 = await ev(pg, "curCalMonth()")
    await act(pg, "calMonthNav", "0")
    check("calendar: month navigation across years", m1 == await ev(pg, f"addMonthKey('{m0}',1)") and m13 == await ev(pg, f"addMonthKey('{m0}',-13)") and await ev(pg, "curCalMonth()") == m0)
    cells = await ev(pg, "document.querySelectorAll('.mcell').length")
    check("calendar: month grid is whole weeks", cells % 7 == 0 and cells >= 28, str(cells))
    pick = await ev(pg, "document.querySelectorAll('.mcell')[10].dataset.id")
    await act(pg, "calPick", pick)
    check("calendar: pick a day", await ev(pg, "calDay") == pick)
    await act(pg, "newEvent", pick)
    await submit(pg)
    check("event: empty title rejected", await err_text(pg))
    await fill(pg, {"etitle": "Vet visit", "etime": "14:30"})
    await submit(pg)
    e = [x for x in (await stored(pg))["events"] if x["title"] == "Vet visit"]
    check("event: add saves", len(e) == 1 and e[0]["date"] == pick)
    check("event: shows on picked day", "Vet visit" in await ev(pg, "document.querySelector('#view').innerText"))
    await act(pg, "editEvent", e[0]["id"])
    await fill(pg, {"etitle": "Vet visit (Paprika)"})
    await submit(pg)
    check("event: edit saves", next(x for x in (await stored(pg))["events"] if x["id"] == e[0]["id"])["title"] == "Vet visit (Paprika)")
    await act(pg, "editEvent", e[0]["id"])
    await confirm_delete(pg)
    check("event: delete", not (await stored(pg))["events"])
    for w in ["sam", "charlie", "all"]:
        await act(pg, "calWho", w)
    await act(pg, "tview", "today")


async def test_budget(pg):
    await act(pg, "tab", "more")
    await act(pg, "mtab", "budget")
    await act(pg, "btab", "spending")
    await act(pg, "newTxn")
    await fill(pg, {"amt": "-5"})
    await submit(pg)
    check("budget: negative amount rejected", "amount" in (await err_text(pg)))
    await fill(pg, {"amt": "12.50", "tnote": "Groceries test"})
    await submit(pg)
    tx = (await stored(pg))["budget"]["txns"]
    check("budget: spending added", len(tx) == 1 and tx[0]["amount"] == 1250, json.dumps(tx)[:200])
    await act(pg, "editTxn", tx[0]["id"])
    await confirm_delete(pg)
    check("budget: spending deleted", not (await stored(pg))["budget"]["txns"])
    await act(pg, "btab", "fund")
    await act(pg, "btab", "plan")
    await act(pg, "btab", "spending")


async def run_all(browser):
    pg = await new_page(browser, storage={}, clock="2026-10-29T10:00:00-07:00")
    check("fresh start: example data seeded", (await ev(pg, "state.chores.length")) > 0)
    for t in [test_tabs, test_chores, test_notes, test_family, test_kitchen, test_calendar, test_budget]:
        try:
            await t(pg)
        except Exception as e:
            check(f"{t.__name__} ran to completion", False, str(e)[:300])
            await ev(pg, "document.querySelector('#sheetRoot').innerHTML=''")
    _pre = (await stored(pg))["people"]["paprika"]["breed"]
    await pg.reload(); await pg.wait_for_timeout(200)
    _b = await ev(pg, "state.people.paprika.breed")
    if _b != "Orange tabby": print("   DIAG pre-reload stored:", repr(_pre), "post keys:", await ev(pg, "Object.keys(localStorage)"), "stored now:", (await stored(pg))["people"]["paprika"]["breed"])
    check("reload: Paprika's breed persisted", (_b or "").startswith("Orange tabby"), repr(_b) + " " + "; ".join(pg.errors)[:300])
    check("no page errors during the run", not pg.errors, "; ".join(pg.errors)[:500])
    await pg.context.close()

    # empty data: everything deleted
    empty = {"zendom:data": json.dumps({"version": 6, "people": {}, "chores": [], "notes": [], "recipes": [], "meals": [], "grocery": [], "pantry": [], "events": []})}
    pg = await new_page(browser, storage=empty, clock="2026-10-29T10:00:00-07:00")
    for tab in ["today", "chores", "kitchen", "family", "more"]:
        await act(pg, "tab", tab)
    await act(pg, "tab", "kitchen")
    for k in ["recipes", "plan", "grocery", "pantry"]:
        await act(pg, "ktab", k)
    await act(pg, "tab", "today")
    for v in ["week", "month", "today"]:
        await act(pg, "tview", v)
    await act(pg, "tab", "chores")
    check("empty state: chores shows add-first button", await ev(pg, "!!document.querySelector('#view [data-act=newChore]')"))
    check("empty state: no page errors", not pg.errors, "; ".join(pg.errors)[:300])
    await pg.context.close()

    # corrupt data is kept as a safety copy, not thrown away
    pg = await new_page(browser, storage={"zendom:data": "{not json"}, clock="2026-10-29T10:00:00-07:00")
    keys = await ev(pg, "Object.keys(localStorage)")
    bk = [k for k in keys if k.startswith("zendom:backup:unreadable")]
    check("corrupt data: original kept as safety copy", len(bk) == 1 and await ev(pg, f"localStorage.getItem('{bk[0]}')") == "{not json")
    check("corrupt data: banner shown", "couldn't be read" in await ev(pg, "document.querySelector('#banners').innerText"))
    await pg.context.close()

    # old v1 data migrates forward and keeps its content
    v1 = {"version": 1, "people": {"sam": {"name": "Sam", "allergies": ["Peanuts"]}}, "chores": [{"id": "c1", "title": "Old chore", "owner": "sam", "freq": "weekly", "start": "2026-01-01"}], "notes": [{"id": "n1", "text": "Old note", "author": "charlie"}], "customField": 42}
    pg = await new_page(browser, storage={"zendom:data": json.dumps(v1)}, clock="2026-10-29T10:00:00-07:00")
    s = await stored(pg)
    keys = await ev(pg, "Object.keys(localStorage)")
    check("migration v1: version bumped", s["version"] == await ev(pg, "SCHEMA"))
    check("migration v1: budget defaults filled", len(s["budget"]["categories"]) > 0)
    check("migration v1: chores/notes/allergies kept", s["chores"][0]["title"] == "Old chore" and s["notes"][0]["text"] == "Old note" and s["people"]["sam"]["allergies"] == ["Peanuts"])
    check("migration v1: unknown fields kept", s.get("customField") == 42)
    check("migration v1: safety copy made", any(k.startswith("zendom:backup:before-v") for k in keys))
    check("migration v1: no page errors", not pg.errors, "; ".join(pg.errors)[:300])
    await pg.context.close()


async def test_dates(browser):
    pg = await new_page(browser, storage={}, clock="2026-10-29T10:00:00-07:00")
    r = await ev(pg, "(() => { const b={nextDue:'2027-01-31', cycle:'monthly', anchorDay:31}; const o=[]; for(let i=0;i<4;i++){ b.nextDue=nextBillDate(b); o.push(b.nextDue);} return o; })()")
    check("dates: bill on the 31st keeps its day after paying", r == ["2027-02-28", "2027-03-31", "2027-04-30", "2027-05-31"], str(r))
    r = await ev(pg, "(() => { const b={nextDue:'2027-03-15', cycle:'yearly', anchorDay:15}; return nextBillDate(b); })()")
    check("dates: yearly bill", r == "2028-03-15", r)
    r = await ev(pg, "(() => { const b={nextDue:'2026-10-29', cycle:'weekly', anchorDay:29}; return nextBillDate(b); })()")
    check("dates: weekly bill", r == "2026-11-05", r)
    r = await ev(pg, "(() => { state.events=[{id:'e1',title:'Rent',date:'2026-10-31',time:'',who:'',repeat:'monthly',note:''}]; return calendarItems('2026-10-01','2027-04-30').filter(x=>x.type==='event').map(x=>x.date); })()")
    check("dates: monthly event on the 31st", r == ["2026-10-31","2026-11-30","2026-12-31","2027-01-31","2027-02-28","2027-03-31","2027-04-30"], str(r))
    r = await ev(pg, "(() => { state.events=[{id:'e2',title:'Leap',date:'2024-02-29',time:'',who:'',repeat:'yearly',note:''}]; return calendarItems('2026-01-01','2029-12-31').filter(x=>x.type==='event').map(x=>x.date); })()")
    check("dates: yearly Feb 29 event returns in leap years", r == ["2026-02-28","2027-02-28","2028-02-29","2029-02-28"], str(r))
    r = await ev(pg, "(() => { state.events=[{id:'e3',title:'Old weekly',date:'2015-01-05',time:'',who:'',repeat:'weekly',note:''}]; return calendarItems('2026-11-01','2026-11-30').filter(x=>x.type==='event').map(x=>x.date); })()")
    check("dates: weekly event started years ago still shows", r == ["2026-11-02","2026-11-09","2026-11-16","2026-11-23","2026-11-30"], str(r))
    r = await ev(pg, "(() => { state.events=[]; state.chores=[{id:'m1',title:'Monthly',owner:'sam',freq:'monthly',everyDays:null,start:'2026-10-31',lastDone:null,history:[],done:false,standard:'',cpe:{c:'',p:'',e:''}}]; return calendarItems('2026-10-29','2027-03-31').filter(x=>x.type==='chore').map(x=>x.date); })()")
    check("dates: monthly chore projection keeps the 31st", r == ["2026-10-31","2026-11-30","2026-12-31","2027-01-31","2027-02-28","2027-03-31"], str(r))
    check("dates: no page errors", not pg.errors, "; ".join(pg.errors))
    await pg.context.close()
    # v6 data with bills: migrates to v7, anchor taken from the due date, nothing lost
    v6 = {"version": 6, "people": {}, "chores": [], "notes": [], "budget": {"categories": [{"id": "k1", "name": "Bills"}], "txns": [], "bills": [{"id": "b1", "name": "Rent", "amount": 250000, "cycle": "monthly", "nextDue": "2026-10-31", "categoryId": "k1", "paidBy": "sam", "shared": True, "autopay": False}]}}
    pg = await new_page(browser, storage={"zendom:data": json.dumps(v6)}, clock="2026-10-29T10:00:00-07:00")
    s = await stored(pg)
    keys = await ev(pg, "Object.keys(localStorage)")
    b = s["budget"]["bills"][0]
    check("migration v6->v7: bill kept and anchored to the 31st", s["version"] == await ev(pg, "SCHEMA") and b["name"] == "Rent" and b["amount"] == 250000 and b["anchorDay"] == 31 and b["categoryId"] == "k1")
    check("migration v6->v7: safety copy made", any(k.startswith("zendom:backup:before-v") for k in keys))
    # pay it through the UI twice
    await act(pg, "tab", "more"); await act(pg, "mtab", "budget"); await act(pg, "btab", "spending")
    await act(pg, "payBill", "b1"); await act(pg, "payBill", "b1")
    s = await stored(pg)
    check("bill: paying twice via the button goes Oct 31 -> Nov 30 -> Dec 31", s["budget"]["bills"][0]["nextDue"] == "2026-12-31" and len(s["budget"]["txns"]) == 2, s["budget"]["bills"][0]["nextDue"])
    await act(pg, "undo")
    s = await stored(pg)
    check("bill: undo restores the previous due date", s["budget"]["bills"][0]["nextDue"] == "2026-11-30" and len(s["budget"]["txns"]) == 1)
    # editing the amount only keeps the anchor; typing a new date resets it
    await act(pg, "editBill", "b1"); await fill(pg, {"bamt": "2600"}); await submit(pg)
    check("bill: editing amount keeps the 31st", (await stored(pg))["budget"]["bills"][0]["anchorDay"] == 31)
    await act(pg, "editBill", "b1"); await fill(pg, {"bdue": "2026-12-01"}); await submit(pg)
    check("bill: new due date resets the repeat day", (await stored(pg))["budget"]["bills"][0]["anchorDay"] == 1)
    await act(pg, "editBill", "b1"); await fill(pg, {"bname": ""}); await submit(pg)
    check("bill: empty name rejected", "Name the bill" in (await err_text(pg)))
    await pg.locator('#sheetForm [data-act=closeSheet]').click()
    await act(pg, "editBill", nth=0)   # the "+ Add" link opens an empty bill form
    await submit(pg)
    check("bill: new bill with no name rejected", "Name the bill" in (await err_text(pg)))
    await pg.locator('#sheetForm [data-act=closeSheet]').click()
    check("bill flows: no page errors", not pg.errors, "; ".join(pg.errors))
    await pg.context.close()


async def test_dupes(browser):
    pg = await new_page(browser, storage={}, clock="2026-10-29T10:00:00-07:00")
    await ev(pg, "state.pantry=[{id:'p1',name:'Eggs',qty:'6',room:'fridge',expires:'2026-11-05',example:false}]; state.grocery=[]; save(); render()")
    await act(pg, "tab", "kitchen"); await act(pg, "ktab", "grocery")
    for name in ["Large eggs", "Paper towels", "Basil"]:
        await pg.fill("#gname", name); await pg.locator("#gadd button[type=submit]").click(); await pg.wait_for_timeout(50)
    await ev(pg, "state.grocery.find(g=>g.name==='Large eggs').qty='12'; state.grocery.find(g=>g.name==='Paper towels').aisle='Household'; save(); render()")
    for g in await ev(pg, "state.grocery.map(g=>g.id)"):
        await act(pg, "gcheck", g)
    await act(pg, "putAway")
    s = await stored(pg)
    eggs = [x for x in s["pantry"] if "egg" in x["name"].lower()]
    check("putaway: eggs merged into the existing entry", len(eggs) == 1 and eggs[0]["id"] == "p1" and eggs[0]["qty"] == "18" and eggs[0]["expires"] == "2026-11-05", json.dumps(eggs))
    check("putaway: new item added", any(x["name"] == "Basil" for x in s["pantry"]))
    check("putaway: household item not stored as food", not any(x["name"] == "Paper towels" for x in s["pantry"]) and not s["grocery"])
    toast = await ev(pg, "document.querySelector('#toastRoot').innerText")
    check("putaway: toast explains all three", "1 put away" in toast and "1 added to what you had" in toast and "1 household or pet item cleared" in toast, toast)
    await act(pg, "undo")
    s = await stored(pg)
    check("putaway: undo restores list and pantry", len(s["grocery"]) == 3 and all(x["checked"] for x in s["grocery"]) and len(s["pantry"]) == 1 and s["pantry"][0]["qty"] == "6")
    # unit-mismatch quantities are kept side by side, not lost
    r = await ev(pg, "mergeQty('1 lb', '2 cups')")
    check("putaway: mismatched units kept side by side", r == "1 lb + 2 cups", r)
    # manual pantry add warns, second Save keeps both
    await act(pg, "ktab", "pantry"); await act(pg, "room", "freezer"); await act(pg, "newPantry")
    await fill(pg, {"pname": "eggs"}); await submit(pg)
    e = await err_text(pg)
    check("pantry: duplicate warns and names the room", await sheet_open(pg) and "already in Fridge" in e and "(6)" in e, e)
    check("pantry: warning offers to open the existing one", await ev(pg, "!!document.querySelector('#sheetForm [data-act=openDupPantry]')"))
    await submit(pg)
    check("pantry: second Save keeps both", len([x for x in (await stored(pg))["pantry"] if x["name"].lower() == "eggs"]) == 2)
    await act(pg, "newPantry"); await fill(pg, {"pname": "Eggs"}); await submit(pg)
    await pg.locator('#sheetForm [data-act=openDupPantry]').click(); await pg.wait_for_timeout(80)
    check("pantry: open-existing jumps to its room and form", await ev(pg, "prefs.pantryRoom") == "fridge" and await ev(pg, "document.querySelector('#pname').value") == "Eggs")
    await fill(pg, {"pqty": "5"}); await submit(pg)
    check("pantry: editing without renaming doesn't warn", not await sheet_open(pg))
    # recipes
    await ev(pg, "state.recipes=[{id:'r1',title:'Mom\u2019s Chili',servings:4,prep:'',cook:'',categories:[],ingredients:['1 lb beans'],steps:['Cook'],notes:'',source:'https://www.example.com/chili/',favorite:false,example:false,created:1,cooked:[],photos:[],pdf:'',pdfName:''}]; state.pantry=[]; save(); render()")
    await act(pg, "ktab", "recipes"); await act(pg, "newRecipe")
    await fill(pg, {"rtitle": "moms chili!"}); await submit(pg)
    e = await err_text(pg)
    check("recipe: same name (case/punctuation) warns", await sheet_open(pg) and "with this name" in e, e)
    await submit(pg)
    check("recipe: second Save keeps both", len((await stored(pg))["recipes"]) == 2)
    await act(pg, "newRecipe")
    await fill(pg, {"rtitle": "Best chili", "source": "http://example.com/chili#comments"}); await submit(pg)
    e = await err_text(pg)
    check("recipe: same link warns", "from the same link" in e, e)
    await pg.locator('#sheetForm [data-act=openDupRecipe]').click(); await pg.wait_for_timeout(80)
    check("recipe: open-existing shows that recipe", "Chili" in await ev(pg, "document.querySelector('#sheetTitle').textContent + document.querySelector('#sheetRoot').innerText"))
    check("recipe: nothing saved from the abandoned form", len((await stored(pg))["recipes"]) == 2)
    await act(pg, "editRecipe", "r1"); await fill(pg, {"servings": "6"}); await submit(pg)
    check("recipe: editing other fields of a duplicate doesn't warn", not await sheet_open(pg) or "already" not in (await err_text(pg)))
    await ev(pg, "document.querySelector('#sheetRoot').innerHTML && closeSheet()")
    await act(pg, "newRecipe"); await fill(pg, {"rtitle": "Totally new soup"}); await submit(pg)
    check("recipe: unique recipe saves first try", not await sheet_open(pg) and len((await stored(pg))["recipes"]) == 3)
    await ev(pg, "ACTIONS.loadExamples(); ACTIONS.loadExamples()")
    titles = [x["title"] for x in (await stored(pg))["recipes"]]
    ex = await ev(pg, "exampleRecipes().map(r => r.title)")
    check("recipe: loading examples twice adds them once", all(titles.count(t) == 1 for t in ex) and len(titles) == 3 + len(ex), str(titles))
    check("dupes: no page errors", not pg.errors, "; ".join(pg.errors))
    await pg.context.close()


async def draw_line(pg, pts):
    box = await pg.locator("#drawCanvas").bounding_box()
    await pg.mouse.move(box["x"] + box["width"] * pts[0][0], box["y"] + box["height"] * pts[0][1])
    await pg.mouse.down()
    for x, y in pts[1:]:
        await pg.mouse.move(box["x"] + box["width"] * x, box["y"] + box["height"] * y, steps=6)
    await pg.mouse.up(); await pg.wait_for_timeout(40)

async def test_drawing(browser):
    pg = await new_page(browser, storage={}, clock="2026-10-29T10:00:00-07:00")
    await act(pg, "tab", "more"); await act(pg, "mtab", "notes")
    n0 = len((await stored(pg))["notes"])
    await act(pg, "newDrawing")
    check("draw: pad opens for a new drawing", await ev(pg, "!!document.querySelector('#drawCanvas') && !document.querySelector('#drawWrap').hidden"))
    await submit(pg)
    check("draw: empty drawing and no words rejected", "Draw something" in (await err_text(pg)), await err_text(pg))
    await draw_line(pg, [(0.1, 0.1), (0.5, 0.5), (0.9, 0.2)])
    await act(pg, "drawInk", "#4f7fc4"); await act(pg, "drawPen", "24")
    await draw_line(pg, [(0.2, 0.8), (0.8, 0.8)])
    await pg.mouse.click(*(lambda b: (b["x"] + b["width"] * 0.5, b["y"] + b["height"] * 0.3))(await pg.locator("#drawCanvas").bounding_box()))
    await pg.wait_for_timeout(40)
    check("draw: three strokes including a dot", await ev(pg, "drawPad.strokes.length") == 3)
    await act(pg, "drawUndo")
    check("draw: undo removes the last stroke", await ev(pg, "drawPad.strokes.length") == 2)
    await act(pg, "drawEraser")
    await draw_line(pg, [(0.2, 0.8), (0.3, 0.8)])
    check("draw: eraser removes the stroke it touches", await ev(pg, "drawPad.strokes.length") == 1 and await ev(pg, "drawPad.strokes[0].c") == "#3a2214")
    await act(pg, "drawUndo")
    check("draw: undo brings an erased stroke back", await ev(pg, "drawPad.strokes.length") == 2)
    await act(pg, "drawClear"); await act(pg, "drawUndo")
    check("draw: clear can be undone", await ev(pg, "drawPad.strokes.length") == 2)
    await submit(pg)
    s = await stored(pg)
    dn = [n for n in s["notes"] if n.get("drawing")]
    check("draw: drawing-only note saves", len(s["notes"]) == n0 + 1 and len(dn) == 1 and dn[0]["text"] == "" and len(dn[0]["drawing"]["strokes"]) == 2)
    st = dn[0]["drawing"]["strokes"]
    check("draw: strokes keep color, width and in-bounds points", st[0]["c"] == "#3a2214" and st[0]["w"] == 10 and st[1]["c"] == "#4f7fc4" and st[1]["w"] == 24 and all(0 <= v <= 1000 for x in st for v in x["p"]) and len(st[0]["p"]) >= 6)
    check("draw: board shows the drawing", await ev(pg, f"!!document.querySelector('[data-act=openNote][data-id=\"{dn[0]['id']}\"] svg.drawing path')"))
    nid = dn[0]["id"]
    await act(pg, "openNote", nid)
    check("draw: note detail shows the drawing", await ev(pg, "document.querySelectorAll('#sheetRoot svg.drawing path').length") == 2)
    await act(pg, "editNote", nid)
    check("draw: editing opens the pad with the drawing", await ev(pg, "!document.querySelector('#drawWrap').hidden && drawPad.strokes.length") == 2)
    await fill(pg, {"text": "tacos tonight?"})
    await draw_line(pg, [(0.6, 0.6), (0.7, 0.7)])
    await submit(pg)
    n = next(x for x in (await stored(pg))["notes"] if x["id"] == nid)
    check("draw: edit adds words and a stroke", n["text"] == "tacos tonight?" and len(n["drawing"]["strokes"]) == 3)
    await act(pg, "newNote")
    check("draw: plain new note keeps the pad closed", await ev(pg, "document.querySelector('#drawWrap').hidden"))
    await submit(pg)
    check("draw: empty plain note still rejected", "words or a drawing" in (await err_text(pg)))
    await act(pg, "drawOpen")
    check("draw: Add a drawing opens the pad", await ev(pg, "!document.querySelector('#drawWrap').hidden"))
    await pg.locator('#sheetForm [data-act=closeSheet]').click()
    # bad stored data is cleaned, not trusted
    await ev(pg, "state.notes.push({id:'bad', text:'', drawing:{strokes:[{c:'red;}<script>', w:999, p:[5,5,99999,-4,'x',3]}]}, author:'sam'}); save()")
    await pg.reload(); await pg.wait_for_timeout(250)
    bad = await ev(pg, "state.notes.find(x => x.id === 'bad') || null")   # cleaned in memory on load
    check("draw: unsafe ink never reaches the page", await ev(pg, "!document.body.innerHTML.includes('red;}<script>')"))
    check("draw: unsafe colors and sizes cleaned on load", bad and bad["drawing"]["strokes"][0]["c"] == "#3a2214" and bad["drawing"]["strokes"][0]["w"] == 10 and bad["drawing"]["strokes"][0]["p"] == [5, 5, 1000, 0], json.dumps(bad))
    check("draw: drawing survives reload", any(x["id"] == nid and len(x["drawing"]["strokes"]) == 3 for x in (await stored(pg))["notes"]))
    check("draw: no page errors", not pg.errors, "; ".join(pg.errors))
    await pg.context.close()
    # v7 notes upgrade to v8 untouched
    v7 = {"version": 7, "notes": [{"id": "n1", "text": "old note", "author": "charlie", "color": "mint"}]}
    pg = await new_page(browser, storage={"zendom:data": json.dumps(v7)}, clock="2026-10-29T10:00:00-07:00")
    s = await stored(pg)
    check("migration v7->v8: notes kept, no drawing added", s["version"] == 8 and s["notes"][0]["text"] == "old note" and s["notes"][0]["drawing"] is None)
    await pg.context.close()


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        await run_all(browser)
        await test_dates(browser)
        await test_dupes(browser)
        await test_drawing(browser)
        await browser.close()
    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)} of {len(results)} checks passed")
    sys.exit(1 if failed else 0)

asyncio.run(main())
