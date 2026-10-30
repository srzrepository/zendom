"""Step 17: open without internet. Registers sw.js (a background worker that keeps a copy of the app
files and also handles notifications), only on the real website (https or localhost).
Usage: python3 patch_step17_offline.py file.html"""
import sys
p = sys.argv[1]; s = open(p).read()
def rep(old, new):
    global s
    assert s.count(old) == 1, (s.count(old), old[:90])
    s = s.replace(old, new)
rep("""window.addEventListener("online", () => {""",
"""// keep a copy of the app on this phone so it opens without internet (website only, not a downloaded file)
if("serviceWorker" in navigator && (location.protocol === "https:" || location.hostname === "localhost")){
  window.addEventListener("load", () => { navigator.serviceWorker.register("sw.js").catch(() => {}); });
}
window.addEventListener("online", () => {""")
open(p, "w").write(s); print("step 17 applied")
