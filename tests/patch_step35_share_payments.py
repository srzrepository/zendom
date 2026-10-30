"""Step 35: paying each other back for a split is a payment, not a payback.
- A shared expense's form now has "I paid Charlie my share ($X)" (or "Charlie paid Sam his share"),
  which opens Record payment filled in with that amount and the expense's name.
- "Someone paid me back" is now worded as being for someone else (not each other).
- A payback that's attached to a shared expense gets "This was between us: make it a payment",
  which turns it into a payment between you (you check who paid and the amount first), so an entry
  recorded the wrong way can be fixed without retyping it.
No data change. Usage: python3 patch_step35_share_payments.py file.html"""
import sys
p = sys.argv[1]; s = open(p).read()
def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (s.count(old), old[:100])
    s = s.replace(old, new)

# ---------- Record payment can start filled in, and can replace a payback ----------
rep("""function settleForm(id){""", """function settleForm(id, preset, replaces){""")
rep("""  const d = t || {amount:Math.abs(bal), date:todayStr(), paidBy: bal > 0 ? "charlie" : "sam", note:settleMemo()};""",
    """  const d = t || Object.assign({amount:Math.abs(bal), date:todayStr(), paidBy: bal > 0 ? "charlie" : "sam", note:settleMemo()}, preset || {});""")
rep("""    if(t) Object.assign(t, data); else state.budget.txns.push(Object.assign({id:uid(), billId:null}, data, settleForm.via ? {source:settleForm.via} : {}));""",
    """    if(t) Object.assign(t, data); else state.budget.txns.push(Object.assign({id:uid(), billId:null}, data, settleForm.via ? {source:settleForm.via} : {}));
    if(!t && replaces) removeBy(state.budget.txns, replaces);   // a payback that was really a payment between you""")

# ---------- the expense form: pay your share; paybacks are for other people ----------
rep("""function paybackBox(t){
  const pb = state.budget.txns.filter(r => r.kind === "income" && r.repays === t.id);""",
    """function paybackBox(t){
  const pb = state.budget.txns.filter(r => r.kind === "income" && r.repays === t.id);
  const nt = netTx().find(x => x.id === t.id) || t, ower = other(t.paidBy), share = t.shared && !t.cancelled ? Math.round(shareOf(nt, ower)) : 0;
  const shareBtn = share ? `<div class="field" id="shareBox"><span class="lab">Split with ${esc(nameOf(other(prefs.user)))}</span>
      <span class="hint">${esc(nameOf(ower))}'s part is ${money(share)}. When it's been paid back, record it here; that's a payment between you, and it clears what's owed.</span>
      <button type="button" class="btn ghost small" data-act="payShare" data-id="${t.id}" style="align-self:flex-start;margin-top:4px">${ower === prefs.user ? `I paid ${esc(nameOf(t.paidBy))} my share (${money(share)})` : `${esc(nameOf(ower))} paid me ${ower === "sam" ? "her" : "his"} share (${money(share)})`}</button></div>` : "";""")
rep("""  return `<div class="field" id="pbBox"><span class="lab">Paid back</span>""",
    """  return shareBtn + `<div class="field" id="pbBox"><span class="lab">Paid back by someone else</span>""")
rep("""      : `<span class="hint">If someone pays you back for this, add it here so it lowers the cost instead of counting as income.</span>`}
    <button type="button" class="btn ghost small" data-act="addPayback" data-id="${t.id}" style="align-self:flex-start;margin-top:4px">+ Someone paid me back</button></div>`;""",
    """      : `<span class="hint">If a friend (not ${esc(nameOf(other(prefs.user)))}) pays you back for this, add it here so it lowers the cost instead of counting as income.</span>`}
    <button type="button" class="btn ghost small" data-act="addPayback" data-id="${t.id}" style="align-self:flex-start;margin-top:4px">+ A friend paid me back</button></div>`;""")
# the income form: say who paybacks are for; offer to fix one that was between you
rep("""    list.length ? `If a friend paid you back, pick what it was for. It lowers that cost instead of counting as income.""",
    """    list.length ? `If a friend paid you back, pick what it was for. It lowers that cost instead of counting as income. Paying each other back? Use Record payment instead.""")
rep("""    <div id="incOnly">${paybackPicker(d)}</div>""",
    """    <div id="incOnly">${paybackPicker(d)}${t && t.repays && (state.budget.txns.find(x => x.id === t.repays) || {}).shared ? `<button type="button" class="btn ghost small" data-act="pbToSettle" data-id="${t.id}" style="align-self:flex-start;margin-top:6px">This was between ${esc(nameOf("sam"))} and ${esc(nameOf("charlie"))}: make it a payment</button>` : ""}</div>""")

# ---------- actions ----------
rep("""  addPayback: id => {""",
    """  payShare: id => { const e = state.budget.txns.find(x => x.id === id && x.kind === "expense"); if(!e) return;
    const nt = netTx().find(x => x.id === id) || e, ower = other(e.paidBy); closeSheet();
    settleForm(null, {amount: Math.round(shareOf(nt, ower)), paidBy: ower, note: expLabel(e), date: todayStr()}); },
  pbToSettle: id => { const r = state.budget.txns.find(x => x.id === id && x.kind === "income"); if(!r) return;
    const e = state.budget.txns.find(x => x.id === r.repays) || {}; closeSheet();
    settleForm(null, {amount: r.amount, date: r.date, note: r.note || expLabel(e), paidBy: e.paidBy ? other(e.paidBy) : r.paidBy}, r.id); },
  addPayback: id => {""")

rep('const BUILD = "2026-10-30 · 34";', 'const BUILD = "2026-10-30 · 35";')
open(p, "w").write(s)
print("patched")
