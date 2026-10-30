"""Step 32: paybacks - pair money someone paid you back with the expense it was for.
- An income entry can point at an expense (repays: <expense id>). It then lowers that expense
  instead of counting as income. The lower total is what gets split between Sam and Charlie, and it
  counts in the expense's month. If the payback reached the other person (Karina pays Sam for
  something Charlie bought), the balance between you moves by that much.
- Pairing: a "Pays back" picker on income (suggested matches first), "+ Someone paid me back" on an
  expense, a suggestion card when income shares a word (usually a name) with a recent expense, and a
  "pays back" option on income rows in a Venmo/bank import. Nothing is paired without a tap.
- Paybacks show under their expense with their date. Deleting an expense keeps its paybacks as
  income. An expense can't be edited below what's been paid back; a payback can't exceed what's left.
Data: new optional fields on income entries (repays, noRepay). Old data needs no change.
Usage: python3 patch_step32_paybacks.py file.html"""
import sys
p = sys.argv[1]; s = open(p).read()
def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (s.count(old), old[:100])
    s = s.replace(old, new)

# ---------- styles ----------
rep(""".txrow .ta.income{color:var(--ok)} .txrow .ta.settle{color:var(--muted)}""",
""".txrow .ta.income{color:var(--ok)} .txrow .ta.settle{color:var(--muted)}
.txrow.payback{border-top:1px dashed var(--line);padding:6px 12px 8px 22px}
.txrow.payback .pbarrow{width:20px;flex:none;text-align:center;color:var(--muted);font-weight:700}
.txrow.payback .tt{font-weight:500}
.txrow .ta.payback{color:var(--ok);font-weight:600}
.txrow.elsewhere .tt,.txrow.elsewhere .ta{opacity:.65}""")

# ---------- the money rules ----------
rep("""function balanceUntil(day){""", r"""/* ---- Paybacks: someone paying you back for an expense ----
   An income entry with repays:<expense id> lowers that expense instead of counting as income. The lower
   total is what's split between you, and it counts in the expense's month. */
function withPaybacks(txns){
  const exp = new Map(); txns.forEach(t => { if(t.kind === "expense" && !t.cancelled) exp.set(t.id, t); });
  const by = new Map();
  txns.forEach(t => { if(t.kind === "income" && t.repays && !t.cancelled && exp.has(t.repays)){ if(!by.has(t.repays)) by.set(t.repays, []); by.get(t.repays).push(t); } });
  if(!by.size) return txns;
  return txns.map(t => {
    if(t.kind === "expense" && by.has(t.id)){
      const pb = by.get(t.id), repaid = Math.min(t.amount, pb.reduce((a, r) => a + r.amount, 0)), net = t.amount - repaid;
      const split = t.split && t.split.mode === "amt" ? {mode:"amt", sam: Math.round(t.split.sam * net / t.amount)} : t.split;   // "by amount" splits shrink in proportion
      return Object.assign({}, t, {amount: net, gross: t.amount, repaid, paybacks: pb, split});
    }
    if(t.kind === "income" && t.repays && !t.cancelled && exp.has(t.repays)) return Object.assign({}, t, {linked: exp.get(t.repays)});
    return t;
  });
}
const netTx = () => withPaybacks(state.budget.txns);
function repaidSoFar(expId, exceptId){ return state.budget.txns.filter(t => t.kind === "income" && t.repays === expId && !t.cancelled && t.id !== exceptId).reduce((a, t) => a + t.amount, 0); }
// A payback that reached the other person (Karina pays Sam for something Charlie bought): Sam owes Charlie that much.
const paybackEff = t => t.linked && t.paidBy !== t.linked.paidBy ? (t.paidBy === "sam" ? -t.amount : t.amount) : 0;
// Words two entries share (usually a name). Leaves out filler, bank words and your own names.
const PB_STOP = new Set(("the and for from with paid pay paying back payback payment you your thanks thank thx venmo zelle cash app split share half owe owed "
  + "deposit transfer online mobile ach direct payroll inc llc com www purchase debit credit card pos refund received request this that our").split(" "));
function pbWords(s){
  const own = new Set(HUMANS.flatMap(h => [String(nameOf(h)).toLowerCase(), SURNAMES[h]]));
  const w = String(s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").match(/[a-z]{3,}/g) || [];
  return new Set(w.filter(x => !PB_STOP.has(x) && !own.has(x)));
}
// Expenses an incoming payment could be paying back, best first.
// inc: {id?, amount, date, note, who?}. hit = shares a word; fits = the amount isn't more than what's left.
function paybackCands(inc){
  const words = pbWords(`${inc.note || ""} ${inc.who || ""}`), R = new Map();
  state.budget.txns.forEach(t => { if(t.kind === "income" && t.repays && !t.cancelled && t.id !== inc.id) R.set(t.repays, (R.get(t.repays) || 0) + t.amount); });
  return state.budget.txns.filter(t => t.kind === "expense" && !t.cancelled && isDate(t.date) && t.date <= inc.date && diffDays(t.date, inc.date) <= 90)
    .map(t => { const left = t.amount - (R.get(t.id) || 0), ew = pbWords(`${t.note || ""} ${t.details || ""}`);
      return {t, left, hit: [...words].some(w => ew.has(w)), fits: !inc.amount || inc.amount <= left}; })
    .filter(c => c.left > 0)
    .sort((a, b) => (b.hit - a.hit) || (b.fits - a.fits) || b.t.date.localeCompare(a.t.date));
}
const bestPayback = inc => paybackCands(inc).find(c => c.hit && c.fits) || null;
const expLabel = t => t.note || catName(t.categoryId);
function balanceUntil(day){""")

rep("""  state.budget.txns.forEach(t => { if(t.cancelled) return;
    if(t.kind === "expense" && t.shared)""", """  netTx().forEach(t => { if(t.cancelled) return; b += paybackEff(t);
    if(t.kind === "expense" && t.shared)""")
rep("""  state.budget.txns.forEach(t => { if(t.date > day || t.cancelled) return;""",
    """  netTx().forEach(t => { if(t.date > day || t.cancelled) return; b += paybackEff(t);""")
rep("""function rangeTx(from, to){ return state.budget.txns.filter(""", """function rangeTx(from, to){ return netTx().filter(""")
rep("""income: sum(tx.filter(t => t.kind === "income")),""", """income: sum(tx.filter(t => t.kind === "income" && !t.linked)),""")

# the owe breakdown: paybacks that reached the other person are a line too
rep("""  const list = state.budget.txns.filter(t => !t.cancelled && ((t.kind === "expense" && t.shared) || t.kind === "settle"))""",
    """  const list = netTx().filter(t => !t.cancelled && ((t.kind === "expense" && t.shared) || t.kind === "settle" || paybackEff(t)))""")
rep("""    const eff = t.kind === "settle" ? (t.paidBy === "charlie" ? -t.amount : t.amount) : (t.paidBy === "sam" ? t.amount - samPart(t) : -samPart(t));""",
    """    const eff = t.kind === "income" ? paybackEff(t) : t.kind === "settle" ? (t.paidBy === "charlie" ? -t.amount : t.amount) : (t.paidBy === "sam" ? t.amount - samPart(t) : -samPart(t));""")
rep("""      const sub = t.kind === "settle" ?""",
    """      const sub = t.kind === "income" ? `${esc(niceDate(t.date))} · ${esc(nameOf(t.paidBy))} got ${money(t.amount)} back for “${esc(expLabel(t.linked))}”, which ${esc(nameOf(t.linked.paidBy))} paid for` : t.kind === "settle" ?""")
rep("""`${esc(nameOf(t.paidBy))} paid ${money(t.amount)} · ${esc(nameOf("sam"))} ${money(sm)}""",
    """`${esc(nameOf(t.paidBy))} paid ${money(t.gross || t.amount)}${t.repaid ? ` − ${money(t.repaid)} paid back` : ""} · ${esc(nameOf("sam"))} ${money(sm)}""")

# month totals and the per-person view
rep("""  const tx = state.budget.txns.filter(t => t.date.slice(0, 7) === k), live""", """  const tx = netTx().filter(t => t.date.slice(0, 7) === k), live""")
rep("""  const income = live.filter(t => t.kind === "income").reduce((a, t) => a + t.amount, 0);""",
    """  const income = live.filter(t => t.kind === "income" && !t.linked).reduce((a, t) => a + t.amount, 0);""")
rep("""    income: live.filter(t => t.kind === "income" && t.paidBy === who).reduce""", """    income: live.filter(t => t.kind === "income" && !t.linked && t.paidBy === who).reduce""")

# ---------- the spending list ----------
rep("""  const days = [...new Set(st.tx.map(t => t.date))].sort().reverse();""",
    """  const listTx = st.tx.filter(t => !t.linked || t.linked.date.slice(0, 7) !== k);   // paybacks sit under their expense; from another month they show here, not counted
  const days = [...new Set(listTx.map(t => t.date))].sort().reverse();""")
rep("""<div class="glist">${st.tx.filter(t => t.date === d).sort((a,b) => b.amount - a.amount).map(t => `<button type="button" class="txrow ${t.cancelled ? "cx" : ""}" data-act="editTxn" data-id="${t.id}">""",
    """<div class="glist">${listTx.filter(t => t.date === d).sort((a,b) => b.amount - a.amount).map(t => `<button type="button" class="txrow ${t.cancelled ? "cx" : ""} ${t.linked ? "elsewhere" : ""}" data-act="editTxn" data-id="${t.id}">""")
rep("""          ${t.details ? `<span class="td">${esc(t.details)}</span>` : ""}${who && t.kind === "expense" && t.shared""",
    """          ${t.repaid ? `<span class="td">${money(t.gross)} − ${money(t.repaid)} paid back</span>` : ""}${t.linked ? `<span class="td">Pays back “${esc(expLabel(t.linked))}” (${esc(niceDate(t.linked.date))}) · counted there</span>` : ""}
          ${t.details ? `<span class="td">${esc(t.details)}</span>` : ""}${who && t.kind === "expense" && t.shared""")
rep("""        <span class="ta ${t.kind}">${t.kind === "income" ? "+" : ""}${money(t.amount)}</span></button>`).join("")}</div></div>`).join("")""",
    """        <span class="ta ${t.kind}">${t.linked ? `(${money(t.amount)})` : (t.kind === "income" ? "+" : "") + money(t.amount)}</span></button>${paybackRows(t)}`).join("")}</div></div>`).join("")""")
rep("""  ${hasShared ? `<section class="card settle">""", """  ${paybackHintHTML()}
  ${hasShared ? `<section class="card settle">""")

rep("""/* ---- forms ---- */
function catOptions(""", r"""// The paybacks under an expense in the list
function paybackRows(t){
  if(!t.paybacks) return "";
  return t.paybacks.slice().sort((a, b) => a.date.localeCompare(b.date)).map(r => `<button type="button" class="txrow payback" data-act="editTxn" data-id="${r.id}">
    <span class="pbarrow" aria-hidden="true">↳</span><span class="tb"><span class="tt">${esc(r.note || "Paid back")}</span>
    <span class="ts">Paid back ${esc(niceDate(r.date))}${r.paidBy !== t.paidBy ? ` to ${esc(nameOf(r.paidBy))}` : ""}</span></span>
    <span class="ta payback">−${money(r.amount)}</span></button>`).join("");
}
// Recent income that looks like it pays something back. One at a time; nothing pairs without a tap.
function paybackHint(){
  const t0 = todayStr();
  const incs = state.budget.txns.filter(t => t.kind === "income" && !t.repays && !t.noRepay && !t.cancelled && isDate(t.date) && diffDays(t.date, t0) <= 60 && diffDays(t.date, t0) >= -1)
    .sort((a, b) => b.date.localeCompare(a.date));
  for(const inc of incs){ const c = bestPayback(inc); if(c) return {inc, c}; }
  return null;
}
function paybackHintHTML(){
  const h = paybackHint(); if(!h) return "";
  const {inc, c} = h, e = c.t;
  return `<section class="card soon-card pbhint"><span class="ic">${IC.budget}</span><div style="flex:1;min-width:0">
    <h3>Payback for “${esc(expLabel(e))}”?</h3>
    <p>${money(inc.amount)} came in ${esc(niceDate(inc.date))}${inc.note ? ` (“${esc(cutText(inc.note, 40))}”)` : ""}. It might be paying back ${esc(expLabel(e))} from ${esc(niceDate(e.date))}${c.left < e.amount ? ` (${money(c.left)} left on it)` : ""}.</p>
    <div class="actions" style="margin-top:8px;justify-content:flex-start"><button type="button" class="btn small" data-act="pbPair" data-id="${inc.id}">Pair them</button>
      <button type="button" class="link" data-act="pbNo" data-id="${inc.id}">Not a payback</button></div></div></section>`;
}
// "Pays back" picker on an income entry
function paybackPicker(d){
  const inc = {id: d.id, amount: d.amount, date: isDate(d.date) ? d.date : todayStr(), note: d.note};
  const list = paybackCands(inc).slice(0, 25);
  const cur = d.repays && state.budget.txns.find(t => t.id === d.repays && t.kind === "expense");
  if(cur && !list.some(c => c.t.id === cur.id)) list.unshift({t: cur, left: cur.amount - repaidSoFar(cur.id, d.id), hit: false});
  const opt = c => `<option value="${c.t.id}" ${d.repays === c.t.id ? "selected" : ""}>${c.hit ? "★ " : ""}${esc(cutText(expLabel(c.t), 28))} · ${esc(niceDate(c.t.date))} · ${money(c.left)} left</option>`;
  return field("trepays", "Pays back an expense?", `<select id="trepays" name="trepays"><option value="">No, it's regular income</option>${list.map(opt).join("")}</select>`,
    list.length ? `If a friend paid you back, pick what it was for. It lowers that cost instead of counting as income.${list.some(c => c.hit) ? " ★ = mentions the same name or words." : ""}` : "No recent spending to pair it with.");
}
// On an expense: its paybacks, and a button to add one
function paybackBox(t){
  const pb = state.budget.txns.filter(r => r.kind === "income" && r.repays === t.id);
  const live = pb.filter(r => !r.cancelled).reduce((a, r) => a + r.amount, 0);
  return `<div class="field" id="pbBox"><span class="lab">Paid back</span>
    ${pb.length ? `<div class="small">${pb.map(r => `${esc(r.note || "Paid back")} · ${money(r.amount)} · ${esc(niceDate(r.date))}${r.cancelled ? " (didn't come in)" : ""}`).join("<br>")}</div>
      <span class="hint">Counts as ${money(Math.max(0, t.amount - live))} after paybacks${t.shared ? ", and that's what you two split" : ""}. Tap a payback in the list to change it.</span>`
      : `<span class="hint">If someone pays you back for this, add it here so it lowers the cost instead of counting as income.</span>`}
    <button type="button" class="btn ghost small" data-act="addPayback" data-id="${t.id}" style="align-self:flex-start;margin-top:4px">+ Someone paid me back</button></div>`;
}
/* ---- forms ---- */
function catOptions(""")

# ---------- the entry form ----------
rep("""    ${splitPicker("t", d.split, d.amount)}
    ${field("tdetails","Details",""",
    """    ${splitPicker("t", d.split, d.amount)}
    <div id="incOnly">${paybackPicker(d)}</div>
    ${t && t.kind === "expense" ? paybackBox(t) : ""}
    ${field("tdetails","Details",""")
rep("""    if(sp.error) return fail("tsplit", sp.error);
    const data = {kind, amount, date,""",
    """    if(sp.error) return fail("tsplit", sp.error);
    const repays = kind === "income" ? val(form, "trepays") : "";
    if(t && t.kind === "expense"){
      const back = repaidSoFar(t.id);
      if(back && kind !== "expense") return fail("trepays", `${money(back)} has been paid back for this. Remove those paybacks before making it income.`);
      if(back && amount < back) return fail("amt", `${money(back)} has already been paid back for this, so the amount can't be less than that.`);
    }
    if(repays){
      const e = state.budget.txns.find(x => x.id === repays && x.kind === "expense");
      if(!e) return fail("trepays", "That expense isn't there anymore. Pick another, or choose regular income.");
      if(e.cancelled) return fail("trepays", "That expense is marked cancelled. Pick another, or choose regular income.");
      const left = e.amount - repaidSoFar(e.id, t ? t.id : null);
      if(amount > left) return fail("trepays", `That's more than what's left on “${expLabel(e)}” (${money(left)}). Lower the amount, or log the extra as separate income.`);
    }
    const data = {kind, amount, date,""")
rep("""    if(t) Object.assign(t, data); else state.budget.txns.push(Object.assign({id:uid(), billId:null}, data));
    budgetMonth = date.slice(0, 7);""",
    """    if(repays){ data.repays = repays; }
    if(t){ Object.assign(t, data); if(!repays) delete t.repays; else delete t.noRepay; } else state.budget.txns.push(Object.assign({id:uid(), billId:null}, data));
    const pe = repays && state.budget.txns.find(x => x.id === repays);
    budgetMonth = (pe ? pe.date : date).slice(0, 7);   // a payback shows under its expense""")
rep("""toast(data.cancelled ? "Saved as cancelled · not counted" : t ? "Saved" : kind === "income" ? "Income logged" : `${money(amount)} logged`);""",
    """toast(data.cancelled ? "Saved as cancelled · not counted" : pe ? `Paired with “${expLabel(pe)}”` : t ? "Saved" : kind === "income" ? "Income logged" : `${money(amount)} logged`);""")
rep("""$("#expOnly").hidden = !exp; $("#sharedBox").hidden = !exp; if(!exp) $("#f-tsplit").hidden = true; };""",
    """$("#expOnly").hidden = !exp; $("#sharedBox").hidden = !exp; if(!exp) $("#f-tsplit").hidden = true; $("#incOnly").hidden = exp; if($("#pbBox")) $("#pbBox").hidden = !exp; };""")

# ---------- actions ----------
rep("""  editCat: id => catForm(id || null),
  editBill: id => billForm(id || null),""",
    """  editCat: id => catForm(id || null),
  editBill: id => billForm(id || null),
  addPayback: id => { const e = state.budget.txns.find(x => x.id === id && x.kind === "expense"); if(!e) return; closeSheet();
    txnForm(null, {kind:"income", repays:e.id, paidBy:e.paidBy, date: todayStr() >= e.date ? todayStr() : e.date, note:""}); },
  pbPair: id => { const inc = state.budget.txns.find(x => x.id === id && x.kind === "income"); if(!inc) return; const c = bestPayback(inc); if(!c) return;
    inc.repays = c.t.id; delete inc.noRepay; save(); render(); toast(`Paired · “${expLabel(c.t)}” now counts as ${money(c.t.amount - repaidSoFar(c.t.id))}`, () => { delete inc.repays; save(); render(); }); },
  pbNo: id => { const inc = state.budget.txns.find(x => x.id === id && x.kind === "income"); if(!inc) return; inc.noRepay = true; save(); render(); toast("OK, it stays income", () => { delete inc.noRepay; save(); render(); }); },""")
rep("""  delTxn: id => removeBy(state.budget.txns, id) && "Entry deleted",""",
    """  delTxn: id => { const pb = state.budget.txns.filter(t => t.kind === "income" && t.repays === id); if(!removeBy(state.budget.txns, id)) return "";
    pb.forEach(t => { delete t.repays; t.noRepay = true; });   // keep the money: it counts as income again
    return pb.length ? `Entry deleted · ${pb.length === 1 ? "its payback counts" : "its paybacks count"} as income now` : "Entry deleted"; },""")

# ---------- stored data: keep the new fields tidy ----------
rep("""note: str(t.note, 80), details: str(t.details, 500), cancelled: !!t.cancelled, billId: t.billId ? String(t.billId) : null })),""",
    """note: str(t.note, 80), details: str(t.details, 500), cancelled: !!t.cancelled, billId: t.billId ? String(t.billId) : null }))
      .map(t => { if(t.kind !== "income" || !t.repays) delete t.repays; else t.repays = String(t.repays); if(t.kind !== "income" || !t.noRepay) delete t.noRepay; else t.noRepay = true; return t; }),""")

# ---------- import: offer "pays back" on money that came in ----------
rep("""        ${k.kind === "expense" ? `<select class="ic" data-change="impCat\"""",
    """        ${k.kind === "income" && !k.partnerRow ? impRepayPick(x) : ""}
        ${k.kind === "expense" ? `<select class="ic" data-change="impCat\"""")
rep("""        shared: k.kind === "expense" && imp.shared && !k.partnerRow, billId:null, imp:x.key, source:imp.fmt});""",
    """        shared: k.kind === "expense" && imp.shared && !k.partnerRow, billId:null, imp:x.key, source:imp.fmt});
      if(k.kind === "income" && !k.partnerRow && x.repays){ const e = state.budget.txns.find(t => t.id === x.repays && t.kind === "expense" && !t.cancelled), nt = state.budget.txns[state.budget.txns.length - 1];
        if(e && Math.abs(x.cents) <= e.amount - repaidSoFar(e.id, nt.id)){ nt.repays = e.id; paired++; } else unpaired++; }""")
rep("""    const pick = imp.rows.filter(x => x.include); if(!pick.length) return;
    let last = "";""", """    const pick = imp.rows.filter(x => x.include); if(!pick.length) return;
    let last = "", paired = 0, unpaired = 0;""")
rep("""    save(); closeSheet(); render(); toast(`Imported ${n} transaction${n===1?"":"s"}`);""",
    """    save(); closeSheet(); render(); toast(`Imported ${n} transaction${n===1?"":"s"}${paired ? ` · ${paired} paired as ${paired === 1 ? "a payback" : "paybacks"}` : ""}${unpaired ? ` · ${unpaired} kept as income (more than was left to pay back)` : ""}`);""")
rep("""  else if(c === "impCat"){ const x = row(); if(x) x.categoryId = el.value || null; return true; }""",
    """  else if(c === "impCat"){ const x = row(); if(x) x.categoryId = el.value || null; return true; }
  else if(c === "impRepay"){ const x = row(); if(x) x.repays = el.value || null; return true; }""")
rep("""function rowKind(x){""", r"""// For money in: up to 3 expenses it might pay back (shared word + amount fits). Starts as plain income.
function impRepayPick(x){
  if(!x.pb) x.pb = paybackCands({amount: Math.abs(x.cents), date: x.date, note: x.note || x.desc, who: x.counterparty}).filter(c => c.hit && c.fits).slice(0, 3);
  if(!x.pb.length) return "";
  return `<select class="ic" data-change="impRepay" data-id="${x.i}" aria-label="Is ${esc(x.desc)} a payback?"><option value="">Income · or pick what it pays back</option>${x.pb.map(c => `<option value="${c.t.id}" ${x.repays === c.t.id ? "selected" : ""}>Pays back “${esc(cutText(expLabel(c.t), 26))}” (${esc(niceDate(c.t.date))})</option>`).join("")}</select>`;
}
function rowKind(x){""")

rep('const BUILD = "2026-10-30 · 31";', 'const BUILD = "2026-10-30 · 32";')
open(p, "w").write(s)
print("patched")

# ---------- fix: "How to split" stayed visible after switching the form to Income ----------
s = open(p).read()
rep("""    const shared = form.elements[sharedName] && form.elements[sharedName].checked, box = $("#f-" + prefix + "split"); if(!box) return;""",
    """    const kindEl = form.querySelector("input[name=kind]:checked");
    const shared = form.elements[sharedName] && form.elements[sharedName].checked && !(kindEl && kindEl.value === "income"), box = $("#f-" + prefix + "split"); if(!box) return;""")
open(p, "w").write(s)
print("split box fix applied")
