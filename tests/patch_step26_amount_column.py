"""Step 26: PDF statements with extra money columns (Apple Card: Daily Cash before Amount).
Use the column headed "Amount" when there is one; ignore Daily Cash / cash back / rewards / points /
balance columns; without headings, a card statement's amount is the last one on the line. Descriptions
lose the trailing "94107 CA USA" style location. Usage: python3 patch_step26_amount_column.py file.html"""
import sys
p = sys.argv[1]; s = open(p).read()
def rep(old, new):
    global s
    assert s.count(old) == 1, (s.count(old), old[:90])
    s = s.replace(old, new)
rep("""  let mode = "", colOut = null, colIn = null, colBal = null;""",
    """  let mode = "", colOut = null, colIn = null, colBal = null, colAmt = null, colSkip = [];""")
rep("""      l.items.forEach(i => { const w = i.s.toLowerCase();
        if(/withdraw|debits?$|money out|subtractions/.test(w)) colOut = i.x2;""",
"""      l.items.forEach(i => { const w = i.s.toLowerCase();
        if(/daily cash|cash ?back|rewards?|points|miles/.test(w)){ colSkip.push(i.x2); return; }
        if(/^(transaction )?amount( \\(\\$\\))?$|^amount\\b/.test(w)) colAmt = i.x2;
        if(/withdraw|debits?$|money out|subtractions/.test(w)) colOut = i.x2;""")
rep("""    if(!pick){ const usable = amts.filter(a => !near(colBal, a)); pick = (usable.length > 1 && !isCard ? usable[0] : usable[0]) || amts[0]; }""",
"""    const skipCol = a => colSkip.some(c => Math.abs(a.x2 - c) < 30) || /%$/.test(a.s);
    if(!pick && colAmt !== null) pick = amts.find(a => near(colAmt, a)) || null;
    if(!pick){ const usable = amts.filter(a => !near(colBal, a) && !skipCol(a)); pick = (isCard ? usable[usable.length - 1] : usable[0]) || amts[amts.length - 1]; }""")
rep("""    rows.push({date, desc: desc || "Statement line", cents: dir === "out" ? -Math.abs(cents) : Math.abs(cents)});""",
"""    const tidy = desc.replace(/\\s+\\d{1,2}%?$/, "").replace(/\\s*\\d{5}(-\\d{4})?\\s+[A-Z]{2}\\s+USA$/, "").replace(/\\s+[A-Z]{2}\\s+USA$/, "").trim();
    rows.push({date, desc: tidy || desc || "Statement line", cents: dir === "out" ? -Math.abs(cents) : Math.abs(cents)});""")
open(p, "w").write(s); print("step 26 applied")
