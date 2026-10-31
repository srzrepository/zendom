"""Step 44: a second "crunching the numbers" animation, picked at random.
Jeff seen from above (from Sam's sketch), in his original sprite style: green bucket hat, glasses,
trotters tapping a calculator, butt swaying side to side. Each time the Summary tab crunches, it picks
this one or the original at random. Frames come from tools/jeff-draft/jeff_topdown_classic.py via
export_topdown.py. No data change.
Usage: python3 patch_step44_second_crunch.py file.html path/to/jeff_anim2.json"""
import sys
p, j = sys.argv[1], sys.argv[2]; s = open(p).read(); anim = open(j).read().strip()
def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (s.count(old), old[:100])
    s = s.replace(old, new)
rep("""@keyframes jf{0%{opacity:1}10%{opacity:0}100%{opacity:0}}""",
    """@keyframes jf{0%{opacity:1}10%{opacity:0}100%{opacity:0}}
.jeffanim .jg{opacity:0;animation:jg 1.04s steps(1) infinite}
@keyframes jg{0%{opacity:1}12.5%{opacity:0}100%{opacity:0}}""")
rep("""@media (prefers-reduced-motion:reduce){.jeffanim .jf{animation:none}.jeffanim .jf0{opacity:1}}""",
    """@media (prefers-reduced-motion:reduce){.jeffanim .jf,.jeffanim .jg{animation:none}.jeffanim .jf0,.jeffanim .jg0{opacity:1}}""")
rep("""let jeffAnimSvg = "";""", """let jeffAnimSvg = "";
// Jeff from above, swaying as he types (tools/jeff-draft/jeff_topdown_classic.py → export_topdown.py)
const JEFF_ANIM2 = """ + anim + """;
let jeffAnimSvg2 = "";
function jeffCrunchSVG2(){
  if(jeffAnimSvg2) return jeffAnimSvg2;
  const A = JEFF_ANIM2;
  return jeffAnimSvg2 = `<svg viewBox="0 0 ${A.w} ${A.h}" shape-rendering="crispEdges" aria-hidden="true">${A.frames.map((g, i) => `<g class="jg jg${i}" style="animation-delay:${(-1.04 + i * .13).toFixed(2)}s">${faceRects(g, A.pal)}</g>`).join("")}</svg>`;
}
let sumCrunchPick = 0;   // which crunching animation this time (0: at the desk, 1: from above)""")
rep("""  if(key !== sumCrunchKey){ sumCrunchKey = key; sumCrunchUntil""", """  if(key !== sumCrunchKey){ sumCrunchKey = key; sumCrunchPick = Math.random() < .5 ? 0 : 1; sumCrunchUntil""")
rep("""${crunching ? jeffCrunchSVG() : pigSvg()}""", """${crunching ? (sumCrunchPick ? jeffCrunchSVG2() : jeffCrunchSVG()) : pigSvg()}""")
rep('const BUILD = "2026-10-30 · 43";', 'const BUILD = "2026-10-30 · 44";')
rep("""const CHANGELOG = [""", """const CHANGELOG = [
  ["44", "2026-10-30", ["A second crunching-the-numbers Jeff on the Summary tab, seen from above with his butt wiggling. It picks one at random each time."]],""")
open(p, "w").write(s); print("patched")
