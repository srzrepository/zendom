"""Step 34: paychecks - income you're expecting.
- Budget → Spending has a Paychecks list: name, usual amount, whose, and how often (every week,
  every 2 weeks, twice a month on two days like the 15th and last day, or once a month). Optionally
  a payday that falls on a weekend comes the Friday before.
- When a payday is close or has passed, "Got it" logs the income (dated the payday, or today if it
  came early) and moves to the next one. Undo is in the toast; the logged entry can be edited.
- The Income number shows what's still expected this month (or that month, when you look ahead).
- Paydays show on the calendar.
Data: new list budget.paydays (synced as "payday~id"). Old data loads with an empty list.
Usage: python3 patch_step34_paydays.py file.html"""
import sys
p = sys.argv[1]; s = open(p).read()
def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (s.count(old), old[:100])
    s = s.replace(old, new)

# ---------- data ----------
rep("""categories: DEFAULT_BUDGET_CATS.map(n => ({id:uid(), name:n, limit:0})), txns:[], bills:[] }; }""",
    """categories: DEFAULT_BUDGET_CATS.map(n => ({id:uid(), name:n, limit:0})), txns:[], bills:[], paydays:[] }; }""")
rep("""      categoryId: catIds.has(x.categoryId) ? x.categoryId : null, paidBy: HUMANS.includes(x.paidBy) ? x.paidBy : "sam", shared: !!x.shared, split: x.shared ? cleanSplit(x.split, cents(x.amount)) : null, autopay: !!x.autopay }))
  });""",
    """      categoryId: catIds.has(x.categoryId) ? x.categoryId : null, paidBy: HUMANS.includes(x.paidBy) ? x.paidBy : "sam", shared: !!x.shared, split: x.shared ? cleanSplit(x.split, cents(x.amount)) : null, autopay: !!x.autopay })),
    paydays: objs(b.paydays).filter(x => str(x.name).trim() && cents(x.amount) && PAY_CYCLES[x.cycle] && isDate(x.next)).map(x => {
      const days = (Array.isArray(x.days) ? x.days : []).map(d => clampInt(d, 1, 31, 0)).filter(Boolean).slice(0, 2).sort((a, b) => a - b);
      const need = x.cycle === "semimonthly" ? 2 : x.cycle === "monthly" ? 1 : 0;
      return Object.assign({}, x, {id: x.id ? String(x.id) : uid(), name: str(x.name, 40).trim(), amount: cents(x.amount), who: HUMANS.includes(x.who) ? x.who : "sam",
        days: days.length >= need ? [...new Set(days)].slice(0, need) : (need === 2 ? [15, 31] : need === 1 ? [+x.next.slice(8)] : []), weekend: !!x.weekend});
    }).filter(x => x.cycle !== "semimonthly" || x.days.length === 2)
  });""")
rep("""d.budget.categories = []; d.budget.txns = []; d.budget.bills = [];""", """d.budget.categories = []; d.budget.txns = []; d.budget.bills = []; d.budget.paydays = [];""")
rep("""["txn", st => st.budget.txns], ["bill", st => st.budget.bills],""", """["txn", st => st.budget.txns], ["bill", st => st.budget.bills], ["payday", st => st.budget.paydays],""")
rep("""  if(kind === "bill"){ if(!n) return null;""", """  if(kind === "payday"){ if(!n || o) return null; return `added a payday: ${clip(n.name, 30)}`; }
  if(kind === "bill"){ if(!n) return null;""")

# ---------- schedule math ----------
rep("""function nextBillDate(b){""", r"""/* ---- Paydays: income you're expecting ----
   p.next is the payday as scheduled. With weekend:true, a Saturday or Sunday payday comes the Friday before. */
const PAY_CYCLES = {weekly:"Every week", biweekly:"Every 2 weeks", semimonthly:"Twice a month", monthly:"Once a month"};
const dayLabel = d => d >= 31 ? "last day" : d + (d % 10 === 1 && d !== 11 ? "st" : d % 10 === 2 && d !== 12 ? "nd" : d % 10 === 3 && d !== 13 ? "rd" : "th");
function payCycleLabel(p){ return p.cycle === "semimonthly" ? `The ${dayLabel(p.days[0])} and ${dayLabel(p.days[1])}` : p.cycle === "monthly" ? `The ${dayLabel(p.days[0])} of each month` : PAY_CYCLES[p.cycle]; }
// The first scheduled payday on or after `from` (by days of the month), or the next one after it (strict)
function payByDays(days, from, strict){
  const out = [];
  for(let k = 0; k < 3; k++){ const mk = addMonths(from.slice(0, 8) + "01", k); days.forEach(d => out.push(withDay(mk, d))); }
  return out.filter(x => strict ? x > from : x >= from).sort()[0];
}
function payAfter(p, d){
  if(p.cycle === "weekly") return addDays(d, 7);
  if(p.cycle === "biweekly") return addDays(d, 14);
  return payByDays(p.days, d, true);
}
function payActual(p, d){ if(!p.weekend) return d; const w = parse(d).getDay(); return w === 6 ? addDays(d, -1) : w === 0 ? addDays(d, -2) : d; }
// Paydays whose money lands between from and to, starting at the next one not logged yet: [{sched, date}]
function payDates(p, from, to){
  const out = []; let d = p.next;
  for(let i = 0; i < 400; i++){ const a = payActual(p, d); if(a > to) break; if(a >= from) out.push({sched: d, date: a}); d = payAfter(p, d); }
  return out;
}
// What's still expected between from and to (only paydays not logged yet), optionally for one person
const expectedPay = (from, to, who) => state.budget.paydays.filter(p => !who || p.who === who).reduce((a, p) => a + payDates(p, from, to).length * p.amount, 0);
function payInfo(p){
  const a = payActual(p, p.next), n = diffDays(todayStr(), a);
  if(n < 0) return {cls:"soon", text:"Did it come in?", n, date:a};
  if(n === 0) return {cls:"today", text:"Payday today", n, date:a};
  if(n === 1) return {cls:"ok", text:"Tomorrow", n, date:a};
  return {cls:"", text: n <= 6 ? `In ${n} days` : niceDate(a), n, date:a};
}
function nextBillDate(b){""")

# ---------- budget page ----------
rep("""  const billTotal = bills.reduce((a, b) => a + billMonthly(b), 0);""",
    """  const billTotal = bills.reduce((a, b) => a + billMonthly(b), 0);
  const pays = state.budget.paydays.filter(p => !who || p.who === who).slice().sort((a, b) => payActual(a, a.next).localeCompare(payActual(b, b.next)));
  const mEnd = toStr(new Date(+k.slice(0, 4), +k.slice(5, 7), 0)), mFrom = k < todayStr().slice(0, 7) ? null : `${k}-01`;
  const expect = mFrom ? expectedPay(mFrom, mEnd, who) : 0;""")
rep("""<b>${money(st.income)}</b><span class="small muted">${st.income ? `${money(Math.abs(st.income - st.spent))} ${st.income >= st.spent ? "after spending" : "short"}` : "None logged"}</span></div>""",
    """<b>${money(st.income)}</b><span class="small muted">${st.income ? `${money(Math.abs(st.income - st.spent))} ${st.income >= st.spent ? "after spending" : "short"}` : "None logged"}</span>${expect ? `<span class="small muted expect">+ ${money(expect)} expected by ${esc(niceDate(mEnd))}</span>` : ""}</div>""")
rep("""  <section class="sec"><div class="sec-head"><span class="label">Bills &amp; subscriptions""",
    """  <section class="sec"><div class="sec-head"><span class="label">Paychecks${pays.length ? ` · ${money(pays.reduce((a, p) => a + payMonthly(p), 0))}/mo` : ""}</span><button type="button" class="link" data-act="editPayday">+ Add</button></div>
    ${pays.length ? `<div class="list">${pays.map(p => { const i = payInfo(p); return `<div class="billrow"><button type="button" class="item" data-act="editPayday" data-id="${p.id}"><div><div class="t">${esc(p.name)}</div>
        <div class="s">${money(p.amount)} · ${esc(payCycleLabel(p))} · ${esc(nameOf(p.who))}</div></div><span class="pill ${i.cls}">${esc(i.text)}</span></button>
        ${i.n <= 2 ? `<button type="button" class="btn ghost small" data-act="gotPay" data-id="${p.id}" aria-label="Got ${esc(p.name)}">Got it</button>` : ""}</div>`; }).join("")}</div>`
      : `<div class="empty"><p>${who ? `No paychecks for ${esc(nameOf(who))} yet.` : "Add your paychecks to see what's still coming in this month."}</p></div>`}
  </section>

  <section class="sec"><div class="sec-head"><span class="label">Bills &amp; subscriptions""")

# ---------- form + actions ----------
rep("""const BUDGET_ACTIONS = {""", r"""// Rough monthly amount of a paycheck (for the list heading)
const payMonthly = p => p.cycle === "weekly" ? Math.round(p.amount * 52 / 12) : p.cycle === "biweekly" ? Math.round(p.amount * 26 / 12) : p.cycle === "semimonthly" ? p.amount * 2 : p.amount;
function dayOptions(sel){ return [...Array(30)].map((_, i) => `<option value="${i + 1}" ${sel === i + 1 ? "selected" : ""}>${dayLabel(i + 1)}</option>`).join("") + `<option value="31" ${sel >= 31 ? "selected" : ""}>Last day</option>`; }
function paydayForm(id){
  const p = id ? state.budget.paydays.find(x => x.id === id) : null; if(id && !p) return;
  const d = p || {name:"Paycheck", amount:0, who:prefs.user, cycle:"biweekly", next:todayStr(), days:[15, 31], weekend:true};
  const dd = d.cycle === "semimonthly" ? d.days : d.cycle === "monthly" ? [d.days[0], 31] : [15, 31];
  openSheet(p ? "Edit paycheck" : "New paycheck", `
    ${field("pname","Name", `<input id="pname" name="pname" maxlength="40" value="${esc(d.name)}" placeholder="Paycheck, Stanford, side gig…" autocomplete="off">`)}
    ${field("pamt","Usual amount", `<input id="pamt" name="pamt" inputmode="decimal" value="${esc(centsToInput(d.amount))}" placeholder="$0.00" autocomplete="off">`, "What lands in your account. You can change it each time.")}
    <div class="field"><span class="lab">Whose?</span>${whoRadios("pwho", d.who)}</div>
    ${field("pcycle","How often", `<select id="pcycle" name="pcycle">${Object.entries(PAY_CYCLES).map(([k, l]) => `<option value="${k}" ${d.cycle === k ? "selected" : ""}>${l}</option>`).join("")}</select>`)}
    <div id="pDateBox">${field("pnext","Next payday", `<input id="pnext" name="pnext" type="date" value="${esc(d.cycle === "weekly" || d.cycle === "biweekly" ? d.next : todayStr())}">`)}</div>
    <div class="two" id="pDaysBox">${field("pday1","On the", `<select id="pday1" name="pday1">${dayOptions(dd[0])}</select>`)}
      <div id="pDay2Wrap">${field("pday2","and the", `<select id="pday2" name="pday2">${dayOptions(dd[1])}</select>`)}</div></div>
    <label class="chip" style="align-self:flex-start;cursor:pointer"><input type="checkbox" name="pweekend" ${d.weekend ? "checked" : ""} style="accent-color:var(--accent)"> If it lands on a weekend, it comes the Friday before</label>
    ${footer(p ? "delPayday:" + p.id : "")}`,
  form => {
    const name = val(form, "pname"), amount = parseMoney(val(form, "pamt")), cycle = val(form, "pcycle");
    const who = (form.querySelector("input[name=pwho]:checked") || {}).value;
    if(!name) return fail("pname", "Name it, like Paycheck.");
    if(amount === null) return fail("pamt", "Enter an amount like 2400 or 2,400.50.");
    if(!PAY_CYCLES[cycle]) return fail("pcycle", "Pick how often it comes.");
    if(!HUMANS.includes(who)) return fail("pname", "Pick whose paycheck it is.");
    let days = [], next;
    if(cycle === "weekly" || cycle === "biweekly"){
      next = val(form, "pnext");
      if(!isDate(next)) return fail("pnext", "Pick the date of your next payday.");
      if(diffDays(todayStr(), next) < -31) return fail("pnext", "Pick your next payday (it can't be more than a month ago).");
    } else {
      const a = clampInt(val(form, "pday1"), 1, 31, 0), b = clampInt(val(form, "pday2"), 1, 31, 0);
      days = cycle === "monthly" ? [a] : [a, b].sort((x, y) => x - y);
      if(!a || (cycle === "semimonthly" && (!b || a === b))) return fail(cycle === "monthly" ? "pday1" : "pday2", "Pick two different days.");
      const same = p && p.cycle === cycle && JSON.stringify(p.days) === JSON.stringify(days);
      next = same ? p.next : payByDays(days, todayStr(), false);   // keep your place unless the days changed
    }
    const data = {name, amount, who, cycle, next, days, weekend: form.elements.pweekend.checked};
    if(p) Object.assign(p, data); else state.budget.paydays.push(Object.assign({id:uid()}, data));
    save(); closeSheet(); render(); toast(`Saved · next payday ${niceDate(payActual(data, next))}`);
  });
  const sync = () => { const c = val($("#sheetForm"), "pcycle"); $("#pDateBox").hidden = !(c === "weekly" || c === "biweekly"); $("#pDaysBox").hidden = !(c === "semimonthly" || c === "monthly"); $("#pDay2Wrap").hidden = c !== "semimonthly"; };
  $("#pcycle").addEventListener("change", sync); sync();
}
const BUDGET_ACTIONS = {""")
rep("""  editCat: id => catForm(id || null),
  editBill: id => billForm(id || null),""",
    """  editCat: id => catForm(id || null),
  editBill: id => billForm(id || null),
  editPayday: id => paydayForm(id || null),
  gotPay: id => { const p = state.budget.paydays.find(x => x.id === id); if(!p) return;
    const t = todayStr(), a = payActual(p, p.next), prev = p.next, date = a > t ? t : a;
    const tx = {id:uid(), kind:"income", amount:p.amount, date, note:p.name, paidBy:p.who, shared:false, categoryId:null, billId:null, paydayId:p.id};
    state.budget.txns.push(tx); p.next = payAfter(p, p.next); budgetMonth = date.slice(0, 7); save(); render();
    toast(`${money(p.amount)} logged · next payday ${niceDate(payActual(p, p.next))}`, () => { state.budget.txns = state.budget.txns.filter(x => x.id !== tx.id); p.next = prev; save(); render(); }); },""")
rep("""  delBill: id => removeBy(state.budget.bills, id) && "Bill deleted",""",
    """  delBill: id => removeBy(state.budget.bills, id) && "Bill deleted",
  delPayday: id => removeBy(state.budget.paydays, id) && "Paycheck removed · income you already logged stays",""")

# ---------- calendar ----------
rep("""bill:{label:"Bills", cls:"t-bill"},""", """bill:{label:"Bills", cls:"t-bill"}, payday:{label:"Paydays", cls:"t-pay"},""")
rep(""":root{--t-chore:#2f9c8f;""", """.t-pay{--tc:#3f9a6b}
:root{--t-chore:#2f9c8f;""")
rep("""  state.budget.bills.forEach(b => project(b.nextDue, b.cycle, 0, {type:"bill",""",
    """  state.budget.paydays.forEach(p => payDates(p, from < t ? t : from, to).forEach(x => push(x.date, {type:"payday", title:`Payday: ${p.name} · ${money(p.amount)}`, who:p.who, act:"editPayday", id:p.id})));
  state.budget.bills.forEach(b => project(b.nextDue, b.cycle, 0, {type:"bill",""")

rep('const BUILD = "2026-10-30 · 33";', 'const BUILD = "2026-10-30 · 34";')
open(p, "w").write(s)
print("patched")
