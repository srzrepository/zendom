"""Step 19: Jeff's month-end wrap-up.
A sheet for any month: total spent (vs the month before), income, where it went by category (with
over-target flags), who paid what (each person's total, shared vs just-theirs, their top categories),
the biggest purchase, and who owed whom at month end. Opened from Budget (past months, or "so far"
from the 25th) and, for the first 5 days of a month, from a card on Today that each phone can dismiss.
No stored-data change (the dismissal lives in this phone's prefs). Usage: python3 patch_step19_wrapup.py file.html"""
import sys
p = sys.argv[1]; s = open(p).read()
def rep(old, new):
    global s
    assert s.count(old) == 1, (s.count(old), old[:90])
    s = s.replace(old, new)

rep(""".catrow .pill,.catrow .cnone{grid-column:1 / -1;justify-self:start}""",
""".catrow .pill,.catrow .cnone{grid-column:1 / -1;justify-self:start}
.wrap-hd{display:flex;gap:12px;align-items:center}
.wrap-hd .jeff-pig{width:72px;height:72px}
.wrap-nums{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}
.wrap-nums div{background:var(--surface-2);border-radius:4px;padding:8px;text-align:center}
.wrap-nums b{display:block;font-size:1.1rem;font-variant-numeric:tabular-nums}
.wrap-nums span{font-size:.75rem;color:var(--muted)}
.wcats{display:flex;flex-direction:column;gap:8px}
.wcat{display:grid;grid-template-columns:1fr auto;gap:2px 10px;font-size:.92rem}
.wcat .t{font-weight:600;min-width:0;overflow-wrap:anywhere}.wcat .v{font-variant-numeric:tabular-nums;font-weight:600}
.wcat .b{grid-column:1 / -1;height:8px;border-radius:4px;background:var(--surface-2);overflow:hidden}.wcat .b i{display:block;height:100%;background:var(--accent)}
.wcat.over .b i{background:var(--late)}
.wwho{display:flex;gap:10px;align-items:flex-start;padding:8px 0;border-top:1px solid var(--line)}
.wwho:first-child{border-top:0}
.wwho .av{width:36px;height:36px;border-radius:4px;overflow:hidden;flex:none;background:var(--surface-2)}
.wwho p{margin:2px 0 0;font-size:.88rem;color:var(--muted)}""")

rep("""function monthStats(k){""",
r"""/* ---------- Jeff's month-end wrap-up ---------- */
// Who owed whom after everything dated up to the end of a month (same 50/50 rule as balance()).
function balanceUntil(day){
  let b = 0;
  state.budget.txns.forEach(t => { if(t.date > day) return;
    if(t.kind === "expense" && t.shared) b += (t.paidBy === "sam" ? 1 : -1) * t.amount / 2;
    if(t.kind === "settle") b += (t.paidBy === "charlie" ? -1 : 1) * t.amount; });
  return Math.round(b);
}
function monthWrap(k){
  const st = monthStats(k), prev = monthStats(addMonthKey(k, -1));
  const exp = st.tx.filter(t => t.kind === "expense");
  const cats = Object.entries(st.byCat).map(([id, amt]) => { const c = state.budget.categories.find(x => x.id === id), L = c ? lim(c, k) : 0;
    return {name: id === "none" ? "Uncategorized" : catName(id), amt, limit: L, over: L && amt > L ? amt - L : 0}; }).sort((a, b) => b.amt - a.amt);
  const who = HUMANS.map(h => { const mine = exp.filter(t => t.paidBy === h), paid = mine.reduce((a, t) => a + t.amount, 0), shared = mine.filter(t => t.shared).reduce((a, t) => a + t.amount, 0);
    const bc = {}; mine.forEach(t => { const n = t.categoryId ? catName(t.categoryId) : "Uncategorized"; bc[n] = (bc[n] || 0) + t.amount; });
    return {h, paid, n: mine.length, shared, own: paid - shared, top: Object.entries(bc).sort((a, b) => b[1] - a[1]).slice(0, 3)}; });
  const sharedTotal = exp.filter(t => t.shared).reduce((a, t) => a + t.amount, 0);
  const biggest = exp.slice().sort((a, b) => b.amount - a.amount)[0] || null;
  const [y, m] = k.split("-").map(Number), lastDay = toStr(new Date(y, m, 0));
  return {k, spent: st.spent, income: st.income, prevSpent: prev.spent, prevK: addMonthKey(k, -1), cats, who, sharedTotal, biggest, count: exp.length,
    bal: balanceUntil(lastDay), settled: st.tx.filter(t => t.kind === "settle").reduce((a, t) => a + t.amount, 0), partial: k === todayStr().slice(0, 7)};
}
function wrapVerdict(w){
  const mn = monthName(w.k).split(" ")[0], pmn = monthName(w.prevK).split(" ")[0];
  if(!w.count) return w.partial ? `Nothing logged in ${mn} yet. I'll be here with my calculator.` : `Nothing was logged in ${mn}. Either you were very good or very forgetful. Oink?`;
  const over = w.cats.filter(c => c.over).sort((a, b) => b.over - a.over);
  const diff = w.spent - w.prevSpent;
  const vs = w.prevSpent ? (Math.abs(diff) < w.prevSpent * .05 ? `about the same as ${pmn}` : `${money(Math.abs(diff))} ${diff < 0 ? "less" : "more"} than ${pmn}`) : "";
  let line = `${w.partial ? "So far" : "All told"}, ${money(w.spent)} went out${vs ? `, ${vs}` : ""}.`;
  if(over.length) line += ` ${over[0].name} ran ${money(over[0].over)} over its target.`;
  else if(diff < 0 && w.prevSpent) line += " Oink of approval.";
  else if(w.cats[0]) line += ` Most of it went to ${w.cats[0].name}.`;
  return line;
}
function wrapSheet(k){
  const w = monthWrap(k), mn = monthName(k), pig = state.budget.pigName, top = w.cats.slice(0, 6), maxC = top.length ? top[0].amt : 1;
  const balTxt = w.bal === 0 ? "You were even." : `${nameOf(w.bal > 0 ? "charlie" : "sam")} owed ${nameOf(w.bal > 0 ? "sam" : "charlie")} ${money(Math.abs(w.bal))}${w.partial ? " so far" : " at month end"}.`;
  const nowBal = balance();
  openSheet(`${pig}'s ${mn} wrap-up${w.partial ? " (so far)" : ""}`, `
    <div class="wrap-hd"><div class="jeff-pig">${pigSvg()}</div><p class="bubble" style="flex:1">${esc(wrapVerdict(w))}</p></div>
    <div class="wrap-nums"><div><b>${money(w.spent)}</b><span>spent · ${w.count} ${w.count === 1 ? "purchase" : "purchases"}</span></div>
      <div><b>${money(w.income)}</b><span>came in</span></div>
      <div><b>${w.income ? money(w.income - w.spent) : "—"}</b><span>${w.income ? (w.income >= w.spent ? "left over" : "short") : "no income logged"}</span></div></div>
    ${w.count ? `<section class="sec"><span class="label">Where it went</span><div class="wbars">${top.map(c => `<div class="wcat ${c.over ? "over" : ""}"><span class="t">${esc(c.name)}${c.over ? ` <span class="pill late">${money(c.over)} over</span>` : ""}</span><span class="v">${money(c.amt)} <span class="small muted">${Math.round(100 * c.amt / w.spent)}%</span></span><span class="b"><i style="width:${Math.max(3, Math.round(100 * c.amt / maxC))}%"></i></span></div>`).join("")}
      ${w.cats.length > top.length ? `<p class="small muted" style="margin:0">+ ${w.cats.length - top.length} smaller ${w.cats.length - top.length === 1 ? "category" : "categories"} (${money(w.cats.slice(top.length).reduce((a, c) => a + c.amt, 0))})</p>` : ""}</div></section>
    <section class="sec"><span class="label">Who paid</span><div>${w.who.map(x => `<div class="wwho"><span class="av">${sprite(x.h)}</span><div style="min-width:0;flex:1">
        <b>${esc(nameOf(x.h))}: ${money(x.paid)}</b> <span class="small muted">· ${x.n} ${x.n === 1 ? "purchase" : "purchases"}</span>
        ${x.paid ? `<p>${money(x.shared)} shared, ${money(x.own)} just ${x.h === prefs.user ? "yours" : (x.h === "sam" ? "hers" : "his")}${x.top.length ? ` · mostly ${x.top.map(([n, a]) => `${esc(n)} ${money(a)}`).join(", ")}` : ""}</p>` : `<p>Nothing logged.</p>`}</div></div>`).join("")}</div>
      ${w.sharedTotal ? `<p class="small" style="margin:6px 0 0">Shared costs came to ${money(w.sharedTotal)}, so ${money(Math.round(w.sharedTotal / 2))} each. ${esc(balTxt)}</p>` : ""}</section>
    ${w.biggest ? `<section class="sec"><span class="label">Biggest purchase</span><p style="margin:0">${money(w.biggest.amount)} · ${esc(w.biggest.note || catName(w.biggest.categoryId))} <span class="small muted">(${esc(nameOf(w.biggest.paidBy))}, ${esc(niceDate(w.biggest.date))})</span></p></section>` : ""}` : ""}
    <div class="actions"><span>${nowBal ? `<button type="button" class="btn ghost small" data-act="settleUp">Record a payment</button>` : ""}</span>
      <div class="r"><button type="button" class="btn" data-act="closeSheet">Close</button></div></div>`, () => {}, false);
}
// Today card for the first 5 days of a month, about the month that just ended
function wrapTeaserHTML(){
  const t = todayStr(), day = +t.slice(8); if(day > 5) return "";
  const k = addMonthKey(t.slice(0, 7), -1);
  if((prefs.wrapSeen || {})[k] || !state.budget.txns.some(x => x.date.slice(0, 7) === k)) return "";
  return `<section class="card soon-card"><span class="ic">${IC.budget}</span><div style="flex:1;min-width:0"><h3>${esc(state.budget.pigName)}'s ${esc(monthName(k).split(" ")[0])} wrap-up is ready</h3>
    <p>How much went out, on what, and who paid.</p>
    <div class="actions" style="margin-top:8px;justify-content:flex-start"><button type="button" class="btn small" data-act="openWrap" data-id="${k}">Read it</button><button type="button" class="link" data-act="wrapDismiss" data-id="${k}">Not now</button></div></div></section>`;
}
function monthStats(k){""")

# Budget: a button under Jeff for past months, or "so far" late in the month
rep("""      <p class="bubble" role="status">${esc(jeffSays(k, st))}</p></div>
  </section>""",
"""      <p class="bubble" role="status">${esc(jeffSays(k, st))}</p>
      ${!isNow || +todayStr().slice(8) >= 25 ? `<button type="button" class="btn small" data-act="openWrap" data-id="${k}" style="align-self:flex-start">${esc(monthName(k).split(" ")[0])} wrap-up${isNow ? " so far" : ""}</button>` : ""}</div>
  </section>""")
rep("""  ${billsDueHTML()}""", """  ${wrapTeaserHTML()}
  ${billsDueHTML()}""")
rep("""  settleUp: () => settleForm(null),""",
"""  settleUp: () => settleForm(null),
  openWrap: id => { if(!/^\\d{4}-\\d{2}$/.test(id)) return; prefs.wrapSeen = Object.assign({}, prefs.wrapSeen, {[id]: true}); savePrefs(); render(); wrapSheet(id); },
  wrapDismiss: id => { prefs.wrapSeen = Object.assign({}, prefs.wrapSeen, {[id]: true}); savePrefs(); render(); },""")

open(p, "w").write(s)
print("step 19 applied")
