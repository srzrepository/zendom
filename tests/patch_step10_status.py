"""Step 10: form fixes + Today follows who's signed in + statuses.
- Radio/checkbox chips no longer stretch to full input size (giant circles on iPhone).
- Date/time boxes stay inside their column on iPhone.
- iPhone home-screen app: no rubber-band bounce (it dragged the bottom bar), bar hides while typing.
- Today always shows the signed-in person. Top-right Sam/Charlie open their Family profile.
  Signed-out phones pick "whose phone is this" in Settings.
- Each person can set a status (emoji + few words). Stored on their person record as
  status:{emoji,text,at}. Additive: older copies keep it untouched (normalize keeps unknown
  fields), so no schema bump. Status changes never trigger a notification.
Usage: python3 patch_step10_status.py file.html"""
import sys
p = sys.argv[1]; s = open(p).read()
def rep(old, new):
    global s
    assert s.count(old) == 1, (s.count(old), old[:90])
    s = s.replace(old, new)

# ---------- CSS ----------
rep(".two > *{min-width:0}\n", """.two > *{min-width:0}
/* radio + checkbox chips: the .field input rule must not turn the little circle into a full-size box */
.chip > input:is([type=radio],[type=checkbox]){width:20px;height:20px;min-height:0;padding:0;margin:0;border:0;flex:none;background:none;box-shadow:none}
.chip:has(> input:checked){color:var(--ink);background:var(--surface);box-shadow:inset 0 0 0 2px var(--accent)}
/* iPhone: date and time boxes have a wide built-in minimum; let them shrink to their column */
@supports (-webkit-touch-callout:none){
  input[type=date],input[type=time]{-webkit-appearance:none;appearance:none;min-width:0;max-width:100%;display:block}
  input::-webkit-date-and-time-value{text-align:left}
}
/* home-screen app: no whole-page bounce (it dragged the bottom bar along) */
html,body{overscroll-behavior-y:none}
body.typing .nav,body.typing .fab{display:none}
/* status */
.who button{position:relative}
.who .st{position:absolute;left:16px;top:-3px;font-size:.78rem;line-height:1;filter:drop-shadow(0 1px 0 var(--bg))}
.status-card{display:flex;flex-direction:column;gap:8px}
.strow{display:flex;align-items:center;gap:10px;width:100%;text-align:left;border:0;background:transparent;padding:2px 0;color:inherit}
.strow .av{width:34px;height:34px;border-radius:10px;overflow:hidden;flex:none;background:var(--surface-2)}
.strow .tx{flex:1;min-width:0}
.strow .tx b{display:block}
.strow .tx span{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.emopick{display:flex;flex-wrap:wrap;gap:6px}
.emopick label{width:42px;height:42px;display:grid;place-items:center;font-size:1.3rem;border-radius:4px;box-shadow:inset 0 0 0 2px var(--line);background:var(--surface);cursor:pointer;position:relative}
.emopick input{position:absolute;opacity:0;inset:0;margin:0;width:100%;height:100%;min-height:0;padding:0}
.emopick label:has(input:checked){box-shadow:inset 0 0 0 3px var(--accent);background:var(--bg)}
.emopick label:has(input:focus-visible){outline:3px solid var(--accent);outline-offset:2px}
.profstatus{margin:4px 0 0;font-size:.95rem}
""")

# ---------- data: keep a tidy status on each human ----------
rep("""    p.vaccines = objs(p.vaccines).map(v => Object.assign(v, {name:str(v.name,80), date: isDate(v.date)?v.date:"", nextDue: isDate(v.nextDue)?v.nextDue:""})).filter(v => v.name.trim());
    out.people[k] = p;""",
"""    p.vaccines = objs(p.vaccines).map(v => Object.assign(v, {name:str(v.name,80), date: isDate(v.date)?v.date:"", nextDue: isDate(v.nextDue)?v.nextDue:""})).filter(v => v.name.trim());
    if(p.kind !== "cat"){ const st = (p.status && typeof p.status === "object") ? p.status : {};
      p.status = {emoji: str(st.emoji, 16).trim(), text: str(st.text, 80).trim(), at: Math.max(0, Number(st.at) || 0)}; }
    out.people[k] = p;""")

# ---------- top bar: shortcuts to Family, with the status emoji ----------
rep("""  $("#who").innerHTML = HUMANS.map(k => `<button type="button" data-act="setUser" data-id="${k}" aria-pressed="${prefs.user===k}"><span class="av">${sprite(k)}</span><span class="nm">${esc(nameOf(k))}</span></button>`).join("");""",
"""  $("#who").innerHTML = HUMANS.map(k => { const st = state.people[k].status;
    return `<button type="button" data-act="goFam" data-id="${k}" aria-label="${esc(nameOf(k))}'s profile${st.text || st.emoji ? ": " + esc((st.emoji + " " + st.text).trim()) : ""}"><span class="av">${sprite(k)}</span>${st.emoji ? `<span class="st" aria-hidden="true">${esc(st.emoji)}</span>` : ""}<span class="nm">${esc(nameOf(k))}</span></button>`; }).join("");""")
rep('<div class="who" role="group" aria-label="Who is using the app" id="who"></div>', '<div class="who" role="group" aria-label="Profiles" id="who"></div>')

# ---------- Today: status card under the room ----------
rep("""    ${roomHTML()}
  </section>

  <section class="sec">
    <div class="sec-head"><span class="label">Up next for you</span>""",
"""    ${roomHTML()}
  </section>

  ${statusCardHTML(me)}

  <section class="sec">
    <div class="sec-head"><span class="label">Up next for you</span>""")

# ---------- Family profile: status line ----------
rep("""      <div style="min-width:0;flex:1"><h2>${esc(p.name)}</h2><div class="muted small">${cat ? "Our cat" : (k==="sam" ? "Samantha Zenteno" : "Charlie Purdom")}</div>
      <button class="link" type="button" data-act="editBasics" style="padding-left:0">Edit details</button></div></div>""",
"""      <div style="min-width:0;flex:1"><h2>${esc(p.name)}</h2><div class="muted small">${cat ? "Our cat" : (k==="sam" ? "Samantha Zenteno" : "Charlie Purdom")}</div>
      ${cat ? "" : `<p class="profstatus">${p.status.text || p.status.emoji ? `${esc(p.status.emoji)} ${esc(p.status.text)} <span class="muted small">· ${esc(sinceText(p.status.at))}</span>` : `<span class="muted small">No status set</span>`}</p>`}
      <button class="link" type="button" data-act="editBasics" style="padding-left:0">Edit details</button>${!cat && k === prefs.user ? ` <button class="link" type="button" data-act="setStatus">Change status</button>` : ""}</div></div>""")

# ---------- Settings: whose phone (only matters when signed out) ----------
rep("""  return `<section class="sec"><span class="label">Look &amp; feel</span>
    <div class="card" style="display:flex;flex-direction:column;gap:14px">""",
"""  const signedWho = sync.user ? Object.keys(ACCOUNTS).find(k => ACCOUNTS[k].includes(sync.user.email)) : null;
  return `<section class="sec"><span class="label">Look &amp; feel</span>
    <div class="card" style="display:flex;flex-direction:column;gap:14px">
      <div class="setrow"><div><b>Whose phone is this?</b><div class="small muted">${signedWho ? `Signed in as ${esc(nameOf(signedWho))}, so Today shows ${esc(nameOf(signedWho))}'s day.` : "Today shows this person's chores and greeting. Signing in sets it for you."}</div></div>
        ${signedWho ? "" : `<div class="seg" role="group" aria-label="Whose phone">${HUMANS.map(k => `<button type="button" class="chip" data-act="setUser" data-id="${k}" aria-pressed="${prefs.user===k}">${esc(nameOf(k))}</button>`).join("")}</div>`}</div>""")

# ---------- actions ----------
rep("  setUser: id => { prefs.user = id; savePrefs(); render(); },",
"""  setUser: id => { if(!HUMANS.includes(id)) return;
    const signed = sync.user && Object.keys(ACCOUNTS).find(k => ACCOUNTS[k].includes(sync.user.email));
    if(signed && signed !== id){ toast(`This phone is signed in as ${nameOf(signed)}`); return; }
    prefs.user = id; savePrefs(); render(); },
  setStatus: () => statusForm(),
  statusPreset: (id, el) => { const f = el.closest("form"); if(!f) return; const t = f.elements.stext; t.value = el.dataset.text || "";
    const r = f.querySelector(`input[name=semoji][value="${CSS.escape(el.dataset.emoji || "")}"]`); if(r) r.checked = true; t.focus(); },
  clearStatus: () => { const p = state.people[prefs.user]; p.status = {emoji:"", text:"", at:Date.now()}; save(); closeSheet(); render(); toast("Status cleared"); },""")

# ---------- status helpers + sheet ----------
rep("function allergyForm(){", r"""const STATUS_EMOJI = ["🙂","😴","🎧","💼","🛒","🍳","🏃","🎮","📚","🤒","🔋","🫠","🎉","❤️","🐱",""];
const STATUS_PRESETS = [["💼","At work"],["🎧","Heads down, focusing"],["😴","Napping"],["🔋","Low battery, need quiet"],["🛒","Out running errands"],["🙂","Free, come say hi"]];
function sinceText(ts){
  if(!ts) return "";
  const m = Math.round((Date.now() - ts) / 60000);
  if(m < 1) return "just now"; if(m < 60) return `${m} min ago`;
  const h = Math.round(m / 60); if(h < 24) return `${h} hr ago`;
  const d = Math.round(h / 24); return d === 1 ? "yesterday" : `${d} days ago`;
}
function statusCardHTML(me){
  const row = (k, mine) => { const st = state.people[k].status, has = st.text || st.emoji;
    return `<button type="button" class="strow" data-act="${mine ? "setStatus" : "goFam"}" data-id="${k}"><span class="av">${sprite(k)}</span>
      <span class="tx"><b>${mine ? "You" : esc(nameOf(k))}</b><span class="${has ? "" : "muted"}">${has ? `${esc(st.emoji)} ${esc(st.text)}` : (mine ? "Tap to set a status" : "No status")}</span></span>
      <span class="muted small">${has ? esc(sinceText(st.at)) : ""}</span></button>`; };
  return `<section class="card status-card" aria-label="Statuses">${row(me, true)}${row(other(me), false)}</section>`;
}
function statusForm(){
  const k = prefs.user, st = state.people[k].status;
  openSheet("Your status", `
    <div class="field"><span class="lab">Pick an emoji</span><div class="emopick" role="radiogroup" aria-label="Emoji">${STATUS_EMOJI.map(e => `<label title="${e || "No emoji"}"><input type="radio" name="semoji" value="${e}" ${st.emoji === e ? "checked" : ""} aria-label="${e || "No emoji"}">${e || "–"}</label>`).join("")}</div></div>
    ${field("stext", "What's up?", `<input id="stext" name="stext" maxlength="80" value="${esc(st.text)}" placeholder="e.g. Heads down until 3" autocomplete="off">`, "Just for fun. It doesn't send a notification.")}
    <div class="seg">${STATUS_PRESETS.map(([e, t]) => `<button type="button" class="chip" data-act="statusPreset" data-emoji="${e}" data-text="${esc(t)}">${e} ${esc(t)}</button>`).join("")}</div>
    <div class="actions">${st.text || st.emoji ? `<button type="button" class="btn ghost small" data-act="clearStatus">Clear status</button>` : "<span></span>"}
      <div class="r"><button type="button" class="btn ghost" data-act="closeSheet">Cancel</button><button type="submit" class="btn">Save</button></div></div>`,
  form => {
    const text = val(form, "stext").slice(0, 80), r = form.querySelector("input[name=semoji]:checked");
    const emoji = r && STATUS_EMOJI.includes(r.value) ? r.value : "";
    if(!text && !emoji) return fail("stext", "Pick an emoji or type a few words, or tap Clear status.");
    state.people[k].status = {emoji, text, at: Date.now()};
    save(); closeSheet(); render(); toast("Status updated");
  }, false);
}

function allergyForm(){""")

# ---------- notifications: a status (or look) change is not "updated the profile" ----------
rep("""  if(kind === "person"){ if(!n || !o || JSON.stringify(n) === JSON.stringify(o)) return null;""",
"""  if(kind === "person"){ const core = x => Object.assign({}, x, {status:null, outfit:null}); if(!n || !o || JSON.stringify(core(n)) === JSON.stringify(core(o))) return null;""")

# ---------- hide the bottom bar while typing (iPhone keyboard pushes fixed bars around) ----------
rep("""document.addEventListener("click", e => {             // tap Paprika for a heart""",
"""const TYPING_SEL = "input:not([type=radio]):not([type=checkbox]):not([type=range]):not([type=file]),textarea,select";
document.addEventListener("focusin", e => { if(e.target.matches && e.target.matches(TYPING_SEL)) document.body.classList.add("typing"); });
document.addEventListener("focusout", () => setTimeout(() => { const a = document.activeElement; if(!(a && a.matches && a.matches(TYPING_SEL))) document.body.classList.remove("typing"); }, 60));
document.addEventListener("click", e => {             // tap Paprika for a heart""")

open(p, "w").write(s)
print("step 10 applied")
