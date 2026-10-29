"""Step 3: Farmhouse look (styles only, no new mechanics) + Jeff holding the money jar on the Fun Fund.
No stored-data change. Usage: python3 patch_step3_farmhouse.py file.html sprites.json"""
import sys, json
p = sys.argv[1]; s = open(p).read()
jar = json.load(open(sys.argv[2]))["jeffjar"]
def rep(old, new):
    global s
    assert s.count(old) == 1, (s.count(old), old[:90])
    s = s.replace(old, new)

rep('family=Fredoka:wght@400;500;600&family=Figtree:wght@400;500;600;700&family=Pixelify+Sans:wght@400;500&display=swap',
    'family=Fredoka:wght@400;500;600&family=Figtree:wght@400;500;600;700&family=Pixelify+Sans:wght@400;500&family=Jersey+15&family=Lexend:wght@400;500;600;700&display=swap')

CSS = r'''
/* ============================================================
   FARMHOUSE LOOK
   A wooden-framed parchment board on a grassy ground. Everything
   below only restyles; remove this block to get the old look back.
   The board's colors live on <body> so the personal palettes keep
   setting the accent, and seasons keep their hero colors.
   ============================================================ */
body{
  --bg:#f3dca6;            /* parchment board */
  --surface:#fcefd2;       /* lighter parchment card */
  --surface-2:#ecd09a;     /* inset slot */
  --ink:#3a2214; --muted:#71502e; --line:#c99b5a;
  --wood:#8a4d22; --wood-dark:#4a2610; --wood-light:#b86f36; --wood-ink:#ffe7b0;
  --frame:#8b5a2b; --bevel:rgba(255,248,226,.55);
  --grass:#3d5c35; --grass-2:#35512e;
  --shadow:0 0 0 3px var(--frame),inset 0 0 0 2px var(--bevel),0 5px 0 3px rgba(74,38,16,.22);
  --r-card:6px; --r-pill:5px;
  --f-display:"Jersey 15","Pixelify Sans","Courier New",monospace;
  --f-pixel:"Jersey 15","Pixelify Sans","Courier New",monospace;
  --f-body:"Lexend","Figtree",system-ui,sans-serif;
  --sam-soft:#f6d2c3; --charlie-soft:#d6e3f3; --paprika-soft:#f6dcb6;
}
:root:not([data-season]) body{--hero-bg:var(--surface);--hero-ink:var(--ink);--hero-muted:var(--muted)}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]) body{
  --bg:#2f2218; --surface:#3b2b1e; --surface-2:#4a3626; --ink:#f5e6c8; --muted:#cfb48e; --line:#6e5034;
  --wood:#5c3418; --wood-dark:#1a0f08; --wood-light:#7a4a26; --wood-ink:#ffe2a8;
  --frame:#1f130a; --bevel:rgba(255,226,168,.10);
  --grass:#1b2a20; --grass-2:#172419;
  --shadow:0 0 0 3px var(--frame),inset 0 0 0 2px var(--bevel),0 5px 0 3px rgba(0,0,0,.35);
  --sam-soft:#5a3a30; --charlie-soft:#2e3d55; --paprika-soft:#4d3a24}}
:root[data-theme="dark"] body{
  --bg:#2f2218; --surface:#3b2b1e; --surface-2:#4a3626; --ink:#f5e6c8; --muted:#cfb48e; --line:#6e5034;
  --wood:#5c3418; --wood-dark:#1a0f08; --wood-light:#7a4a26; --wood-ink:#ffe2a8;
  --frame:#1f130a; --bevel:rgba(255,226,168,.10);
  --grass:#1b2a20; --grass-2:#172419;
  --shadow:0 0 0 3px var(--frame),inset 0 0 0 2px var(--bevel),0 5px 0 3px rgba(0,0,0,.35);
  --sam-soft:#5a3a30; --charlie-soft:#2e3d55; --paprika-soft:#4d3a24}

/* the app hides elements with the hidden attribute; keep that true outside claude.ai too */
[hidden]{display:none!important}
.jeff:has(.jar){flex-direction:column;align-items:stretch;text-align:left}
.jeff:has(.jar) .jeff-pig{align-self:center}

/* ground and board */
body{background-color:var(--grass);background-image:repeating-linear-gradient(90deg,rgba(0,0,0,.07) 0 2px,transparent 2px 12px),repeating-linear-gradient(0deg,rgba(255,255,255,.035) 0 2px,transparent 2px 10px)}
body::before{background:var(--grass)}
.wrap{background:var(--bg);margin-top:10px;border:4px solid var(--wood-dark);border-radius:8px;box-shadow:inset 0 0 0 3px var(--wood-light),inset 0 0 0 6px var(--wood),0 6px 0 rgba(0,0,0,.25);padding:0 12px 14px;min-height:calc(100vh - 120px)}
.top{background:var(--bg);margin-inline:-8px;padding-inline:8px;border-radius:4px}
h1,h2,h3{font-weight:400;letter-spacing:.01em}
h2{font-size:1.7rem}
.hero-text h1{font-size:2.1rem;line-height:1}
.sheet h2{font-size:1.85rem}
.label{font-size:1.3rem;letter-spacing:.02em;text-transform:none;color:var(--muted);line-height:1.1}
.meal .slot,.hv{font-size:1.1rem;text-transform:none;letter-spacing:0}
.note .by{font-size:1.1rem}

/* header: brand on a wooden plaque */
.brand{font-weight:400;font-size:1.9rem;line-height:1;background:var(--wood);color:var(--wood-ink);border:3px solid var(--wood-dark);box-shadow:inset 0 0 0 2px var(--wood-light),0 3px 0 rgba(0,0,0,.25);border-radius:4px;padding:4px 10px 2px}
.brand .dot{color:var(--wood-ink);opacity:.75}
.who{border-radius:6px;box-shadow:inset 0 0 0 2px var(--line)}
.who button{border-radius:4px}
.who .av{border-radius:4px}

/* cards: shared radius for everything framed by --shadow */
.card,.row,.item,.note,.rcard,.day,.glist,.bubble,.ready-box,.mgrid,.hero,.empty,.stp[aria-current="step"]{border-radius:var(--r-card)}
.hero{border-radius:8px}
.empty{border:3px dashed var(--line);background:var(--surface)}
.note:nth-child(odd){transform:rotate(-.8deg)} .note:nth-child(even){transform:rotate(.7deg)}
.room{background:var(--surface-2);border-radius:4px;box-shadow:inset 0 0 0 3px var(--frame);padding:6px;margin:2px 0}
.room canvas{filter:none}
.roomnote{border-radius:4px}

/* insets: chips, sub-tabs, slots */
.chip,.sub,.meal,.ing,.stp,.fact,.pastebox,details.cpe,.confirm,.readycard,.subtabs,.tag,.suggest button,.colorpick label{border-radius:4px}
.chip{box-shadow:inset 0 0 0 2px var(--line)}
.chip[aria-pressed="true"],.sub[aria-selected="true"]{background:var(--wood);color:var(--wood-ink);box-shadow:inset 0 0 0 2px var(--wood-light),0 0 0 2px var(--wood-dark)}
.chip[aria-pressed="true"] .muted,.sub[aria-selected="true"] .n{color:var(--wood-ink)}
.sub[aria-selected="true"] .n{background:var(--wood-dark)}
.subtabs{box-shadow:inset 0 0 0 2px var(--line)}
.sub{font-family:var(--f-display);font-size:1.3rem;font-weight:400}

/* inventory-slot checkboxes */
.check{border-radius:4px;border:3px solid var(--wood-dark);background:var(--surface);box-shadow:inset 0 3px 0 var(--surface-2)}
.check[aria-pressed="true"]{background:var(--accent);border-color:var(--wood-dark);box-shadow:inset 0 -4px 0 rgba(0,0,0,.18)}
.check.small{border-radius:4px}
.owner,.prof .big,.calitem .cav,.reply .av,.whorow .av{border-radius:4px;box-shadow:0 0 0 2px var(--frame)}

/* buttons: chunky and bevelled */
.btn{border-radius:4px;border:3px solid var(--wood-dark);box-shadow:inset 0 -4px 0 rgba(0,0,0,.18),0 3px 0 rgba(74,38,16,.3);font-family:var(--f-display);font-weight:400;font-size:1.4rem;line-height:1}
.btn.small{font-size:1.25rem}
.btn.ghost{background:var(--surface-2);color:var(--ink)}
.btn.danger{background:var(--late-soft);color:var(--late);border-color:var(--late)}
.btn:active{transform:translateY(2px);box-shadow:inset 0 -2px 0 rgba(0,0,0,.18)}
.fab{border-radius:4px;background:var(--wood);color:var(--wood-ink);border:3px solid var(--wood-dark);box-shadow:inset 0 0 0 2px var(--wood-light),0 5px 0 rgba(0,0,0,.3);font-family:var(--f-display);font-weight:400;font-size:1.45rem}

/* form fields */
.field input,.field select,.field textarea,input[type=search],.gadd input{border-radius:4px;border:2px solid var(--line);background:var(--surface)}
.field label,.field .lab{font-weight:600}

/* bottom bar: a wooden shelf */
.nav{background:var(--wood);border-top:4px solid var(--wood-dark);box-shadow:inset 0 3px 0 var(--wood-light)}
.nav button{color:var(--wood-ink);border-radius:4px;font-family:var(--f-display);font-weight:400;font-size:1.2rem;line-height:1}
.nav button[aria-current="page"]{background:var(--bg);color:var(--ink);box-shadow:0 0 0 3px var(--wood-dark),inset 0 0 0 2px var(--bevel)}

/* sheet: a parchment panel slid up from the shelf */
.sheet{background:var(--bg);border-radius:8px 8px 0 0;border:4px solid var(--wood-dark);border-bottom:0;box-shadow:inset 0 0 0 3px var(--wood-light),0 -8px 0 rgba(0,0,0,.15)}
.grab{border-radius:2px;background:var(--wood);height:6px}
.backdrop{background:rgba(20,14,8,.45)}

/* toast: a little dialogue box */
.toast{background:var(--surface);color:var(--ink);border:3px solid var(--wood-dark);border-radius:4px;box-shadow:4px 4px 0 rgba(0,0,0,.25)}
.toast button{color:var(--accent-ink);font-family:var(--f-display);font-weight:400;font-size:1.35rem}

/* Fun Fund: Jeff and his jar */
.jeff-pig{border-radius:4px;box-shadow:inset 0 0 0 3px var(--frame);background:var(--surface-2)}
.jeff-pig.jar{width:152px;height:152px;padding:2px}
.bubble{border:3px solid var(--wood-dark);box-shadow:3px 3px 0 rgba(0,0,0,.2)}
.fundtotal b{font-family:var(--f-display);font-weight:400;font-size:3rem}
.gbar,.wbar,.ready .bar{border-radius:2px;box-shadow:inset 0 0 0 2px var(--frame)}
.gbar i,.wbar i,.ready .bar i{border-radius:0}

'''
rep('</style>', CSS + '</style>')

rep('function pigSvg(cls){ return `<svg class="pixel ${cls||""}" viewBox="0 0 32 32" width="100%" height="100%" aria-hidden="true">${spriteRects(PIG.rows, PIG.pal)}</svg>`; }',
    'const JEFF_JAR = ' + json.dumps(jar, separators=(",", ":")) + ';   // Jeff hugging the Fun Fund jar\n'
    'function pigSvg(cls, sp){ sp = sp || PIG; return `<svg class="pixel ${cls||""}" viewBox="0 0 32 32" width="100%" height="100%" aria-hidden="true">${spriteRects(sp.rows, sp.pal)}</svg>`; }')
rep('''  <section class="jeff card"><div class="jeff-pig">${pigSvg()}</div>
    <div class="jeff-talk"><span class="label">${esc(f.name)}</span>''',
    '''  <section class="jeff card"><div class="jeff-pig jar">${pigSvg("", JEFF_JAR)}</div>
    <div class="jeff-talk"><span class="label">${esc(f.name)}</span>''')
open(p, 'w').write(s)
print("patched", p)
