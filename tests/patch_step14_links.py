"""Step 14: add a recipe from a website link.
Paste a link into the recipe paste box (or tap "Read it") and the zen·dom notifier worker fetches
the page and reads the schema.org Recipe data most recipe sites publish. Fields fill in for review;
nothing is saved until Save. Needs a signed-in account (the worker only answers the two of you).
No stored-data change. Usage: python3 patch_step14_links.py file.html"""
import sys
p = sys.argv[1]; s = open(p).read()
def rep(old, new):
    global s
    assert s.count(old) == 1, (s.count(old), old[:90])
    s = s.replace(old, new)

rep("""function fillFromPaste(auto){
  const box = $("#paste"); if(!box) return;
  const txt = box.value.trim();
  const status = $("#pasteStatus");
  if(!txt){ fail("paste", "Paste some recipe text first."); return; }""",
"""const LINK_RE = /^https?:\\/\\/[^\\s]+\\.[^\\s]+$/i;
// A pasted web link: ask the zen·dom worker to read the recipe off the page.
async function readRecipeLink(url){
  const status = $("#pasteStatus"), say = t => { if(status) status.textContent = t; };
  let host = ""; try { host = new URL(url).hostname.replace(/^www\\./, ""); } catch(e){}
  const set = (id, v) => { const el = $("#" + id); if(el && v){ el.value = v; el.classList.add("filled"); } };
  set("source", url.slice(0, 500));
  if(!NOTIFY.url || !window.zdBackend || !sync.user){ say(`Reading links needs you signed in (More → Settings). For now, copy the recipe text from ${host || "the page"} and paste it here.`); return; }
  say(`Reading the recipe from ${host}…`); readRecipeLink.busy = url;
  let j = null, err = "";
  try {
    const idToken = await window.zdBackend.idToken();
    const res = await fetch(NOTIFY.url.replace(/\\/$/, "") + "/recipe", {method:"POST", headers:{"Content-Type":"text/plain"}, body: JSON.stringify({idToken, url})});
    j = await res.json().catch(() => null);
    if(!res.ok) err = (j && j.error) || "the site didn't answer";
  } catch(e){ err = navigator.onLine === false ? "you're offline" : "couldn't reach the recipe reader"; }
  if(readRecipeLink.busy !== url || !$("#paste")) return;            // the sheet closed or another link was pasted
  readRecipeLink.busy = null;
  if(err || !j){ say(`Couldn't read that link (${err}). Copy the recipe text from the page and paste it here instead.`); return; }
  if(!j.found){ set("rtitle", (j.title || "").slice(0, 100)); say(`${host} doesn't share its recipe in a form the app can read. Copy the ingredients and steps from the page and paste them here; the link is saved below.`); return; }
  set("rtitle", (j.title || "").slice(0, 100));
  if(j.servings) set("servings", String(Math.min(99, j.servings)));
  set("prep", (j.prep || "").slice(0, 20)); set("cook", (j.cook || "").slice(0, 20));
  set("ings", (j.ingredients || []).join("\\n")); set("steps", (j.steps || []).join("\\n")); set("rnotes", (j.notes || "").slice(0, 2000));
  const box = $("#paste"); if(box) box.value = "";
  const ni = (j.ingredients || []).length, ns = (j.steps || []).length;
  say(`Got it from ${host}: ${ni} ingredient${ni === 1 ? "" : "s"} and ${ns} step${ns === 1 ? "" : "s"}. Check them below, then Save.`);
  const t = $("#rtitle"); if(t) t.scrollIntoView({block:"start", behavior:"smooth"});
}
function fillFromPaste(auto){
  const box = $("#paste"); if(!box) return;
  const txt = box.value.trim();
  const status = $("#pasteStatus");
  if(!txt){ fail("paste", "Paste some recipe text or a link first."); return; }
  if(LINK_RE.test(txt)){ readRecipeLink(txt); return; }""")
rep("""field("paste", r ? "Paste the recipe again to re-sort it" : "Copied a recipe? Paste it here",""",
    """field("paste", r ? "Paste the recipe again to re-sort it" : "Paste a recipe or a link to one",""")
rep("""data-act="pasteRecipe">Paste a recipe</button><label""", """data-act="pasteRecipe">Paste a recipe or link</button><label""")
rep("""<div class="addrow"><button type="button" class="btn ghost small" data-act="pasteRecipe">Paste a recipe</button>""",
    """<div class="addrow"><button type="button" class="btn ghost small" data-act="pasteRecipe">Paste a recipe or link</button>""")

open(p, "w").write(s)
print("step 14 applied")
