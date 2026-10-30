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

async def new_page(browser, storage=None, clock=None, ticking=False):
    ctx = await browser.new_context(viewport={"width": 390, "height": 844}, timezone_id="America/Los_Angeles", accept_downloads=True)
    # block the Google Fonts request (no network in the test sandbox)
    await ctx.route("**/fonts.googleapis.com/**", lambda r: r.abort())
    await ctx.route("**/fonts.gstatic.com/**", lambda r: r.abort())
    pg = await ctx.new_page()
    pg.errors = []
    pg.on("pageerror", lambda e: pg.errors.append(str(e)))
    if clock and ticking:
        await pg.clock.install(time=clock)          # time can be moved forward with pg.clock.run_for
    elif clock:
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
    check("bottom bar is Today, Chores, Kitchen, Budget, More", await ev(pg, "[...document.querySelectorAll('#nav button')].map(b => b.dataset.id).join(',')") == "today,chores,kitchen,budget,more")
    for tab in ["today", "chores", "kitchen", "budget", "more"]:
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
    for k in ["notes", "family", "settings"]:
        await act(pg, "mtab", k)
        check(f"more sub-tab {k} renders", await ev(pg, f"document.querySelector('[data-act=mtab][data-id={k}]').getAttribute('aria-selected')") == "true")
    await act(pg, "mtab", "notes")
    await act(pg, "tab", "budget")
    check("budget tab shows its add-spending button", await ev(pg, "document.querySelector('#fab').dataset.act") == "newTxn" and not await ev(pg, "document.querySelector('#fab').hidden"))
    for k in ["spending", "plan", "fund"]:
        await act(pg, "btab", k)
        check(f"budget sub-tab {k} renders", await ev(pg, f"document.querySelector('[data-act=btab][data-id={k}]').getAttribute('aria-pressed')") == "true")
    await act(pg, "btab", "spending")
    await act(pg, "tab", "more"); await act(pg, "mtab", "family")
    check("family has no stray add button", await ev(pg, "document.querySelector('#fab').hidden"))
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
    await act(pg, "tab", "more"); await act(pg, "mtab", "family")
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
    check("event: a vet visit offers to add it to health history", "Add to health history?" in await ev(pg, "document.querySelector('#sheetTitle').innerText"))
    await ev(pg, "closeSheet()")
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
    await act(pg, "tab", "budget")
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
    for tab in ["today", "chores", "kitchen", "budget", "more"]:
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

    # a phone last left on the old Family tab, or on More → Budget
    pg = await new_page(browser, storage={"zendom:prefs": json.dumps({"tab": "family", "fam": "paprika"})}, clock="2026-10-29T10:00:00-07:00")
    check("old Family tab opens More → Family", await ev(pg, "prefs.tab + '/' + prefs.moreTab") == "more/family" and "Paprika" in await ev(pg, "document.querySelector('#view').innerText"))
    await pg.context.close()
    pg = await new_page(browser, storage={"zendom:prefs": json.dumps({"tab": "more", "moreTab": "budget"})}, clock="2026-10-29T10:00:00-07:00")
    check("old More → Budget opens the Budget tab", await ev(pg, "prefs.tab") == "budget" and await ev(pg, "!!document.querySelector('[data-act=btab]')"))
    check("Health heads-up's Family link goes to More → Family", await ev(pg, "ACTIONS.goFam('charlie'); prefs.tab + '/' + prefs.moreTab + '/' + prefs.fam") == "more/family/charlie")
    check("Bills due's Budget link goes to the Budget tab", await ev(pg, "ACTIONS.goBudget(); prefs.tab") == "budget")
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
    await act(pg, "tab", "budget"); await act(pg, "btab", "spending")
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
    check("migration v7->v8: notes kept, no drawing added", s["version"] == await ev(pg, "SCHEMA") and s["notes"][0]["text"] == "old note" and s["notes"][0]["drawing"] is None)
    await pg.context.close()


async def test_calendar_links(browser):
    from urllib.parse import urlparse, parse_qs
    pg = await new_page(browser, storage={}, clock="2026-10-29T10:00:00-07:00")
    await ev(pg, "state.events=[{id:'ev1', title:'Vet: Paprika', date:'2026-11-03', time:'14:30', who:'', repeat:'yearly', note:'Bring the carrier, treats; and vax card'}, {id:'ev2', title:'Anniversary', date:'2026-12-31', time:'', who:'', repeat:'none', note:''}]; save(); render()")
    await act(pg, "tab", "today"); await act(pg, "tview", "week")
    await ev(pg, "eventForm('ev1')")
    hrefs = await ev(pg, "[...document.querySelectorAll('#sheetForm a.chip')].map(a => a.href)")
    check("cal: event form offers Google and two Outlook links", len(hrefs) == 3 and "calendar.google.com" in hrefs[0] and "outlook.office.com" in hrefs[1] and "outlook.live.com" in hrefs[2], str(hrefs))
    g = parse_qs(urlparse(hrefs[0]).query)
    # 2:30pm Pacific on Nov 3 2026 is 22:30 UTC (PST, after the Nov 1 change)
    check("cal: Google link has title, UTC times and the yearly repeat", g["action"] == ["TEMPLATE"] and g["text"] == ["Vet: Paprika"] and g["dates"] == ["20261103T223000Z/20261103T233000Z"] and g["recur"] == ["RRULE:FREQ=YEARLY"] and "treats" in g["details"][0], str(g))
    o = parse_qs(urlparse(hrefs[1]).query)
    check("cal: Outlook link has title and UTC start/end", o["subject"] == ["Vet: Paprika"] and o["startdt"] == ["2026-11-03T22:30:00Z"] and o["enddt"] == ["2026-11-03T23:30:00Z"] and o["allday"] == ["false"] and o["rru"] == ["addevent"], str(o))
    check("cal: repeating event warns Outlook links can't repeat", "can't repeat" in await ev(pg, "document.querySelector('#sheetForm').innerText"))
    ics = await ev(pg, "icsText(state.events[0])")
    lines = ics.split("\r\n")
    check("cal: .ics is a valid single event", lines[0] == "BEGIN:VCALENDAR" and "BEGIN:VEVENT" in lines and lines[-2] == "END:VCALENDAR" and lines[-1] == "" and "DTSTART:20261103T223000Z" in lines and "RRULE:FREQ=YEARLY" in lines, ics[:400])
    unfolded = ics.replace("\r\n ", "")
    check("cal: .ics escapes commas, semicolons and new lines", "DESCRIPTION:Bring the carrier\\, treats\\; and vax card\\n\\nFrom zen·dom" in unfolded, unfolded)
    check("cal: .ics lines are folded under 75 bytes", all(len(l.encode()) <= 75 for l in lines))
    async with pg.expect_download() as dl:
        await act(pg, "icsFile", "ev1")
    d = await dl.value
    check("cal: tapping Calendar file downloads an .ics", d.suggested_filename == "Vet Paprika.ics", d.suggested_filename)
    await pg.locator('#sheetForm [data-act=closeSheet]').click()
    await ev(pg, "eventForm('ev2')")
    hrefs = await ev(pg, "[...document.querySelectorAll('#sheetForm a.chip')].map(a => a.href)")
    g = parse_qs(urlparse(hrefs[0]).query); o = parse_qs(urlparse(hrefs[1]).query)
    check("cal: all-day event uses whole days", g["dates"] == ["20261231/20270101"] and "recur" not in g and o["allday"] == ["true"] and o["startdt"] == ["2026-12-31"], str(g) + str(o))
    check("cal: all-day .ics uses dates", "DTSTART;VALUE=DATE:20261231" in await ev(pg, "icsText(state.events[1])"))
    check("cal: no repeat warning on a one-off event", "can't repeat" not in await ev(pg, "document.querySelector('#sheetForm').innerText"))
    await pg.locator('#sheetForm [data-act=closeSheet]').click()
    await ev(pg, "eventForm(null, '2026-11-05')")
    check("cal: new unsaved event shows no calendar links yet", await ev(pg, "document.querySelectorAll('#sheetForm a.chip').length") == 0)
    check("cal: no page errors", not pg.errors, "; ".join(pg.errors))
    await pg.context.close()


async def test_appointments(browser):
    pg = await new_page(browser, storage={}, clock="2026-10-29T10:00:00-07:00")
    await act(pg, "tab", "more"); await act(pg, "mtab", "family"); await act(pg, "fam", "sam")
    await act(pg, "editCheckup")
    await fill(pg, {"cname": "Dentist cleaning", "months": "6", "last": "2026-04-20", "ndate": "2026-10-01"})
    await submit(pg)
    check("appt: booking a past date is refused", "already happened" in await err_text(pg), await err_text(pg))
    await fill(pg, {"ndate": "", "ntime": "09:15"})
    await submit(pg)
    check("appt: a time without a date is refused", "Add the date" in await err_text(pg))
    await fill(pg, {"ndate": "2026-11-04", "ntime": "09:15", "nwhere": "Dr. Lee, 2nd floor"})
    await submit(pg)
    c = (await stored(pg))["people"]["sam"]["checkups"][0]
    check("appt: booking saves date, time and place", c["next"] == {"date": "2026-11-04", "time": "09:15", "where": "Dr. Lee, 2nd floor"} and c["last"] == "2026-04-20", json.dumps(c))
    check("appt: toast says it's booked", "Booked for" in await ev(pg, "document.querySelector('#toastRoot').innerText"))
    check("appt: list shows the booking", "Booked Nov 4" in await ev(pg, "document.querySelector('#view').innerText"))
    items = await ev(pg, "calendarItems('2026-11-01','2026-11-30').filter(x => x.type === 'health').map(x => [x.date, x.title, x.time || ''])")
    check("appt: calendar shows it on the booked day with its time", ["2026-11-04", "Sam: Dentist cleaning", "09:15"] in items, str(items))
    await ev(pg, "ACTIONS.tab('today'); ACTIONS.tview('today')")
    check("appt: Today's health heads-up lists it within a week", "Booked Nov 4" in await ev(pg, "document.querySelector('#view').innerText"))
    await ev(pg, "ACTIONS.goFam('sam')")
    await act(pg, "editCheckup", c["id"])
    hrefs = await ev(pg, "[...document.querySelectorAll('#sheetForm a.chip')].map(a => a.href)")
    check("appt: add-to-calendar links appear for a booking", len(hrefs) == 3 and "Dentist" in hrefs[0])
    async with pg.expect_download() as dl:
        await act(pg, "icsFile", "appt~" + c["id"])
    check("appt: calendar file for the appointment", (await dl.value).suggested_filename.startswith("Sam Dentist"))
    await fill(pg, {"ndate": "2026-11-12", "ntime": "16:00"})
    await submit(pg)
    check("appt: reschedule moves it", (await stored(pg))["people"]["sam"]["checkups"][0]["next"]["date"] == "2026-11-12" and "Rescheduled" in await ev(pg, "document.querySelector('#toastRoot').innerText"))
    await act(pg, "editCheckup", c["id"])
    await act(pg, "apptCancel", c["id"])
    check("appt: cancel clears it", (await stored(pg))["people"]["sam"]["checkups"][0]["next"] is None)
    await act(pg, "undo")
    check("appt: cancel can be undone", (await stored(pg))["people"]["sam"]["checkups"][0]["next"]["date"] == "2026-11-12")
    # it happened: jump the clock past the appointment
    await pg.context.close()
    data = await stored(pg) if False else None
    pg2 = await new_page(browser, storage={"zendom:data": json.dumps({"version": 9, "people": {"sam": {"name": "Sam", "checkups": [{"id": "k1", "name": "Eye exam", "months": 12, "last": "2025-10-01", "provider": "", "next": {"date": "2026-10-27", "time": "", "where": ""}}]}}})}, clock="2026-10-29T10:00:00-07:00")
    await ev(pg2, "ACTIONS.goFam('sam')")
    check("appt: a passed booking asks if it happened", "Did it happen?" in await ev(pg2, "document.querySelector('#view').innerText"))
    await act(pg2, "editCheckup", "k1")
    await act(pg2, "apptDone", "k1")
    k = (await stored(pg2))["people"]["sam"]["checkups"][0]
    check("appt: Mark as done logs the visit on its date", k["last"] == "2026-10-27" and k["next"] is None, json.dumps(k))
    check("appt: and says when the next one is due", "next due around Oct 27, 2027" in await ev(pg2, "document.querySelector('#toastRoot').innerText"))
    check("appt: no page errors", not pg2.errors, "; ".join(pg2.errors))
    await pg2.context.close()
    # older data upgrades without inventing appointments
    pg3 = await new_page(browser, storage={"zendom:data": json.dumps({"version": 8, "people": {"sam": {"name": "Sam", "checkups": [{"id": "k2", "name": "Physical", "months": 12, "last": "2026-01-10"}]}}})}, clock="2026-10-29T10:00:00-07:00")
    k = (await stored(pg3))["people"]["sam"]["checkups"][0]
    check("migration v8->v9: checkups kept, nothing booked", (await stored(pg3))["version"] == 9 and k["last"] == "2026-01-10" and k["next"] is None)
    await pg3.context.close()


async def test_status(browser):
    pg = await new_page(browser, clock="2026-11-12T10:00:00-08:00")
    view = lambda: ev(pg, "document.querySelector('#view').innerText")
    check("status: Today invites you to set one", "Tap to pick a face" in await view())
    # top-right buttons are now Family shortcuts, not a user switch
    await pg.locator('#who [data-id="charlie"]').click(); await pg.wait_for_timeout(80)
    check("top-right Charlie opens Charlie's profile", await ev(pg, "prefs.tab + '/' + prefs.moreTab + '/' + prefs.fam") == "more/family/charlie")
    check("…without changing whose Today it is", await ev(pg, "prefs.user") == "sam")
    await pg.locator('#who [data-id="sam"]').click(); await pg.wait_for_timeout(80)
    check("top-right Sam opens Sam's profile", await ev(pg, "prefs.fam") == "sam" and "Change status" in await view())
    # signed out: choose whose phone in Settings
    await ev(pg, "ACTIONS.tab('more'); ACTIONS.mtab('settings')")
    check("settings: whose-phone choice shown when signed out", "Whose phone is this?" in await view())
    await act(pg, "setUser", "charlie"); await ev(pg, "ACTIONS.tab('today')")
    check("settings: picking Charlie makes Today Charlie's", "Charlie" in await ev(pg, "document.querySelector('.hero h1').innerText"))
    await ev(pg, "ACTIONS.setUser('sam'); ACTIONS.tab('today')")
    # set a status: empty is refused
    await act(pg, "setStatus")
    check("status: sheet opens", await sheet_open(pg))
    await submit(pg)
    check("status: empty is refused with a message", await sheet_open(pg) and "Pick a face or type" in await ev(pg, "document.querySelector('#sheetForm').innerText"))
    await pg.locator('#sheetForm [data-act="statusPreset"]', has_text="Napping").click()
    await submit(pg)
    st = (await stored(pg))["people"]["sam"]["status"]
    check("status: preset saves a face and words", st["face"] == "sleepy" and st["text"] == "Napping" and st["at"] > 0, json.dumps(st))
    dbg = await ev(pg, "[document.querySelector('.status-card .strow .sbub') && document.querySelector('.status-card .strow .sbub').textContent, document.querySelectorAll('.status-card .strow:first-child .face rect').length, (faceSVG('sam','sleepy').match(/<rect/g)||[]).length]")
    check("status: shows on Today in a speech bubble with the face", dbg[0] == "Napping" and dbg[1] == dbg[2] and "just now" in await view(), json.dumps(dbg))
    check("status: little speech bubble on the top-right avatar", await ev(pg, "!!document.querySelector('#who [data-id=sam] .st') && !document.querySelector('#who [data-id=charlie] .st')"))
    await ev(pg, "ACTIONS.goFam('sam')")
    check("status: shows on the Family profile", "Napping" in await view() and "Sleepy" in await view())
    await ev(pg, "ACTIONS.goFam('charlie')")
    check("status: can't change someone else's", "Change status" not in await view() and "No status set" in await view())
    # a face with no words is a status too; every face draws; tail wag animates
    await ev(pg, "ACTIONS.tab('today')"); await act(pg, "setStatus")
    ftxt = await ev(pg, "document.querySelector('#sheetForm').innerText")
    check("faces: all 17 offered, with the renamed and new ones", await ev(pg, "document.querySelectorAll('#sheetForm input[name=sface]').length") == 17 and all(n in ftxt for n in ("Normal style", "Tail wag", "Doggy world", "Idiot hair", "Hamburger", "Muggin'")))
    await pg.locator('#sheetForm label', has_text="Tail wag").click(); await fill(pg, {"stext": ""}); await submit(pg)
    st = (await stored(pg))["people"]["sam"]["status"]
    check("faces: a face alone saves", st["face"] == "wag" and st["text"] == "", json.dumps(st))
    check("faces: tail wag has two animated tail frames", await ev(pg, "document.querySelectorAll('.status-card .face .wa rect').length > 0 && document.querySelectorAll('.status-card .face .wb rect').length > 0"))
    sizes = await ev(pg, "FACE_KEYS.flatMap(k => ['sam','charlie'].map(w => (faceSVG(w,k).match(/<rect/g)||[]).length))")
    check("faces: every face renders for both of you", all(n > 200 for n in sizes) and len(set(sizes)) > 10, json.dumps(sizes))
    await ev(pg, "ACTIONS.tab('today')")
    # edit with typed text, over-long
    await ev(pg, "ACTIONS.tab('today')"); await act(pg, "setStatus")
    await fill(pg, {"stext": "x" * 120}); await submit(pg)
    check("status: long text kept to 80 characters", len((await stored(pg))["people"]["sam"]["status"]["text"]) <= 80)
    await act(pg, "setStatus"); await act(pg, "clearStatus")
    st = (await stored(pg))["people"]["sam"]["status"]
    check("status: Clear status empties it", st["face"] == "normal" and st["text"] == "")
    # a status change never becomes a notification; a real profile edit still does
    r = await ev(pg, """(() => { const o = JSON.parse(JSON.stringify(state.people.sam)); const n = Object.assign({}, o, {status:{emoji:'🎧',text:'Focus',at:1}});
      const m = Object.assign({}, o, {name:'Sammy'}); return [describeChange('person~sam', o, n), describeChange('person~sam', o, m)]; })()""")
    check("status: no notification for a status change", r[0] is None and r[1] and "profile" in r[1], json.dumps(r))
    # signed in as Charlie: this phone can't be switched to Sam
    await ev(pg, "sync.user = {email:'charliepurdomva@gmail.com'}; prefs.user = 'charlie'; ACTIONS.setUser('sam')")
    check("signed in: Today stays with the signed-in person", await ev(pg, "prefs.user") == "charlie")
    await ev(pg, "sync.user = null")
    check("status: no page errors", not pg.errors, "; ".join(pg.errors))
    await pg.context.close()
    # forms: radio chips stay small, date box stays inside the sheet
    pg = await new_page(browser)
    await ev(pg, "ACTIONS.tab('budget'); ACTIONS.newTxn()")
    box = await ev(pg, "(() => { const r = document.querySelector('#sheetForm input[name=paidBy]') || document.querySelector('#sheetForm input[type=radio]'); const b = r.getBoundingClientRect(); return [b.width, b.height]; })()")
    check("forms: who-paid radio is a small circle", box[0] <= 24 and box[1] <= 24, json.dumps(box))
    over = await ev(pg, "(() => { const d = document.querySelector('#sheetForm input[type=date]'), f = document.querySelector('#sheetForm'); return d.getBoundingClientRect().right - f.getBoundingClientRect().right; })()")
    check("forms: date box stays inside the sheet", over <= 0.5, over)
    await pg.locator('#sheetForm input[name=tnote]').first.focus(); await pg.wait_for_timeout(50)
    check("typing hides the bottom bar", await ev(pg, "getComputedStyle(document.querySelector('nav.nav')).display") == "none")
    await pg.locator('#sheetForm input[type=radio]').first.focus(); await pg.wait_for_timeout(120)
    check("…and it comes back after", await ev(pg, "getComputedStyle(document.querySelector('nav.nav')).display") != "none")
    small = await ev(pg, "[...document.querySelectorAll('#sheetForm input:not([type=radio]):not([type=checkbox]),#sheetForm select')].filter(e => parseFloat(getComputedStyle(e).fontSize) < 16).length")
    check("forms: text boxes are 16px+ so iPhone doesn't zoom", small == 0, small)
    await pg.context.close()
    # older data without statuses, and junk statuses, load fine
    pg = await new_page(browser, storage={"zendom:data": json.dumps({"version": 9, "people": {"sam": {"name": "Sam"}, "charlie": {"name": "Charlie", "status": {"emoji": 5, "text": {"x": 1}, "at": "nope"}}}})})
    d = {"people": await ev(pg, "state.people")}
    check("status: old data gets an empty status", d["people"]["sam"]["status"] == {"face": "normal", "emoji": "", "text": "", "at": 0} and "status" not in d["people"]["paprika"], json.dumps(d["people"]["sam"].get("status")))
    check("status: junk is cleaned up", d["people"]["charlie"]["status"]["at"] == 0 and isinstance(d["people"]["charlie"]["status"]["text"], str))
    check("status: old data no page errors", not pg.errors, "; ".join(pg.errors))
    await pg.context.close()


async def test_smart(browser):
    pg = await new_page(browser, clock="2026-11-12T10:00:00-08:00")
    view = lambda: ev(pg, "document.querySelector('#view').innerText")
    check("payback: nothing when even", "back $" not in await view())
    # Charlie pays $2,000 rent, shared -> Sam owes $1,000
    await ev(pg, "state.budget.txns.push({id:'r1', kind:'expense', amount:200000, date:'2026-11-01', categoryId:null, paidBy:'charlie', shared:true, note:'Rent', billId:null}); save(); ACTIONS.tab('today')")
    check("payback: Sam's Today says pay Charlie back $1,000", "Pay Charlie back $1,000" in await view(), (await view())[:400])
    await ev(pg, "prefs.user = 'charlie'; render()")
    check("payback: not on Charlie's Today", "back $" not in await view())
    await ev(pg, "prefs.user = 'sam'; render()")
    await act(pg, "settleUp")
    check("payback: I paid opens the payment form with the amount", await ev(pg, "document.querySelector('#samt').value") in ("1000", "1000.00", "1,000.00"), await ev(pg, "document.querySelector('#samt').value"))
    await submit(pg)
    check("payback: gone once paid", "back $" not in await view())
    # health spotting
    await ev(pg, "ACTIONS.tview('week'); ACTIONS.newEvent('2026-11-20')")
    await fill(pg, {"etitle": "Charlie dentist", "etime": "09:30", "enote": "Dr. Lee, 2nd floor"}); await submit(pg)
    check("health: a dentist event asks to add it", await sheet_open(pg) and "Add to health history?" in await ev(pg, "document.querySelector('#sheetForm').innerText"))
    check("health: guesses Charlie from the title and the visit type", await ev(pg, "document.querySelector('input[name=hwho]:checked').value") == "charlie" and await ev(pg, "document.querySelector('#hname').value") == "Dentist cleaning")
    await submit(pg)
    d = await stored(pg); c = [x for x in d["people"]["charlie"]["checkups"] if x["name"] == "Dentist cleaning"]
    check("health: booked as Charlie's next dentist appointment", len(c) == 1 and c[0]["next"] == {"date": "2026-11-20", "time": "09:30", "where": "Dr. Lee, 2nd floor"}, json.dumps(c))
    check("health: no duplicate on the calendar", not any(e["title"] == "Charlie dentist" for e in d["events"]) and await ev(pg, "calendarItems('2026-11-20','2026-11-20').filter(x => /dentist/i.test(x.title)).length") == 1)
    await act(pg, "undo")
    d = await stored(pg)
    check("health: undo puts the event back", any(e["title"] == "Charlie dentist" for e in d["events"]) and not any(x["name"] == "Dentist cleaning" for x in d["people"]["charlie"]["checkups"]))
    # vet in the past -> logged for Paprika; 'Not now' leaves things alone
    await ev(pg, "ACTIONS.newEvent('2026-11-02')"); await fill(pg, {"etitle": "Vet for shots"}); await submit(pg)
    check("health: vet goes to Paprika", await ev(pg, "document.querySelector('input[name=hwho]:checked').value") == "paprika")
    await submit(pg)
    k = [x for x in (await stored(pg))["people"]["paprika"]["checkups"] if x["name"] == "Wellness exam"]
    check("health: a past visit is logged as the last visit", len(k) == 1 and k[0]["last"] == "2026-11-02" and k[0]["next"] is None, json.dumps(k))
    n = len((await stored(pg))["events"])
    await ev(pg, "ACTIONS.newEvent('2026-11-25')"); await fill(pg, {"etitle": "Dr. Patel follow up"}); await submit(pg)
    await pg.locator('#sheetForm [data-act="closeSheet"]').click(); await pg.wait_for_timeout(60)
    d = await stored(pg)
    check("health: Not now keeps just the calendar event", len(d["events"]) == n + 1 and not any(x["name"].startswith("Dr. Patel") for k2 in ("sam","charlie") for x in d["people"][k2]["checkups"]))
    await ev(pg, "ACTIONS.newEvent('2026-11-26')"); await fill(pg, {"etitle": "Dinner with Mom"}); await submit(pg)
    check("health: ordinary events don't ask", not await sheet_open(pg))
    r = await ev(pg, "['Hair appointment','Physical therapy','Eye exam','Derm','Vision check','Team checkup sync'].map(t => healthGuess(t) && healthGuess(t).name)")
    check("health: word matching behaves as expected (incl. a known false positive)", r == [None, "Physical", "Eye exam", "Dermatology", "Eye exam", "Physical"], json.dumps(r))
    check("smart: no page errors", not pg.errors, "; ".join(pg.errors))
    await pg.context.close()


async def test_qol(browser):
    pg = await new_page(browser, clock="2026-10-29T22:00:00-07:00")
    view = lambda: ev(pg, "document.querySelector('#view').innerText")
    # Add event uses the selected day (month) / the visible week (week)
    await ev(pg, "ACTIONS.tab('today'); ACTIONS.tview('month'); ACTIONS.calPick('2026-10-30')")
    await pg.locator('#fab').click(); await pg.wait_for_timeout(60)
    check("calendar: Add event on Month uses the selected day", await ev(pg, "document.querySelector('#edate').value") == "2026-10-30")
    await ev(pg, "closeSheet()")
    await ev(pg, "ACTIONS.calPick('2026-11-01')")
    check("calendar: tapping Nov 1 from October opens November", await ev(pg, "curCalMonth()") == "2026-11" and "November" in await view() and await ev(pg, "calDay") == "2026-11-01")
    await pg.locator('#fab').click(); await pg.wait_for_timeout(60)
    check("calendar: and Add event starts on Nov 1", await ev(pg, "document.querySelector('#edate').value") == "2026-11-01")
    await ev(pg, "closeSheet(); ACTIONS.calMonthNav('-1')")
    check("calendar: month arrows still work after that", await ev(pg, "curCalMonth()") == "2026-10")
    await ev(pg, "ACTIONS.tview('week'); ACTIONS.calWeekNav('1')")
    await pg.locator('#fab').click(); await pg.wait_for_timeout(60)
    check("calendar: Add event on next week starts on that week", await ev(pg, "document.querySelector('#edate').value") == await ev(pg, "curCalWeek()") and await ev(pg, "curCalWeek()") > "2026-10-29")
    await ev(pg, "closeSheet(); ACTIONS.calWeekNav('0')")
    await pg.locator('#fab').click(); await pg.wait_for_timeout(60)
    check("calendar: this week starts on today", await ev(pg, "document.querySelector('#edate').value") == "2026-10-29")
    await ev(pg, "closeSheet()")
    # Board link lands on the board
    await ev(pg, "ACTIONS.tab('more'); ACTIONS.mtab('settings'); ACTIONS.tab('today'); ACTIONS.tview('today')")
    await pg.locator('[data-act=goTo][data-id="more/notes"]').click(); await pg.wait_for_timeout(60)
    check("Board link opens More on the board", await ev(pg, "prefs.tab + '/' + prefs.moreTab") == "more/notes")
    # Notify pop-up goes away when you go somewhere else, or open a form
    await ev(pg, "ACTIONS.tab('today'); showNudge(['finished “Dishes”'])")
    check("nudge: shows", await ev(pg, "!!document.querySelector('.nudge')"))
    await pg.locator('nav.nav [data-id=chores]').click(); await pg.wait_for_timeout(60)
    check("nudge: gone after switching pages", not await ev(pg, "!!document.querySelector('.nudge')") and await ev(pg, "notifyQ.nudge") is None)
    await ev(pg, "showNudge(['added a chore'])"); await ev(pg, "ACTIONS.newChore()")
    check("nudge: gone when a form opens", not await ev(pg, "!!document.querySelector('.nudge')"))
    await ev(pg, "closeSheet(); showNudge(['added a chore']); render()")
    check("nudge: stays if you're still on the same page", await ev(pg, "!!document.querySelector('.nudge')"))
    await ev(pg, "nudgeDismiss()")
    # Plan a meal on next week starts there
    await ev(pg, "ACTIONS.tab('kitchen'); ACTIONS.ktab('plan'); ACTIONS.week('1')")
    await pg.locator('#fab').click(); await pg.wait_for_timeout(60)
    check("meal plan: Plan a meal on next week starts on that week", await ev(pg, "document.querySelector('#mdate').value") == await ev(pg, "curWeek()"))
    await ev(pg, "closeSheet(); ACTIONS.week('0')")
    # chore hidden by the filter: filter follows it
    await ev(pg, "ACTIONS.tab('chores'); ACTIONS.filter('me'); ACTIONS.newChore()")
    await fill(pg, {"title": "Vacuum the stairs"}); await pg.locator('#sheetForm input[name=owner][value=charlie]').check(); await submit(pg)
    check("chores: a new card for Charlie shows instead of vanishing", await ev(pg, "prefs.choreFilter") == "them" and "Vacuum the stairs" in await view())
    # pantry item added to another room: go there
    await ev(pg, "ACTIONS.tab('kitchen'); ACTIONS.ktab('pantry'); ACTIONS.room('fridge'); ACTIONS.newPantry()")
    await fill(pg, {"pname": "Mochi ice cream", "proom": "freezer"}); await submit(pg)
    check("pantry: adding to the freezer from the fridge shows the freezer", await ev(pg, "prefs.pantryRoom") == "freezer" and "Mochi ice cream" in await view())
    # meal comments
    await ev(pg, "ACTIONS.ktab('plan')"); await pg.locator('#fab').click(); await pg.wait_for_timeout(60)
    await fill(pg, {"mtext": "Tacos", "mcomment": "I'll cook!"}); await submit(pg)
    d = await stored(pg); m = [x for x in d["meals"] if x["text"] == "Tacos"]
    check("meal comments: a comment can go with a new meal", len(m) == 1 and m[0]["comments"][0]["text"] == "I'll cook!" and m[0]["comments"][0]["by"] == "sam", json.dumps(m))
    check("meal comments: count shows on the plan", "1 comment" in await view())
    await ev(pg, "ACTIONS.tab('today'); ACTIONS.tview('today')")
    check("meal comments: latest shows on Today's dinner card", "Sam: I'll cook!" in await view())
    await ev(pg, "prefs.user = 'charlie'; render()")
    await pg.locator('.soon-card [data-act=editMeal]').click(); await pg.wait_for_timeout(60)
    check("meal comments: the thread shows in the meal", "I'll cook!" in await ev(pg, "document.querySelector('#sheetForm').innerText") and not await ev(pg, "!!document.querySelector('#sheetForm [data-act=delMealComment]')"))
    await fill(pg, {"mcomment": "yay, I'll do dishes"}); await submit(pg)
    m = [x for x in (await stored(pg))["meals"] if x["text"] == "Tacos"][0]
    check("meal comments: reply saved in order", [c["by"] for c in m["comments"]] == ["sam", "charlie"])
    r = await ev(pg, "(() => { const n = state.meals.find(x => x.text === 'Tacos'); const o = Object.assign({}, n, {comments: n.comments.slice(0, 1)}); return describeChange('meal~' + n.id, o, n); })()")
    check("meal comments: described for a notification", r.startswith("commented on Thursday's dinner") and "dishes" in r, r)
    await ev(pg, "prefs.user = 'sam'; render()")
    await ev(pg, "ACTIONS.editMeal(state.meals.find(x => x.text === 'Tacos').id)")
    await pg.locator('#sheetForm [data-act=delMealComment]').click(); await pg.wait_for_timeout(60)
    m = [x for x in (await stored(pg))["meals"] if x["text"] == "Tacos"][0]
    check("meal comments: you can delete your own", [c["by"] for c in m["comments"]] == ["charlie"])
    await act(pg, "undo")
    m = [x for x in (await stored(pg))["meals"] if x["text"] == "Tacos"][0]
    check("meal comments: and undo it", [c["by"] for c in m["comments"]] == ["sam", "charlie"])
    await ev(pg, "closeSheet()")
    # note replies keep their own look (status bubble class no longer leaks)
    await ev(pg, "state.notes[0].replies.push({id:'r1',by:'charlie',text:'ok',at:Date.now()}); save(); noteDetail(state.notes[0].id)")
    bw = await ev(pg, "getComputedStyle(document.querySelector('.reply .bub')).borderTopWidth")
    check("note replies: no status-bubble border", bw in ("0px", ""), bw)
    check("qol: no page errors", not pg.errors, "; ".join(pg.errors))
    await pg.context.close()
    # older meals without comments load fine
    pg = await new_page(browser, storage={"zendom:data": json.dumps({"version": 9, "meals": [{"id": "m1", "date": "2026-10-29", "slot": "dinner", "text": "Soup"}]})}, clock="2026-10-29T18:00:00-07:00")
    check("meal comments: old meals get an empty list", await ev(pg, "JSON.stringify(state.meals[0].comments)") == "[]" and "Soup" in await ev(pg, "document.querySelector('#view').innerText"))
    await ev(pg, "ACTIONS.tab('kitchen'); ACTIONS.ktab('plan')")
    check("meal comments: old meals no page errors", not pg.errors, "; ".join(pg.errors))
    await pg.context.close()


async def test_links(browser):
    pg = await new_page(browser)
    seen = []
    async def handle(route):
        body = json.loads(route.request.post_data or "{}"); seen.append(body)
        u = body.get("url", "")
        if "nodata" in u: data = {"found": False, "title": "Grandma's Pie", "source": u}
        elif "down" in u: return await route.fulfill(status=502, content_type="application/json", body=json.dumps({"error": "the site said 404"}))
        else: data = {"found": True, "title": "Fish Tacos", "servings": 4, "prep": "15 min", "cook": "1 hr 5 min", "ingredients": ["1 lb cod", "2 cups cabbage"], "steps": ["Season the cod.", "Fry it."], "notes": "Crispy.", "source": u}
        await route.fulfill(status=200, content_type="application/json", headers={"Access-Control-Allow-Origin": "*"}, body=json.dumps(data))
    await pg.route("https://notify.test/recipe", handle)
    # signed out: explains, keeps the link
    await ev(pg, "ACTIONS.tab('kitchen'); ACTIONS.ktab('recipes'); ACTIONS.pasteRecipe()")
    await pg.locator('#paste').fill("https://www.example.com/fish-tacos"); await pg.locator('[data-act=fillFromPaste]').click(); await pg.wait_for_timeout(100)
    check("links: signed out, it explains and keeps the link", "needs you signed in" in await ev(pg, "document.querySelector('#pasteStatus').textContent") and await ev(pg, "document.querySelector('#source').value") == "https://www.example.com/fish-tacos")
    await ev(pg, "closeSheet()")
    # signed in
    await ev(pg, "NOTIFY.url = 'https://notify.test'; window.zdBackend = Object.assign(window.zdBackend || {}, {idToken: async () => 'tok-sam'}); sync.user = {email:'samzenteno@gmail.com'}")
    await ev(pg, "ACTIONS.pasteRecipe()")
    await pg.locator('#paste').fill("https://www.example.com/fish-tacos"); await pg.locator('[data-act=fillFromPaste]').click(); await pg.wait_for_timeout(300)
    vals = await ev(pg, "['rtitle','servings','prep','cook','ings','steps','rnotes','source'].map(id => document.querySelector('#' + id).value)")
    check("links: fills the form from the link", vals == ["Fish Tacos", "4", "15 min", "1 hr 5 min", "1 lb cod\n2 cups cabbage", "Season the cod.\nFry it.", "Crispy.", "https://www.example.com/fish-tacos"], json.dumps(vals))
    check("links: sends the sign-in token and the link", seen and seen[-1] == {"idToken": "tok-sam", "url": "https://www.example.com/fish-tacos"}, json.dumps(seen))
    check("links: says what it found", "Got it from example.com: 2 ingredients and 2 steps" in await ev(pg, "document.querySelector('#pasteStatus').textContent"))
    check("links: nothing saved until Save", not any(r["title"] == "Fish Tacos" for r in (await stored(pg))["recipes"]))
    await submit(pg)
    r = [x for x in (await stored(pg))["recipes"] if x["title"] == "Fish Tacos"]
    check("links: Save keeps it, with the source link", len(r) == 1 and r[0]["source"] == "https://www.example.com/fish-tacos" and r[0]["ingredients"] == ["1 lb cod", "2 cups cabbage"])
    # pasting a link straight into the box works too (no button)
    await ev(pg, "ACTIONS.pasteRecipe()")
    await pg.locator('#paste').focus()
    await ev(pg, "(() => { const b = document.querySelector('#paste'); b.value = 'https://site.test/nodata'; b.dispatchEvent(new Event('paste')); })()"); await pg.wait_for_timeout(300)
    check("links: a page without recipe data says so and keeps title + link", "doesn't share its recipe" in await ev(pg, "document.querySelector('#pasteStatus').textContent") and await ev(pg, "document.querySelector('#rtitle').value") == "Grandma's Pie" and await ev(pg, "document.querySelector('#source').value") == "https://site.test/nodata")
    await ev(pg, "closeSheet(); ACTIONS.pasteRecipe()")
    await pg.locator('#paste').fill("https://site.test/down"); await pg.locator('[data-act=fillFromPaste]').click(); await pg.wait_for_timeout(300)
    check("links: a broken page is explained", "Couldn't read that link (the site said 404)" in await ev(pg, "document.querySelector('#pasteStatus').textContent"))
    await ev(pg, "closeSheet(); ACTIONS.pasteRecipe()")
    await pg.locator('#paste').fill("2 cups rice\n1 egg\n\nFry the rice. Add the egg."); await pg.locator('[data-act=fillFromPaste]').click(); await pg.wait_for_timeout(100)
    check("links: pasted recipe text still sorts like before", len(seen) == 3 and "1 egg" in await ev(pg, "document.querySelector('#ings').value"))
    check("links: no page errors", not pg.errors, "; ".join(pg.errors))
    await pg.context.close()


async def test_shortcut_paste(browser):
    pg = await new_page(browser)
    data = {"zendom": 1, "url": "https://cooking.example.com/recipes/123-miso-salmon", "recipe": [
        {"@context": "https://schema.org", "@type": "NewsArticle", "headline": "x"},
        {"@context": "https://schema.org", "@type": "Recipe", "name": "Miso-Glazed Salmon", "recipeYield": "4 servings", "totalTime": "PT25M",
         "description": "Sweet &amp; salty.", "recipeIngredient": ["4 salmon fillets", "&frac14; cup white miso"],
         "recipeInstructions": [{"@type": "HowToStep", "text": "Heat the broiler."}, {"@type": "HowToStep", "text": "Brush with miso and broil 8 minutes."}]}]}
    await ev(pg, "ACTIONS.tab('kitchen'); ACTIONS.ktab('recipes'); ACTIONS.pasteRecipe()")
    await pg.locator('#paste').fill(json.dumps(data)); await pg.locator('[data-act=fillFromPaste]').click(); await pg.wait_for_timeout(100)
    vals = await ev(pg, "['rtitle','servings','prep','cook','ings','steps','rnotes','source'].map(id => document.querySelector('#' + id).value)")
    check("shortcut paste: fills every field", vals == ["Miso-Glazed Salmon", "4", "", "25 min", "4 salmon fillets\n¼ cup white miso", "Heat the broiler.\nBrush with miso and broil 8 minutes.", "Sweet & salty.", "https://cooking.example.com/recipes/123-miso-salmon"], json.dumps(vals))
    check("shortcut paste: says where it came from", "Got it from cooking.example.com: 2 ingredients and 2 steps" in await ev(pg, "document.querySelector('#pasteStatus').textContent"))
    await submit(pg)
    check("shortcut paste: saves", any(r["title"] == "Miso-Glazed Salmon" and r["source"].endswith("miso-salmon") for r in (await stored(pg))["recipes"]))
    await ev(pg, "ACTIONS.pasteRecipe()")
    await pg.locator('#paste').fill(json.dumps({"zendom": 1, "url": "https://x.example.com/", "recipe": [{"@type": "WebPage"}]})); await pg.locator('[data-act=fillFromPaste]').click(); await pg.wait_for_timeout(100)
    check("shortcut paste: a page with no recipe is explained", "didn't have a recipe" in await ev(pg, "document.querySelector('#pasteStatus').textContent"))
    await ev(pg, "closeSheet(); ACTIONS.pasteRecipe()")
    await pg.locator('#paste').fill("Lemon Pasta\n\nIngredients\n1 lb spaghetti\n2 lemons\n\nSteps\nBoil the pasta.\nToss with lemon."); await pg.locator('[data-act=fillFromPaste]').click(); await pg.wait_for_timeout(100)
    check("shortcut paste: plain page text still goes through the text sorter", "2 lemons" in await ev(pg, "document.querySelector('#ings').value"))
    check("shortcut paste: no page errors", not pg.errors, "; ".join(pg.errors))
    await pg.context.close()


async def test_bedtime(browser):
    pg = await new_page(browser, clock="2026-11-12T22:59:30-08:00")
    await pg.wait_for_timeout(300)
    lab = lambda: ev(pg, "document.querySelector('#roomCv').getAttribute('aria-label')")
    check("bedtime: 10:59 pm is still the sofa", "on the sofa" in await lab() and await ev(pg, "!RM_RT.base.bed"))
    await pg.clock.set_fixed_time("2026-11-12T23:00:05-08:00"); await pg.wait_for_timeout(400)
    check("bedtime: at 11 pm the room switches by itself (no tap needed)", await ev(pg, "RM_RT.base.bed") == "phone")
    await ev(pg, "render()")
    check("bedtime: 11 pm label: Sam on her phone, Charlie asleep, Paprika on Charlie", "Sam up on her phone, Charlie asleep with Paprika curled up on Charlie" in await lab())
    await pg.clock.set_fixed_time("2026-11-13T00:00:05-08:00"); await pg.wait_for_timeout(400)
    check("bedtime: at midnight both are asleep", await ev(pg, "RM_RT.base.bed") == "asleep")
    await pg.clock.set_fixed_time("2026-11-13T06:00:05-08:00"); await pg.wait_for_timeout(400)
    check("bedtime: at 6 am they're back on the sofa", await ev(pg, "!RM_RT.base.bed"))
    # the picture really changes (bed pixels differ from the sofa scene)
    pix = await ev(pg, "(() => { const a = rmStatic(Object.assign(roomInfo(), {bed:''})).B.d, b = rmStatic(Object.assign(roomInfo(), {bed:'asleep'})).B.d; let n = 0; for(let i = 0; i < a.length; i++) if(a[i] !== b[i]) n++; return n; })()")
    check("bedtime: the bed scene is actually drawn", pix > 500, pix)
    # tapping Paprika on the bed still gives a heart
    await pg.clock.set_fixed_time("2026-11-13T01:00:00-08:00"); await ev(pg, "render()"); await pg.wait_for_timeout(300)
    box = await ev(pg, "(() => { const b = RM_RT.papBox, r = document.querySelector('#roomCv').getBoundingClientRect(); return [r.left + (b[0] + b[2]) / 2 * r.width / RM.W, r.top + (b[1] + b[3]) / 2 * r.height / RM.H]; })()")
    await pg.mouse.click(box[0], box[1]); await pg.wait_for_timeout(100)
    check("bedtime: tapping sleeping Paprika still says mrrp", "mrrp" in await ev(pg, "document.querySelector('#toastRoot').innerText"))
    check("bedtime: no page errors", not pg.errors, "; ".join(pg.errors))
    await pg.context.close()


WRAP_SEED = """(() => {
  const B = state.budget; B.categories = [{id:'g', name:'Groceries', limit:60000}, {id:'r', name:'Rent', limit:300000}, {id:'e', name:'Eating out', limit:20000}];
  B.txns = [
    {id:'1', kind:'expense', amount:300000, date:'2026-10-01', categoryId:'r', paidBy:'charlie', shared:true, note:'Rent', billId:null},
    {id:'2', kind:'expense', amount:18450, date:'2026-10-05', categoryId:'g', paidBy:'sam', shared:true, note:"Trader Joe's", billId:null},
    {id:'4', kind:'expense', amount:31200, date:'2026-10-21', categoryId:'e', paidBy:'sam', shared:false, note:'Birthday dinner', billId:null},
    {id:'6', kind:'income', amount:520000, date:'2026-10-15', categoryId:null, paidBy:'sam', shared:false, note:'Paycheck', billId:null},
    {id:'8', kind:'expense', amount:60000, date:'2026-09-10', categoryId:'g', paidBy:'sam', shared:true, note:'Costco', billId:null},
    {id:'9', kind:'settle', amount:50000, date:'2026-10-10', categoryId:null, paidBy:'sam', shared:false, note:'', billId:null},
    {id:'10', kind:'expense', amount:9900, date:'2026-11-01', categoryId:'g', paidBy:'charlie', shared:true, note:'Nov groceries', billId:null}];
  save(); render(); })()"""

async def test_wrapup(browser):
    pg = await new_page(browser, clock="2026-11-02T09:00:00-08:00", ticking=True)
    await ev(pg, WRAP_SEED)
    w = await ev(pg, "monthWrap('2026-10')")
    check("wrap-up: totals", w["spent"] == 349650 and w["income"] == 520000 and w["count"] == 3 and w["prevSpent"] == 60000, json.dumps([w["spent"], w["income"], w["count"], w["prevSpent"]]))
    who = {x["h"]: x for x in w["who"]}
    check("wrap-up: who paid what", who["sam"]["paid"] == 49650 and who["sam"]["shared"] == 18450 and who["sam"]["own"] == 31200 and who["charlie"]["paid"] == 300000 and who["charlie"]["n"] == 1, json.dumps(w["who"]))
    check("wrap-up: categories, biggest first, with over-target", [c["name"] for c in w["cats"]] == ["Rent", "Eating out", "Groceries"] and w["cats"][1]["over"] == 11200, json.dumps(w["cats"]))
    check("wrap-up: who owed whom at month end (later months not counted)", w["bal"] == -60775, w["bal"])
    check("wrap-up: biggest purchase", w["biggest"]["id"] == "1")
    view = lambda: ev(pg, "document.querySelector('#view').innerText")
    check("wrap-up: Today shows the card in the first days of the month", "Jeff's October wrap-up is ready" in await view())
    await act(pg, "openWrap", "2026-10")
    check("wrap-up: Read it opens Budget → Summary on last month", await ev(pg, "prefs.tab + '/' + prefs.budgetTab + '/' + sumRange().preset") == "budget/summary/last")
    check("summary: Jeff crunches numbers first", await ev(pg, "!!document.querySelector('.jeffanim svg .jf9')") and "Crunching the numbers" in await view())
    await pg.clock.run_for(2000); await pg.wait_for_timeout(100)
    t = await view()
    check("summary: then gives his verdict", "Crunching" not in t and "$2,896.50 more than September" in t and "Eating out ran $112.00 over" in t, t[:400])
    check("summary: who paid and how it split", "Sam: $496.50" in t and "Charlie: $3,000.00" in t and "Sam owed Charlie $607.75 at month end" in t)
    await ev(pg, "ACTIONS.tab('today')")
    check("wrap-up: once read, the Today card goes away (this phone)", "wrap-up is ready" not in await view())
    await ev(pg, "delete prefs.wrapSeen['2026-10']; render()")
    await act(pg, "wrapDismiss", "2026-10")
    check("wrap-up: Not now hides it too", "wrap-up is ready" not in await view())
    # presets and custom dates
    await ev(pg, "ACTIONS.tab('budget'); ACTIONS.btab('summary'); ACTIONS.sumPreset('3m')"); await pg.clock.run_for(2000)
    r = await ev(pg, "rangeWrap(sumRange().from, sumRange().to)")
    check("summary: last 3 months covers Sep–Nov with a month-by-month list", r["from"] == "2026-09-01" and r["to"] == "2026-11-30" and [m["spent"] for m in r["months"]] == [60000, 349650, 9900] and "Month by month" in await view(), json.dumps(r["months"]))
    await ev(pg, "ACTIONS.sumPreset('year')"); await pg.clock.run_for(2000)
    check("summary: this year", await ev(pg, "sumRange().from + '/' + sumRange().to") == "2026-01-01/2026-12-31")
    await ev(pg, "ACTIONS.sumPreset('custom')"); await pg.clock.run_for(2000)
    await pg.locator('#sumFrom').fill('2026-10-05'); await pg.wait_for_timeout(50)
    await pg.locator('#sumTo').fill('2026-10-21'); await pg.wait_for_timeout(50); await pg.clock.run_for(2000)
    c = await ev(pg, "rangeWrap(sumRange().from, sumRange().to)")
    check("summary: custom dates include both ends", c["spent"] == 49650 and c["count"] == 2, json.dumps([c["spent"], c["count"]]))
    check("summary: custom range shown in Jeff's label", "Oct 5 – Oct 21, 2026" in await view())
    await ev(pg, "prefs.sum = {preset:'custom', from:'2027-03-01', to:'2026-11-30'}; render()"); await pg.clock.run_for(2000)
    check("summary: From after To is swapped and explained", "Swapped the dates" in await view() and await ev(pg, "sumRange().from") == "2026-11-30")
    await ev(pg, "prefs.sum = {preset:'custom', from:'2030-01-01', to:'2030-02-01'}; render()"); await pg.clock.run_for(2000)
    t = await view()
    check("summary: a range with no data doesn't break", "Nothing was logged" in t and "$0.00" in t and "NaN" not in t and "Infinity" not in t, t[:300])
    await ev(pg, "prefs.sum = {preset:'custom', from:'', to:'nope'}; render()"); await pg.clock.run_for(2000)
    check("summary: blank or broken dates fall back sensibly", await ev(pg, "isDate(sumRange().from) && isDate(sumRange().to)") and "NaN" not in await view())
    await ev(pg, "state.budget.txns = []; save(); ACTIONS.sumPreset('month')"); await pg.clock.run_for(2000)
    check("summary: no spending at all doesn't break", "NaN" not in await view() and "Nothing logged" in await view())
    check("summary: no page errors", not pg.errors, "; ".join(pg.errors))
    await pg.context.close()
    pg = await new_page(browser, clock="2026-10-27T09:00:00-07:00")
    await ev(pg, WRAP_SEED); await ev(pg, "ACTIONS.tab('budget'); ACTIONS.btab('spending')")
    check("wrap-up: from the 25th, this month's 'so far' button", "October wrap-up so far" in await ev(pg, "document.querySelector('#view').innerText"))
    await ev(pg, "ACTIONS.bmonth('-2')")
    await act(pg, "openWrap", "2026-08")
    check("wrap-up: an older month opens as a date range", await ev(pg, "sumRange().from + '/' + sumRange().to") == "2026-08-01/2026-08-31")
    check("wrap-up: no page errors", not pg.errors, "; ".join(pg.errors))
    await pg.context.close()

async def test_dinner_suggestions(browser):
    pg = await new_page(browser, clock="2026-10-30T08:30:00-07:00")
    await ev(pg, """(() => { state.meals = []; state.pantry = [{id:'p1', name:'butter', qty:'', room:'fridge', expires:''}, {id:'p2', name:'flour', qty:'', room:'pantry', expires:''}, {id:'p3', name:'chicken', qty:'', room:'fridge', expires:''}];
      state.recipes = [{id:'c', title:'London Fog Cookies', servings:12, prep:'', cook:'', categories:['Dessert'], ingredients:['1 cup butter', '2 cups flour'], steps:['Bake.'], notes:'', source:'', favorite:false, example:false, created:1, cooked:[], photos:[]},
                       {id:'d', title:'Chicken and butter', servings:2, prep:'', cook:'', categories:['Dinner'], ingredients:['1 lb chicken', '2 tbsp butter'], steps:['Cook.'], notes:'', source:'', favorite:false, example:false, created:1, cooked:[], photos:[]}];
      save(); ACTIONS.tab('today'); ACTIONS.tview('today'); })()""")
    card = await ev(pg, "[...document.querySelectorAll('.soon-card')].map(e => e.innerText).find(t => t.includes(\"Tonight's dinner\")) || ''")
    check("dinner ideas: dinner recipes are suggested", "Chicken and butter" in card, card)
    check("dinner ideas: cookies (dessert) are not", "London Fog" not in card, card)
    await act(pg, "whatCanWeMake")
    check("dinner ideas: What can we make? opens on Lunch/Dinner recipes", await ev(pg, "[...rf.types].join()") == "Dinner" and "London Fog" not in await ev(pg, "document.querySelector('#view').innerText"))
    await ev(pg, "state.recipes.forEach(r => r.categories = ['Dessert']); save(); ACTIONS.tab('today')")
    check("dinner ideas: with no Lunch/Dinner recipes it says how to get ideas", "Tag recipes as Lunch or Dinner" in await ev(pg, "document.querySelector('#view').innerText"))
    check("viewport covers the notch area so the status bar strip is painted", "viewport-fit=cover" in await ev(pg, "document.querySelector('meta[name=viewport]').content"))
    check("dinner ideas: no page errors", not pg.errors, "; ".join(pg.errors))
    await pg.context.close()


async def test_entries_import(browser):
    pg = await new_page(browser, clock="2026-10-30T09:00:00-07:00")
    await ev(pg, """(() => { state.budget.categories = [{id:'g', name:'Groceries', limit:60000}]; state.budget.txns = [
        {id:'m1', kind:'expense', amount:18450, date:'2026-10-03', categoryId:'g', paidBy:'sam', shared:true, note:"Trader Joe's", billId:null},
        {id:'m2', kind:'expense', amount:4200, date:'2026-10-10', categoryId:'g', paidBy:'sam', shared:false, note:'Pharmacy', billId:null}];
      save(); ACTIONS.tab('budget'); ACTIONS.btab('spending'); render(); })()""")
    # details + cancelled
    await ev(pg, "ACTIONS.editTxn('m2')")
    await fill(pg, {"tdetails": "Allergy meds + sunscreen, order #4411"}); await pg.locator('#sheetForm input[name=tcancel]').check(); await submit(pg)
    t = [x for x in (await stored(pg))["budget"]["txns"] if x["id"] == "m2"][0]
    check("entries: details and cancelled save", t["details"] == "Allergy meds + sunscreen, order #4411" and t["cancelled"] is True, json.dumps(t))
    view = await ev(pg, "document.querySelector('#view').innerText")
    check("entries: cancelled shows in the list, marked", "Cancelled" in view and "Allergy meds" in view and await ev(pg, "!!document.querySelector('.txrow.cx')"))
    check("entries: cancelled isn't counted in the month", await ev(pg, "monthStats('2026-10').spent") == 18450)
    check("entries: or in the summary or who owes whom", await ev(pg, "rangeWrap('2026-10-01','2026-10-31').spent") == 18450 and await ev(pg, "balance()") == 9225)
    await ev(pg, "ACTIONS.editTxn('m2')"); await pg.locator('#sheetForm input[name=tcancel]').uncheck(); await submit(pg)
    check("entries: un-cancelling counts it again", await ev(pg, "monthStats('2026-10').spent") == 22650)
    # import: a typed entry posting 2 days later, an exact re-import, and a new purchase
    csv = "Date,Description,Amount\n10/05/2026,TRADER JOE'S #123,-184.50\n10/12/2026,PHARMACY 22,-42.00\n10/20/2026,BLUE BOTTLE,-6.75\n"
    res = await pg.evaluate("c => buildImport(c, 'oct.csv').rows.map(x => [x.desc, x.include, x.dup])", csv)
    by = {d: (inc, dup) for d, inc, dup in res}
    check("import: a typed entry 2 days earlier is flagged and unticked", by["TRADER JOE'S #123"][0] is False and "Trader Joe" in by["TRADER JOE'S #123"][1] and "Oct 3" in by["TRADER JOE'S #123"][1], json.dumps(res))
    check("import: so is one 2 days off the other way", by["PHARMACY 22"][0] is False and "Pharmacy" in by["PHARMACY 22"][1], json.dumps(res))
    check("import: a new purchase is ticked", by["BLUE BOTTLE"][0] is True and not by["BLUE BOTTLE"][1])
    await pg.evaluate("c => importPreview(buildImport(c, 'oct.csv'))", csv); await submit(pg)
    n1 = len((await stored(pg))["budget"]["txns"])
    check("import: only the new one is added", n1 == 3, n1)
    res2 = await pg.evaluate("c => buildImport(c, 'oct.csv').rows.map(x => x.dup)", csv)
    check("import: the same file again is all 'already imported' or matched", all(res2) and "Already imported" in res2, json.dumps(res2))
    # each typed entry matches only one row
    csv2 = "Date,Description,Amount\n10/03/2026,TJ A,-184.50\n10/04/2026,TJ B,-184.50\n"
    res3 = await pg.evaluate("c => buildImport(c, 'b.csv').rows.map(x => !!x.dup)", csv2)
    check("import: one typed entry can't hide two statement lines", sorted(res3) == [False, True], json.dumps(res3))
    # a Venmo payment that's also on the bank statement
    await ev(pg, "state.budget.txns.push({id:'v1', kind:'expense', amount:2500, date:'2026-10-15', categoryId:null, paidBy:'sam', shared:false, note:'Pizza · Charlie', billId:null, imp:'venmo|x', source:'venmo'}); save()")
    res4 = await ev(pg, "buildImport('Date,Description,Amount\\n10/16/2026,VENMO PAYMENT,-25.00\\n', 'bank.csv').rows.map(x => x.dup)")
    check("import: a Venmo payment also on the bank statement is flagged", res4[0] and "Venmo import" in res4[0], json.dumps(res4))
    check("entries/import: no page errors", not pg.errors, "; ".join(pg.errors))
    await pg.context.close()


async def test_person_view(browser):
    pg = await new_page(browser, clock="2026-10-30T09:00:00-07:00")
    await ev(pg, """(() => { state.budget.categories = [{id:'g', name:'Groceries', limit:60000}, {id:'f', name:'Fun', limit:0}]; state.budget.txns = [
        {id:'1', kind:'expense', amount:300000, date:'2026-10-01', categoryId:'g', paidBy:'charlie', shared:true, note:'Big shop', billId:null},
        {id:'2', kind:'expense', amount:2000, date:'2026-10-02', categoryId:'f', paidBy:'sam', shared:false, note:'Sam book', billId:null},
        {id:'3', kind:'expense', amount:5000, date:'2026-10-03', categoryId:'f', paidBy:'charlie', shared:false, note:'Charlie game', billId:null},
        {id:'4', kind:'income', amount:100000, date:'2026-10-15', categoryId:null, paidBy:'sam', shared:false, note:'Sam pay', billId:null},
        {id:'5', kind:'income', amount:80000, date:'2026-10-15', categoryId:null, paidBy:'charlie', shared:false, note:'Charlie pay', billId:null},
        {id:'6', kind:'expense', amount:9999, date:'2026-10-04', categoryId:'f', paidBy:'sam', shared:false, note:'Cancelled thing', cancelled:true, billId:null}];
      save(); ACTIONS.tab('budget'); ACTIONS.btab('spending'); })()""")
    view = lambda: ev(pg, "document.querySelector('#view').innerText")
    t = await view()
    check("person view: Both shows the household", "$3,070.00" in t and "$1,800.00" in t and "Sam book" in t and "Charlie game" in t)
    await act(pg, "spendWho", "sam"); t = await view()
    check("person view: Sam's share = own + half of shared", "Sam's share" in t and "$1,520.00" in t and "$20.00 paid by Sam" in t, t[:600])
    check("person view: Sam's income only", "Sam's income" in t and "$1,000.00" in t and "$1,800.00" not in t)
    check("person view: Sam's list leaves out Charlie's own things", "Sam book" in t and "Big shop" in t and "Charlie game" not in t)
    check("person view: shared entries show Sam's half", "Sam's half: $1,500.00" in t)
    check("person view: cancelled still not counted", await ev(pg, "personStats(monthStats('2026-10'), 'sam').spent") == 152000)
    check("person view: categories show Sam's share, targets explained", "Groceries" in t and "$1,500.00" in t and "Targets are for both of you" in t)
    await act(pg, "spendWho", "charlie"); t = await view()
    check("person view: Charlie's share", "$1,550.00" in t and "$3,050.00 paid by Charlie" in t and "Sam book" not in t, t[:500])
    check("person view: remembered on this phone", await ev(pg, "JSON.parse(localStorage.getItem('zendom:prefs')).spendWho") == "charlie")
    await act(pg, "spendWho", ""); t = await view()
    check("person view: back to both", "Sam book" in t and "Charlie game" in t)
    await ev(pg, "prefs.spendWho = 'sam'; budgetMonth = '2026-08'; render()")
    check("person view: an empty month for one person is fine", "Nothing for Sam in August 2026" in await view())
    check("status bar: the header carries its own cover for the strip above it", await ev(pg, "getComputedStyle(document.querySelector('.top'), '::before').content") in ('""', "''"))
    check("person view: no page errors", not pg.errors, "; ".join(pg.errors))
    await pg.context.close()


async def test_pdf_statements(browser):
    import os
    V = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor") + "/"; F = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures") + "/"
    pg = await new_page(browser, clock="2026-10-30T10:00:00-07:00")
    await pg.context.route("**/pdf.js/3.11.174/pdf.min.js", lambda r: r.fulfill(path=V + "pdf.min.js", content_type="application/javascript"))
    await pg.context.route("**/pdf.js/3.11.174/pdf.worker.min.js", lambda r: r.fulfill(path=V + "pdf.worker.min.js", content_type="application/javascript"))
    await ev(pg, """(() => { state.budget.categories = [{id:'g', name:'Groceries', limit:60000}]; state.budget.txns = [
        {id:'m1', kind:'expense', amount:18450, date:'2026-10-03', categoryId:'g', paidBy:'sam', shared:true, note:"Trader Joe's", billId:null}];
      save(); ACTIONS.tab('budget'); ACTIONS.btab('spending'); ACTIONS.importCsv(); })()""")
    check("pdf import: the picker takes PDFs", "pdf" in await ev(pg, "document.querySelector('#csvFile').accept"))
    await pg.locator('#csvFile').set_input_files(F + "card_oct.pdf"); await pg.wait_for_timeout(1500)
    rows = await ev(pg, "imp && imp.rows.map(x => [x.desc, x.cents, x.include, x.dup])")
    check("pdf import: a card statement opens the preview", rows and len(rows) == 5, json.dumps(rows))
    by = {r[0]: r for r in rows or []}
    check("pdf import: purchases are money out", by.get("BLUE BOTTLE COFFEE", [0, 0])[1] == -675 and by["AMAZON MKTPLACE PMTS"][1] == -6499)
    check("pdf import: the return is money in", by["AMAZON MKTPLACE RETURN"][1] == 6499)
    check("pdf import: the card payment starts unticked as a transfer", by["AUTOPAY PAYMENT - THANK YOU"][2] is False and "transfer" in by["AUTOPAY PAYMENT - THANK YOU"][3])
    check("pdf import: the duplicate check still works", by["TRADER JOE'S #123 SAN JOSE CA"][2] is False and "Trader Joe" in by["TRADER JOE'S #123 SAN JOSE CA"][3])
    check("pdf import: the preview says it came from a PDF", "PDF card statement" in await ev(pg, "document.querySelector('#sheetForm').innerText"))
    await submit(pg)
    tx = (await stored(pg))["budget"]["txns"]
    check("pdf import: ticked rows import (coffee, Amazon, return)", len(tx) == 4 and sorted(t["note"] for t in tx if t.get("imp")) == ["AMAZON MKTPLACE PMTS", "AMAZON MKTPLACE RETURN", "BLUE BOTTLE COFFEE"], json.dumps([t["note"] for t in tx]))
    check("pdf import: the return comes in as income-side money", [t["kind"] for t in tx if t["note"] == "AMAZON MKTPLACE RETURN"] == ["income"])
    # checking statement with Withdrawals / Deposits / Balance columns
    r = await pg.evaluate("async b => { const bin = atob(b), u = new Uint8Array(bin.length); for(let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i); return statementRows(await pdfLines(u.buffer)); }", __import__("base64").b64encode(open(F + "checking.pdf", "rb").read()).decode())
    got = [(x["date"], x["desc"], x["cents"]) for x in r["rows"]]
    check("pdf import: bank columns decide money in/out; balances skipped", got == [("2026-09-18", "PG&E UTILITY BILL", -8420), ("2026-10-01", "PAYROLL DIRECT DEP EXAMPLE CO", 220181), ("2026-10-02", "ONLINE TRANSFER TO SAVINGS", -50000), ("2026-10-05", "EXAMPLE CARD AUTOPAY PAYMENT", -35000), ("2026-10-09", "FARMERS MARKET", -2350)], json.dumps(got))
    r = await pg.evaluate("async b => { const bin = atob(b), u = new Uint8Array(bin.length); for(let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i); return statementRows(await pdfLines(u.buffer)); }", __import__("base64").b64encode(open(F + "card_jan.pdf", "rb").read()).decode())
    check("pdf import: a December line on a January statement gets last year", [x["date"] for x in r["rows"]] == ["2026-12-20", "2027-01-05"], json.dumps(r["rows"]))
    # not a statement / not a PDF
    await ev(pg, "ACTIONS.importCsv()")
    await pg.locator('#csvFile').set_input_files(files=[{"name": "fake.pdf", "mimeType": "application/pdf", "buffer": b"hello"}]); await pg.wait_for_timeout(300)
    check("pdf import: a file that isn't a PDF is explained", "isn't a PDF" in await ev(pg, "document.querySelector('#toastRoot').innerText"))
    check("pdf import: no page errors", not pg.errors, "; ".join(pg.errors))
    await pg.context.close()


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        await run_all(browser)
        await test_dates(browser)
        await test_dupes(browser)
        await test_drawing(browser)
        await test_calendar_links(browser)
        await test_appointments(browser)
        await test_status(browser)
        await test_smart(browser)
        await test_qol(browser)
        await test_links(browser)
        await test_shortcut_paste(browser)
        await test_bedtime(browser)
        await test_wrapup(browser)
        await test_dinner_suggestions(browser)
        await test_entries_import(browser)
        await test_person_view(browser)
        await test_pdf_statements(browser)
        await browser.close()
    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)} of {len(results)} checks passed")
    sys.exit(1 if failed else 0)

asyncio.run(main())
