"""Step 28: no stray "Tell Charlie?" pop-up after coming back to the app; Today button opens Today.
- The pop-up only appears for changes made in the last 30 seconds while the app is on screen
  (resends after reconnecting or after combining edits no longer trigger it), and it closes when
  the app goes to the background.
- Tapping Today in the bottom bar shows the plain Today view (not Week/Month) at the top.
Usage: python3 patch_step28_nudge_today.py file.html"""
import sys
p = sys.argv[1]; s = open(p).read()
def rep(old, new):
    global s
    assert s.count(old) == 1, (s.count(old), old[:90])
    s = s.replace(old, new)
rep("""function save(){
  if(!lsSet(KEY, JSON.stringify(state))){""",
"""let lastEditAt = 0;                                  // when this phone last saved a change made here
function save(){
  lastEditAt = Date.now();
  if(!lsSet(KEY, JSON.stringify(state))){""")
rep("""  if(nudges.length) showNudge(nudges);""",
    """  if(nudges.length && !document.hidden && Date.now() - lastEditAt < 30000) showNudge(nudges);   // only right after you changed something""")
rep("""window.addEventListener("load", () => setTimeout(checkForUpdate, 2500));""",
"""window.addEventListener("load", () => setTimeout(checkForUpdate, 2500));
document.addEventListener("visibilitychange", () => { if(document.hidden && typeof nudgeDismiss === "function" && $("#nudgeRoot").innerHTML) nudgeDismiss(); });""")
rep("""  tab: id => { prefs.tab = id; savePrefs(); render(); window.scrollTo(0,0); },""",
    """  tab: id => { prefs.tab = id; if(id === "today") prefs.todayView = "today"; savePrefs(); render(); window.scrollTo(0,0); },""")
open(p, "w").write(s); print("step 28 applied")
