"""Step 13: ease-of-use fixes + comments on the meal plan.
Fixes (reported): Add event uses the day you're looking at; tapping a day from the next/previous
month on the month calendar goes to that month; Board (and See spending) open the right sub-tab;
the "Tell X? Notify" pop-up goes away when you move to another page or open a form.
Fixes (found while looking): Plan a meal starts on the week you're viewing; adding a chore that the
current filter hides switches the filter so you see it; adding a pantry item to another room switches
to that room; the status speech bubble's style was leaking onto note replies (renamed the class).
New: comments on planned meals (data: meal.comments = [{id, by, text, at}], additive, older records
just have none). Comments notify the other phone right away, like note replies (only if they opted in).
Usage: python3 patch_step13_qol.py file.html"""
import sys
p = sys.argv[1]; s = open(p).read()
def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (s.count(old), old[:90])
    s = s.replace(old, new)

# ---------- status bubble: own class name (was colliding with note replies' .bub) ----------
rep(".bub{position:relative;display:inline-block;", ".sbub{position:relative;display:inline-block;")
rep('.bub::before{content:"";position:absolute;left:-9px;', '.sbub::before{content:"";position:absolute;left:-9px;')
rep('.bub::after{content:"";position:absolute;left:-5px;', '.sbub::after{content:"";position:absolute;left:-5px;')
rep('<br><span class="bub">${esc(p.status.text)}</span>', '<br><span class="sbub">${esc(p.status.text)}</span>')
rep('<br><span class="bub">${esc(st.text)}</span>', '<br><span class="sbub">${esc(st.text)}</span>')

# ---------- 1. Add event starts on the day you're looking at ----------
rep("  newEvent: id => eventForm(null, isDate(id) ? id : null),",
"""  newEvent: id => eventForm(null, isDate(id) ? id : calDefaultDay()),""")
rep("const curCalMonth = () => calMonth || (calMonth = todayStr().slice(0, 7));",
"""const curCalMonth = () => calMonth || (calMonth = todayStr().slice(0, 7));
// The day a new event should start on: the selected day in Month, the first day you can see in Week
// (today if today is on screen).
function calDefaultDay(){
  const t = todayStr();
  if(prefs.todayView === "month"){ const k = curCalMonth(); return calDay && calDay.slice(0, 7) === k ? calDay : (t.slice(0, 7) === k ? t : k + "-01"); }
  if(prefs.todayView === "week"){ const ws = curCalWeek(); return t >= ws && t <= addDays(ws, 6) ? t : ws; }
  return t;
}""")

# ---------- 2. tapping a day from the next/previous month goes there ----------
rep("  calPick: id => { if(isDate(id)){ calDay = id; render(); } },",
    "  calPick: id => { if(isDate(id)){ calDay = id; calMonth = id.slice(0, 7); render(); } },")

# ---------- 3. links that should land on a sub-tab ----------
rep("""<span class="label">Pinned notes</span><button class="link" type="button" data-act="tab" data-id="more">Board</button>""",
    """<span class="label">Pinned notes</span><button class="link" type="button" data-act="goTo" data-id="more/notes">Board</button>""")
rep("""      <button type="button" class="link" data-act="tab" data-id="budget">See spending</button></div></div></section>`;""",
    """      <button type="button" class="link" data-act="goTo" data-id="budget/spending">See spending</button></div></div></section>`;""")
rep("  tab: id => { prefs.tab = id; savePrefs(); render(); window.scrollTo(0,0); },",
"""  tab: id => { prefs.tab = id; savePrefs(); render(); window.scrollTo(0,0); },
  // "tab/subtab", e.g. more/notes: open a tab on a particular sub-tab
  goTo: id => { const [t, sub] = String(id).split("/"); if(!TABS.some(x => x[0] === t)) return; prefs.tab = t;
    if(t === "more" && MTABS[sub]) prefs.moreTab = sub; if(t === "budget" && BTABS[sub]) prefs.budgetTab = sub; if(t === "kitchen" && KTABS[sub]) prefs.kitchenTab = sub;
    savePrefs(); render(); window.scrollTo(0,0); },""")

# ---------- 4. the Notify pop-up goes away when you go somewhere else ----------
rep("""function render(){
  if(!TABS.some(t => t[0] === prefs.tab)) prefs.tab = "today";""",
"""const navKey = () => [prefs.tab, prefs.kitchenTab, prefs.moreTab, prefs.budgetTab, prefs.todayView, prefs.fam].join("|");
function render(){
  if(!TABS.some(t => t[0] === prefs.tab)) prefs.tab = "today";
  if(typeof notifyQ !== "undefined" && notifyQ.nudgeAt && notifyQ.nudgeAt !== navKey()) nudgeDismiss();""")
rep("""  clearTimeout(nudgeTimer); nudgeTimer = setTimeout(() => { $("#nudgeRoot").innerHTML = ""; notifyQ.nudge = null; }, 9000);
}""",
"""  notifyQ.nudgeAt = navKey();
  clearTimeout(nudgeTimer); nudgeTimer = setTimeout(nudgeDismiss, 9000);
}
function nudgeDismiss(){ clearTimeout(nudgeTimer); $("#nudgeRoot").innerHTML = ""; notifyQ.nudge = null; notifyQ.nudgeAt = null; }""")
rep("""function openSheet(title, inner, onSubmit, autofocus = true){
  lastFocus = document.activeElement;""",
"""function openSheet(title, inner, onSubmit, autofocus = true){
  if(typeof nudgeDismiss === "function" && $("#nudgeRoot").innerHTML) nudgeDismiss();
  lastFocus = document.activeElement;""")
rep("""  nudgeClose: () => { clearTimeout(nudgeTimer); $("#nudgeRoot").innerHTML = ""; notifyQ.nudge = null; },""",
    """  nudgeClose: () => nudgeDismiss(),""")
rep("""  nudgeSend: async () => { const items = notifyQ.nudge || []; clearTimeout(nudgeTimer); $("#nudgeRoot").innerHTML = ""; notifyQ.nudge = null;""",
    """  nudgeSend: async () => { const items = notifyQ.nudge || []; nudgeDismiss();""")

# ---------- 5. Plan a meal starts on the week you're viewing ----------
rep("""plan:["planDinner","Plan a meal"]""", """plan:["planMeal","Plan a meal"]""")
rep("  addMeal: id => mealForm(null, id),",
"""  addMeal: id => mealForm(null, id),
  planMeal: () => { const ws = curWeek(), t = todayStr(); mealForm(null, t >= ws && t <= addDays(ws, 6) ? t : ws); },""")

# ---------- 6. a chore the current filter would hide: switch the filter so you see it ----------
rep("""    else state.chores.push(Object.assign({id:uid(), lastDone:null, history:[], done:false, example:false}, data));
    save(); closeSheet(); render(); toast(c ? "Card saved" : "Card added");""",
"""    else state.chores.push(Object.assign({id:uid(), lastDone:null, history:[], done:false, example:false}, data));
    const fkey = !data.owner ? "none" : data.owner === prefs.user ? "me" : "them";
    const moved = prefs.tab === "chores" && prefs.choreFilter !== "all" && prefs.choreFilter !== fkey;
    if(moved){ prefs.choreFilter = fkey; savePrefs(); }
    save(); closeSheet(); render(); toast((c ? "Card saved" : "Card added") + (moved ? ` · showing ${fkey === "none" ? "unassigned" : nameOf(data.owner) + "'s"} cards` : ""));""")

# ---------- 7. pantry item saved to another room: go to that room ----------
rep("""    save(); closeSheet(); render(); toast(p ? "Saved" : `Added to ${ROOMS[rm]}`);""",
    """    if(prefs.tab === "kitchen" && prefs.pantryRoom !== rm){ prefs.pantryRoom = rm; savePrefs(); }
    save(); closeSheet(); render(); toast(p ? "Saved" : `Added to ${ROOMS[rm]}`);""")

# ---------- 8. comments on planned meals ----------
rep("""    id: m.id ? String(m.id) : uid(), slot: SLOTS[m.slot] ? m.slot : "dinner", recipeId: m.recipeId ? String(m.recipeId) : null, text: str(m.text, 80) }));""",
"""    id: m.id ? String(m.id) : uid(), slot: SLOTS[m.slot] ? m.slot : "dinner", recipeId: m.recipeId ? String(m.recipeId) : null, text: str(m.text, 80),
    comments: (Array.isArray(m.comments) ? m.comments : []).filter(c => c && typeof c === "object" && str(c.text).trim() && HUMANS.includes(c.by))
      .map(c => ({id: c.id ? String(c.id) : uid(), by: c.by, text: str(c.text, 300).trim(), at: Number(c.at) || 0})).slice(-100) }));""")
rep(""".meal .mt{font-weight:600;overflow-wrap:anywhere;min-width:0}""",
""".meal .mt{font-weight:600;overflow-wrap:anywhere;min-width:0;flex:1}
.meal .mc{flex:none;font-size:.78rem;color:var(--muted);font-weight:600;white-space:nowrap}
.mlast{margin:4px 0 0;font-size:.9rem;color:var(--muted)}""")
rep("""<span class="slot">${SLOTS[m.slot]}</span><span class="mt">${esc(mealLabel(m))}</span></button>`).join("")""",
    """<span class="slot">${SLOTS[m.slot]}</span><span class="mt">${esc(mealLabel(m))}</span>${(m.comments || []).length ? `<span class="mc">${m.comments.length} ${m.comments.length === 1 ? "comment" : "comments"}</span>` : ""}</button>`).join("")""")
# meal form: the thread + a comment box
rep("""    ${m && m.recipeId && state.recipes.some(r => r.id === m.recipeId) ? `<button type="button" class="btn ghost small" data-act="openRecipe" data-id="${m.recipeId}" style="align-self:flex-start">Open recipe</button>` : ""}
    ${footer(m ? "delMeal:" + m.id : "")}`,""",
"""    ${m && m.recipeId && state.recipes.some(r => r.id === m.recipeId) ? `<button type="button" class="btn ghost small" data-act="openRecipe" data-id="${m.recipeId}" style="align-self:flex-start">Open recipe</button>` : ""}
    ${m && (m.comments = Array.isArray(m.comments) ? m.comments : []).length ? `<div class="thread" aria-label="Comments">${m.comments.map(c => `<div class="reply"><span class="av ${c.by}">${sprite(c.by)}</span><div class="bub"><p>${esc(c.text)}</p><span class="when"><span>${esc(nameOf(c.by))} · ${new Date(c.at).toLocaleString(undefined,{month:"short",day:"numeric",hour:"numeric",minute:"2-digit"})}</span>${c.by === prefs.user ? `<button type="button" data-act="delMealComment" data-id="${m.id}" data-c="${c.id}" aria-label="Delete comment">Delete</button>` : ""}</span></div></div>`).join("")}</div>` : ""}
    ${field("mcomment", m && m.comments.length ? "Add a comment" : "Comment", `<textarea id="mcomment" name="mcomment" maxlength="300" placeholder="I'll cook! · Can we do 7 instead? · Need anything from the store?"></textarea>`, "Optional. Saved with the meal.")}
    ${footer(m ? "delMeal:" + m.id : "")}`,""")
rep("""    const data = {date, slot, recipeId: rid || null, text};
    if(m) Object.assign(m, data); else state.meals.push(Object.assign({id:uid()}, data));
    planWeek = weekStart(date);
    save(); closeSheet(); render(); toast(m ? "Meal saved" : `Planned for ${parse(date).toLocaleDateString(undefined,{weekday:"long"})}`);""",
"""    const data = {date, slot, recipeId: rid || null, text};
    const note = form.elements.mcomment.value.trim().slice(0, 300);
    const target = m ? Object.assign(m, data) : Object.assign({id:uid(), comments:[]}, data);
    if(!Array.isArray(target.comments)) target.comments = [];
    if(!m) state.meals.push(target);
    if(note) target.comments.push({id:uid(), by:prefs.user, text:note, at:Date.now()});
    planWeek = weekStart(date);
    save(); closeSheet(); render(); toast(note ? "Comment added" : m ? "Meal saved" : `Planned for ${parse(date).toLocaleDateString(undefined,{weekday:"long"})}`);""")
rep("""  delMeal: id => removeBy(state.meals, id) && "Meal removed",""",
"""  delMeal: id => removeBy(state.meals, id) && "Meal removed",""")
rep("  editMeal: id => mealForm(id),",
"""  editMeal: id => mealForm(id),
  delMealComment: (id, el) => { const m = state.meals.find(x => x.id === id); if(!m) return;
    const i = m.comments.findIndex(c => c.id === el.dataset.c && c.by === prefs.user); if(i < 0) return;
    const removed = m.comments.splice(i, 1)[0]; save(); render(); mealForm(id);
    toast("Comment deleted", () => { m.comments.splice(i, 0, removed); save(); render(); if($("#sheetRoot").innerHTML) mealForm(id); }); },""")
# Today's dinner card: latest comment + a way to comment
rep("""      return r ? `<button type="button" class="link dinner-link" data-act="openRecipe" data-id="${r.id}" style="padding-left:0;font-size:1rem">${esc(r.title)} →</button>` : `<p>${esc(mealLabel(m))}</p>`; }).join("")}
    <button type="button" class="link" data-act="goKitchen" data-id="plan" style="padding-left:0">See the week</button></div></section>`;""",
"""      if(!Array.isArray(m.comments)) m.comments = [];
      const last = m.comments[m.comments.length - 1];
      return (r ? `<button type="button" class="link dinner-link" data-act="openRecipe" data-id="${r.id}" style="padding-left:0;font-size:1rem">${esc(r.title)} →</button>` : `<p>${esc(mealLabel(m))}</p>`)
        + (last ? `<p class="mlast"><b>${esc(nameOf(last.by))}:</b> ${esc(last.text)}${m.comments.length > 1 ? ` <span class="small">(+${m.comments.length - 1} more)</span>` : ""}</p>` : "")
        + `<button type="button" class="link" data-act="editMeal" data-id="${m.id}" style="padding-left:0">${m.comments.length ? "Reply" : "Comment"}</button>`; }).join("")}
    <button type="button" class="link" data-act="goKitchen" data-id="plan" style="padding-left:0">See the week</button></div></section>`;""")
# notifications: a comment goes out right away, like a note reply
rep("""  if(kind === "meal"){ if(!n || o) return null;""",
"""  if(kind === "meal"){
    if(n && o && (n.comments || []).length > (o.comments || []).length){ const c = n.comments[n.comments.length - 1];
      return `commented on ${parse(n.date).toLocaleDateString(undefined, {weekday:"long"})}'s ${SLOTS[n.slot].toLowerCase()}: “${clip(c && c.text, 50)}”`; }
    if(!n || o) return null;""")
rep("""    if(d){ if(w.id.startsWith("note~")) notifyQ.items.push(d); else nudges.push(d); }""",
    """    if(d){ if(w.id.startsWith("note~") || d.startsWith("commented on ")) notifyQ.items.push(d); else nudges.push(d); }""")
rep("""New notes and replies right away, plus""", """New notes, replies and meal comments right away, plus""")

open(p, "w").write(s)
print("step 13 applied")
