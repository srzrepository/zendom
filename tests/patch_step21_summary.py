"""Step 21: Budget -> Summary tab with date filters (This month, Last month, Last 3 months, This year,
or From/To). Same report as the month wrap-up for any range, a month-by-month breakdown for longer
ranges, and Jeff crunching numbers for a moment whenever the range changes. Empty ranges and odd
dates (From after To, blank) are handled. The wrap-up card/buttons now open this tab.
The chosen range lives in this phone's prefs. Usage: python3 patch_step21_summary.py file.html jeff_anim.js"""
import sys
p = sys.argv[1]; s = open(p).read(); JEFF = open(sys.argv[2]).read()
def rep(old, new):
    global s
    assert s.count(old) == 1, (s.count(old), old[:90])
    s = s.replace(old, new)

rep('const BTABS = {spending:"Spending", plan:"Plan", fund:"Fun Fund"};', 'const BTABS = {spending:"Spending", plan:"Plan", fund:"Fun Fund", summary:"Summary"};')
rep('return sub + (bt === "plan" ? viewBudgetPlan() : bt === "fund" ? viewFund() : viewBudget());',
    'return sub + (bt === "plan" ? viewBudgetPlan() : bt === "fund" ? viewFund() : bt === "summary" ? viewSummary() : viewBudget());')

rep(""".wwho p{margin:2px 0 0;font-size:.88rem;color:var(--muted)}""",
""".wwho p{margin:2px 0 0;font-size:.88rem;color:var(--muted)}
.sumrange{display:flex;flex-direction:column;gap:8px}
.sumdates{display:grid;grid-template-columns:1fr 1fr;gap:10px}.sumdates > *{min-width:0}
.jeffanim{width:112px;height:132px;flex:none}
.jeffanim svg{width:100%;height:100%;display:block}
.jeffanim .jf{opacity:0;animation:jf 1.1s steps(1) infinite}
@keyframes jf{0%{opacity:1}10%{opacity:0}100%{opacity:0}}
@media (prefers-reduced-motion:reduce){.jeffanim .jf{animation:none}.jeffanim .jf0{opacity:1}}""")

# --- range report (monthWrap becomes a range report for one month) ---
rep("""function monthWrap(k){
  const st = monthStats(k), prev = monthStats(addMonthKey(k, -1));
  const exp = st.tx.filter(t => t.kind === "expense");
  const cats = Object.entries(st.byCat).map(([id, amt]) => { const c = state.budget.categories.find(x => x.id === id), L = c ? lim(c, k) : 0;
    return {name: id === "none" ? "Uncategorized" : catName(id), amt, limit: L, over: L && amt > L ? amt - L : 0}; }).sort((a, b) => b.amt - a.amt);""",
"""function rangeTx(from, to){ return state.budget.txns.filter(t => isDate(t.date) && t.date >= from && t.date <= to); }
function monthWrap(k){
  const [y, m] = k.split("-").map(Number);
  return Object.assign(rangeWrap(`${k}-01`, toStr(new Date(y, m, 0)), k), {k, prevK: addMonthKey(k, -1), partial: k === todayStr().slice(0, 7)});
}
// The report for any range of dates. monthKey: when the range is exactly one month (targets apply).
function rangeWrap(from, to, monthKey){
  const tx = rangeTx(from, to), exp = tx.filter(t => t.kind === "expense");
  const days = diffDays(from, to) + 1, pFrom = addDays(from, -days), pTo = addDays(from, -1);
  const prevExp = rangeTx(pFrom, pTo).filter(t => t.kind === "expense");
  const byCat = {}; exp.forEach(t => { const id = t.categoryId || "none"; byCat[id] = (byCat[id] || 0) + t.amount; });
  const cats = Object.entries(byCat).map(([id, amt]) => { const c = state.budget.categories.find(x => x.id === id), L = c && monthKey ? lim(c, monthKey) : 0;
    return {name: id === "none" ? "Uncategorized" : catName(id), amt, limit: L, over: L && amt > L ? amt - L : 0}; }).sort((a, b) => b.amt - a.amt);""")
rep("""  const sharedTotal = exp.filter(t => t.shared).reduce((a, t) => a + t.amount, 0);
  const biggest = exp.slice().sort((a, b) => b.amount - a.amount)[0] || null;
  const [y, m] = k.split("-").map(Number), lastDay = toStr(new Date(y, m, 0));
  return {k, spent: st.spent, income: st.income, prevSpent: prev.spent, prevK: addMonthKey(k, -1), cats, who, sharedTotal, biggest, count: exp.length,
    bal: balanceUntil(lastDay), settled: st.tx.filter(t => t.kind === "settle").reduce((a, t) => a + t.amount, 0), partial: k === todayStr().slice(0, 7)};
}""",
"""  const sharedTotal = exp.filter(t => t.shared).reduce((a, t) => a + t.amount, 0);
  const biggest = exp.slice().sort((a, b) => b.amount - a.amount)[0] || null;
  const sum = l => l.reduce((a, t) => a + t.amount, 0);
  const months = []; for(let k = from.slice(0, 7); k <= to.slice(0, 7) && months.length < 120; k = addMonthKey(k, 1)) months.push({k, spent: sum(exp.filter(t => t.date.slice(0, 7) === k))});
  return {from, to, days, spent: sum(exp), income: sum(tx.filter(t => t.kind === "income")), prevSpent: sum(prevExp), prevFrom: pFrom, prevTo: pTo, cats, who, sharedTotal, biggest,
    count: exp.length, bal: balanceUntil(to), settled: sum(tx.filter(t => t.kind === "settle")), months, partial: to >= todayStr() && from <= todayStr()};
}""")
# verdict: works for months and ranges
rep("""function wrapVerdict(w){
  const mn = monthName(w.k).split(" ")[0], pmn = monthName(w.prevK).split(" ")[0];
  if(!w.count) return w.partial ? `Nothing logged in ${mn} yet. I'll be here with my calculator.` : `Nothing was logged in ${mn}. Either you were very good or very forgetful. Oink?`;""",
"""function wrapVerdict(w){
  const mn = w.k ? monthName(w.k).split(" ")[0] : rangeLabel(w.from, w.to), pmn = w.k ? monthName(w.prevK).split(" ")[0] : "the same stretch before";
  if(!w.count) return w.partial ? `Nothing logged ${w.k ? "in " : "for "}${mn} yet. I'll be here with my calculator.` : `Nothing was logged ${w.k ? "in " : "for "}${mn}. Either you were very good or very forgetful. Oink?`;""")

# replace the wrap-up sheet with a reusable report body
i = s.index("function wrapSheet(k){"); j = s.index("// Today card for the first 5 days of a month")
s = s[:i] + r"""function rangeLabel(from, to){
  const f = parse(from), t = parse(to), sameY = f.getFullYear() === t.getFullYear();
  if(from === to) return niceDate(from);
  if(from.slice(8) === "01" && toStr(new Date(t.getFullYear(), t.getMonth() + 1, 0)) === to) return from.slice(0, 7) === to.slice(0, 7) ? monthName(from.slice(0, 7)) : `${monthName(from.slice(0, 7)).split(" ")[0]}${sameY ? "" : " " + f.getFullYear()} – ${monthName(to.slice(0, 7))}`;
  return `${f.toLocaleDateString(undefined, {month:"short", day:"numeric", year: sameY ? undefined : "numeric"})} – ${t.toLocaleDateString(undefined, {month:"short", day:"numeric", year:"numeric"})}`;
}
function summaryBody(w){
  const top = w.cats.slice(0, 6), maxC = top.length ? top[0].amt : 1, maxM = Math.max(1, ...w.months.map(m => m.spent));
  const end = w.k ? (w.partial ? " so far" : " at month end") : (w.partial ? " so far" : ` on ${niceDate(w.to)}`);
  const balTxt = w.bal === 0 ? "You were even." : `${nameOf(w.bal > 0 ? "charlie" : "sam")} owed ${nameOf(w.bal > 0 ? "sam" : "charlie")} ${money(Math.abs(w.bal))}${end}.`;
  const pct = n => w.spent ? Math.round(100 * n / w.spent) : 0;
  return `<div class="wrap-nums"><div><b>${money(w.spent)}</b><span>spent · ${w.count} ${w.count === 1 ? "purchase" : "purchases"}</span></div>
      <div><b>${money(w.income)}</b><span>came in</span></div>
      <div><b>${w.income ? money(Math.abs(w.income - w.spent)) : "—"}</b><span>${w.income ? (w.income >= w.spent ? "left over" : "short") : "no income logged"}</span></div></div>
    ${w.months.length > 1 && w.count ? `<section class="sec"><span class="label">Month by month</span><div class="wbars">${w.months.map(m => `<div class="wcat"><span class="t">${esc(monthName(m.k))}</span><span class="v">${money(m.spent)}</span><span class="b"><i style="width:${m.spent ? Math.max(3, Math.round(100 * m.spent / maxM)) : 0}%"></i></span></div>`).join("")}</div></section>` : ""}
    ${w.count ? `<section class="sec"><span class="label">Where it went</span><div class="wbars">${top.map(c => `<div class="wcat ${c.over ? "over" : ""}"><span class="t">${esc(c.name)}${c.over ? ` <span class="pill late">${money(c.over)} over</span>` : ""}</span><span class="v">${money(c.amt)} <span class="small muted">${pct(c.amt)}%</span></span><span class="b"><i style="width:${Math.max(3, Math.round(100 * c.amt / maxC))}%"></i></span></div>`).join("")}
      ${w.cats.length > top.length ? `<p class="small muted" style="margin:0">+ ${w.cats.length - top.length} smaller ${w.cats.length - top.length === 1 ? "category" : "categories"} (${money(w.cats.slice(top.length).reduce((a, c) => a + c.amt, 0))})</p>` : ""}</div></section>
    <section class="sec"><span class="label">Who paid</span><div>${w.who.map(x => `<div class="wwho"><span class="av">${sprite(x.h)}</span><div style="min-width:0;flex:1">
        <b>${esc(nameOf(x.h))}: ${money(x.paid)}</b> <span class="small muted">· ${x.n} ${x.n === 1 ? "purchase" : "purchases"}</span>
        ${x.paid ? `<p>${money(x.shared)} shared, ${money(x.own)} just ${x.h === prefs.user ? "yours" : (x.h === "sam" ? "hers" : "his")}${x.top.length ? ` · mostly ${x.top.map(([n, a]) => `${esc(n)} ${money(a)}`).join(", ")}` : ""}</p>` : `<p>Nothing logged.</p>`}</div></div>`).join("")}</div>
      ${w.sharedTotal ? `<p class="small" style="margin:6px 0 0">Shared costs came to ${money(w.sharedTotal)}, so ${money(Math.round(w.sharedTotal / 2))} each. ${esc(balTxt)}</p>` : ""}</section>
    ${w.biggest ? `<section class="sec"><span class="label">Biggest purchase</span><p style="margin:0">${money(w.biggest.amount)} · ${esc(w.biggest.note || catName(w.biggest.categoryId))} <span class="small muted">(${esc(nameOf(w.biggest.paidBy))}, ${esc(niceDate(w.biggest.date))})</span></p></section>` : ""}` : ""}
    ${balance() ? `<div class="actions" style="justify-content:flex-start"><button type="button" class="btn ghost small" data-act="settleUp">Record a payment</button></div>` : ""}`;
}
/* ---- Jeff crunching numbers (10 frames of original pixel art, see tools/jeff-draft) ---- */
""" + JEFF + r"""
let jeffAnimSvg = "";
function jeffCrunchSVG(){
  if(jeffAnimSvg) return jeffAnimSvg;
  const A = JEFF_ANIM, base = A.base.map(r => r.split(""));
  const frames = [base].concat(A.d.map(segs => { const g = base.map(r => r.slice()); segs.forEach(([y, x, t]) => { for(let i = 0; i < t.length; i++) g[y][x + i] = t[i]; }); return g; }));
  return jeffAnimSvg = `<svg viewBox="0 0 ${A.w} ${A.h}" shape-rendering="crispEdges" aria-hidden="true">${frames.map((g, i) => `<g class="jf jf${i}" style="animation-delay:${(-1.1 + i * .11).toFixed(2)}s">${faceRects(g.map(r => r.join("")), A.pal)}</g>`).join("")}</svg>`;
}
/* ---- the Summary tab ---- */
const SUM_PRESETS = [["month", "This month"], ["last", "Last month"], ["3m", "Last 3 months"], ["year", "This year"], ["custom", "Pick dates"]];
let sumCrunchUntil = 0, sumCrunchKey = "";
function sumRange(){
  const t = todayStr(), k = t.slice(0, 7), sm = prefs.sum || {}, monthEnd = mk => { const [y, m] = mk.split("-").map(Number); return toStr(new Date(y, m, 0)); };
  const P = sm.preset || "month";
  if(P === "last"){ const lk = addMonthKey(k, -1); return {preset:P, from:`${lk}-01`, to:monthEnd(lk), k:lk}; }
  if(P === "3m") return {preset:P, from:`${addMonthKey(k, -2)}-01`, to:monthEnd(k)};
  if(P === "year") return {preset:P, from:`${k.slice(0, 4)}-01-01`, to:`${k.slice(0, 4)}-12-31`};
  if(P === "custom"){
    let f = isDate(sm.from) ? sm.from : `${k}-01`, to = isDate(sm.to) ? sm.to : t, note = "";
    if(f > to){ [f, to] = [to, f]; note = "Swapped the dates so From comes first."; }
    if(diffDays(f, to) > 3660){ f = addDays(to, -3660); note = "That's more than 10 years; showing the last 10."; }
    const one = f.slice(8) === "01" && f.slice(0, 7) === to.slice(0, 7) && to === monthEnd(f.slice(0, 7));
    return {preset:P, from:f, to, note, k: one ? f.slice(0, 7) : null};
  }
  return {preset:"month", from:`${k}-01`, to:monthEnd(k), k};
}
function viewSummary(){
  const R = sumRange(), w = R.k ? monthWrap(R.k) : rangeWrap(R.from, R.to);
  const key = R.from + R.to, reduce = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
  if(key !== sumCrunchKey){ sumCrunchKey = key; sumCrunchUntil = reduce ? 0 : Date.now() + 1800; setTimeout(() => { if(prefs.tab === "budget" && prefs.budgetTab === "summary") render(); }, 1850); }
  const crunching = Date.now() < sumCrunchUntil;
  const label = rangeLabel(R.from, R.to);
  return `<div class="sumrange"><div class="seg" role="group" aria-label="Dates">${SUM_PRESETS.map(([id, l]) => `<button type="button" class="chip" data-act="sumPreset" data-id="${id}" aria-pressed="${R.preset === id}">${l}</button>`).join("")}</div>
      ${R.preset === "custom" ? `<div class="sumdates">${field("sumFrom", "From", `<input id="sumFrom" type="date" data-change="sumFrom" value="${esc(R.from)}">`)}${field("sumTo", "To", `<input id="sumTo" type="date" data-change="sumTo" value="${esc(R.to)}">`)}</div>
        ${R.note ? `<p class="small muted" style="margin:0">${esc(R.note)}</p>` : ""}` : ""}</div>
    <section class="jeff card">
      <div class="${crunching ? "jeffanim" : "jeff-pig"}">${crunching ? jeffCrunchSVG() : pigSvg()}</div>
      <div class="jeff-talk"><span class="label">${esc(state.budget.pigName)} · ${esc(label)}</span>
        <p class="bubble" role="status">${crunching ? "Crunching the numbers…" : esc(wrapVerdict(w))}</p></div>
    </section>
    ${summaryBody(w)}`;
}
""" + s[j:]

# wrap-up entry points now open the Summary tab
rep("""  openWrap: id => { if(!/^\\d{4}-\\d{2}$/.test(id)) return; prefs.wrapSeen = Object.assign({}, prefs.wrapSeen, {[id]: true}); savePrefs(); render(); wrapSheet(id); },""",
"""  openWrap: id => { if(!/^\\d{4}-\\d{2}$/.test(id)) return; prefs.wrapSeen = Object.assign({}, prefs.wrapSeen, {[id]: true});
    const k = todayStr().slice(0, 7), [y, m] = id.split("-").map(Number);
    prefs.sum = id === k ? {preset:"month"} : id === addMonthKey(k, -1) ? {preset:"last"} : {preset:"custom", from:`${id}-01`, to:toStr(new Date(y, m, 0))};
    prefs.tab = "budget"; prefs.budgetTab = "summary"; savePrefs(); render(); window.scrollTo(0, 0); },
  sumPreset: id => { if(!SUM_PRESETS.some(x => x[0] === id)) return; const cur = sumRange();
    prefs.sum = id === "custom" ? {preset:"custom", from:cur.from, to:cur.to} : {preset:id}; savePrefs(); render(); },""")
rep("""  if(el.dataset.change === "rsort"){ ACTIONS.rsort(el.value); }""",
"""  if(el.dataset.change === "rsort"){ ACTIONS.rsort(el.value); }
  if(el.dataset.change === "sumFrom" || el.dataset.change === "sumTo"){ const cur = sumRange();
    prefs.sum = {preset:"custom", from: el.dataset.change === "sumFrom" ? el.value : cur.from, to: el.dataset.change === "sumTo" ? el.value : cur.to}; savePrefs(); render(); }""")

open(p, "w").write(s)
print("step 21 applied")
