"""Step 38: with both phones open, an edit form no longer undoes the other person's changes.
Before: a form that was open while the other phone changed the same item saved every field as it was
when the form opened, so their change was quietly put back (e.g. Charlie set an amount, Sam saved a
note change, Charlie's amount was lost).
Now each edit form remembers the item as it was when it opened, and Save writes only the fields you
changed; everything else keeps whatever the other phone saved. If you both changed the same field,
yours is kept and a note says the other person had changed it too.
Covers every edit form: spending/income, payments, categories, bills, paychecks, events, Fun Fund
entries and goals, chores, notes, recipes, meals, grocery and pantry items, meds, checkups, vaccines.
No data change. Usage: python3 patch_step38_keep_their_changes.py file.html"""
import sys
p = sys.argv[1]; s = open(p).read()
def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (s.count(old), old[:100])
    s = s.replace(old, new)

rep("""function removeBy(arr, id){""", r"""/* ---- edit forms: save only what you changed ---- */
const sameVal = (a, b) => JSON.stringify(a === undefined ? null : a) === JSON.stringify(b === undefined ? null : b);
// Call when an edit form opens on an existing item: remembers it as it was.
function editStart(o){ editStart.obj = o || null; editStart.base = o ? JSON.parse(JSON.stringify(o)) : null; }
// Write a form's values into the item, but only the fields the form changed. Returns the fields that the
// other phone had also changed meanwhile (yours win; a note says so).
function applyEdit(o, data){
  const base = editStart.obj === o ? editStart.base : null, both = [];
  Object.keys(data).forEach(k => {
    if(base && sameVal(data[k], base[k])) return;                       // you didn't change it: keep what's there now
    if(base && !sameVal(o[k], base[k]) && !sameVal(o[k], data[k])) both.push(k);
    o[k] = data[k];
  });
  if(both.length) setTimeout(() => toast(`${nameOf(other(prefs.user))} had changed this too while you were editing. Your changes were kept.`), 1900);
  return both;
}
function removeBy(arr, id){""")

# remember the item when each edit form opens
opens = [
  ("""  const r = id ? state.recipes.find(x => x.id === id) : null; if(id && !r) return;""", "r"),
  ("""  const m = id ? state.meals.find(x => x.id === id) : null; if(id && !m) return;""", "m"),
  ("""  const g = state.grocery.find(x => x.id === id); if(!g) return;""", "g"),
  ("""  const p = id ? state.pantry.find(x => x.id === id) : null; if(id && !p) return;""", "p"),
  ("""  const t = id ? state.budget.txns.find(x => x.id === id) : null; if(id && !t) return;
  if(t && t.kind === "settle") return settleForm(t.id);""", "t"),
  ("""  const t = id ? state.budget.txns.find(x => x.id === id) : null;
  const bal = balance();""", "t"),
  ("""  const c = id ? state.budget.categories.find(x => x.id === id) : null; if(id && !c) return;""", "c"),
  ("""  const b = id ? state.budget.bills.find(x => x.id === id) : null; if(id && !b) return;""", "b"),
  ("""  const p = id ? state.budget.paydays.find(x => x.id === id) : null; if(id && !p) return;""", "p"),
  ("""  const e = id ? state.events.find(x => x.id === id) : null; if(id && !e) return;""", "e"),
  ("""  const f = fund(), e = id ? f.entries.find(x => x.id === id) : null; if(id && !e) return;""", "e"),
  ("""  const g = id ? fund().goals.find(x => x.id === id) : null; if(id && !g) return;""", "g"),
  ("""  const c = id ? state.chores.find(x => x.id === id) : null;
  if(id && !c) return;""", "c"),
  ("""  const n = id ? state.notes.find(x => x.id === id) : null; if(id && !n) return;""", "n"),
  ("""  const p = state.people[prefs.fam]; const m = id ? p.meds.find(x => x.id === id) : null; if(id && !m) return;""", "m"),
  ("""  const p = state.people[prefs.fam]; const c = id ? p.checkups.find(x => x.id === id) : null; if(id && !c) return;""", "c"),
  ("""  const p = state.people[prefs.fam]; const v = id ? p.vaccines.find(x => x.id === id) : null; if(id && !v) return;""", "v"),
]
for old, var in opens:
    rep(old, old + f" editStart({var});")

# save only what changed
saves = [
  ("""    if(r){ Object.assign(r, data); r.example = false;""", """    if(r){ applyEdit(r, data); r.example = false;"""),
  ("""    const target = m ? Object.assign(m, data) : Object.assign({id:uid(), comments:[]}, data);""", """    const target = m ? (applyEdit(m, data), m) : Object.assign({id:uid(), comments:[]}, data);"""),
  ("""    Object.assign(g, {name, qty:val(form,"gqty"), aisle: AISLES.includes(aisle) ? aisle : "Other"});""", """    applyEdit(g, {name, qty:val(form,"gqty"), aisle: AISLES.includes(aisle) ? aisle : "Other"});"""),
  ("""    if(p){ Object.assign(p, data); p.example = false; } else state.pantry.push(""", """    if(p){ applyEdit(p, data); p.example = false; } else state.pantry.push("""),
  ("""    if(t) Object.assign(t, data); else state.budget.txns.push(Object.assign({id:uid(), billId:null}, data, settleForm.via""", """    if(t) applyEdit(t, data); else state.budget.txns.push(Object.assign({id:uid(), billId:null}, data, settleForm.via"""),
  ("""    if(c) Object.assign(c, {name, limit}); else state.budget.categories.push(""", """    if(c) applyEdit(c, {name, limit}); else state.budget.categories.push("""),
  ("""    if(b) Object.assign(b, data); else state.budget.bills.push(""", """    if(b) applyEdit(b, data); else state.budget.bills.push("""),
  ("""    if(p) Object.assign(p, data); else state.budget.paydays.push(""", """    if(p) applyEdit(p, data); else state.budget.paydays.push("""),
  ("""    if(e) Object.assign(e, data); else { added = Object.assign({id:uid()}, data); state.events.push(added); }""", """    if(e) applyEdit(e, data); else { added = Object.assign({id:uid()}, data); state.events.push(added); }"""),
  ("""    if(e) Object.assign(e, data); else f.entries.push(""", """    if(e) applyEdit(e, data); else f.entries.push("""),
  ("""    if(g) Object.assign(g, {name, target, by}); else fund().goals.push(""", """    if(g) applyEdit(g, {name, target, by}); else fund().goals.push("""),
  ("""    if(c){ Object.assign(c, data); c.example = false;""", """    if(c){ applyEdit(c, data); c.example = false;"""),
  ("""    if(n) Object.assign(n, {text, drawing, color, pinned, updated:Date.now()});""", """    if(n) applyEdit(n, {text, drawing, color, pinned, updated:Date.now()});"""),
  ("""    if(m) Object.assign(m, data); else p.meds.push(""", """    if(m) applyEdit(m, data); else p.meds.push("""),
  ("""    if(c) Object.assign(c, data); else p.checkups.push(""", """    if(c) applyEdit(c, data); else p.checkups.push("""),
  ("""    if(v) Object.assign(v, data); else p.vaccines.push(""", """    if(v) applyEdit(v, data); else p.vaccines.push("""),
]
for old, new in saves:
    rep(old, new)

# spending/income: the payback link is a field like any other
rep("""    if(repays){ data.repays = repays; }""", """    data.repays = repays || null;""")
rep("""    if(t){ Object.assign(t, data); if(!repays) delete t.repays; else delete t.noRepay; } else state.budget.txns.push(Object.assign({id:uid(), billId:null}, data));""",
    """    if(t){ applyEdit(t, data); if(!t.repays) delete t.repays; else delete t.noRepay; }
    else { const nt = Object.assign({id:uid(), billId:null}, data); if(!nt.repays) delete nt.repays; state.budget.txns.push(nt); }""")

rep('const BUILD = "2026-10-30 · 37";', 'const BUILD = "2026-10-30 · 38";')
open(p, "w").write(s)
print("patched")
