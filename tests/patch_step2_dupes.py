"""Step 2: no duplicate pantry items; warn before saving a duplicate recipe or pantry item.
No stored-data format change (schema stays 7). Usage: python3 patch_step2_dupes.py file.html"""
import sys
p = sys.argv[1]; s = open(p).read()
def rep(old, new):
    global s
    assert s.count(old) == 1, (s.count(old), old[:90])
    s = s.replace(old, new)

# --- shared helper: warn once, let a second Save go through ---
rep('''function val(form, name){''', '''// Shows a duplicate warning under a field the first time; returns true to stop this save.
// Tapping Save again with the same match keeps both. openAct/openId add a button to jump to the existing one.
function warnDuplicate(form, fieldId, matchId, msg, openAct, openId){
  if(form.dataset.dupOk === matchId) return false;
  form.dataset.dupOk = matchId;
  fail(fieldId, msg);
  const f = $("#f-" + fieldId);
  if(f && openAct) f.insertAdjacentHTML("beforeend", `<button type="button" class="link" data-act="${openAct}" data-id="${esc(openId)}" style="align-self:flex-start;padding-left:0">Open the one you have</button>`);
  return true;
}
function val(form, name){''')

# --- recipes ---
rep('''function recipeForm(id, focusPaste, preset){''', '''const titleKey = t => String(t || "").toLowerCase().replace(/['\u2018\u2019`]/g, "").replace(/&/g, " and ").replace(/[^a-z0-9]+/g, " ").trim();
const sourceKey = u => String(u || "").trim().toLowerCase().replace(/^https?:\\/\\//, "").replace(/^www\\./, "").replace(/#.*$/, "").replace(/\\/+$/, "");
// Another recipe with the same name (ignoring case and punctuation) or the same source link
function findDuplicateRecipe(title, source, exceptId){
  const tk = titleKey(title), sk = sourceKey(source);
  for(const x of state.recipes){
    if(x.id === exceptId) continue;
    if(sk && sourceKey(x.source) === sk) return {r:x, why:"from the same link"};
    if(tk && titleKey(x.title) === tk) return {r:x, why:"with this name"};
  }
  return null;
}
function recipeForm(id, focusPaste, preset){''')
rep('''    if(r){ Object.assign(r, data); r.example = false; if(cookState[r.id]) cookState[r.id].target = r.servings; }''',
'''    const unchanged = r && titleKey(r.title) === titleKey(data.title) && sourceKey(r.source) === sourceKey(data.source);   // editing other fields doesn't re-warn
    const dup = unchanged ? null : findDuplicateRecipe(data.title, data.source, r && r.id);
    if(dup && warnDuplicate(form, dup.why === "with this name" ? "rtitle" : "source", dup.r.id, `You already have a recipe ${dup.why}: “${dup.r.title}”. Tap Save again to keep both.`, "openDupRecipe", dup.r.id)) return;
    if(r){ Object.assign(r, data); r.example = false; if(cookState[r.id]) cookState[r.id].target = r.servings; }''')
rep('''  loadExamples: () => { state.recipes.push(...exampleRecipes()); save(); render(); toast("Added 2 example recipes"); },''',
'''  loadExamples: () => { const add = exampleRecipes().filter(x => !findDuplicateRecipe(x.title, "", null));
    if(!add.length){ toast("The example recipes are already here"); return; }
    state.recipes.push(...add); save(); render(); toast(`Added ${add.length} example recipe${add.length === 1 ? "" : "s"}`); },
  openDupRecipe: id => { closeSheet(); recipeView(id); },''')

# --- pantry: putting groceries away merges into what's already there ---
rep('''  putAway: () => { const done = state.grocery.filter(g => g.checked); let n = 0;
    done.forEach(g => { if(g.aisle === "Household" || g.aisle === "Pet") return; state.pantry.push({id:uid(), name:g.name, qty:g.qty, room:guessRoom(g.aisle, g.name), expires:"", example:false}); n++; });
    state.grocery = state.grocery.filter(g => !g.checked); save(); render(); toast(n ? `Put ${n} away in the pantry` : "Cleared"); },''',
'''  putAway: () => { const done = state.grocery.filter(g => g.checked); let added = 0, merged = 0, other = 0;
    const before = {grocery: JSON.parse(JSON.stringify(state.grocery)), pantry: JSON.parse(JSON.stringify(state.pantry))};
    done.forEach(g => {
      if(g.aisle === "Household" || g.aisle === "Pet"){ other++; return; }     // not food: checked off, not stored
      const have = state.pantry.find(p => normName(p.name) === normName(g.name));
      if(have){ have.qty = mergeQty(have.qty, g.qty); have.example = false; merged++; return; }
      state.pantry.push({id:uid(), name:g.name, qty:g.qty, room:guessRoom(g.aisle, g.name), expires:"", example:false}); added++; });
    state.grocery = state.grocery.filter(g => !g.checked); save(); render();
    const msg = [added && `${added} put away`, merged && `${merged} added to what you had`, other && `${other} household or pet item${other === 1 ? "" : "s"} cleared`].filter(Boolean).join(" · ");
    toast(msg || "Cleared", () => { state.grocery = before.grocery; state.pantry = before.pantry; save(); render(); }); },''')
rep('''    const data = {name, qty:val(form,"pqty"), room:rm, expires:exp};
    if(p){''', '''    const data = {name, qty:val(form,"pqty"), room:rm, expires:exp};
    const same = p && normName(p.name) === normName(name) ? null : state.pantry.find(x => x !== p && normName(x.name) === normName(name));
    if(same && warnDuplicate(form, "pname", same.id, `“${same.name}” is already in ${ROOMS[same.room]}${same.qty ? ` (${same.qty})` : ""}. Tap Save again to add a second entry.`, "openDupPantry", same.id)) return;
    if(p){''')
rep('''  newPantry: () => pantryForm(null),''', '''  newPantry: () => pantryForm(null),
  openDupPantry: id => { const x = state.pantry.find(q => q.id === id); if(!x) return; closeSheet(); prefs.pantryRoom = x.room; savePrefs(); render(); pantryForm(id); },''')
open(p, 'w').write(s)
print("patched", p)
