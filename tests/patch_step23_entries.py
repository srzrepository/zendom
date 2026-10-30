"""Step 23: spending entries get Details and a Cancelled/refunded switch; statement import finds
duplicates better.
- Details: free text (what was bought, order number, ...), up to 500 characters.
- Cancelled: the entry stays in the list (crossed out) but no total counts it: month stats, summaries,
  wrap-ups, who-owes-whom.
- Import: an entry you typed counts as a likely duplicate if the amount matches and the date is within
  3 days (statements often post a day or two later); so does the same payment already imported from a
  different file (e.g. Venmo + bank). Each existing entry matches at most one row, the closest date.
  The note says which entry it matched.
Data: txn.details (string), txn.cancelled (bool); additive, older entries just have neither.
Usage: python3 patch_step23_entries.py file.html"""
import sys
p = sys.argv[1]; s = open(p).read()
def rep(old, new):
    global s
    assert s.count(old) == 1, (s.count(old), old[:90])
    s = s.replace(old, new)

# data
rep("""shared: t.kind === "expense" && !!t.shared, note: str(t.note, 80), billId: t.billId ? String(t.billId) : null })),""",
    """shared: t.kind === "expense" && !!t.shared, note: str(t.note, 80), details: str(t.details, 500), cancelled: !!t.cancelled, billId: t.billId ? String(t.billId) : null })),""")

# totals ignore cancelled entries
rep("""  state.budget.txns.forEach(t => {
    if(t.kind === "expense" && t.shared) b += (t.paidBy === "sam" ? 1 : -1) * t.amount / 2;""",
"""  state.budget.txns.forEach(t => { if(t.cancelled) return;
    if(t.kind === "expense" && t.shared) b += (t.paidBy === "sam" ? 1 : -1) * t.amount / 2;""")
rep("""  state.budget.txns.forEach(t => { if(t.date > day) return;""", """  state.budget.txns.forEach(t => { if(t.date > day || t.cancelled) return;""")
rep("""function rangeTx(from, to){ return state.budget.txns.filter(t => isDate(t.date) && t.date >= from && t.date <= to); }""",
    """function rangeTx(from, to){ return state.budget.txns.filter(t => !t.cancelled && isDate(t.date) && t.date >= from && t.date <= to); }""")
rep("""  const tx = state.budget.txns.filter(t => t.date.slice(0, 7) === k);
  const spent = tx.filter(t => t.kind === "expense").reduce((a, t) => a + t.amount, 0);
  const income = tx.filter(t => t.kind === "income").reduce((a, t) => a + t.amount, 0);
  const byCat = {}; tx.filter(t => t.kind === "expense").forEach(t => {""",
"""  const tx = state.budget.txns.filter(t => t.date.slice(0, 7) === k), live = tx.filter(t => !t.cancelled);   // tx: for the list; live: for totals
  const spent = live.filter(t => t.kind === "expense").reduce((a, t) => a + t.amount, 0);
  const income = live.filter(t => t.kind === "income").reduce((a, t) => a + t.amount, 0);
  const byCat = {}; live.filter(t => t.kind === "expense").forEach(t => {""")

# list rows: crossed out + a details line
rep(""".txrow .tt{font-weight:600;overflow-wrap:anywhere}""",
""".txrow .tt{font-weight:600;overflow-wrap:anywhere}
.txrow .td{font-size:.8rem;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.txrow.cx .tt,.txrow.cx .ta{text-decoration:line-through;opacity:.6}""")
rep("""<button type="button" class="txrow" data-act="editTxn" data-id="${t.id}">
        <span class="av ${t.paidBy}">${sprite(t.paidBy, "", true)}</span>""",
"""<button type="button" class="txrow ${t.cancelled ? "cx" : ""}" data-act="editTxn" data-id="${t.id}">
        <span class="av ${t.paidBy}">${sprite(t.paidBy, "", true)}</span>""")
rep("""          <span class="ts">${t.kind === "expense" ? `${esc(catName(t.categoryId))}${t.shared ? " · shared" : ` · ${esc(nameOf(t.paidBy))}'s`}` : t.kind === "settle" ? `${esc(nameOf(t.paidBy))} paid ${esc(nameOf(other(t.paidBy)))}` : `${esc(nameOf(t.paidBy))}`}</span></span>""",
"""          <span class="ts">${t.cancelled ? `<span class="pill late">${t.kind === "income" ? "Didn't come in" : "Cancelled"}</span> ` : ""}${t.kind === "expense" ? `${esc(catName(t.categoryId))}${t.shared ? " · shared" : ` · ${esc(nameOf(t.paidBy))}'s`}` : t.kind === "settle" ? `${esc(nameOf(t.paidBy))} paid ${esc(nameOf(other(t.paidBy)))}` : `${esc(nameOf(t.paidBy))}`}</span>
          ${t.details ? `<span class="td">${esc(t.details)}</span>` : ""}</span>""")

# form: details + cancelled
rep("""    <label class="chip" id="sharedBox" style="align-self:flex-start;cursor:pointer"><input type="checkbox" name="shared" ${d.shared?"checked":""} style="accent-color:var(--accent)"> Shared cost (split 50/50)</label>
    ${footer(t ? "delTxn:" + t.id : "")}`,""",
"""    <label class="chip" id="sharedBox" style="align-self:flex-start;cursor:pointer"><input type="checkbox" name="shared" ${d.shared?"checked":""} style="accent-color:var(--accent)"> Shared cost (split 50/50)</label>
    ${field("tdetails","Details", `<textarea id="tdetails" name="tdetails" maxlength="500" rows="2" placeholder="What exactly you got, order number, why it was returned…">${esc(d.details || "")}</textarea>`, "Optional")}
    <label class="chip" style="align-self:flex-start;cursor:pointer"><input type="checkbox" name="tcancel" ${d.cancelled?"checked":""}> Cancelled or refunded (don't count it)</label>
    ${footer(t ? "delTxn:" + t.id : "")}`,""")
rep("""    const data = {kind, amount, date, note:val(form,"tnote"), paidBy, categoryId: kind === "expense" && state.budget.categories.some(c => c.id === cid) ? cid : null, shared: kind === "expense" && form.elements.shared.checked};""",
"""    const data = {kind, amount, date, note:val(form,"tnote"), paidBy, categoryId: kind === "expense" && state.budget.categories.some(c => c.id === cid) ? cid : null, shared: kind === "expense" && form.elements.shared.checked,
      details: form.elements.tdetails.value.trim().slice(0, 500), cancelled: form.elements.tcancel.checked};""")
rep("""    save(); closeSheet(); render(); toast(t ? "Saved" : kind === "income" ? "Income logged" : `${money(amount)} logged`);""",
    """    save(); closeSheet(); render(); toast(data.cancelled ? "Saved as cancelled · not counted" : t ? "Saved" : kind === "income" ? "Income logged" : `${money(amount)} logged`);""")

# import: smarter duplicate check
rep("""  const keys = new Set(state.budget.txns.map(t => t.imp).filter(Boolean));
  const manual = state.budget.txns.filter(t => !t.imp);
  out.forEach(x => {
    x.key = impKey(x.date, x.cents, x.desc);
    if(keys.has(x.key)){ x.dup = "Already imported"; x.include = false; }
    else if(manual.some(t => t.date === x.date && t.amount === Math.abs(x.cents))){ x.dup = "Might match an entry you typed"; x.include = false; }
  });""",
"""  const keys = new Set(state.budget.txns.map(t => t.imp).filter(Boolean));
  out.forEach(x => { x.key = impKey(x.date, x.cents, x.desc); if(keys.has(x.key)){ x.dup = "Already imported"; x.include = false; } });
  // close matches: same amount within 3 days, typed by hand or imported from a different file; each entry matches one row
  const used = new Set();
  out.filter(x => !x.dup).map(x => {
    const cands = state.budget.txns.filter(t => !used.has(t.id) && t.amount === Math.abs(x.cents) && Math.abs(diffDays(t.date, x.date)) <= 3 && (!t.imp || t.source !== fmt));
    return {x, cands};
  }).filter(o => o.cands.length).sort((a, b) => a.cands.length - b.cands.length).forEach(({x}) => {
    const t = state.budget.txns.filter(t => !used.has(t.id) && t.amount === Math.abs(x.cents) && Math.abs(diffDays(t.date, x.date)) <= 3 && (!t.imp || t.source !== fmt))
      .sort((a, b) => Math.abs(diffDays(a.date, x.date)) - Math.abs(diffDays(b.date, x.date)))[0];
    if(!t) return; used.add(t.id);
    const what = t.note ? `“${cutText(t.note, 30)}”` : "an entry";
    x.dup = t.imp ? `Might be ${what} from your ${t.source === "venmo" ? "Venmo" : "bank"} import (${niceDate(t.date)})` : `Might be ${what} you entered on ${niceDate(t.date)}`;
    x.include = false;
  });""")

open(p, "w").write(s)
print("step 23 applied")
