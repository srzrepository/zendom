"""Step 25: import PDF statements (bank and credit card), not just CSV.
The PDF is read on the phone with pdf.js (already used for recipe PDFs); nothing is uploaded.
Each line that starts with a date and has an amount becomes a row; the year comes from the
statement period (a December line on a January statement is the year before); money in vs out comes
from the amount's column (Withdrawals/Deposits), its sign or CR, the section it's in (Payments and
Credits, Purchases, Deposits, ...) and whether it's a credit card statement. Balance lines and totals
are skipped. The rows go through the same preview + duplicate check as a CSV.
Also for every import: card payments and transfers between your own accounts start unticked
("Looks like a transfer or card payment"), because they aren't spending.
Usage: python3 patch_step25_pdf_statements.py file.html"""
import sys
p = sys.argv[1]; s = open(p).read()
def rep(old, new):
    global s
    assert s.count(old) == 1, (s.count(old), old[:90])
    s = s.replace(old, new)

rep("""function buildImport(text, fileName){""", r"""/* ---- PDF statements ---- */
// Text lines from a PDF, top to bottom, each with its pieces' left/right edges (for columns).
async function pdfLines(buf){
  const lib = await loadPdfJs();
  const doc = await lib.getDocument({data:new Uint8Array(buf.slice(0)), isEvalSupported:false, disableFontFace:true}).promise;
  const out = [];
  for(let p = 1; p <= Math.min(doc.numPages, 30); p++){
    const page = await doc.getPage(p), tc = await page.getTextContent();
    const items = tc.items.filter(it => it.str && it.str.trim()).map(it => ({x:it.transform[4], y:it.transform[5], x2:it.transform[4] + (it.width || 0), s:it.str.trim()}));
    items.sort((a, b) => b.y - a.y || a.x - b.x);
    let cur = null;
    items.forEach(it => { if(cur && Math.abs(cur.y - it.y) <= 2.5) cur.items.push(it); else { cur = {y:it.y, items:[it]}; out.push(cur); } });
  }
  out.forEach(l => { l.items.sort((a, b) => a.x - b.x); l.text = l.items.map(i => i.s).join(" ").replace(/\s+/g, " ").trim(); });
  return out;
}
const MONTHS3 = ["jan","feb","mar","apr","may","jun","jul","aug","sep","oct","nov","dec"];
const AMT_RE = /^\(?-?\$?\s?-?\d{1,3}(?:,\d{3})*\.\d{2}\)?\s?(?:CR|DR|-)?$/i;
function amtCents(s){ const neg = /^\(|^-|\$\s?-|-$|\)$|CR$/i.test(s.trim()); const n = Math.round(parseFloat(s.replace(/[^\d.]/g, "")) * 100); return neg ? -n : n; }
// Turn statement lines into rows {date, desc, cents} (cents < 0 = money out).
function statementRows(lines){
  const full = lines.map(l => l.text).join("\n");
  const isCard = /credit card|minimum payment|credit limit|new balance|rewards card/i.test(full);
  // the statement's last date sets the year (MM/DD/YYYY, Month DD, YYYY or YYYY-MM-DD)
  const ends = [];
  full.replace(/\b(\d{1,2})\/(\d{1,2})\/(\d{4})\b/g, (_, m, d, y) => ends.push([+y, +m, +d]));
  full.replace(/\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.? (\d{1,2}),? (\d{4})\b/gi, (_, mo, d, y) => ends.push([+y, MONTHS3.indexOf(mo.slice(0, 3).toLowerCase()) + 1, +d]));
  full.replace(/\b(\d{4})-(\d{2})-(\d{2})\b/g, (_, y, m, d) => ends.push([+y, +m, +d]));
  const end = ends.filter(e => e[1] >= 1 && e[1] <= 12).sort((a, b) => (b[0] - a[0]) || (b[1] - a[1]) || (b[2] - a[2]))[0] || null;
  const today = todayStr();
  const yearFor = (m, d) => { if(end) return m > end[1] ? end[0] - 1 : end[0];
    const y = +today.slice(0, 4), iso = `${y}-${pad(m)}-${pad(d)}`; return iso > today ? y - 1 : y; };
  let mode = "", colOut = null, colIn = null, colBal = null;
  const rows = [];
  const dateAt = t => {
    let m = /^(\d{1,2})[\/-](\d{1,2})(?:[\/-](\d{2,4}))?\b\s*/.exec(t);
    if(m && +m[1] >= 1 && +m[1] <= 12 && +m[2] >= 1 && +m[2] <= 31) return {mo:+m[1], d:+m[2], y: m[3] ? (m[3].length === 2 ? 2000 + +m[3] : +m[3]) : null, len:m[0].length};
    m = /^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.? (\d{1,2})(?:,? (\d{4}))?\b\s*/i.exec(t);
    if(m) return {mo: MONTHS3.indexOf(m[1].slice(0, 3).toLowerCase()) + 1, d:+m[2], y: m[3] ? +m[3] : null, len:m[0].length};
    return null;
  };
  lines.forEach(l => {
    const amts = l.items.filter(i => AMT_RE.test(i.s));
    const dt = dateAt(l.text);
    if(!dt){
      // column headings (Withdrawals / Deposits / Balance) and section headings (Purchases, Payments and Credits...)
      l.items.forEach(i => { const w = i.s.toLowerCase();
        if(/withdraw|debits?$|money out|subtractions/.test(w)) colOut = i.x2;
        else if(/deposit|credits?$|money in|additions/.test(w)) colIn = i.x2;
        else if(/^balance$|daily balance/.test(w)) colBal = i.x2; });
      if(!amts.length && l.text.length < 60){
        if(/payments?|credits?|deposits?|refunds?|money in|additions/i.test(l.text) && !/purchases|charges/i.test(l.text)) mode = "in";
        else if(/purchases|withdrawals|debits|checks|fees|charges|money out|subtractions|transactions/i.test(l.text)) mode = "out";
      }
      return;
    }
    if(!amts.length) return;
    let rest = l.text.slice(dt.len); const d2 = dateAt(rest); if(d2) rest = rest.slice(d2.len);       // a second (posting) date
    if(/beginning balance|ending balance|previous balance|new balance|balance forward|opening balance|closing balance|^total/i.test(rest)) return;
    let pick = null, dir = "";
    const near = (col, a) => col !== null && Math.abs(a.x2 - col) < 30;
    if(colOut !== null || colIn !== null){
      pick = amts.find(a => near(colOut, a)); if(pick) dir = "out";
      else { pick = amts.find(a => near(colIn, a)); if(pick) dir = "in"; }
    }
    if(!pick){ const usable = amts.filter(a => !near(colBal, a)); pick = (usable.length > 1 && !isCard ? usable[0] : usable[0]) || amts[0]; }
    let cents = amtCents(pick.s);
    if(!dir){
      if(cents < 0) dir = isCard ? "in" : "out";                         // a minus on a card statement is a payment/credit
      else if(isCard) dir = mode === "in" ? "in" : "out";
      else dir = mode || "out";
    }
    const desc = rest.slice(0, rest.indexOf(pick.s) >= 0 ? rest.indexOf(pick.s) : undefined).replace(AMT_RE, "").replace(/\s+/g, " ").trim().replace(/\s+-?\$?\d[\d,]*\.\d{2}$/, "");
    const y = dt.y || yearFor(dt.mo, dt.d), date = `${y}-${pad(dt.mo)}-${pad(dt.d)}`;
    if(!isDate(date)) return;
    rows.push({date, desc: desc || "Statement line", cents: dir === "out" ? -Math.abs(cents) : Math.abs(cents)});
  });
  return {rows, isCard, end};
}
async function importPdf(file){
  if(file.size > 15 * 1024 * 1024){ toast("That PDF is over 15 MB. Try one month at a time."); return; }
  const buf = await file.arrayBuffer();
  if(!new TextDecoder().decode(new Uint8Array(buf.slice(0, 1024))).includes("%PDF")){ toast("That file isn't a PDF."); return; }
  toast("Reading the statement…");
  let res;
  try { res = statementRows(await pdfLines(buf)); }
  catch(e){ toast(navigator.onLine === false ? "Reading PDFs needs the internet the first time (to load the PDF reader)." : "Couldn't read that PDF."); return; }
  if(!res.rows.length){ toast("Couldn't find any transactions in that PDF. If it's a scan or a photo, the CSV download will work better."); return; }
  const q = v => `"${String(v).replace(/"/g, '""')}"`;
  const csv = "Date,Description,Amount\n" + res.rows.map(r => `${r.date},${q(r.desc)},${(r.cents / 100).toFixed(2)}`).join("\n");
  const out = buildImport(csv, file.name);
  if(out.error){ toast(out.error); return; }
  out.flip = false; out.fromPdf = true; out.isCard = res.isCard;
  clearTimeout(toastTimer); $("#toastRoot").innerHTML = "";
  importPreview(out);
}
const TRANSFER_RE = /autopay|payment\s*[-–]?\s*thank you|online (banking )?transfer|transfer (to|from)|card payment|credit card (auto)?pay|e-?payment|mobile payment|ach pmt|internet payment/i;
function buildImport(text, fileName){""")
# transfers start unticked
rep("""  // most bank files show spending as negative; if nearly everything is positive, it's probably the other way""",
"""  if(fmt !== "venmo") out.forEach(x => { if(!x.dup && TRANSFER_RE.test(x.desc)){ x.dup = "Looks like a transfer or card payment"; x.include = false; } });
  // most bank files show spending as negative; if nearly everything is positive, it's probably the other way""")
# file picker accepts PDFs
rep("""    <label class="btn" for="csvFile" style="align-self:flex-start;cursor:pointer">Choose CSV file<input type="file" id="csvFile" accept=".csv,text/csv,text/plain" class="sr"></label>""",
    """    <label class="btn" for="csvFile" style="align-self:flex-start;cursor:pointer">Choose a statement (PDF or CSV)<input type="file" id="csvFile" accept=".csv,text/csv,text/plain,.pdf,application/pdf" class="sr"></label>""")
rep("""    <p class="small" style="margin:0">Download a CSV from your bank, credit card or Venmo, then choose it here. You'll see everything before anything is added.</p>""",
    """    <p class="small" style="margin:0">Choose a PDF statement or a CSV download from your bank, credit card or Venmo. You'll see everything before anything is added, and it's read on this phone (nothing is uploaded).</p>""")
rep("""  if(el.id === "csvFile" && el.files && el.files[0]){
    const f = el.files[0];""",
"""  if(el.id === "csvFile" && el.files && el.files[0]){
    const f = el.files[0];
    if(/\\.pdf$/i.test(f.name) || f.type === "application/pdf"){ importPdf(f); return true; }""")
rep("""    <p class="small muted" style="margin:0">From ${esc(imp.fileName)} · ${imp.fmt === "venmo" ? "Venmo statement" : "bank or card export"}. Check what's right, then import.</p>""",
    """    <p class="small muted" style="margin:0">From ${esc(imp.fileName)} · ${imp.fromPdf ? `PDF ${imp.isCard ? "card" : "bank"} statement. Read from the PDF, so check the dates, amounts and money in/out` : imp.fmt === "venmo" ? "Venmo statement. Check what's right" : "bank or card export. Check what's right"}, then import.</p>""")

open(p, "w").write(s)
print("step 25 applied")
