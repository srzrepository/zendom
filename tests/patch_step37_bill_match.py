"""Step 37: one way to log a bill.
Typing a bill into Add spending (same amount, or the bill's name, within 20 days of its due date)
now points you at the bill's Paid button instead: logging it by hand doesn't move the bill to its
next date, so Paid would add it again later. "Use the bill's Paid button" logs it from the bill
(with the bill's split). Tapping Save again still logs it by hand. Together with step 36 (Paid asks
when it was already logged), rent can't quietly end up in your spending twice, whichever you do first.
No data change. Usage: python3 patch_step37_bill_match.py file.html"""
import sys
p = sys.argv[1]; s = open(p).read()
def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (s.count(old), old[:100])
    s = s.replace(old, new)

rep("""const dupMsg = d =>""", r"""// A bill this hand-typed spending is probably for: same amount or a word of its name, near its due date
function billMatch(d){
  const w = pbWords(d.note);
  return state.budget.bills.find(b => (b.amount === d.amount || [...pbWords(b.name)].some(x => w.has(x))) && Math.abs(diffDays(d.date, b.nextDue)) <= 20) || null;
}
const dupMsg = d =>""")
rep("""    if(!t){ const dup = dupOf(data); if(dup && warnOnce(form, "dup" + dup.id, "amt", dupMsg(dup), dup.id)) return; }""",
    """    if(!t){ const dup = dupOf(data); if(dup && warnOnce(form, "dup" + dup.id, "amt", dupMsg(dup), dup.id)) return; }
    if(!t && kind === "expense"){ const bm = billMatch(data);
      if(bm && warnOnce(form, "bill" + bm.id, "amt", `This looks like your ${bm.name} bill (${money(bm.amount)}, due ${niceDate(bm.nextDue)}). Logging it here won't move the bill to its next date, so its Paid button would add it again. Use the bill's Paid button, or tap Save again to log it here anyway.`)){
        $("#f-amt").insertAdjacentHTML("beforeend", `<button type="button" class="link" data-act="billFromForm" data-id="${bm.id}" style="align-self:flex-start;padding-left:0">Use the bill's Paid button</button>`); return; } }""")
rep("""  billSkip: id => {""", """  billFromForm: id => { closeSheet(); ACTIONS.payBill(id); },
  billSkip: id => {""")
rep('const BUILD = "2026-10-30 · 36";', 'const BUILD = "2026-10-30 · 37";')
open(p, "w").write(s)
print("patched")
