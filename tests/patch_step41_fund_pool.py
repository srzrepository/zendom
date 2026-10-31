"""Step 41: the Fun Fund is one pool with goals, not money in places.
- No more "where is it kept" or moving money between places. The fund is one pool: what's free to use,
  plus what's set aside for goals. Money in shows where it came from (an income line, or a note like
  a gift); "Where it came from" sums it up.
- Goals hold money: tap a goal to add money to it from the pool, move money back to the pool, or spend
  from it. Money can also go straight to a goal when you add it. Deleting a goal puts its money back
  in the pool.
- Old entries are kept: amounts and totals don't change; old "moved between places" entries stay in the
  ledger, marked as from before, and don't affect anything.
- What's new: More → Settings → "What's new" lists every version in plain words, and after an update
  the app offers to show what changed.
Data: new Fun Fund entry kinds "assign" (pool → goal) and "release" (goal → pool); place is optional now.
Usage: python3 patch_step41_fund_pool.py file.html"""
import sys, re
p = sys.argv[1]; s = open(p).read()
def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (s.count(old), old[:100])
    s = s.replace(old, new)
def rep_func(name, new):
    """Replace a whole top-level function (up to the next top-level function/const/comment line)."""
    global s
    start = s.index(f"\nfunction {name}(") + 1
    m = re.compile(r"\n(function |const |let |// |/\*)").search(s, start + 10)
    s = s[:start] + new.strip("\n") + "\n" + s[m.start() + 1:]

# ---------- money math ----------
rep("""function goalSaved(gid){ return fund().entries.reduce((a, e) => a + (e.goalId === gid ? (e.kind === "in" ? e.amount : e.kind === "out" ? -e.amount : 0) : 0), 0); }""",
    """// A goal's money: added straight to it, assigned from the pool, minus spent from it and moved back
function goalSaved(gid){ return fund().entries.reduce((a, e) => a + (e.goalId === gid ? ({in:1, assign:1, out:-1, release:-1}[e.kind] || 0) * e.amount : 0), 0); }
const goalsTotal = () => fund().goals.reduce((a, g) => a + Math.max(0, goalSaved(g.id)), 0);
const poolFree = () => fundTotal() - goalsTotal();
const goalName = id => (fund().goals.find(g => g.id === id) || {name:"a goal that was deleted"}).name;""")

# ---------- the Fun Fund page ----------
rep_func("viewFund", r'''
function viewFund(){
  const f = fund(), total = fundTotal(), free = poolFree(), inGoals = goalsTotal(), yr = todayStr().slice(0, 4);
  const by = k => f.entries.filter(e => e.kind === "in" && e.who === k).reduce((a, e) => a + e.amount, 0);
  const byYr = k => f.entries.filter(e => e.kind === "in" && e.who === k && e.date.startsWith(yr)).reduce((a, e) => a + e.amount, 0);
  const tot = by("sam") + by("charlie");
  const entries = f.entries.slice().sort((a, b) => b.date.localeCompare(a.date) || b.created - a.created);
  // where the money came from: income lines by name, other money by its note
  const src = {}; f.entries.filter(e => e.kind === "in").forEach(e => { const i = e.incomeId && state.budget.txns.find(t => t.id === e.incomeId);
    const k = i ? (i.note || "Income") : (e.note && !/^From /.test(e.note) ? e.note : e.note ? e.note.replace(/^From /, "") : "Other"); src[k] = (src[k] || 0) + e.amount; });
  const srcList = Object.entries(src).sort((a, b) => b[1] - a[1]);
  return `
  <section class="jeff card"><div class="jeff-pig jar">${pigSvg("", JEFF_JAR)}</div>
    <div class="jeff-talk"><span class="label">${esc(f.name)}</span><p class="bubble" role="status">${esc(fundJeff())}</p></div></section>
  <div class="fundtotal"><span class="label">In the fund</span><b>${money(total)}</b>
    ${f.goals.length ? `<span class="small muted">${money(free)} free to use · ${money(inGoals)} in goals</span>` : ""}</div>
  <div class="btools fundbtns"><button type="button" class="btn small" data-act="fundIn">Add money</button><button type="button" class="btn ghost small" data-act="fundOut" ${total > 0 ? "" : "disabled"}>Spend</button></div>
  <section class="sec"><div class="sec-head"><span class="label">Shared goals</span><button type="button" class="link" data-act="editGoal">+ New goal</button></div>
    ${f.goals.length ? `<div class="list">${f.goals.map(g => { const sv = goalSaved(g.id), pct = g.target ? Math.max(0, Math.min(100, Math.round(100 * sv / g.target))) : 0;
      return `<button type="button" class="item goal" data-act="openGoal" data-id="${g.id}"><div style="flex:1;min-width:0"><div class="t">${esc(g.name)}${pct >= 100 ? ' <span class="pill ok">Reached!</span>' : ""}</div>
        <div class="gbar" role="img" aria-label="${pct} percent saved"><i style="width:${pct}%"></i></div>
        <div class="s">${money(sv)} of ${money(g.target)}${g.by ? ` · by ${niceDate(g.by)}` : ""}</div></div></button>`; }).join("")}</div>
      <p class="small muted" style="margin:6px 0 0">Tap a goal to add money to it from the pool, or move money back out.</p>`
      : `<div class="empty"><p>Pick something to save for together, like a trip, a spa day or a new couch.</p></div>`}</section>
  ${srcList.length ? `<section class="sec"><span class="label">Where it came from</span><div class="glist">${srcList.slice(0, 8).map(([k, v]) => `<div class="catrow"><span class="cn">${esc(k)}</span><span class="cv">${money(v)}</span></div>`).join("")}
    ${srcList.length > 8 ? `<div class="catrow"><span class="cn">Everything else</span><span class="cv">${money(srcList.slice(8).reduce((a, x) => a + x[1], 0))}</span></div>` : ""}</div></section>` : ""}
  ${tot ? `<section class="sec"><span class="label">Who's put in</span><div class="card whoin">
    ${HUMANS.map(k => `<div class="whorow"><span class="av ${k}">${sprite(k, "", true)}</span><span class="wn">${esc(nameOf(k))}</span>
      <span class="wbar"><i class="${k}" style="width:${tot ? Math.round(100 * by(k) / tot) : 0}%"></i></span><span class="wv">${money(by(k))}</span></div>`).join("")}
    <span class="small muted">This year: ${esc(nameOf("sam"))} ${money(byYr("sam"))} · ${esc(nameOf("charlie"))} ${money(byYr("charlie"))}</span></div></section>` : ""}
  <section class="sec"><span class="label">Ledger</span>
    ${entries.length ? `<div class="glist">${entries.map(fundRow).join("")}</div>`
      : `<div class="empty"><p>No entries yet. Tap Add money to start the fund.</p></div>`}</section>`;
}
function fundRow(e){
  const inc = e.incomeId && state.budget.txns.find(t => t.id === e.incomeId);
  const title = e.kind === "in" ? `${nameOf(e.who)} added` : e.kind === "out" ? (e.note || "Spent") : e.kind === "assign" ? `To ${goalName(e.goalId)}` : e.kind === "release" ? `Back from ${goalName(e.goalId)}` : "Moved between places (from before)";
  const sub = [niceDate(e.date),
    e.kind === "in" && inc ? `from ${inc.note || "income"} (${niceDate(inc.date)})` : "",
    e.kind === "in" && e.note && !(inc && e.note === `From ${inc.note}`) ? e.note : "",
    (e.kind === "in" || e.kind === "out") && e.goalId ? (e.kind === "in" ? `to ${goalName(e.goalId)}` : `from ${goalName(e.goalId)}`) : "",
    (e.kind === "assign" || e.kind === "release") ? `${nameOf(e.who)}${e.note ? " · " + e.note : ""}` : "",
    e.kind === "move" ? "doesn't change any totals" : ""].filter(Boolean).join(" · ");
  const cls = e.kind === "in" ? "income" : e.kind === "out" ? "" : "settle";
  return `<button type="button" class="txrow ${e.kind === "move" ? "elsewhere" : ""}" data-act="editFund" data-id="${e.id}">
    <span class="av ${e.who}">${sprite(e.who, "", true)}</span>
    <span class="tb"><span class="tt">${esc(title)}</span><span class="ts">${esc(sub)}</span></span>
    <span class="ta ${cls}">${e.kind === "in" ? "+" : e.kind === "out" ? "−" : ""}${money(e.amount)}</span></button>`;
}
''')

# ---------- add / spend form (no places) ----------
rep_func("fundForm", r'''
function fundForm(kind, id, preset){
  const f = fund(), e = id ? f.entries.find(x => x.id === id) : null; if(id && !e) return;
  if(e && (e.kind === "assign" || e.kind === "release")) return goalMoveForm(e.kind, e.goalId, e.id);
  if(e && e.kind === "move") return oldMoveSheet(e);
  editStart(e);
  kind = e ? e.kind : kind;
  const d = e || Object.assign({amount:0, date:todayStr(), who:prefs.user, goalId:"", note:""}, preset || {});
  const own = e ? e.amount : 0;
  const goalOpts = sel => f.goals.map(g => `<option value="${g.id}" ${sel === g.id ? "selected" : ""}>${esc(g.name)} · ${money(goalSaved(g.id) + (e && e.goalId === g.id && kind === "out" ? own : 0))} in it</option>`).join("");
  openSheet(e ? "Edit entry" : kind === "in" ? "Add to the Fun Fund" : "Spend from the Fun Fund", `
    <div class="two">${field("famt","Amount", `<input id="famt" name="famt" inputmode="decimal" placeholder="$0.00" value="${esc(centsToInput(d.amount))}" autocomplete="off">`)}
    ${field("fdate","Date", `<input id="fdate" name="fdate" type="date" value="${esc(d.date)}">`)}</div>
    <div class="field"><span class="lab">${kind === "in" ? "Who put it in?" : "Who's spending it?"}</span>${whoRadios("fwho", d.who)}</div>
    ${kind === "in" ? (() => { const src = fundSources(e ? e.id : null, d.incomeId);
      return field("fsrc", "Where did it come from?", `<select id="fsrc" name="fsrc"><option value="">Not linked to income</option>${src.map(x => `<option value="${x.t.id}" ${d.incomeId === x.t.id ? "selected" : ""}>${esc(cutText(x.t.note || "Income", 24))} · ${esc(niceDate(x.t.date))} · ${money(x.left)} left</option>`).join("")}<option value="new">New income: log it too</option></select>`,
        "Pick the paycheck or gift it came out of, so you can see where fund money came from."); })() : ""}
    ${field("fnote", kind === "in" ? "Note" : "What was it for?", `<input id="fnote" name="fnote" maxlength="80" value="${esc(d.note)}" placeholder="${kind === "in" ? "Birthday money, bonus…" : "Concert tickets, dinner out…"}" autocomplete="off">`, kind === "in" ? "Optional" : "")}
    ${f.goals.length ? field("fgoal", kind === "in" ? "Put it toward a goal?" : "Spend it from", `<select id="fgoal" name="fgoal"><option value="">${kind === "in" ? "No, keep it free to use" : `Free money (${money(poolFree() + (e && !e.goalId ? own : 0))})`}</option>${goalOpts(d.goalId)}</select>`) : ""}
    ${footer(e ? "delFund:" + e.id : "")}`,
  form => {
    const amount = parseMoney(val(form,"famt")), date = val(form,"fdate");
    const who = (form.querySelector("input[name=fwho]:checked") || {}).value;
    if(amount === null) return fail("famt","Enter an amount like 50.");
    if(!isDate(date)) return fail("fdate","Pick a valid date.");
    if(kind === "out" && !val(form,"fnote")) return fail("fnote","Say what it was for, so the ledger makes sense later.");
    const gid = form.elements.fgoal ? val(form,"fgoal") : "", goalId = f.goals.some(g => g.id === gid) ? gid : "";
    if(kind === "out"){
      const have = goalId ? goalSaved(goalId) + (e && e.goalId === goalId ? own : 0) : poolFree() + (e && !e.goalId ? own : 0);
      if(amount > have) return fail(goalId ? "fgoal" : "famt", goalId ? `Only ${money(Math.max(0, have))} is in ${goalName(goalId)}.` : `Only ${money(Math.max(0, have))} is free to use${f.goals.length ? " (the rest is in goals)" : ""}.`);
    }
    let incomeId = kind === "in" && form.elements.fsrc ? val(form, "fsrc") : "";
    if(incomeId && incomeId !== "new"){
      const inc = state.budget.txns.find(t => t.id === incomeId && t.kind === "income");
      if(!inc) return fail("fsrc", "That income line isn't there anymore. Pick another.");
      const left = inc.amount - fundFrom(inc.id, e ? e.id : null);
      if(amount > left) return fail("fsrc", `Only ${money(Math.max(0, left))} of “${inc.note || "that income"}” is left to put in the fund.`);
    }
    if(incomeId === "new"){
      if(!val(form, "fnote")) return fail("fnote", "Say what the income was, like Birthday money from Mom.");
      const inc = {id:uid(), kind:"income", amount, date, note: val(form, "fnote").slice(0, 80), paidBy: HUMANS.includes(who) ? who : prefs.user, shared:false, categoryId:null, billId:null};
      state.budget.txns.push(inc); incomeId = inc.id;
    }
    const data = {kind, amount, date, who: HUMANS.includes(who) ? who : prefs.user, goalId, note: val(form,"fnote").slice(0, 80)};
    if(kind === "in") data.incomeId = incomeId || null;
    if(e){ applyEdit(e, data); if(!e.incomeId) delete e.incomeId; } else { const ne = Object.assign({id:uid(), created:Date.now(), place:"", toPlace:""}, data); if(!ne.incomeId) delete ne.incomeId; f.entries.push(ne); }
    save(); closeSheet(); render(); toast(e ? "Saved" : kind === "in" ? `${money(amount)} added${goalId ? ` to ${goalName(goalId)}` : " to the fund"}${incomeId ? " · linked to its income" : ""}` : `${money(amount)} spent${goalId ? ` from ${goalName(goalId)}` : ""}`);
  });
}
// A goal: what's in it, and what you can do with it
function goalSheet(id){
  const g = fund().goals.find(x => x.id === id); if(!g) return;
  const sv = goalSaved(g.id), pct = g.target ? Math.max(0, Math.min(100, Math.round(100 * sv / g.target))) : 0, free = poolFree();
  openSheet(g.name, `
    <div class="gbar" role="img" aria-label="${pct} percent saved"><i style="width:${pct}%"></i></div>
    <p style="margin:0"><b>${money(sv)}</b> of ${money(g.target)}${g.by ? ` · by ${esc(niceDate(g.by))}` : ""}${sv < g.target ? ` · ${money(g.target - sv)} to go` : " · reached!"}</p>
    <p class="small muted" style="margin:0">${money(free)} is free to use in the fund.</p>
    <div class="actions" style="flex-wrap:wrap;justify-content:flex-start;gap:8px">
      <button type="button" class="btn small" data-act="goalAdd" data-id="${g.id}" ${free > 0 ? "" : "disabled"}>Add from the pool</button>
      <button type="button" class="btn ghost small" data-act="goalBack" data-id="${g.id}" ${sv > 0 ? "" : "disabled"}>Move back to the pool</button>
      <button type="button" class="btn ghost small" data-act="goalSpend" data-id="${g.id}" ${sv > 0 ? "" : "disabled"}>Spend from it</button></div>
    ${(() => { const L = fund().entries.filter(e => e.goalId === g.id).sort((a, b) => b.date.localeCompare(a.date) || b.created - a.created).slice(0, 12);
      return L.length ? `<div class="glist">${L.map(fundRow).join("")}</div>` : ""; })()}
    <div class="actions"><button type="button" class="link" data-act="editGoal" data-id="${g.id}">Edit goal</button><div class="r"><button type="button" class="btn" data-act="closeSheet">Done</button></div></div>`, () => {}, false);
}
// Move money between the pool and a goal (kind "assign": pool → goal, "release": goal → pool)
function goalMoveForm(kind, goalId, id){
  const f = fund(), e = id ? f.entries.find(x => x.id === id) : null, g = f.goals.find(x => x.id === goalId);
  if(!g && !e) return; editStart(e);
  const own = e ? e.amount : 0, free = poolFree() + (e && kind === "assign" ? own : 0), inGoal = (g ? goalSaved(g.id) : 0) + (e && kind === "release" ? own : 0);
  const d = e || {amount: kind === "assign" ? Math.max(0, Math.min(free, g.target - goalSaved(g.id))) : inGoal, date: todayStr(), who: prefs.user, note: ""};
  openSheet(e ? "Edit entry" : kind === "assign" ? `Add to ${g.name}` : `Move back from ${g.name}`, `
    <p class="small muted" style="margin:0">${kind === "assign" ? `${money(free)} is free to use. It moves into ${esc(g ? g.name : "the goal")} and stays in the fund.` : `${money(inGoal)} is in ${esc(g ? g.name : "the goal")}. It moves back to the free pool.`}</p>
    <div class="two">${field("gmamt","Amount", `<input id="gmamt" name="gmamt" inputmode="decimal" value="${esc(centsToInput(d.amount))}" placeholder="$0.00" autocomplete="off">`)}
    ${field("gmdate","Date", `<input id="gmdate" name="gmdate" type="date" value="${esc(d.date)}">`)}</div>
    ${field("gmnote","Note", `<input id="gmnote" name="gmnote" maxlength="80" value="${esc(d.note || "")}" autocomplete="off" placeholder="${kind === "release" ? "Needed it for the vet bill…" : ""}">`, "Optional")}
    ${footer(e ? "delFund:" + e.id : "")}`,
  form => {
    const amount = parseMoney(val(form, "gmamt")), date = val(form, "gmdate");
    if(amount === null) return fail("gmamt", "Enter an amount like 50.");
    if(!isDate(date)) return fail("gmdate", "Pick a valid date.");
    const max = kind === "assign" ? free : inGoal;
    if(amount > max) return fail("gmamt", kind === "assign" ? `Only ${money(Math.max(0, max))} is free to use.` : `Only ${money(Math.max(0, max))} is in this goal.`);
    const data = {kind, amount, date, who: e ? e.who : prefs.user, goalId: e ? e.goalId : g.id, note: val(form, "gmnote").slice(0, 80)};
    if(e) applyEdit(e, data); else f.entries.push(Object.assign({id:uid(), created:Date.now(), place:"", toPlace:""}, data));
    save(); closeSheet(); render(); toast(kind === "assign" ? `${money(amount)} added to ${goalName(data.goalId)}` : `${money(amount)} moved back to the pool`);
    if(!e && g) goalSheet(g.id);
  });
}
// Entries from when the fund tracked places
function oldMoveSheet(e){
  openSheet("Moved between places", `<p style="margin:0">${money(e.amount)} moved from ${esc(e.place)} to ${esc(e.toPlace)} on ${esc(niceDate(e.date))}.</p>
    <p class="small muted" style="margin:0">The fund doesn't track places anymore, so this doesn't change any totals. You can keep it or delete it.</p>
    ${footer("delFund:" + e.id)}`, () => closeSheet(), false);
}
''')

# goal form: deleting returns its money to the pool
rep("""Deleting the goal keeps its ledger entries.</p>""", """Deleting the goal puts its money back in the pool.</p>""")
rep("""return ok && "Goal deleted. Its money stays in the fund."; }""", """return ok && "Goal deleted. Its money is back in the pool."; }""")
rep("""  editFund: id => fundForm(null, id), editGoal: id => goalForm(id || null)""",
    """  editFund: id => fundForm(null, id), editGoal: id => goalForm(id || null), openGoal: id => goalSheet(id),
  goalAdd: id => goalMoveForm("assign", id), goalBack: id => goalMoveForm("release", id), goalSpend: id => fundForm("out", null, {goalId: id})""")
rep("""fundMove: () => fundForm("move"),""", """fundMove: () => fundForm("in"),""")

# stored data: new kinds; place only needed for old moves
rep("""    entries: objs(f.entries).filter(e => ["in","out","move"].includes(e.kind) && cents(e.amount) && isDate(e.date) && str(e.place).trim()).map(e => Object.assign({}, e, {""",
    """    entries: objs(f.entries).filter(e => ["in","out","move","assign","release"].includes(e.kind) && cents(e.amount) && isDate(e.date) && (e.kind !== "move" || str(e.place).trim())).map(e => Object.assign({}, e, {""")

# paychecks: no "Kept in"
rep("""    ${field("pfplace", "Kept in", `<input id="pfplace" name="pfplace" list="placeList2" maxlength="30" value="${esc(d.fundPlace || placeList()[0])}" autocomplete="off"><datalist id="placeList2">${placeList().map(x => `<option value="${esc(x)}">`).join("")}</datalist>`)}</div>""",
    """    <div></div></div>""")
rep("""    const fRaw = val(form, "pfund"), toFund = fRaw ? parseMoney(fRaw) : 0, fundPlace = val(form, "pfplace").slice(0, 30);""",
    """    const fRaw = val(form, "pfund"), toFund = fRaw ? parseMoney(fRaw) : 0, fundPlace = "";""")
rep("""    if(toFund && !fundPlace) return fail("pfplace", "Say where it's kept, like Savings account.");\n""", "")
rep("""place:p.fundPlace || "Savings account", toPlace:"",""", """place:"", toPlace:"",""")
rep("""fundPlace: cents(x.toFund) ? (str(x.fundPlace, 30).trim() || "Savings account") : "",""", """fundPlace: "",""")

rep('const BUILD = "2026-10-30 · 40";', 'const BUILD = "2026-10-30 · 41";')
open(p, "w").write(s)
print("patched")

# ---------- What's new ----------
s = open(p).read()
rep('const BUILD = "2026-10-30 · 41";', r'''const BUILD = "2026-10-30 · 41";
// What's new, newest first: [version, date, changes]. Add a line here with every version.
const CHANGELOG = [
  ["41", "2026-10-30", ["The Fun Fund is one pool: no more “where is it kept”. Money in shows where it came from, and “Where it came from” sums it up.",
    "Tap a goal to add money to it from the pool, move money back out, or spend from it. Deleting a goal puts its money back in the pool.",
    "This “What's new” list (More → Settings), and a heads-up after each update."]],
  ["40", "2026-10-30", ["Fun Fund money can come from an income line (a paycheck, or a gift logged as income).", "A paycheck can put a set amount in the Fun Fund every payday."]],
  ["39", "2026-10-30", ["Payments between you sit under what they paid for, and the cost says whose part is paid.", "One payment can cover several costs (like a Venmo for rent and internet).", "Venmo imports offer to group a payment with the costs it adds up to."]],
  ["38", "2026-10-30", ["With both phones open, saving an edit no longer undoes what the other person just changed."]],
  ["37", "2026-10-30", ["Typing a bill into Add spending points you to the bill's Paid button, so rent isn't logged twice."]],
  ["36", "2026-10-30", ["Warnings before saving something that looks like a duplicate, and a “Possible duplicates” review.", "A bill's Paid button asks first if that bill was just logged."]],
  ["35", "2026-10-30", ["“I paid Charlie my share” on shared costs; “someone paid me back” is now for friends.", "Paychecks you're expecting: Got it logs them, and Income shows what's still coming."]],
  ["33", "2026-10-30", ["A first try at stopping forms from jumping when the iPhone keyboard opens."]],
  ["32", "2026-10-30", ["Paybacks: money a friend pays you back lowers the cost instead of counting as income."]],
  ["31", "2026-10-30", ["A memo on payments between you, and Pay in Venmo with the same memo."]],
  ["30", "2026-10-30", ["Split shared costs any way (by percent or amount); tap who-owes-whom to see why."]],
  ["28", "2026-10-30", ["No stray Notify pop-up after coming back to the app; the Today button opens Today."]],
  ["27", "2026-10-30", ["The app shows its version and offers Reload when a newer one is out."]],
  ["Before", "2026-10-29", ["Chores, kitchen, family health, notes with drawings, calendar and budget with Jeff.", "Sync between both phones, offline use, notifications and morning reminders.",
    "Bank, card and Venmo imports (CSV and PDF), Jeff's month-end wrap-up and the Summary tab."]]
];
function whatsNew(){
  openSheet("What's new", `${CHANGELOG.map(([v, d, items]) => `<section class="sec"><span class="label">${v === "Before" ? "Before version numbers" : `Version ${esc(v)}`} · ${esc(niceDate(d))}${BUILD.endsWith("· " + v) ? ' <span class="pill ok">You have this</span>' : ""}</span>
    <ul class="small" style="margin:4px 0 0;padding-left:18px">${items.map(x => `<li>${esc(x)}</li>`).join("")}</ul></section>`).join("")}
    <div class="actions"><div class="r"><button type="button" class="btn" data-act="closeSheet">Done</button></div></div>`, () => {}, false);
}
// After an update: offer to show what changed (once per version)
setTimeout(() => { try {
  if(prefs.seenBuild && prefs.seenBuild !== BUILD) toast(`Updated to version ${BUILD.split("· ")[1]}`, () => whatsNew(), "What's new", 9000);
  if(prefs.seenBuild !== BUILD){ prefs.seenBuild = BUILD; savePrefs(); } } catch(e){} }, 1200);''')
rep("""      <p class="small muted" style="margin:0">zen·dom version ${BUILD}</p>""",
    """      <p class="small muted" style="margin:0">zen·dom version ${BUILD} · <button type="button" class="link" data-act="whatsNew" style="padding:0">What's new</button></p>""")
rep("""openGoal: id => goalSheet(id),""", """openGoal: id => goalSheet(id), whatsNew: () => whatsNew(),""")
open(p, "w").write(s)
print("whats new added")
