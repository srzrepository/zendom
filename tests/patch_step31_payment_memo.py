"""Step 31: memo on payments between you, and Venmo with the same memo.
- Record payment has a Memo (pre-filled with what it covers since you were last even); it's the
  entry's name in the list. Editing keeps it.
- With Venmo usernames saved, "Pay in Venmo" opens Venmo with the amount + memo and records the
  payment (source: venmo). The Venmo links on the pay-back and Shared spending cards use the same
  memo. A later Venmo statement import then finds it (same amount within 3 days).
No data change (settle entries already had a note). Usage: python3 patch_step31_payment_memo.py file.html"""
import sys
p = sys.argv[1]; s = open(p).read()
def rep(old, new):
    global s
    assert s.count(old) == 1, (s.count(old), old[:90])
    s = s.replace(old, new)
rep("""function venmoLink(user, cents){""", r"""// What a payment would cover: the shared costs since you were last even, newest first, in a few words.
function settleMemo(){
  const L = oweLedger(); let start = 0;
  for(let i = L.length - 1; i >= 0; i--) if(Math.round(L[i].run) === 0){ start = i + 1; break; }
  const names = [...new Set(L.slice(start).filter(x => x.t.kind === "expense").reverse().map(x => x.t.note || catName(x.t.categoryId)))];
  if(!names.length) return "zen·dom settle up";
  let out = ""; for(const n of names){ const next = out ? out + ", " + n : n; if(Array.from(next).length > 55){ out += ", …"; break; } out = next; }
  return out;
}
function venmoLink(user, cents, memo){
  return `https://venmo.com/${encodeURIComponent(user)}?txn=pay&amount=${(cents/100).toFixed(2)}&note=${encodeURIComponent(memo || settleMemo())}`;
}
function venmoLinkOld(user, cents){""")
rep("""  const d = t || {amount:Math.abs(bal), date:todayStr(), paidBy: bal > 0 ? "charlie" : "sam", note:""};""",
    """  const d = t || {amount:Math.abs(bal), date:todayStr(), paidBy: bal > 0 ? "charlie" : "sam", note:settleMemo()};
  const payee = other(d.paidBy), vu = (state.budget.venmo || {})[payee];""")
rep("""    ${field("sdate","Date", `<input id="sdate" name="sdate" type="date" value="${esc(d.date)}">`)}</div>
    ${footer(t ? "delTxn:" + t.id : "")}`,
  form => {""",
"""    ${field("sdate","Date", `<input id="sdate" name="sdate" type="date" value="${esc(d.date)}">`)}</div>
    ${field("smemo","Memo", `<input id="smemo" name="smemo" maxlength="80" value="${esc(d.note || "")}" placeholder="What it's for, e.g. October rent + groceries" autocomplete="off">`, t ? "" : "Pre-filled with what it covers. Change it to anything.")}
    ${!t ? `<div id="venmoRow">${vu ? `<button type="button" class="btn ghost" data-act="settleVenmo" style="align-self:flex-start">Pay in Venmo and record it</button><span class="hint" style="display:block;margin-top:4px">Opens Venmo with the same amount and memo.</span>` : `<span class="hint">Add your Venmo usernames in ${esc(state.budget.pigName)}'s settings to pay from here.</span>`}</div>` : ""}
    ${footer(t ? "delTxn:" + t.id : "")}`,
  form => {""")
rep("""    const data = {kind:"settle", amount, date, paidBy, shared:false, categoryId:null, note:""};
    if(t) Object.assign(t, data); else state.budget.txns.push(Object.assign({id:uid(), billId:null}, data));
    save(); closeSheet(); render(); toast("Payment recorded");
  });
}""",
"""    const data = {kind:"settle", amount, date, paidBy, shared:false, categoryId:null, note: val(form, "smemo").slice(0, 80)};
    if(t) Object.assign(t, data); else state.budget.txns.push(Object.assign({id:uid(), billId:null}, data, settleForm.via ? {source:settleForm.via} : {}));
    settleForm.via = null;
    save(); closeSheet(); render(); toast("Payment recorded");
  });
}
// Venmo: record the payment, then open Venmo with the same amount and memo
function settleVenmo(){
  const form = $("#sheetForm"); if(!form) return;
  const amount = parseMoney(val(form, "samt")), paidBy = (form.querySelector("input[name=paidBy]:checked") || {}).value;
  if(amount === null){ fail("samt", "Enter an amount like 20 or 42.50."); return; }
  const vu = (state.budget.venmo || {})[other(paidBy)];
  if(!vu){ toast(`Add ${nameOf(other(paidBy))}'s Venmo username in ${state.budget.pigName}'s settings first.`); return; }
  const link = venmoLink(vu, amount, val(form, "smemo") || settleMemo());
  settleForm.via = "venmo"; form.requestSubmit();
  window.open(link, "_blank", "noopener");
}""")
rep("""  settleUp: () => settleForm(null),""", """  settleUp: () => settleForm(null),
  settleVenmo: () => settleVenmo(),""")
rep("""function venmoLinkOld(user, cents){
  return `https://venmo.com/${encodeURIComponent(user)}?txn=pay&amount=${(cents/100).toFixed(2)}&note=${encodeURIComponent("zen·dom settle up")}`;
}
""", "")
rep("""    .slice().sort((a, b) => a.date.localeCompare(b.date) || (a.kind === "settle") - (b.kind === "settle"));""",
    """    .map((t, i) => [t, i]).sort((a, b) => a[0].date.localeCompare(b[0].date) || a[1] - b[1]).map(x => x[0]);   // same day: in the order they were added""")
open(p, "w").write(s); print("step 31 applied")
