"""Step 30: tap who-owes-whom to see the entries behind it.
A sheet lists every shared cost and payment between you since you were last even (or everything),
oldest first: what it was, who paid, each person's part, how it moved the balance, and the running
total, ending at the current balance. Opened from the Shared spending card and the pay-back card.
No data change. Usage: python3 patch_step30_owe_breakdown.py file.html"""
import sys
p = sys.argv[1]; s = open(p).read()
def rep(old, new):
    global s
    assert s.count(old) == 1, (s.count(old), old[:90])
    s = s.replace(old, new)
rep(""".settle{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap}""",
""".settle{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap}
.owebtn{border:0;background:transparent;padding:0;text-align:left;color:inherit;font:inherit;cursor:pointer}
.owebtn u{text-decoration-thickness:2px;text-underline-offset:3px}
.owerow{display:grid;grid-template-columns:1fr auto;gap:2px 10px;padding:9px 0;border-top:1px solid var(--line)}
.owerow:first-child{border-top:0}
.owerow .ot{font-weight:600;min-width:0;overflow-wrap:anywhere}.owerow .os{grid-column:1;font-size:.82rem;color:var(--muted)}
.owerow .ov{text-align:right;font-variant-numeric:tabular-nums;font-weight:600}.owerow .or{grid-column:2;text-align:right;font-size:.8rem;color:var(--muted);font-variant-numeric:tabular-nums}""")
rep("""      <p style="margin:2px 0 0;font-weight:600">${bal === 0 ? "You're even." : `${bal > 0 ? "Charlie owes Sam" : "Sam owes Charlie"} ${money(Math.abs(bal))}`}</p>
      <span class="small muted">Shared costs split 50/50.</span></div>""",
"""      <p style="margin:2px 0 0;font-weight:600"><button type="button" class="owebtn" data-act="oweDetail">${bal === 0 ? "You're even." : `<u>${bal > 0 ? "Charlie owes Sam" : "Sam owes Charlie"} ${money(Math.abs(bal))}</u>`}</button></p>
      <span class="small muted">Tap to see what makes it up.</span></div>""")
rep("""      <button type="button" class="link" data-act="goTo" data-id="budget/spending">See spending</button></div></div></section>`;""",
    """      <button type="button" class="link" data-act="oweDetail">What's it for?</button></div></div></section>`;""")
rep("""function monthStats(k){""", r"""// Every entry that moves who-owes-whom, oldest first, with the running balance (+ = Charlie owes Sam).
function oweLedger(){
  const list = state.budget.txns.filter(t => !t.cancelled && ((t.kind === "expense" && t.shared) || t.kind === "settle"))
    .slice().sort((a, b) => a.date.localeCompare(b.date) || (a.kind === "settle") - (b.kind === "settle"));
  let run = 0;
  return list.map(t => {
    const eff = t.kind === "settle" ? (t.paidBy === "charlie" ? -t.amount : t.amount) : (t.paidBy === "sam" ? t.amount - samPart(t) : -samPart(t));
    run += eff; return {t, eff, run};
  });
}
function oweSheet(all){
  const L = oweLedger(); let start = 0;
  if(!all) for(let i = L.length - 1; i >= 0; i--) if(Math.round(L[i].run) === 0){ start = i + 1; break; }
  const rows = L.slice(start), bal = balance();
  const who = v => v > 0 ? `${nameOf("charlie")} owes ${nameOf("sam")}` : `${nameOf("sam")} owes ${nameOf("charlie")}`;
  const sign = v => (Math.round(v) === 0 ? "even" : `${v > 0 ? nameOf("charlie") : nameOf("sam")} +${money(Math.abs(Math.round(v)))}`);
  openSheet(bal === 0 ? "You're even" : `${who(bal)} ${money(Math.abs(bal))}`, `
    <p class="small muted" style="margin:0">${all || start === 0 ? "Every shared cost and payment between you." : `Since you were last even (${esc(niceDate(L[start - 1].t.date))}).`} Each line shows how it moved the balance, and the running total on the right.</p>
    ${rows.length ? `<div>${rows.map(({t, eff, run}) => { const sm = Math.round(samPart(t));
      const sub = t.kind === "settle" ? `${esc(nameOf(t.paidBy))} paid ${esc(nameOf(other(t.paidBy)))}` : `${esc(nameOf(t.paidBy))} paid ${money(t.amount)} · ${esc(nameOf("sam"))} ${money(sm)}, ${esc(nameOf("charlie"))} ${money(t.amount - sm)}`;
      return `<button type="button" class="owerow owebtn" data-act="editTxn" data-id="${t.id}" style="width:100%"><span class="ot">${esc(t.note || (t.kind === "settle" ? "Payment between you" : catName(t.categoryId)))}</span>
        <span class="ov">${esc(sign(eff).replace("even", "—"))}</span><span class="os">${esc(niceDate(t.date))} · ${sub}</span><span class="or">${Math.round(run) === 0 ? "even" : `${money(Math.abs(Math.round(run)))} ${run > 0 ? "→ " + esc(nameOf("sam")) : "→ " + esc(nameOf("charlie"))}`}</span></button>`; }).join("")}</div>`
      : `<div class="empty"><p>No shared costs or payments yet.</p></div>`}
    <p class="small" style="margin:0">"${esc(nameOf("charlie"))} +$X" means ${esc(nameOf("charlie"))} owes ${esc(nameOf("sam"))} $X more because of that line; the right column is who's owed after it.</p>
    <div class="actions"><span>${!all && start > 0 ? `<button type="button" class="link" data-act="oweAll">Show everything</button>` : ""}</span>
      <div class="r">${bal ? `<button type="button" class="btn ghost" data-act="settleUp">Record payment</button>` : ""}<button type="button" class="btn" data-act="closeSheet">Close</button></div></div>`, () => {}, false);
}
function monthStats(k){""")
rep("""  settleUp: () => settleForm(null),""", """  settleUp: () => settleForm(null),
  oweDetail: () => oweSheet(false),
  oweAll: () => oweSheet(true),""")
open(p, "w").write(s); print("step 30 applied")
