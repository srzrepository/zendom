"""Step 40: Fun Fund money comes from your income lines.
- Add to the Fun Fund has "Where did it come from?": one of your income lines from the last 90 days
  (a paycheck, a gift you logged as income...), showing what's already gone to the fund from it.
  Or "New income: log it too", which also adds the income line (e.g. birthday money) and links them.
  It can't take more from a line than is left on it.
- A paycheck can put a set amount in the Fun Fund every payday: "Got it" logs the paycheck and that
  amount into the fund, linked to it (undo takes back both).
- Income lines show "$X to the Fun Fund"; ledger entries show which income they came from.
Data: optional incomeId on Fun Fund entries, optional toFund (cents) and fundPlace on paychecks.
Usage: python3 patch_step40_fund_sources.py file.html"""
import sys
p = sys.argv[1]; s = open(p).read()
def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (s.count(old), old[:100])
    s = s.replace(old, new)

# ---------- helpers ----------
rep("""function placeList(){""", r"""// Fun Fund money that came from one income line (excluding one entry, when editing it)
const fundFrom = (incId, exceptId) => fund().entries.filter(e => e.kind === "in" && e.incomeId === incId && e.id !== exceptId).reduce((a, e) => a + e.amount, 0);
// Income lines you can say fund money came from: last 90 days, not paybacks, not cancelled
function fundSources(exceptId, keepId){
  const t0 = todayStr();
  return state.budget.txns.filter(t => t.kind === "income" && !t.cancelled && !t.repays && isDate(t.date) && (diffDays(t.date, t0) <= 90 || t.id === keepId))
    .map(t => ({t, used: fundFrom(t.id, exceptId)})).map(x => Object.assign(x, {left: x.t.amount - x.used}))
    .filter(x => x.left > 0 || x.t.id === keepId).sort((a, b) => b.t.date.localeCompare(a.t.date)).slice(0, 30);
}
function placeList(){""")

# ---------- the Add money form ----------
rep("""    ${kind !== "move" && f.goals.length ? field("fgoal",""", """    ${kind === "in" ? (() => { const src = fundSources(e ? e.id : null, d.incomeId);
      return field("fsrc", "Where did it come from?", `<select id="fsrc" name="fsrc"><option value="">Not linked to income</option>${src.map(x => `<option value="${x.t.id}" ${d.incomeId === x.t.id ? "selected" : ""}>${esc(cutText(x.t.note || "Income", 24))} · ${esc(niceDate(x.t.date))} · ${money(x.left)} left</option>`).join("")}<option value="new">New income: log it too</option></select>`,
        "Pick the paycheck or gift it came out of, so you can see where fund money came from."); })() : ""}
    ${kind !== "move" && f.goals.length ? field("fgoal",""")
rep("""    const gid = kind !== "move" && form.elements.fgoal ? val(form,"fgoal") : "";""",
    """    const gid = kind !== "move" && form.elements.fgoal ? val(form,"fgoal") : "";
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
    }""")
rep("""    if(e) applyEdit(e, data); else f.entries.push(Object.assign({id:uid(), created:Date.now()}, data));
    save(); closeSheet(); render(); toast(e ? "Saved" : kind === "in" ? `${money(amount)} added to the fund` :""",
    """    if(kind === "in") data.incomeId = incomeId || null;
    if(e){ applyEdit(e, data); if(!e.incomeId) delete e.incomeId; } else { const ne = Object.assign({id:uid(), created:Date.now()}, data); if(!ne.incomeId) delete ne.incomeId; f.entries.push(ne); }
    save(); closeSheet(); render(); toast(e ? "Saved" : kind === "in" ? `${money(amount)} added to the fund${incomeId ? " · linked to its income" : ""}` :""")
rep("""      .filter(e => e.kind !== "move" || e.toPlace) });""",
    """      .filter(e => e.kind !== "move" || e.toPlace)
      .map(e => { if(e.kind === "in" && e.incomeId) e.incomeId = String(e.incomeId); else delete e.incomeId; return e; }) });""")
# ledger: which income it came from
rep("""${e.kind === "in" && e.note ? ` · ${esc(e.note)}` : ""}</span></span>""",
    """${e.kind === "in" && e.note ? ` · ${esc(e.note)}` : ""}${e.incomeId ? (() => { const i = state.budget.txns.find(t => t.id === e.incomeId); return i ? ` · from ${esc(i.note || "income")} (${esc(niceDate(i.date))})` : ""; })() : ""}</span></span>""")
# income lines: how much went to the fund
rep("""${t.linked ? `<span class="td">Pays back “""", """${t.kind === "income" && !t.linked && fundFrom(t.id) ? `<span class="td">${money(fundFrom(t.id))} to the ${esc(fund().name)}</span>` : ""}${t.linked ? `<span class="td">Pays back “""")

# ---------- paychecks: a set amount to the fund each payday ----------
rep("""    <label class="chip" style="align-self:flex-start;cursor:pointer"><input type="checkbox" name="pweekend\"""",
    """    <div class="two">${field("pfund", "To the Fun Fund each payday", `<input id="pfund" name="pfund" inputmode="decimal" placeholder="$0 (optional)" value="${esc(centsToInput(d.toFund || 0))}" autocomplete="off">`)}
    ${field("pfplace", "Kept in", `<input id="pfplace" name="pfplace" list="placeList2" maxlength="30" value="${esc(d.fundPlace || placeList()[0])}" autocomplete="off"><datalist id="placeList2">${placeList().map(x => `<option value="${esc(x)}">`).join("")}</datalist>`)}</div>
    <label class="chip" style="align-self:flex-start;cursor:pointer"><input type="checkbox" name="pweekend\"""")
rep("""    const data = {name, amount, who, cycle, next, days, weekend: form.elements.pweekend.checked};""",
    """    const fRaw = val(form, "pfund"), toFund = fRaw ? parseMoney(fRaw) : 0, fundPlace = val(form, "pfplace").slice(0, 30);
    if(toFund === null) return fail("pfund", "Enter an amount like 100, or leave it empty.");
    if(toFund > amount) return fail("pfund", "That's more than the paycheck.");
    if(toFund && !fundPlace) return fail("pfplace", "Say where it's kept, like Savings account.");
    const data = {name, amount, who, cycle, next, days, weekend: form.elements.pweekend.checked, toFund: toFund || 0, fundPlace: toFund ? fundPlace : ""};""")
rep("""      return Object.assign({}, x, {id: x.id ? String(x.id) : uid(), name: str(x.name, 40).trim(), amount: cents(x.amount), who: HUMANS.includes(x.who) ? x.who : "sam",""",
    """      return Object.assign({}, x, {id: x.id ? String(x.id) : uid(), name: str(x.name, 40).trim(), amount: cents(x.amount), who: HUMANS.includes(x.who) ? x.who : "sam",
        toFund: Math.min(cents(x.toFund), cents(x.amount)), fundPlace: cents(x.toFund) ? (str(x.fundPlace, 30).trim() || "Savings account") : "",""")
rep("""    state.budget.txns.push(tx); p.next = payAfter(p, p.next); budgetMonth = date.slice(0, 7); save(); render();
    toast(`${money(p.amount)} logged · next payday ${niceDate(payActual(p, p.next))}`, () => { state.budget.txns = state.budget.txns.filter(x => x.id !== tx.id); p.next = prev; save(); render(); }); },""",
    """    state.budget.txns.push(tx); p.next = payAfter(p, p.next); budgetMonth = date.slice(0, 7);
    const fe = p.toFund ? {id:uid(), created:Date.now(), kind:"in", amount:p.toFund, date, who:p.who, place:p.fundPlace || "Savings account", toPlace:"", goalId:"", note:`From ${p.name}`, incomeId:tx.id} : null;
    if(fe) fund().entries.push(fe);
    save(); render();
    toast(`${money(p.amount)} logged${fe ? ` · ${money(fe.amount)} to the ${fund().name}` : ""} · next payday ${niceDate(payActual(p, p.next))}`, () => {
      state.budget.txns = state.budget.txns.filter(x => x.id !== tx.id); if(fe) removeBy(fund().entries, fe.id); p.next = prev; save(); render(); }); },""")
rep('const BUILD = "2026-10-30 · 39";', 'const BUILD = "2026-10-30 · 40";')
open(p, "w").write(s)
print("patched")
