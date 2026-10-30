"""Step 20: Tonight's dinner only suggests recipes tagged Lunch or Dinner (and "What can we make?"
from that card opens with Lunch + Dinner selected). Also: content no longer shows through behind
the iPhone status bar (viewport-fit=cover, so the existing safe-area padding takes effect).
Usage: python3 patch_step20_meals.py file.html"""
import sys
p = sys.argv[1]; s = open(p).read()
def rep(old, new):
    global s
    assert s.count(old) == 1, (s.count(old), old[:90])
    s = s.replace(old, new)
rep('<meta name="viewport" content="width=device-width,initial-scale=1">', '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">')
rep("""function closestHTML(){
  if(!state.pantry.length) return "";
  const best = state.recipes.filter(r => r.ingredients.length).map(r => ({r, rd:readiness(r)})).filter(x => x.rd.pct >= 50)""",
"""const MEALTIME = /^(lunch|dinner)$/i;
const isMealRecipe = r => r.categories.some(c => MEALTIME.test(c));
function closestHTML(){
  if(!state.pantry.length) return "";
  if(state.recipes.some(r => r.ingredients.length) && !state.recipes.some(isMealRecipe))
    return `<p class="small muted" style="margin:6px 0 0">Tag recipes as Lunch or Dinner and I'll suggest the ones you can almost make.</p>`;
  const best = state.recipes.filter(r => r.ingredients.length && isMealRecipe(r)).map(r => ({r, rd:readiness(r)})).filter(x => x.rd.pct >= 50)""")
rep("""  whatCanWeMake: () => { prefs.tab = "kitchen"; prefs.kitchenTab = "recipes"; recipeSort = "ready"; rf.types.clear();""",
"""  whatCanWeMake: () => { prefs.tab = "kitchen"; prefs.kitchenTab = "recipes"; recipeSort = "ready"; rf.types.clear();
    allCategories([]).filter(c => MEALTIME.test(c) && state.recipes.some(r => r.categories.includes(c))).forEach(c => rf.types.add(c));""")
open(p, "w").write(s); print("step 20 applied")
