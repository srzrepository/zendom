"""Step 24: Budget -> Spending gets a Both of us / Sam / Charlie switch (remembered per phone).
Person view: Spent = their share (things just for them + half of every shared cost, whoever paid),
with what they actually paid underneath; Income = their income; categories show their share (targets
are household-wide, so bars show only in Both); the list shows entries that involve them.
Also: a second cover for the iPhone status-bar strip, attached to the sticky header (the body::before
cover isn't painting on Sam's phone), and the Spending footer no longer says "only on this device"
when the two phones sync. No data change. Usage: python3 patch_step24_mine.py file.html"""
import sys
p = sys.argv[1]; s = open(p).read()
def rep(old, new):
    global s
    assert s.count(old) == 1, (s.count(old), old[:90])
    s = s.replace(old, new)

# status-bar strip: hang a cover off the top of the sticky header
rep(""".top{background:var(--bg);margin-inline:-8px;padding-inline:8px;border-radius:4px}""",
""".top{background:var(--bg);margin-inline:-8px;padding-inline:8px;border-radius:4px}
.top::before{content:"";position:absolute;left:calc(50% - 50vw);width:100vw;bottom:100%;height:calc(env(safe-area-inset-top,0px) + 12px);background:var(--grass);pointer-events:none}""")

# the person switch + person-aware numbers
rep("""function viewBudget(){
  const k = curMonth(), st = monthStats(k), bal = balance();""",
"""// One person's view of a month: their share of spending (own things + half of shared), their income.
function personStats(st, who){
  const live = st.tx.filter(t => !t.cancelled), share = t => t.shared ? Math.round(t.amount / 2) : (t.paidBy === who ? t.amount : 0);
  const exp = live.filter(t => t.kind === "expense"), byCat = {};
  exp.forEach(t => { const v = share(t); if(v) byCat[t.categoryId || "none"] = (byCat[t.categoryId || "none"] || 0) + v; });
  return {spent: exp.reduce((a, t) => a + share(t), 0), paid: exp.filter(t => t.paidBy === who).reduce((a, t) => a + t.amount, 0),
    income: live.filter(t => t.kind === "income" && t.paidBy === who).reduce((a, t) => a + t.amount, 0), byCat,
    tx: st.tx.filter(t => t.kind === "settle" || t.paidBy === who || (t.kind === "expense" && t.shared))};
}
function viewBudget(){
  const k = curMonth(), stAll = monthStats(k), bal = balance();
  const who = HUMANS.includes(prefs.spendWho) ? prefs.spendWho : "", ps = who ? personStats(stAll, who) : null;
  const st = who ? Object.assign({}, stAll, {spent: ps.spent, income: ps.income, byCat: ps.byCat, tx: ps.tx, budgeted: 0}) : stAll;""")
rep("""  <div class="btools"><button type="button" class="btn ghost small" data-act="importCsv">Import from bank or Venmo</button><button type="button" class="link" data-act="jeffSettings">${esc(state.budget.pigName)}'s settings</button></div>
  <div class="stats">
    <div class="stat"><span class="label">Spent</span><b>${money(st.spent)}</b>${st.budgeted ? `<span class="small muted">of ${money(st.budgeted)} budgeted</span>` : ""}</div>""",
"""  <div class="btools"><button type="button" class="btn ghost small" data-act="importCsv">Import from bank or Venmo</button><button type="button" class="link" data-act="jeffSettings">${esc(state.budget.pigName)}'s settings</button></div>
  <div class="seg" role="group" aria-label="Whose spending">${[["", "Both of us"], ...HUMANS.map(h => [h, nameOf(h)])].map(([id, l]) => `<button type="button" class="chip" data-act="spendWho" data-id="${id}" aria-pressed="${who === id}">${esc(l)}</button>`).join("")}</div>
  <div class="stats">
    <div class="stat"><span class="label">${who ? `${esc(nameOf(who))}'s share` : "Spent"}</span><b>${money(st.spent)}</b>${who ? `<span class="small muted">${money(ps.paid)} paid by ${esc(nameOf(who))}</span>` : st.budgeted ? `<span class="small muted">of ${money(st.budgeted)} budgeted</span>` : ""}</div>""")
rep("""    <div class="stat"><span class="label">Income</span><b>${money(st.income)}</b><span class="small muted">${st.income ? `${money(st.income - st.spent)} after spending` : "None logged"}</span></div>""",
"""    <div class="stat"><span class="label">${who ? `${esc(nameOf(who))}'s income` : "Income"}</span><b>${money(st.income)}</b><span class="small muted">${st.income ? `${money(Math.abs(st.income - st.spent))} ${st.income >= st.spent ? "after spending" : "short"}` : "None logged"}</span></div>""")
rep("""  <section class="sec"><div class="sec-head"><span class="label">Categories</span><button type="button" class="link" data-act="editCat">+ Add</button></div>
    <div class="glist">${cats.map(c => { const L = lim(c, k), sp = st.byCat[c.id] || 0,""",
"""  <section class="sec"><div class="sec-head"><span class="label">Categories${who ? ` · ${esc(nameOf(who))}'s share` : ""}</span><button type="button" class="link" data-act="editCat">+ Add</button></div>
    ${who ? `<p class="small muted" style="margin:0 0 6px">Targets are for both of you, so they show under Both of us.</p>` : ""}
    <div class="glist">${cats.map(c => { const L = who ? 0 : lim(c, k), sp = st.byCat[c.id] || 0,""")
rep("""${L ? `<span class="cbar ${over ? "over" : pct >= 85 ? "near" : ""}"><i style="width:${pct}%"></i></span>${over ? `<span class="pill late">${money(sp - L)} over</span>` : ""}` : `<span class="small muted cnone">Nothing assigned</span>`}</button>`; }).join("")}""",
    """${L ? `<span class="cbar ${over ? "over" : pct >= 85 ? "near" : ""}"><i style="width:${pct}%"></i></span>${over ? `<span class="pill late">${money(sp - L)} over</span>` : ""}` : who ? "" : `<span class="small muted cnone">Nothing assigned</span>`}</button>`; }).join("")}""")
# in a person's list, say what part of a shared cost is theirs
rep("""          ${t.details ? `<span class="td">${esc(t.details)}</span>` : ""}</span>""",
    """          ${t.details ? `<span class="td">${esc(t.details)}</span>` : ""}${who && t.kind === "expense" && t.shared ? `<span class="td">${esc(nameOf(who))}'s half: ${money(Math.round(t.amount / 2))}</span>` : ""}</span>""")
rep("""      : `<div class="empty"><p>No spending logged for ${esc(monthName(k))}.</p>${isNow ? `<button type="button" class="btn" data-act="newTxn">${IC.plus} Add spending</button>` : ""}</div>`}
  </section>
  <p class="private">${IC.lock} Typed in by you and stored only on this device. Nothing connects to your bank.</p>`;""",
"""      : `<div class="empty"><p>${who ? `Nothing for ${esc(nameOf(who))} in ${esc(monthName(k))}.` : `No spending logged for ${esc(monthName(k))}.`}</p>${isNow ? `<button type="button" class="btn" data-act="newTxn">${IC.plus} Add spending</button>` : ""}</div>`}
  </section>
  <p class="private">${IC.lock} ${sync.status === "on" ? "Shared only between your two accounts." : "Stored only on this device."} Nothing connects to your bank.</p>`;""")
rep("""  settleUp: () => settleForm(null),""",
"""  settleUp: () => settleForm(null),
  spendWho: id => { prefs.spendWho = HUMANS.includes(id) ? id : ""; savePrefs(); render(); },""")

open(p, "w").write(s)
print("step 24 applied")
