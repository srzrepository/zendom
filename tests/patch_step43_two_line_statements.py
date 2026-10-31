"""Step 43: PDF statements that put the store on a second line (Schwab Bank and others).
Schwab checking statements show a generic type on the dated line ("Visa Debit Card Point of Sale
Purchase", "Electronic Withdrawal", "Check") and the merchant on the line below, so every purchase was
imported as "Visa Debit Card Point of Sale Purchase". Now, when a row's description is one of those
generic types, the next line or two (that have no date or amount) become its description, tidied
(no ", CA, US", "~ Tran: ACHDD", date codes or "SQ *"/"TST*" prefixes). Card payments written as
"... CRD EPAY" are recognized as transfers too. Other statements are unchanged.
No data change. Usage: python3 patch_step43_two_line_statements.py file.html"""
import sys
p = sys.argv[1]; s = open(p).read()
def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (s.count(old), old[:100])
    s = s.replace(old, new)

rep("""  lines.forEach(l => {
    const amts""", r"""  // Descriptions that are only a transaction type: the real one is on the line(s) below (Schwab and others)
  const GENERIC = /^(visa debit card (point of sale )?purchase|debit card purchase|pos purchase|point of sale purchase|electronic (withdrawal|deposit|payment)|ach (debit|credit|withdrawal|deposit)|check|atm withdrawal|withdrawal|deposit|recurring debit card purchase)$/i;
  const NOISE = /©|page \d+ of|account number|statement period|\(continued\)|^activity|^date$|^posted|beginning balance|ending balance|^summary|checks paid|interest earned/i;
  let last = null;
  lines.forEach(l => {
    const amts""")
rep("""    const dt = dateAt(l.text);
    if(!dt){""", """    const dt = dateAt(l.text);
    if(!dt && last && !l.items.some(i => AMT_RE.test(i.s)) && last.extra.length < 2 && l.text.length <= 100 && !NOISE.test(l.text)){ last.extra.push(l.text); return; }
    if(!dt) last = null;
    if(!dt){""")
rep("""    rows.push({date, desc: tidy || desc || "Statement line", cents: dir === "out" ? -Math.abs(cents) : Math.abs(cents)});""",
    """    const row = {date, desc: tidy || desc || "Statement line", cents: dir === "out" ? -Math.abs(cents) : Math.abs(cents), extra: []};
    rows.push(row); last = GENERIC.test(row.desc) ? row : null;""")
rep("""  return {rows, isCard, end};""", r"""  // a generic row takes its detail line(s) as the description
  const tidyDetail = t => t.replace(/~?\s*Tran:\s*\w+/i, "").replace(/\s+\d{6}~?(?=\s|$)/g, "").replace(/\s+Visa Direct\b/i, "")
    .replace(/,\s*[A-Z]{2},\s*US$/i, "").replace(/,\s*US$/i, "").replace(/^(SQ|TST|PY|SP|DD)\s?\*\s*/i, "").replace(/\s+/g, " ").trim();
  rows.forEach(r => { if(r.extra.length){ const x = tidyDetail(r.extra.join(" "));
      if(x) r.desc = /^check$/i.test(r.desc) ? ("Check " + x.replace(/^check\s*(paid\s*)?/i, "")).trim() : cutText(x, 80); }
    delete r.extra; });
  return {rows, isCard, end};""")
rep("""const TRANSFER_RE = /autopay|""", """const TRANSFER_RE = /crd epay|\\bepay\\b|autopay|""")
rep('const BUILD = "2026-10-30 · 42";', 'const BUILD = "2026-10-30 · 43";')
rep("""const CHANGELOG = [""", """const CHANGELOG = [
  ["43", "2026-10-30", ["Schwab (and similar) PDF statements: purchases come in with the store's name instead of “Visa Debit Card Point of Sale Purchase”, and card payments start unticked as transfers."]],""")
open(p, "w").write(s)
print("patched")
