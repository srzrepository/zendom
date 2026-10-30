"""Step 27: know which version is running, and get updates reliably.
- BUILD constant, shown in More -> Settings.
- On open (and when the app comes back to the foreground) it quietly checks the website's index.html;
  if the published BUILD differs, a toast offers Reload.
- toast() can take a button label (default Undo).
Usage: python3 patch_step27_version.py file.html BUILD"""
import sys
p = sys.argv[1]; build = sys.argv[2]; s = open(p).read()
def rep(old, new):
    global s
    assert s.count(old) == 1, (s.count(old), old[:90])
    s = s.replace(old, new)
rep("""function toast(msg, undo){
  clearTimeout(toastTimer);
  $("#toastRoot").innerHTML = `<div class="toast" role="status"><span>${esc(msg)}</span>${undo ? '<button type="button" data-act="undo">Undo</button>' : ""}</div>`;
  toast.undo = undo || null;
  toastTimer = setTimeout(() => { $("#toastRoot").innerHTML = ""; toast.undo = null; }, undo ? 5000 : 2200);
}""",
f"""function toast(msg, undo, label, ms){{
  clearTimeout(toastTimer);
  $("#toastRoot").innerHTML = `<div class="toast" role="status"><span>${{esc(msg)}}</span>${{undo ? `<button type="button" data-act="undo">${{esc(label || "Undo")}}</button>` : ""}}</div>`;
  toast.undo = undo || null;
  toastTimer = setTimeout(() => {{ $("#toastRoot").innerHTML = ""; toast.undo = null; }}, ms || (undo ? 5000 : 2200));
}}
/* ---- which version is this, and is there a newer one? ---- */
const BUILD = "{build}";
let updateSeen = "";
async function checkForUpdate(){{
  if(!/^https?:$/.test(location.protocol) || navigator.onLine === false) return;
  try {{
    const res = await fetch("index.html?v=" + Date.now(), {{cache:"no-store"}}); if(!res.ok) return;
    const m = /const BUILD = "([^"]+)"/.exec(await res.text());
    if(m && m[1] !== BUILD && m[1] !== updateSeen){{ updateSeen = m[1];
      toast("A newer version of zen·dom is ready", () => location.reload(), "Reload", 15000); }}
  }} catch(e){{}}
}}
window.addEventListener("load", () => setTimeout(checkForUpdate, 2500));
document.addEventListener("visibilitychange", () => {{ if(!document.hidden) checkForUpdate(); }});""")
rep("""      <p class="small muted" style="margin:0">Recipe photos and PDFs stay on this phone""",
    """      <p class="small muted" style="margin:0">zen·dom version ${BUILD}</p>
      <p class="small muted" style="margin:0">Recipe photos and PDFs stay on this phone""")
open(p, "w").write(s); print("step 27 applied")
