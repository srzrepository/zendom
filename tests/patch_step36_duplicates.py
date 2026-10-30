"""Step 36: guard against duplicate entries, and help clean up ones that already happened.
Why they happen: the same real-world payment can be entered several ways (a bill's Paid button and
Add spending; Record payment, "I paid Charlie my share" and fixing a payback; a Venmo import), and
until now only imports checked for an existing match.
- New spending, income or a payment between you: if there's already one of the same kind and amount
  within 3 days, Save shows it with "Open the one you have"; tapping Save again keeps both.
- Record payment also warns when the amount is more than what's owed (it would flip who owes whom).
  Pay in Venmo no longer opens Venmo while a warning is showing.
- A bill's Paid button: if that amount (or that bill) was already logged recently, it asks:
  just mark the bill paid, log it anyway, or cancel.
- Budget → Spending shows "Possible duplicates" when entries of the same kind and amount are within
  3 days of each other. Review lists them in pairs to open (and delete) or Keep both.
- Keyboard: while it's up, the open sheet now stays pinned above it (bottom-anchored) rather than
  moving to the top of the screen.
Data: optional notDup list on entries (pairs you said to keep). Usage: python3 patch_step36_duplicates.py file.html"""
import sys
p = sys.argv[1]; s = open(p).read()
def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (s.count(old), old[:100])
    s = s.replace(old, new)

# ---------- helpers ----------
rep("""const expLabel = t => t.note || catName(t.categoryId);""", r"""const expLabel = t => t.note || catName(t.categoryId);
/* ---- duplicates ---- */
const sameDupKind = (a, b) => a.kind === b.kind && a.amount === b.amount && (a.kind !== "settle" || a.paidBy === b.paidBy);
// An existing entry that looks like the same thing: same kind and amount within 3 days (payments: same payer)
function dupOf(c, exceptId){
  return state.budget.txns.find(t => t.id !== exceptId && !t.cancelled && isDate(t.date) && sameDupKind(t, c) && Math.abs(diffDays(t.date, c.date)) <= 3) || null;
}
const txLabel = t => t.note || (t.kind === "settle" ? "Payment between you" : t.kind === "income" ? "Income" : catName(t.categoryId));
// Pairs that look like duplicates (last 120 days), minus ones you said to keep
function dupPairs(){
  const t0 = todayStr(), live = state.budget.txns.filter(t => !t.cancelled && isDate(t.date) && diffDays(t.date, t0) <= 120).sort((a, b) => a.date.localeCompare(b.date));
  const kept = (a, b) => (a.notDup || []).includes(b.id) || (b.notDup || []).includes(a.id);
  const out = [];
  for(let i = 0; i < live.length; i++) for(let j = i + 1; j < live.length && diffDays(live[i].date, live[j].date) <= 3; j++)
    if(sameDupKind(live[i], live[j]) && !kept(live[i], live[j])) out.push([live[i], live[j]]);
  return out;
}
// Show a warning under a field once per form; tapping Save again goes ahead
function warnOnce(form, key, fieldId, msg, openId){
  const k = "ok" + key.replace(/[^a-z0-9]/gi, ""); if(form.dataset[k]) return false;
  form.dataset[k] = "1"; fail(fieldId, msg);
  const f = $("#f-" + fieldId);
  if(f && openId) f.insertAdjacentHTML("beforeend", `<button type="button" class="link" data-act="editTxn" data-id="${esc(openId)}" style="align-self:flex-start;padding-left:0">Open the one you have</button>`);
  return true;
}
const dupMsg = d => `You already have “${txLabel(d)}” for ${money(d.amount)} on ${niceDate(d.date)}. If this is a different one, tap Save again.`;""")

# ---------- Add spending / income ----------
rep("""    if(repays){ data.repays = repays; }
    if(t){""", """    if(repays){ data.repays = repays; }
    if(!t){ const dup = dupOf(data); if(dup && warnOnce(form, "dup" + dup.id, "amt", dupMsg(dup), dup.id)) return; }
    if(t){""")

# ---------- Record payment ----------
rep("""    const data = {kind:"settle", amount, date, paidBy, shared:false, categoryId:null, note: val(form, "smemo").slice(0, 80)};""",
    """    const data = {kind:"settle", amount, date, paidBy, shared:false, categoryId:null, note: val(form, "smemo").slice(0, 80)};
    if(!t){
      const dup = dupOf(data); if(dup && warnOnce(form, "dup" + dup.id, "samt", dupMsg(dup), dup.id)) return;
      const nb = bal + (paidBy === "charlie" ? -amount : amount), owes = paidBy === "sam" ? Math.max(0, -bal) : Math.max(0, bal);
      if(amount > owes + 100 && Math.sign(nb) === (paidBy === "sam" ? 1 : -1) && warnOnce(form, "over" + paidBy + amount, "samt",
        `${owes ? `${nameOf(paidBy)} only owes ${money(owes)} right now` : `${nameOf(paidBy)} doesn't owe anything right now`}, so this would leave ${nameOf(other(paidBy))} owing ${money(Math.abs(nb))}. If that's right, tap Save again.`)) return;
    }""")
rep("""  settleForm.via = "venmo"; form.requestSubmit();
  window.open(link, "_blank", "noopener");""",
    """  settleForm.via = "venmo"; form.requestSubmit();
  if(document.contains(form)){ settleForm.via = null; return; }   // a warning is showing; nothing recorded yet
  window.open(link, "_blank", "noopener");""")

# ---------- a bill's Paid button ----------
rep("""  payBill: id => { const b = state.budget.bills.find(x => x.id === id); if(!b) return;""",
    """  payBill: (id, el, how) => { const b = state.budget.bills.find(x => x.id === id); if(!b) return;
    if(how !== "skip" && how !== "add"){ const d = billDup(b); if(d){ billDupSheet(b, d); return; } }""")
rep("""    state.budget.txns.push(tx); b.nextDue = nextBillDate(b); save(); render();
    toast(`${b.name} paid · next ${niceDate(b.nextDue)}`, () => {""",
    """    if(how !== "skip") state.budget.txns.push(tx); b.nextDue = nextBillDate(b); save(); render();
    toast(`${b.name} ${how === "skip" ? "marked paid (not logged again)" : "paid"} · next ${niceDate(b.nextDue)}`, () => {""")
rep("""const BUDGET_ACTIONS = {""", r"""// Spending that might already be this bill: logged from it in the last 20 days, or the same amount within a week
function billDup(b){
  const t0 = todayStr();
  return state.budget.txns.find(t => !t.cancelled && t.kind === "expense" && isDate(t.date) && ((t.billId === b.id && Math.abs(diffDays(t.date, t0)) <= 20) || (t.amount === b.amount && Math.abs(diffDays(t.date, t0)) <= 7))) || null;
}
function billDupSheet(b, d){
  openSheet(`Already logged ${b.name}?`, `
    <p style="margin:0">“${esc(txLabel(d))}” for ${money(d.amount)} is already in your spending (${esc(niceDate(d.date))}, ${esc(nameOf(d.paidBy))}${d.shared ? ", shared" : ""}).</p>
    <p class="small muted" style="margin:0">Marking the bill paid moves it to the next due date. Logging it again adds another ${money(b.amount)}.</p>
    <div class="actions" style="flex-wrap:wrap"><div class="r" style="flex-wrap:wrap">
      <button type="button" class="btn ghost" data-act="closeSheet">Cancel</button>
      <button type="button" class="btn ghost" data-act="billAdd" data-id="${b.id}">Log it again</button>
      <button type="button" class="btn" data-act="billSkip" data-id="${b.id}">Just mark it paid</button></div></div>`, () => {}, false);
}
// "Possible duplicates" card and review sheet
function dupCardHTML(){
  const n = dupPairs().length; if(!n) return "";
  return `<section class="card soon-card dupcard"><span class="ic">${IC.budget}</span><div style="flex:1;min-width:0"><h3>${n === 1 ? "A possible duplicate" : `${n} possible duplicates`}</h3>
    <p>Entries with the same amount within a few days of each other.</p>
    <div class="actions" style="margin-top:8px;justify-content:flex-start"><button type="button" class="btn small" data-act="dupReview">Review</button></div></div></section>`;
}
function dupRow(t){
  const sub = t.kind === "settle" ? `${nameOf(t.paidBy)} paid ${nameOf(other(t.paidBy))}` : t.kind === "income" ? `Income · ${nameOf(t.paidBy)}` : `${catName(t.categoryId)} · ${t.shared ? "shared" : nameOf(t.paidBy) + "'s"}${t.billId ? " · from the bill's Paid button" : ""}${t.imp ? " · imported" : ""}`;
  return `<button type="button" class="txrow" data-act="editTxn" data-id="${t.id}"><span class="av ${t.paidBy}">${sprite(t.paidBy, "", true)}</span>
    <span class="tb"><span class="tt">${esc(txLabel(t))}</span><span class="ts">${esc(niceDate(t.date))} · ${esc(sub)}</span></span><span class="ta ${t.kind}">${money(t.amount)}</span></button>`;
}
function dupSheet(){
  const P = dupPairs();
  openSheet(P.length ? "Possible duplicates" : "No duplicates", P.length ? `
    <p class="small muted" style="margin:0">Each pair has the same amount within 3 days. Tap the extra one to open it and delete it, or Keep both if they're really separate.</p>
    ${P.map(([a, b]) => `<div class="sec"><div class="glist">${dupRow(a)}${dupRow(b)}</div>
      <div class="actions" style="justify-content:flex-end;margin-top:4px"><button type="button" class="link" data-act="dupKeep" data-id="${a.id}|${b.id}">Keep both</button></div></div>`).join("")}
    <div class="actions"><div class="r"><button type="button" class="btn" data-act="closeSheet">Done</button></div></div>`
    : `<p style="margin:0">Nothing looks doubled up.</p><div class="actions"><div class="r"><button type="button" class="btn" data-act="closeSheet">Done</button></div></div>`, () => {}, false);
}
const BUDGET_ACTIONS = {""")
rep("""  editPayday: id => paydayForm(id || null),""", """  editPayday: id => paydayForm(id || null),
  billSkip: id => { closeSheet(); ACTIONS.payBill(id, null, "skip"); },
  billAdd: id => { closeSheet(); ACTIONS.payBill(id, null, "add"); },
  dupReview: () => dupSheet(),
  dupKeep: id => { const [a, b] = String(id).split("|"), A = state.budget.txns.find(t => t.id === a), B = state.budget.txns.find(t => t.id === b); if(!A || !B) return;
    B.notDup = [...new Set([...(B.notDup || []), A.id])]; save(); render(); if(dupPairs().length) dupSheet(); else { closeSheet(); toast("OK, keeping both"); } },""")
rep("""  ${paybackHintHTML()}""", """  ${dupCardHTML()}${paybackHintHTML()}""")
# keep notDup tidy in stored data
rep("""      .map(t => { if(t.kind !== "income" || !t.repays) delete t.repays;""",
    """      .map(t => { if(Array.isArray(t.notDup)) t.notDup = t.notDup.map(String).slice(0, 50); else delete t.notDup;
        if(t.kind !== "income" || !t.repays) delete t.repays;""")
# after deleting an entry from the review, go back to the list of pairs
rep("""  if(DELETES[kind] && id){ const msg = DELETES[kind](id); save(); closeSheet(); render(); if(msg) toast(msg); return; }""",
    """  if(DELETES[kind] && id){ const reopen = kind === "delTxn" && dupSheet.open; const msg = DELETES[kind](id); save(); closeSheet(); render(); if(msg) toast(msg); if(reopen && dupPairs().length){ dupSheet.open = true; dupSheet(); } return; }""")
rep("""  dupReview: () => dupSheet(),""", """  dupReview: () => { dupSheet.open = true; dupSheet(); },""")
rep("""function closeSheet(){ discardPendingPdf();""", """function closeSheet(){ dupSheet.open = false; discardPendingPdf();""")

# ---------- keyboard: stay pinned above it ----------
rep("""  if(kb){ sh.style.top = Math.round(vv.offsetTop + 8) + "px"; sh.style.bottom = "auto"; sh.style.maxHeight = Math.round(vv.height - 8) + "px"; }""",
    """  if(kb){ sh.style.top = ""; sh.style.bottom = Math.max(0, Math.round(fullH - vv.height - vv.offsetTop)) + "px"; sh.style.maxHeight = Math.round(vv.height - 12) + "px"; }""")

rep('const BUILD = "2026-10-30 · 35";', 'const BUILD = "2026-10-30 · 36";')
open(p, "w").write(s)
print("patched")
