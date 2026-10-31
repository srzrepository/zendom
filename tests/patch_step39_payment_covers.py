"""Step 39: payments between you are grouped under what they paid for.
- A payment between Sam and Charlie can say what it covers: one or several shared costs (covers:[ids]).
  Record payment has a "What does it cover?" checklist (shared costs where that person still owes
  something, newest first; a new payment starts with what's been shared since you were last even).
- In the spending list the payment sits under each cost it covers ("↳ Sam paid her share · Oct 30"),
  split across them oldest first, and the cost says "Sam's part paid" or "Sam paid $X of $Y".
  A payment covering costs in another month still shows on its own day, marked with what it's for.
- "I paid Charlie my share" and "make it a payment" fill in what it covers.
- Venmo import: a payment with Charlie that adds up exactly to one or more of the shared costs you
  owe for (up to 3) is offered grouped with them; you can choose not to.
- Payments recorded before this: if one adds up exactly to what you owed for some costs, a card
  offers to group them (Group them / Not now).
Grouping never changes any totals or who owes whom; it only shows what paid for what.
Data: optional covers (list of ids) and noCover on payments. Usage: python3 patch_step39_payment_covers.py file.html"""
import sys
p = sys.argv[1]; s = open(p).read()
def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (s.count(old), old[:100])
    s = s.replace(old, new)

# ---------- model ----------
rep("""/* ---- duplicates ---- */""", r"""/* ---- payments between you: what they paid for ---- */
const sumAmt = l => (l || []).reduce((a, x) => a + x.amt, 0);
const hisHer = h => h === "sam" ? "her" : "his";
// expense id -> [{p: payment, amt}]: each payment's amount spread over the costs it covers, oldest first,
// up to what the payer owed on each. txs: netTx() (paybacks already taken off).
function coverMap(txs){
  const byId = new Map(txs.map(t => [t.id, t])), alloc = new Map();
  txs.filter(t => t.kind === "settle" && !t.cancelled && Array.isArray(t.covers) && t.covers.length).sort((a, b) => a.date.localeCompare(b.date)).forEach(p => {
    let left = p.amount;
    p.covers.map(id => byId.get(id)).filter(e => e && e.kind === "expense" && e.shared && !e.cancelled && e.paidBy === other(p.paidBy))
      .sort((a, b) => a.date.localeCompare(b.date)).forEach(e => {
        const owed = Math.round(shareOf(e, p.paidBy)), amt = Math.max(0, Math.min(left, owed - sumAmt(alloc.get(e.id))));
        if(!alloc.has(e.id)) alloc.set(e.id, []); alloc.get(e.id).push({p, amt}); left -= amt; });
  });
  return alloc;
}
// The costs a payment covers that still exist
const coveredBy = (p, txs) => (p.covers || []).map(id => txs.find(t => t.id === id)).filter(e => e && e.kind === "expense" && !e.cancelled);
// Shared costs a payer owes on, with what's left (excluding one payment, when editing it)
function coverCands(payer, exceptId){
  const net = netTx(), cm = coverMap(net.filter(x => x.id !== exceptId)), t0 = todayStr();
  return net.filter(e => e.kind === "expense" && e.shared && !e.cancelled && isDate(e.date) && e.paidBy === other(payer) && diffDays(e.date, t0) <= 150)
    .map(e => { const owed = Math.round(shareOf(e, payer)); return {e, owed, left: owed - sumAmt((cm.get(e.id) || []).filter(x => x.p.id !== exceptId))}; });
}
// Costs a payment most likely paid for: ones that add up exactly to it (1 to 3 of them). Null if none.
function coverGuess(payer, amount, date, note, exceptId){
  const words = pbWords(note), c = coverCands(payer, exceptId).filter(x => x.left > 0 && x.e.date <= addDays(date, 3) && diffDays(x.e.date, date) <= 90)
    .map(x => Object.assign(x, {hit: [...pbWords(expLabel(x.e))].some(w => words.has(w))}))
    .sort((a, b) => (b.hit - a.hit) || b.e.date.localeCompare(a.e.date)).slice(0, 12);
  const ok = n => Math.abs(n - amount) <= 1;
  for(const x of c) if(ok(x.left)) return [x.e.id];
  for(let i = 0; i < c.length; i++) for(let j = i + 1; j < c.length; j++) if(ok(c[i].left + c[j].left)) return [c[i].e.id, c[j].e.id];
  for(let i = 0; i < c.length; i++) for(let j = i + 1; j < c.length; j++) for(let k = j + 1; k < c.length; k++) if(ok(c[i].left + c[j].left + c[k].left)) return [c[i].e.id, c[j].e.id, c[k].e.id];
  return null;
}
// Shared costs since you were last even that this person owes on (what a new payment usually covers)
function sinceEvenFor(payer){
  const L = oweLedger(); let start = 0;
  for(let i = L.length - 1; i >= 0; i--) if(Math.round(L[i].run) === 0){ start = i + 1; break; }
  return L.slice(start).filter(x => x.t.kind === "expense" && x.t.paidBy === other(payer)).map(x => x.t.id);
}
/* ---- duplicates ---- */""")
rep("""      .map(t => { if(Array.isArray(t.notDup))""",
    """      .map(t => { if(t.kind === "settle" && Array.isArray(t.covers) && t.covers.length) t.covers = [...new Set(t.covers.map(String))].slice(0, 50); else delete t.covers;
        if(t.kind === "settle" && t.noCover) t.noCover = true; else delete t.noCover;
        if(Array.isArray(t.notDup))""")

# ---------- spending list ----------
rep("""  const listTx = st.tx.filter(t => !t.linked || t.linked.date.slice(0, 7) !== k);""",
    """  const NET = netTx(), CM = coverMap(NET);
  const covInMonth = t => { const c = coveredBy(t, NET); return c.length && c.every(e => e.date.slice(0, 7) === k); };
  const listTx = st.tx.filter(t => (!t.linked || t.linked.date.slice(0, 7) !== k) && !(t.kind === "settle" && covInMonth(t)));""")
rep("""${paybackRows(t)}`).join("")}</div></div>`).join("")""", """${paybackRows(t)}${coverRows(t, CM)}`).join("")}</div></div>`).join("")""")
rep("""          ${t.repaid ? `<span class="td">${money(t.gross)} − ${money(t.repaid)} paid back</span>` : ""}""",
    """          ${t.repaid ? `<span class="td">${money(t.gross)} − ${money(t.repaid)} paid back</span>` : ""}${coverStatus(t, CM)}${t.kind === "settle" && t.covers && t.covers.length ? `<span class="td">For ${esc(coveredBy(t, NET).map(expLabel).join(", ") || "costs that were deleted")}</span>` : ""}""")
rep("""// The paybacks under an expense in the list""", r"""// Payments between you under the cost they paid for
function coverRows(t, CM){
  const l = t.kind === "expense" && CM.get(t.id); if(!l || !l.length) return "";
  return l.map(({p, amt}) => `<button type="button" class="txrow payback" data-act="editTxn" data-id="${p.id}">
    <span class="pbarrow" aria-hidden="true">↳</span><span class="tb"><span class="tt">${esc(nameOf(p.paidBy))} paid ${hisHer(p.paidBy)} share</span>
    <span class="ts">${esc(niceDate(p.date))}${p.covers.length > 1 ? ` · part of a ${money(p.amount)} payment` : ""}${p.note ? ` · ${esc(cutText(p.note, 30))}` : ""}</span></span>
    <span class="ta settle">${money(amt)}</span></button>`).join("");
}
function coverStatus(t, CM){
  const l = t.kind === "expense" && t.shared && CM.get(t.id); if(!l || !l.length) return "";
  const ower = other(t.paidBy), owed = Math.round(shareOf(t, ower)), paid = sumAmt(l);
  return `<span class="td">${paid >= owed ? `${esc(nameOf(ower))}'s part paid ✓` : `${esc(nameOf(ower))} paid ${money(paid)} of ${money(owed)}`}</span>`;
}
// The paybacks under an expense in the list""")

# ---------- Record payment: what does it cover ----------
rep("""    ${!t ? `<div id="venmoRow">""", """    <div id="covBox"></div>
    ${!t ? `<div id="venmoRow">""")
rep("""    const data = {kind:"settle", amount, date, paidBy, shared:false, categoryId:null, note: val(form, "smemo").slice(0, 80)};
    if(!t){""", """    const covers = [...form.querySelectorAll("input[name=scov]:checked")].map(x => x.value);
    const data = {kind:"settle", amount, date, paidBy, shared:false, categoryId:null, note: val(form, "smemo").slice(0, 80), covers: covers.length ? covers : null};
    if(!t){""")
rep("""    if(t) applyEdit(t, data); else state.budget.txns.push(Object.assign({id:uid(), billId:null}, data, settleForm.via ? {source:settleForm.via} : {}));""",
    """    if(t){ applyEdit(t, data); if(!t.covers) delete t.covers; else delete t.noCover; }
    else { const nt = Object.assign({id:uid(), billId:null}, data, settleForm.via ? {source:settleForm.via} : {}); if(!nt.covers) delete nt.covers; state.budget.txns.push(nt); }""")
rep("""    save(); closeSheet(); render(); toast("Payment recorded");
  });
}""", """    save(); closeSheet(); render(); toast(covers.length ? `Payment recorded · grouped under ${covers.length === 1 ? "what it paid for" : covers.length + " costs"}` : "Payment recorded");
  });
  // "What does it cover?": rebuilt when you change who paid
  const pre = t ? (t.covers || []) : (d.covers || sinceEvenFor(d.paidBy));
  const drawCov = () => {
    const form = $("#sheetForm"); if(!form) return;
    const who = (form.querySelector("input[name=paidBy]:checked") || {}).value || d.paidBy;
    const had = new Set([...form.querySelectorAll("input[name=scov]:checked")].map(x => x.value)), first = !form.dataset.covDrawn;
    const all = coverCands(who, t ? t.id : null), open = new Set(all.filter(c => c.left > 0).map(c => c.e.id));
    const keep = first ? new Set(who === d.paidBy ? pre.filter(id => t || open.has(id)) : []) : had;   // a new payment: only costs with something left
    const list = all.filter(c => c.left > 0 || keep.has(c.e.id)).sort((a, b) => b.e.date.localeCompare(a.e.date)).slice(0, 30);
    $("#covBox").innerHTML = list.length ? `<div class="field" id="f-scovers"><span class="lab">What does it cover?</span>
      <div class="glist covlist">${list.map(c => `<label class="txrow" style="cursor:pointer"><input type="checkbox" name="scov" value="${c.e.id}" data-left="${Math.max(0, c.left)}" ${keep.has(c.e.id) ? "checked" : ""} style="accent-color:var(--accent);flex:none">
        <span class="tb"><span class="tt">${esc(expLabel(c.e))}</span><span class="ts">${esc(niceDate(c.e.date))} · ${esc(nameOf(who))}'s part ${money(c.owed)}${c.left < c.owed ? ` · ${money(Math.max(0, c.left))} left` : ""}</span></span></label>`).join("")}</div>
      <span class="hint" id="scovsum"></span></div>` : "";
    form.dataset.covDrawn = "1"; sumCov();
  };
  const sumCov = () => { const form = $("#sheetForm"), h = $("#scovsum"); if(!form || !h) return;
    const ch = [...form.querySelectorAll("input[name=scov]:checked")], tot = ch.reduce((a, x) => a + +x.dataset.left, 0), amt = parseMoney(val(form, "samt")) || 0;
    h.textContent = !ch.length ? "Optional. Ticking what it paid for groups it under those in your list." : `Ticked: ${money(tot)}${amt && Math.abs(tot - amt) > 1 ? ` · the payment is ${money(amt)}` : " ✓"}`; };
  const f0 = $("#sheetForm");
  f0.addEventListener("change", e => { if(e.target.name === "paidBy") drawCov(); else sumCov(); });
  f0.addEventListener("input", e => { if(e.target.name === "samt") sumCov(); });
  drawCov();
}""")

# share button / fix-a-payback fill in what it covers
rep("""    settleForm(null, {amount: Math.round(shareOf(nt, ower)), paidBy: ower, note: expLabel(e), date: todayStr()}); },""",
    """    settleForm(null, {amount: Math.round(shareOf(nt, ower)), paidBy: ower, note: expLabel(e), date: todayStr(), covers: [e.id]}); },""")
rep("""    settleForm(null, {amount: r.amount, date: r.date, note: r.note || expLabel(e), paidBy: e.paidBy ? other(e.paidBy) : r.paidBy}, r.id); },""",
    """    settleForm(null, {amount: r.amount, date: r.date, note: r.note || expLabel(e), paidBy: e.paidBy ? other(e.paidBy) : r.paidBy, covers: e.id ? [e.id] : []}, r.id); },""")

# ---------- owe breakdown: say what a payment was for ----------
rep(""": t.kind === "settle" ? `${esc(nameOf(t.paidBy))} paid ${esc(nameOf(other(t.paidBy)))}` : `${esc(nameOf(t.paidBy))} paid ${money(t.gross || t.amount)}""",
    """: t.kind === "settle" ? `${esc(nameOf(t.paidBy))} paid ${esc(nameOf(other(t.paidBy)))}${t.covers && t.covers.length ? ` · for ${esc(coveredBy(t, state.budget.txns).map(expLabel).join(", "))}` : ""}` : `${esc(nameOf(t.paidBy))} paid ${money(t.gross || t.amount)}""")

# ---------- suggest grouping payments recorded before ----------
rep("""function paybackHintHTML(){""", r"""// Earlier payments that add up exactly to some costs: offer to group them (one card for all)
function groupSuggestions(){
  const taken = new Set(), t0 = todayStr(), out = [];
  state.budget.txns.filter(t => t.kind === "settle" && !t.cancelled && !(t.covers && t.covers.length) && !t.noCover && isDate(t.date) && diffDays(t.date, t0) <= 120)
    .sort((a, b) => a.date.localeCompare(b.date)).forEach(p => {
      const g = coverGuess(p.paidBy, p.amount, p.date, p.note, p.id);
      if(g && !g.some(id => taken.has(id))){ g.forEach(id => taken.add(id)); out.push({p, ids: g}); } });
  return out;
}
function groupHintHTML(){
  const G = groupSuggestions(); if(!G.length) return "";
  const lbl = id => { const e = state.budget.txns.find(t => t.id === id); return e ? expLabel(e) : ""; };
  return `<section class="card soon-card grouphint"><span class="ic">${IC.budget}</span><div style="flex:1;min-width:0">
    <h3>Group ${G.length === 1 ? "a payment" : G.length + " payments"} with what ${G.length === 1 ? "it" : "they"} paid for?</h3>
    <p>${G.slice(0, 3).map(x => `${esc(nameOf(x.p.paidBy))}'s ${money(x.p.amount)} on ${esc(niceDate(x.p.date))} → ${esc(x.ids.map(lbl).join(" + "))}`).join("<br>")}${G.length > 3 ? `<br>and ${G.length - 3} more` : ""}</p>
    <div class="actions" style="margin-top:8px;justify-content:flex-start"><button type="button" class="btn small" data-act="groupYes">Group them</button><button type="button" class="link" data-act="groupNo">Not now</button></div></div></section>`;
}
function paybackHintHTML(){""")
rep("""  ${dupCardHTML()}${paybackHintHTML()}""", """  ${dupCardHTML()}${groupHintHTML()}${paybackHintHTML()}""")
rep("""  dupReview: () =>""", """  groupYes: () => { const G = groupSuggestions(); G.forEach(x => { x.p.covers = x.ids; }); save(); render();
    toast(`Grouped ${G.length} payment${G.length === 1 ? "" : "s"}`, () => { G.forEach(x => { delete x.p.covers; }); save(); render(); }); },
  groupNo: () => { const G = groupSuggestions(); G.forEach(x => { x.p.noCover = true; }); save(); render(); toast("OK. You can still tick what a payment covers by opening it."); },
  dupReview: () =>""")

# ---------- Venmo import ----------
rep("""        ${k.partnerRow ? `<select class="ic" data-change="impMode\"""",
    """        ${k.partnerRow && k.kind === "settle" ? impCoverPick(x, k) : ""}
        ${k.partnerRow ? `<select class="ic" data-change="impMode\"""")
rep("""function impRepayPick(x){""", r"""// A payment with your partner that adds up exactly to some shared costs: offered grouped with them
function impCoverPick(x, k){
  const key = k.paidBy + Math.abs(x.cents);
  if(x.covKey !== key){ x.covKey = key; x.covGuess = coverGuess(k.paidBy, Math.abs(x.cents), x.date, x.note || x.desc); x.covers = x.covGuess; }
  if(!x.covGuess) return "";
  const lbl = x.covGuess.map(id => expLabel(state.budget.txns.find(t => t.id === id) || {})).join(" + ");
  return `<select class="ic" data-change="impCover" data-id="${x.i}" aria-label="What this payment covers"><option value="1" ${x.covers ? "selected" : ""}>For ${esc(cutText(lbl, 40))}</option><option value="" ${x.covers ? "" : "selected"}>Don't group it</option></select>`;
}
function impRepayPick(x){""")
rep("""  else if(c === "impRepay"){""", """  else if(c === "impCover"){ const x = row(); if(x) x.covers = el.value ? x.covGuess : null; return true; }
  else if(c === "impRepay"){""")
rep("""      if(k.kind === "income" && !k.partnerRow && x.repays){""", """      if(k.kind === "settle" && x.covers && x.covers.length) state.budget.txns[state.budget.txns.length - 1].covers = x.covers.slice();
      if(k.kind === "income" && !k.partnerRow && x.repays){""")

rep('const BUILD = "2026-10-30 · 38";', 'const BUILD = "2026-10-30 · 39";')
open(p, "w").write(s)
print("patched")
