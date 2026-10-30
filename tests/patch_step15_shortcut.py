"""Step 15: paste recipe data copied by the "Copy for zen·dom" iPhone Shortcut.
The Shortcut runs in the person's own Safari (signed in to sites they subscribe to), reads the page's
schema.org Recipe data and copies {"zendom":1,"url":...,"recipe":...}. Pasting that fills the form.
Plain schema.org JSON-LD pastes work too. No stored-data change.
Usage: python3 patch_step15_shortcut.py file.html"""
import sys
p = sys.argv[1]; s = open(p).read()
def rep(old, new):
    global s
    assert s.count(old) == 1, (s.count(old), old[:90])
    s = s.replace(old, new)

rep("""const LINK_RE = /^https?:\\/\\/[^\\s]+\\.[^\\s]+$/i;""",
r"""const LINK_RE = /^https?:\/\/[^\s]+\.[^\s]+$/i;
/* Recipe data in the schema.org format (what the "Copy for zen·dom" Shortcut copies). Mirrors the worker. */
const LD_ENT = {amp:"&", lt:"<", gt:">", quot:'"', apos:"'", nbsp:" ", ndash:"–", mdash:"—", frac12:"½", frac14:"¼", frac34:"¾", deg:"°", rsquo:"’", lsquo:"‘", rdquo:"”", ldquo:"“", hellip:"…"};
function ldClean(t){ return String(t == null ? "" : t).replace(/<[^>]*>/g, " ").replace(/&#x([0-9a-f]+);/gi, (_, h) => String.fromCodePoint(parseInt(h, 16)))
  .replace(/&#(\d+);/g, (_, d) => String.fromCodePoint(+d)).replace(/&([a-z0-9]+);/gi, (m, n) => LD_ENT[n.toLowerCase()] ?? m).replace(/\s+/g, " ").trim(); }
function ldDuration(iso){ const m = /^P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:\d+S)?)?$/i.exec(String(iso || "").trim()); if(!m) return ldClean(iso).slice(0, 20);
  const h = (+(m[1] || 0)) * 24 + (+(m[2] || 0)), min = +(m[3] || 0); return [h ? h + " hr" : "", min ? min + " min" : ""].filter(Boolean).join(" "); }
const ldIs = (o, t) => o && (o["@type"] === t || (Array.isArray(o["@type"]) && o["@type"].includes(t)));
function ldFind(node, depth = 0){
  if(!node || typeof node !== "object" || depth > 6) return null;
  if(Array.isArray(node)){ for(const x of node){ const r = ldFind(x, depth + 1); if(r) return r; } return null; }
  if(ldIs(node, "Recipe")) return node;
  for(const k of ["recipe", "@graph", "mainEntity", "mainEntityOfPage", "itemListElement"]){ const r = ldFind(node[k], depth + 1); if(r) return r; }
  return null;
}
function ldSteps(ins, out = []){
  if(!ins) return out;
  if(typeof ins === "string"){ ldClean(ins).split(/(?<=\.)\s+(?=[A-Z])/).forEach(x => x.trim() && out.push(x.trim())); return out; }
  if(Array.isArray(ins)){ ins.forEach(x => ldSteps(x, out)); return out; }
  if(ldIs(ins, "HowToSection")){ if(ins.name) out.push(ldClean(ins.name).toUpperCase() + ":"); return ldSteps(ins.itemListElement, out); }
  const t = ldClean(ins.text || ins.name || ""); if(t) out.push(t); return out;
}
// Pasted text -> {title, servings, prep, cook, ingredients, steps, notes, source} or null if it isn't recipe data.
function recipeFromPastedData(txt){
  if(!/^[\[{]/.test(txt)) return null;
  let o; try { o = JSON.parse(txt); } catch(e){ return null; }
  const r = ldFind(o); if(!r) return null;
  const y = r.recipeYield, yt = ldClean(Array.isArray(y) ? (y.find(v => /\d/.test(String(v))) || y[0]) : y), sv = parseInt((/\d+/.exec(yt) || [""])[0], 10);
  const src = o && typeof o.url === "string" && /^https?:\/\//.test(o.url) ? o.url : (typeof r.url === "string" && /^https?:\/\//.test(r.url) ? r.url : "");
  return {title: ldClean(r.name).slice(0, 100), servings: sv > 0 && sv < 100 ? sv : null, prep: ldDuration(r.prepTime), cook: ldDuration(r.cookTime) || (!r.prepTime ? ldDuration(r.totalTime) : ""),
    ingredients: (Array.isArray(r.recipeIngredient) ? r.recipeIngredient : []).map(ldClean).filter(Boolean).slice(0, 80), steps: ldSteps(r.recipeInstructions).slice(0, 80),
    notes: ldClean(r.description).slice(0, 600), source: src};
}""")
rep("""  if(LINK_RE.test(txt)){ readRecipeLink(txt); return; }""",
"""  if(LINK_RE.test(txt)){ readRecipeLink(txt); return; }
  const ld = recipeFromPastedData(txt);
  if(ld){
    const set = (id, v) => { const el = $("#" + id); if(el && v){ el.value = v; el.classList.add("filled"); } };
    set("rtitle", ld.title); if(ld.servings) set("servings", String(ld.servings)); set("prep", ld.prep.slice(0, 20)); set("cook", ld.cook.slice(0, 20));
    set("ings", ld.ingredients.map(x => x.slice(0, 200)).join("\\n")); set("steps", ld.steps.map(x => x.slice(0, 1000)).join("\\n")); set("rnotes", ld.notes); set("source", ld.source.slice(0, 500));
    box.value = "";
    let host = ""; try { host = ld.source ? new URL(ld.source).hostname.replace(/^www\\./, "") : ""; } catch(e){}
    if(status) status.textContent = `Got it${host ? " from " + host : ""}: ${ld.ingredients.length} ingredient${ld.ingredients.length === 1 ? "" : "s"} and ${ld.steps.length} step${ld.steps.length === 1 ? "" : "s"}. Check them below, then Save.`;
    const t = $("#rtitle"); if(t) t.scrollIntoView({block:"start", behavior: auto ? "smooth" : "auto"});
    return;
  }
  if(/^[\\[{]/.test(txt) && /"@type"/.test(txt)){ if(status) status.textContent = "That copied page didn't have a recipe in it. Make sure the recipe itself is open in Safari, then run the Shortcut again."; return; }""")

open(p, "w").write(s)
print("step 15 applied")
