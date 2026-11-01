"""Step 45: tap a category to see what's in it; keep the bottom bar at the bottom.
- Budget → Spending: tapping a category (or Uncategorized) opens what made up that month's total:
  each entry with its date, who paid, shared or not, and anything paid back; in a person's view, their
  part of each. The total matches the number on the category row. Tapping an entry opens it to edit;
  "Edit category" changes the name or target.
- Bottom bar (and Add button, messages): iPhone sometimes leaves bars pinned to the bottom stuck partway
  up the screen after the keyboard or a form closes, until something forces a redraw. They're now
  re-anchored to the bottom of what's actually on screen whenever the visible area changes, and the app
  nudges iPhone to redraw after typing ends and after a form closes.
No data change. Usage: python3 patch_step45_category_detail.py file.html"""
import sys
p = sys.argv[1]; s = open(p).read()
def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (s.count(old), old[:100])
    s = s.replace(old, new)

# ---------- category detail ----------
rep("""      return `<button type="button" class="catrow" data-act="editCat" data-id="${c.id}"><span class="cn">""",
    """      return `<button type="button" class="catrow" data-act="catDetail" data-id="${c.id}"><span class="cn">""")
rep("""      ${st.byCat.none ? `<div class="catrow"><span class="cn">Uncategorized</span><span class="cv">${money(st.byCat.none)}</span></div>` : ""}</div>""",
    """      ${st.byCat.none ? `<button type="button" class="catrow" data-act="catDetail" data-id="none"><span class="cn">Uncategorized</span><span class="cv">${money(st.byCat.none)}</span></button>` : ""}</div>""")
rep("""/* ---- forms ---- */
function catOptions(""", r"""// What made up one category's total this month (same entries and amounts as the category row)
function catDetail(id){
  const k = curMonth(), who = HUMANS.includes(prefs.spendWho) ? prefs.spendWho : "", c = state.budget.categories.find(x => x.id === id);
  if(id !== "none" && !c) return;
  const amt = t => who ? Math.round(shareOf(t, who)) : t.amount;
  const tx = netTx().filter(t => t.kind === "expense" && !t.cancelled && isDate(t.date) && t.date.slice(0, 7) === k && (t.categoryId || "none") === id && amt(t) > 0)
    .sort((a, b) => b.date.localeCompare(a.date) || amt(b) - amt(a));
  const total = tx.reduce((a, t) => a + amt(t), 0), L = !who && c ? lim(c, k) : 0;
  const sub = t => [niceDate(t.date), t.shared ? (who ? `shared · ${nameOf(t.paidBy)} paid ${money(t.amount)}` : `${splitLabel(t)} · ${nameOf(t.paidBy)} paid`) : `${nameOf(t.paidBy)}'s`,
    t.repaid ? `${money(t.gross)} − ${money(t.repaid)} paid back` : "", t.billId ? "from a bill" : ""].filter(Boolean).join(" · ");
  openSheet(c ? c.name : "Uncategorized", `
    <p style="margin:0">${esc(monthName(k))}: <b>${money(total)}</b>${who ? ` · ${esc(nameOf(who))}'s part` : ""}${L ? ` of ${money(L)} target${total > L ? ` · <span class="pill late">${money(total - L)} over</span>` : ` · ${money(L - total)} left`}` : ""} · ${tx.length} ${tx.length === 1 ? "entry" : "entries"}</p>
    ${tx.length ? `<div class="glist">${tx.map(t => `<button type="button" class="txrow" data-act="editTxn" data-id="${t.id}">
        <span class="av ${t.paidBy}">${sprite(t.paidBy, "", true)}</span>
        <span class="tb"><span class="tt">${esc(t.note || catName(t.categoryId))}</span><span class="ts">${esc(sub(t))}</span></span>
        <span class="ta expense">${money(amt(t))}</span></button>`).join("")}</div>`
      : `<div class="empty"><p>Nothing in ${esc(c ? c.name : "Uncategorized")} for ${esc(monthName(k))}${who ? ` for ${esc(nameOf(who))}` : ""}.</p></div>`}
    <p class="small muted" style="margin:0">Tap an entry to change it, or move it to another category.</p>
    <div class="actions">${c ? `<button type="button" class="link" data-act="editCat" data-id="${c.id}">Edit category</button>` : "<span></span>"}<div class="r"><button type="button" class="btn" data-act="closeSheet">Done</button></div></div>`, () => {}, false);
}
/* ---- forms ---- */
function catOptions(""")
rep("""  editCat: id => catForm(id || null),""", """  editCat: id => catForm(id || null),
  catDetail: id => catDetail(id),""")

# ---------- keep fixed bars at the bottom of what's on screen ----------
rep(""".fab{border-radius:4px;""", """.nav,.fab{translate:0 var(--vvfix,0px)}
.toast,.nudge{translate:0 var(--vvfix,0px)}
.fab{border-radius:4px;""")
rep("""let sheetFullH = window.innerHeight;""", r"""let sheetFullH = window.innerHeight;
// iPhone can leave bottom-pinned bars stuck partway up after the keyboard or a form closes. Move them to the
// bottom of what's actually on screen. vv: {height, offsetTop, scale}; layoutH: the layout viewport's height.
function vvShift(vv, layoutH){
  if(!vv || Math.abs((vv.scale || 1) - 1) > .01) return 0;               // pinch-zoomed: leave it alone
  if(document.body.classList.contains("typing")) return 0;               // bars are hidden while typing
  const d = Math.round(vv.offsetTop + vv.height - layoutH);
  return Math.abs(d) <= 1 ? 0 : d;
}
function fixBars(){
  if(!window.visualViewport) return;
  const d = vvShift(window.visualViewport, document.documentElement.clientHeight);
  document.documentElement.style.setProperty("--vvfix", d + "px");
}
// make iPhone redraw fixed bars (a no-op scroll), then re-anchor them
function nudgeBars(){ [60, 350].forEach(ms => setTimeout(() => { try { window.scrollTo(window.scrollX, window.scrollY); } catch(e){} fixBars(); }, ms)); }
document.addEventListener("focusout", () => setTimeout(() => { if(!document.body.classList.contains("typing")) nudgeBars(); }, 80));""")
rep("""  const onVV = () => { if(!document.querySelector(".sheet")){ sheetFullH = window.innerHeight; return; }""",
    """  const onVV = () => { fixBars(); if(!document.querySelector(".sheet")){ sheetFullH = window.innerHeight; return; }""")
rep("""  window.addEventListener("orientationchange", () => { sheetFullH = 0; setTimeout(onVV, 300); });""",
    """  window.addEventListener("orientationchange", () => { sheetFullH = 0; setTimeout(onVV, 300); });
  window.addEventListener("pageshow", nudgeBars); document.addEventListener("visibilitychange", () => { if(!document.hidden) nudgeBars(); });""")
rep("""function closeSheet(){ dupSheet.open = false; discardPendingPdf(); $("#sheetRoot").innerHTML = ""; document.documentElement.classList.remove("sheet-open");""",
    """function closeSheet(){ dupSheet.open = false; discardPendingPdf(); $("#sheetRoot").innerHTML = ""; document.documentElement.classList.remove("sheet-open"); nudgeBars();""")

rep('const BUILD = "2026-10-30 · 44";', 'const BUILD = "2026-10-31 · 45";')
rep("""const CHANGELOG = [""", """const CHANGELOG = [
  ["45", "2026-10-31", ["Tap a category to see the entries that make up its total.", "A fix for the bottom bar getting stuck partway up the screen on iPhone."]],""")
open(p, "w").write(s); print("patched")
