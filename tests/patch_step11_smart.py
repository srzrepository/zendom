"""Step 11: two small "smart" helpers. Both work on the phone, from words and numbers already in
the app: no AI service, no account.
1. Pay-back to-do: when shared spending leaves one of you owing the other, the person who owes
   sees "Pay X back $N" on their Today, with Venmo (if set up) and "I paid". It is worked out
   from the Budget balance every time, so it is never stored, can't duplicate, and goes away
   once a payment is recorded. The morning reminder mentions it too.
2. Health visit spotting: saving a NEW calendar event whose title sounds medical (dentist, eye
   exam, dermatology, physical, doctor, vet...) asks whether to add it to someone's health
   history. Upcoming: it becomes that checkup's booked appointment (and leaves the plain
   calendar list, since health appointments already show on the calendar). Past or today: it
   logs the visit date. Nothing is added without a tap, and it can be undone.
No stored-data change. Usage: python3 patch_step11_smart.py file.html"""
import sys
p = sys.argv[1]; s = open(p).read()
def rep(old, new):
    global s
    assert s.count(old) == 1, (s.count(old), old[:90])
    s = s.replace(old, new)

# ---------- 1. pay-back card on Today ----------
rep("""  ${statusCardHTML(me)}
""", """  ${statusCardHTML(me)}
  ${payBackHTML(me)}
""")
rep("function monthStats(k){", r"""// Who owes whom right now, as a to-do for the person who owes. Null when even.
function owed(){
  const b = balance(); if(!b) return null;
  return b > 0 ? {from:"charlie", to:"sam", cents:b} : {from:"sam", to:"charlie", cents:-b};
}
function payBackHTML(me){
  const o = owed(); if(!o || o.from !== me) return "";
  const v = (state.budget.venmo || {})[o.to];
  return `<section class="card soon-card payback"><span class="ic">${IC.budget}</span><div style="flex:1;min-width:0">
    <h3>Pay ${esc(nameOf(o.to))} back ${money(o.cents)}</h3><p>Your half of shared spending. This goes away when you record the payment.</p>
    <div class="actions" style="margin-top:8px;justify-content:flex-start">${v ? `<a class="btn ghost small" href="${esc(venmoLink(v, o.cents))}" target="_blank" rel="noopener">Venmo</a>` : ""}
      <button type="button" class="btn small" data-act="settleUp">I paid</button>
      <button type="button" class="link" data-act="tab" data-id="budget">See spending</button></div></div></section>`;
}
function monthStats(k){""")

# ---------- 2. health visit spotting ----------
rep("""    if(e) Object.assign(e, data); else state.events.push(Object.assign({id:uid()}, data));
    calDay = date; calMonth = date.slice(0, 7);""",
"""    let added = null;
    if(e) Object.assign(e, data); else { added = Object.assign({id:uid()}, data); state.events.push(added); }
    calDay = date; calMonth = date.slice(0, 7);""")
rep("""    save(); closeSheet(); render(); toast(e ? "Event saved" : `Added to ${parse(date).toLocaleDateString(undefined,{weekday:"long", month:"short", day:"numeric"})}`);
  });
}""",
"""    save(); closeSheet(); render(); toast(e ? "Event saved" : `Added to ${parse(date).toLocaleDateString(undefined,{weekday:"long", month:"short", day:"numeric"})}`);
    if(added && healthGuess(added.title)) healthPrompt(added.id);
  });
}
// Does an event title sound like a health visit? Returns {name, who} or null. Plain word matching:
// it will miss some and wrongly suggest others, which is why it always asks.
const HEALTH_WORDS = [
  [/\\b(vet|vets|veterinar\\w*)\\b/i, "Wellness exam", "paprika"],
  [/\\b(dentist|dental|teeth|hygienist|orthodont\\w*)\\b/i, "Dentist cleaning"],
  [/\\b(eye exam|eye doctor|optometr\\w*|ophthalm\\w*|vision)\\b/i, "Eye exam"],
  [/\\b(derm|dermatolog\\w*|skin check)\\b/i, "Dermatology"],
  [/\\b(physical|annual exam|check-?up|wellness visit|primary care|pcp)\\b/i, "Physical"],
  [/(\\bdr\\.?\\s|\\bdoctor\\b|\\bclinic\\b|\\bob-?gyn\\b|\\bgyn\\w*|\\burgent care\\b|\\blab work\\b|\\bblood ?work\\b|\\bx-?ray\\b|\\bmri\\b|\\bspecialist\\b|\\bphysio\\w*|\\bcardiolog\\w*|\\baudiolog\\w*|\\bdermatolog\\w*)/i, ""]
];
function healthGuess(title){
  const t = String(title || "");
  for(const [re, name, who] of HEALTH_WORDS){ if(re.test(t)) return {name: name || t.replace(/\\s+/g, " ").trim().slice(0, 80), who: who || null}; }
  return null;
}
const sameName = (a, b) => a.toLowerCase().replace(/['’]/g, "").trim() === b.toLowerCase().replace(/['’]/g, "").trim();
function healthPrompt(eventId){
  const ev = state.events.find(x => x.id === eventId); if(!ev) return;
  const g = healthGuess(ev.title); if(!g) return;
  const named = PEOPLE.find(k => new RegExp("\\\\b" + nameOf(k).replace(/[.*+?^${}()|[\\]\\\\]/g, "\\\\$&") + "\\\\b", "i").test(ev.title));
  const who = g.who || named || ev.who || prefs.user;
  const upcoming = ev.date >= todayStr() && !(ev.date === todayStr() && ev.time && ev.time < new Date().toTimeString().slice(0, 5));
  const when = parse(ev.date).toLocaleDateString(undefined, {weekday:"short", month:"short", day:"numeric"});
  openSheet("Add to health history?", `
    <p style="margin:0">“${esc(ev.title)}” on ${esc(when)} sounds like a health visit.</p>
    <div class="field"><span class="lab">Whose?</span><div class="seg" role="radiogroup">${PEOPLE.map(k => `<label class="chip" style="cursor:pointer"><input type="radio" name="hwho" value="${k}" ${who === k ? "checked" : ""}> ${esc(nameOf(k))}</label>`).join("")}</div></div>
    ${field("hname", "Kind of visit", `<input id="hname" name="hname" maxlength="80" value="${esc(g.name)}" autocomplete="off">`, upcoming ? "It becomes the booked appointment for this checkup, and stays on the calendar." : "It's logged as their last visit.")}
    <div class="actions"><span></span><div class="r"><button type="button" class="btn ghost" data-act="closeSheet">Not now</button><button type="submit" class="btn">Add</button></div></div>`,
  form => {
    const k = (form.querySelector("input[name=hwho]:checked") || {}).value, name = val(form, "hname");
    if(!PEOPLE.includes(k)) return fail("hname", "Pick whose visit it is.");
    if(!name) return fail("hname", "Name the visit, like Dentist cleaning.");
    const p = state.people[k], before = JSON.stringify(p.checkups), evBefore = JSON.stringify(state.events);
    let c = p.checkups.find(x => sameName(x.name, name));
    if(!c){ c = {id:uid(), name, months:12, last:"", provider:"", next:null}; p.checkups.push(c); }
    let msg;
    if(upcoming){
      c.next = {date: ev.date, time: ev.time, where: (ev.note || "").slice(0, 120)};
      removeBy(state.events, ev.id);
      msg = `Booked in ${p.name}'s health history`;
    } else {
      if(!c.last || ev.date > c.last) c.last = ev.date;
      if(c.next && c.next.date === ev.date) c.next = null;
      msg = `Logged in ${p.name}'s health history`;
    }
    save(); closeSheet(); render();
    toast(msg, () => { p.checkups = JSON.parse(before); state.events = JSON.parse(evBefore); save(); render(); });
  }, false);
}""")

rep(".chip > input:is([type=radio],[type=checkbox]){width:20px;", ".chip > input:is([type=radio],[type=checkbox]){accent-color:var(--accent);width:20px;")

open(p, "w").write(s)
print("step 11 applied")
