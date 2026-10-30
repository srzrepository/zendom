"""Step 29: shared costs can be split any way, not just 50/50.
Data: txn.split / bill.split = {mode:"pct", sam:<Sam's percent 0-100>} or {mode:"amt", sam:<Sam's cents>};
no split (or anything invalid) = 50/50, so existing entries are unchanged. Paying a bill copies its split.
Everything that used "half" now uses the real parts: who owes whom, the pay-back card, each person's
share, the summaries/wrap-ups, the import preview's shared toggle (still 50/50 by default).
Usage: python3 patch_step29_splits.py file.html"""
import sys
p = sys.argv[1]; s = open(p).read()
def rep(old, new, n=1):
    global s
    assert s.count(old) == n, (s.count(old), old[:90])
    s = s.replace(old, new)

# --- helpers ---
rep("""function balanceUntil(day){""", r"""// Sam's part of a shared cost (cents; may be x.5 for an even 50/50 split, rounded where shown)
function samPart(t){
  const sp = t.split;
  if(sp && sp.mode === "amt") return Math.max(0, Math.min(t.amount, Math.round(sp.sam)));
  if(sp && sp.mode === "pct") return Math.round(t.amount * Math.max(0, Math.min(100, sp.sam)) / 100);
  return t.amount / 2;
}
// What one person's part of an expense is
function shareOf(t, who){
  if(t.kind !== "expense") return 0;
  if(!t.shared) return t.paidBy === who ? t.amount : 0;
  const s = samPart(t); return who === "sam" ? s : t.amount - s;
}
function splitLabel(t){
  if(!t.shared) return "";
  const s = samPart(t), sp = t.split;
  if(!sp || (sp.mode === "pct" && sp.sam === 50)) return "shared";
  return sp.mode === "pct" ? `shared ${Math.round(sp.sam)}/${100 - Math.round(sp.sam)}` : `shared · ${nameOf("sam")} ${money(Math.round(s))}, ${nameOf("charlie")} ${money(t.amount - Math.round(s))}`;
}
function cleanSplit(sp, amount){
  if(!sp || typeof sp !== "object") return null;
  const v = Number(sp.sam); if(!isFinite(v)) return null;
  if(sp.mode === "pct") return v === 50 ? null : {mode:"pct", sam: Math.max(0, Math.min(100, Math.round(v * 10) / 10))};
  if(sp.mode === "amt") return {mode:"amt", sam: Math.max(0, Math.min(amount, Math.round(v)))};
  return null;
}
function balanceUntil(day){""")
# who owes whom: the other person's part of what one paid
rep("""    if(t.kind === "expense" && t.shared) b += (t.paidBy === "sam" ? 1 : -1) * t.amount / 2;""",
    """    if(t.kind === "expense" && t.shared) b += t.paidBy === "sam" ? t.amount - samPart(t) : -samPart(t);""", 2)
rep("""  const live = st.tx.filter(t => !t.cancelled), share = t => t.shared ? Math.round(t.amount / 2) : (t.paidBy === who ? t.amount : 0);""",
    """  const live = st.tx.filter(t => !t.cancelled), share = t => Math.round(shareOf(t, who));""")
rep("""${who && t.kind === "expense" && t.shared ? `<span class="td">${esc(nameOf(who))}'s half: ${money(Math.round(t.amount / 2))}</span>` : ""}</span>""",
    """${who && t.kind === "expense" && t.shared ? `<span class="td">${esc(nameOf(who))}'s part: ${money(Math.round(shareOf(t, who)))}</span>` : ""}</span>""")
# summaries
rep("""      ${w.sharedTotal ? `<p class="small" style="margin:6px 0 0">Shared costs came to ${money(w.sharedTotal)}, so ${money(Math.round(w.sharedTotal / 2))} each. ${esc(balTxt)}</p>` : ""}</section>""",
    """      ${w.sharedTotal ? `<p class="small" style="margin:6px 0 0">Shared costs came to ${money(w.sharedTotal)}: ${esc(nameOf("sam"))}'s part ${money(Math.round(w.sharedSam))}, ${esc(nameOf("charlie"))}'s part ${money(w.sharedTotal - Math.round(w.sharedSam))}. ${esc(balTxt)}</p>` : ""}</section>""")
rep("""  const sharedTotal = exp.filter(t => t.shared).reduce((a, t) => a + t.amount, 0);
  const biggest = exp.slice().sort((a, b) => b.amount - a.amount)[0] || null;
  const sum = l => l.reduce((a, t) => a + t.amount, 0);""",
"""  const sharedTotal = exp.filter(t => t.shared).reduce((a, t) => a + t.amount, 0), sharedSam = exp.filter(t => t.shared).reduce((a, t) => a + samPart(t), 0);
  const biggest = exp.slice().sort((a, b) => b.amount - a.amount)[0] || null;
  const sum = l => l.reduce((a, t) => a + t.amount, 0);""")
rep("""  return {from, to, days, spent: sum(exp), income: sum(tx.filter(t => t.kind === "income")), prevSpent: sum(prevExp), prevFrom: pFrom, prevTo: pTo, cats, who, sharedTotal, biggest,""",
    """  return {from, to, days, spent: sum(exp), income: sum(tx.filter(t => t.kind === "income")), prevSpent: sum(prevExp), prevFrom: pFrom, prevTo: pTo, cats, who, sharedTotal, sharedSam, biggest,""")
# list label
rep("""${t.shared ? " · shared" : ` · ${esc(nameOf(t.paidBy))}'s`}""", """${t.shared ? " · " + esc(splitLabel(t)) : ` · ${esc(nameOf(t.paidBy))}'s`}""")
# data
rep("""shared: t.kind === "expense" && !!t.shared, note: str(t.note, 80), details: str(t.details, 500), cancelled: !!t.cancelled, billId: t.billId ? String(t.billId) : null })),""",
    """shared: t.kind === "expense" && !!t.shared, split: t.kind === "expense" && t.shared ? cleanSplit(t.split, cents(t.amount)) : null, note: str(t.note, 80), details: str(t.details, 500), cancelled: !!t.cancelled, billId: t.billId ? String(t.billId) : null })),""")
rep("""      categoryId: catIds.has(x.categoryId) ? x.categoryId : null, paidBy: HUMANS.includes(x.paidBy) ? x.paidBy : "sam", shared: !!x.shared, autopay: !!x.autopay }))""",
    """      categoryId: catIds.has(x.categoryId) ? x.categoryId : null, paidBy: HUMANS.includes(x.paidBy) ? x.paidBy : "sam", shared: !!x.shared, split: x.shared ? cleanSplit(x.split, cents(x.amount)) : null, autopay: !!x.autopay }))""")
rep("""    const prevDue = b.nextDue, tx = {id:uid(), kind:"expense", amount:b.amount, date:todayStr(), note:b.name, categoryId:b.categoryId, paidBy:b.paidBy, shared:b.shared, billId:b.id};""",
    """    const prevDue = b.nextDue, tx = {id:uid(), kind:"expense", amount:b.amount, date:todayStr(), note:b.name, categoryId:b.categoryId, paidBy:b.paidBy, shared:b.shared, split: b.shared && b.split ? Object.assign({}, b.split) : null, billId:b.id};""")

# --- the split picker (shared by the spending and bill forms) ---
rep("""function txnForm(id, preset){""", r"""function splitPicker(prefix, sp, amount){
  const mode = sp ? sp.mode : "half";
  const v = !sp ? "" : sp.mode === "pct" ? String(sp.sam) : centsToInput(sp.sam);
  return `<div class="field splitbox" id="f-${prefix}split"><span class="lab">How to split</span>
    <div class="seg" role="radiogroup" aria-label="How to split">${[["half", "50/50"], ["pct", "By percent"], ["amt", "By amount"]].map(([k, l]) => `<label class="chip" style="cursor:pointer"><input type="radio" name="${prefix}smode" value="${k}" ${mode === k ? "checked" : ""}> ${l}</label>`).join("")}</div>
    <div class="two" id="${prefix}sval" ${mode === "half" ? "hidden" : ""}><div class="field"><label for="${prefix}sv" id="${prefix}svlab">${mode === "amt" ? `${esc(nameOf("sam"))}'s part ($)` : `${esc(nameOf("sam"))}'s part (%)`}</label>
      <input id="${prefix}sv" name="${prefix}sv" inputmode="decimal" value="${esc(v)}" placeholder="${mode === "amt" ? "e.g. 1000" : "e.g. 40"}" autocomplete="off"></div>
      <div class="field"><span class="lab">${esc(nameOf("charlie"))}'s part</span><span class="small" id="${prefix}sother" style="padding-top:12px">—</span></div></div>
    <span class="hint" id="${prefix}shint"></span></div>`;
}
// Read the split from a form. Returns {split} or {error}.
function readSplit(form, prefix, amount){
  const mode = (form.querySelector(`input[name=${prefix}smode]:checked`) || {}).value || "half";
  if(mode === "half") return {split:null};
  const raw = val(form, prefix + "sv");
  if(mode === "pct"){ const n = parseFloat(raw.replace("%", "")); if(!(n >= 0 && n <= 100)) return {error:`Enter ${nameOf("sam")}'s percent, from 0 to 100.`}; return {split: cleanSplit({mode:"pct", sam:n}, amount)}; }
  const c = parseMoney(raw); if(c === null || c > amount) return {error:`Enter ${nameOf("sam")}'s part, from $0 up to the total.`};
  return {split: {mode:"amt", sam:c}};
}
// Keep the split box in step with the Shared switch, the mode and the amount.
function wireSplit(prefix, sharedName, amountName){
  const form = $("#sheetForm"); if(!form) return;
  const upd = () => {
    const shared = form.elements[sharedName] && form.elements[sharedName].checked, box = $("#f-" + prefix + "split"); if(!box) return;
    box.hidden = !shared;
    const mode = (form.querySelector(`input[name=${prefix}smode]:checked`) || {}).value || "half";
    $("#" + prefix + "sval").hidden = mode === "half";
    $("#" + prefix + "svlab").textContent = `${nameOf("sam")}'s part (${mode === "amt" ? "$" : "%"})`;
    const amt = parseMoney(val(form, amountName)) || 0, r = readSplit(form, prefix, amt || 1e12), other = $("#" + prefix + "sother"), hint = $("#" + prefix + "shint");
    if(r.error || !amt){ other.textContent = "—"; hint.textContent = amt ? "" : "Enter the amount to see each part."; return; }
    const sm = Math.round(r.split ? samPart({amount:amt, split:r.split}) : amt / 2);
    other.textContent = mode === "pct" ? `${Math.round((100 - parseFloat(val(form, prefix + "sv"))) * 10) / 10}% · ${money(amt - sm)}` : money(amt - sm);
    hint.textContent = `${nameOf("sam")} ${money(sm)} · ${nameOf("charlie")} ${money(amt - sm)}`;
  };
  form.addEventListener("input", upd); form.addEventListener("change", upd); upd();
}
function txnForm(id, preset){""")
rep("""    <label class="chip" id="sharedBox" style="align-self:flex-start;cursor:pointer"><input type="checkbox" name="shared" ${d.shared?"checked":""} style="accent-color:var(--accent)"> Shared cost (split 50/50)</label>
    ${field("tdetails","Details",""",
"""    <label class="chip" id="sharedBox" style="align-self:flex-start;cursor:pointer"><input type="checkbox" name="shared" ${d.shared?"checked":""} style="accent-color:var(--accent)"> Shared cost</label>
    ${splitPicker("t", d.split, d.amount)}
    ${field("tdetails","Details",""")
rep("""    const data = {kind, amount, date, note:val(form,"tnote"), paidBy, categoryId: kind === "expense" && state.budget.categories.some(c => c.id === cid) ? cid : null, shared: kind === "expense" && form.elements.shared.checked,
      details: form.elements.tdetails.value.trim().slice(0, 500), cancelled: form.elements.tcancel.checked};""",
"""    const shared = kind === "expense" && form.elements.shared.checked, sp = shared ? readSplit(form, "t", amount) : {split:null};
    if(sp.error) return fail("tsplit", sp.error);
    const data = {kind, amount, date, note:val(form,"tnote"), paidBy, categoryId: kind === "expense" && state.budget.categories.some(c => c.id === cid) ? cid : null, shared, split: sp.split,
      details: form.elements.tdetails.value.trim().slice(0, 500), cancelled: form.elements.tcancel.checked};""")
rep("""  const sync = () => { const exp = (document.querySelector("input[name=kind]:checked") || {}).value !== "income"; $("#expOnly").hidden = !exp; $("#sharedBox").hidden = !exp; };
  document.querySelectorAll("input[name=kind]").forEach(r => r.addEventListener("change", sync)); sync();""",
"""  wireSplit("t", "shared", "amt");
  const sync = () => { const exp = (document.querySelector("input[name=kind]:checked") || {}).value !== "income"; $("#expOnly").hidden = !exp; $("#sharedBox").hidden = !exp; if(!exp) $("#f-tsplit").hidden = true; };
  document.querySelectorAll("input[name=kind]").forEach(r => r.addEventListener("change", sync)); sync();""")
# bills
rep("""    <div class="seg"><label class="chip" style="cursor:pointer"><input type="checkbox" name="bshared" ${d.shared?"checked":""} style="accent-color:var(--accent)"> Shared (50/50)</label>
      <label class="chip" style="cursor:pointer"><input type="checkbox" name="bauto" ${d.autopay?"checked":""} style="accent-color:var(--accent)"> On autopay</label></div>
    ${footer(b ? "delBill:" + b.id : "")}`,""",
"""    <div class="seg"><label class="chip" style="cursor:pointer"><input type="checkbox" name="bshared" ${d.shared?"checked":""} style="accent-color:var(--accent)"> Shared</label>
      <label class="chip" style="cursor:pointer"><input type="checkbox" name="bauto" ${d.autopay?"checked":""} style="accent-color:var(--accent)"> On autopay</label></div>
    ${splitPicker("b", d.split, d.amount)}
    ${footer(b ? "delBill:" + b.id : "")}`,""")
rep("""    const cid = val(form,"bcat");
    const data = {name, amount, cycle, nextDue:due, categoryId: state.budget.categories.some(c => c.id === cid) ? cid : null, paidBy: HUMANS.includes(paidBy) ? paidBy : prefs.user, shared:form.elements.bshared.checked,""",
"""    const cid = val(form,"bcat"), bsp = form.elements.bshared.checked ? readSplit(form, "b", amount) : {split:null};
    if(bsp.error) return fail("bsplit", bsp.error);
    const data = {name, amount, cycle, nextDue:due, categoryId: state.budget.categories.some(c => c.id === cid) ? cid : null, paidBy: HUMANS.includes(paidBy) ? paidBy : prefs.user, shared:form.elements.bshared.checked, split: bsp.split,""")
rep("""    save(); closeSheet(); render(); toast("Bill saved");
  });
}""", """    save(); closeSheet(); render(); toast("Bill saved");
  });
  wireSplit("b", "bshared", "bamt");
}""")

open(p, "w").write(s)
print("step 29 applied")
