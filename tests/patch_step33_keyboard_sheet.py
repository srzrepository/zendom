"""Step 33: forms don't jump when the iPhone keyboard opens.
iOS Safari doesn't shrink the page for the keyboard; it slides the whole page up instead, dragging
the bottom sheet (which is pinned to the bottom of the page) with it. Now, while the keyboard is up,
the open sheet is fitted to the part of the screen you can see (window.visualViewport), and the box
you tapped is scrolled into view inside the sheet. The page behind the sheet can't scroll while a
sheet is open. When the keyboard closes the sheet goes back to normal.
No data change. Usage: python3 patch_step33_keyboard_sheet.py file.html"""
import sys
p = sys.argv[1]; s = open(p).read()
def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (s.count(old), old[:100])
    s = s.replace(old, new)

rep(""".sheet .in{max-width:520px;margin:0 auto;display:flex;flex-direction:column;gap:14px}""",
""".sheet .in{max-width:520px;margin:0 auto;display:flex;flex-direction:column;gap:14px}
html.sheet-open,html.sheet-open body{overflow:hidden}
.sheet{overscroll-behavior:contain}""")

rep("""function closeSheet(){ discardPendingPdf(); $("#sheetRoot").innerHTML = "";""",
r"""// iPhone keyboard: fit the open sheet to what's visible instead of letting Safari slide the page.
// vv: {height, offsetTop}; fullH: the page's height without the keyboard.
function fitSheet(vv, fullH){
  const sh = document.querySelector(".sheet"); if(!sh || !vv) return false;
  const kb = fullH - vv.height > 120;          // a real keyboard, not the address bar shrinking
  if(kb){ sh.style.top = Math.round(vv.offsetTop + 8) + "px"; sh.style.bottom = "auto"; sh.style.maxHeight = Math.round(vv.height - 8) + "px"; }
  else { sh.style.top = ""; sh.style.bottom = ""; sh.style.maxHeight = ""; }
  const a = document.activeElement;
  if(kb && a && sh.contains(a) && a.matches && a.matches(TYPING_SEL)){
    const r = a.getBoundingClientRect(), box = sh.getBoundingClientRect();
    if(r.top < box.top + 8 || r.bottom > box.bottom - 8) sh.scrollTop += r.top - box.top - Math.max(8, (box.height - r.height) / 3);
  }
  return kb;
}
let sheetFullH = window.innerHeight;
if(window.visualViewport){
  const onVV = () => { if(!document.querySelector(".sheet")){ sheetFullH = window.innerHeight; return; }
    sheetFullH = Math.max(sheetFullH, window.innerHeight); fitSheet(window.visualViewport, sheetFullH); };
  window.visualViewport.addEventListener("resize", onVV);
  window.visualViewport.addEventListener("scroll", onVV);
  window.addEventListener("orientationchange", () => { sheetFullH = 0; setTimeout(onVV, 300); });
}
function closeSheet(){ discardPendingPdf(); $("#sheetRoot").innerHTML = ""; document.documentElement.classList.remove("sheet-open");""")

rep("""  const form = $("#sheetForm");
  form.addEventListener("submit", e => { e.preventDefault(); clearErrors(form); onSubmit(form); });""",
"""  const form = $("#sheetForm");
  document.documentElement.classList.add("sheet-open");
  if(window.visualViewport) fitSheet(window.visualViewport, Math.max(sheetFullH, window.innerHeight));
  form.addEventListener("submit", e => { e.preventDefault(); clearErrors(form); onSubmit(form); });""")

rep('const BUILD = "2026-10-30 · 32";', 'const BUILD = "2026-10-30 · 33";')
open(p, "w").write(s)
print("patched")
