"""Step 7: Budget becomes a bottom tab; Family moves into More (Notes · Family · Settings).
Only this phone's view preferences change; household data is untouched. Usage: python3 patch_step7_tabs.py file.html"""
import sys
p = sys.argv[1]; s = open(p).read()
def rep(old, new, n=1):
    global s
    assert s.count(old) == n, (s.count(old), old[:90])
    s = s.replace(old, new)

rep('''const TABS = [["today","Today"],["chores","Chores"],["kitchen","Kitchen"],["family","Family"],["more","More"]];''',
    '''const TABS = [["today","Today"],["chores","Chores"],["kitchen","Kitchen"],["budget","Budget"],["more","More"]];''')
rep('''  wallet:''', '''  budget:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="7" y="2.5" width="10" height="3.5" rx="1"/><path d="M7.5 6h9c1.4 1.3 2.5 3 2.5 5.5V18a3.5 3.5 0 0 1-3.5 3.5h-7A3.5 3.5 0 0 1 5 18v-6.5C5 9 6.1 7.3 7.5 6z"/><circle cx="12" cy="15" r="2.6"/></svg>',
  wallet:''')
rep('''  v.innerHTML = ({today:viewToday, chores:viewChores, kitchen:viewKitchen, family:viewFamily, more:viewMore})[prefs.tab]();''',
    '''  v.innerHTML = ({today:viewToday, chores:viewChores, kitchen:viewKitchen, budget:viewBudgetArea, more:viewMore})[prefs.tab]();''')
rep('''  const mfab = {notes:["newNote","New note"], budget:bfab}[MTABS[prefs.moreTab] ? prefs.moreTab : "notes"];
  if(mfab) fabs.more = mfab;''', '''  if(bfab) fabs.budget = bfab;
  const mfab = {notes:["newNote","New note"]}[MTABS[prefs.moreTab] ? prefs.moreTab : "notes"];
  if(mfab) fabs.more = mfab;''')
rep('''const MTABS = {notes:"Notes", budget:"Budget", settings:"Settings"};''', '''const MTABS = {notes:"Notes", family:"Family", settings:"Settings"};''')
rep('''  return sub + (mt === "budget" ? viewBudgetArea() : mt === "settings" ? viewSettings() : viewNotes());''',
    '''  return sub + (mt === "family" ? viewFamily() : mt === "settings" ? viewSettings() : viewNotes());''')
rep('''<button class="link" type="button" data-act="tab" data-id="family">Family</button>''',
    '''<button class="link" type="button" data-act="goFam" data-id="${esc(prefs.fam)}">Family</button>''')
rep('''  goFam: id => { prefs.fam = id; prefs.tab = "family"; savePrefs(); render(); window.scrollTo(0,0); },''',
    '''  goFam: id => { if(PEOPLE.includes(id)) prefs.fam = id; prefs.tab = "more"; prefs.moreTab = "family"; savePrefs(); render(); window.scrollTo(0,0); },''')
rep('''  goBudget: () => { prefs.tab = "more"; prefs.moreTab = "budget"; prefs.budgetTab = "spending"; budgetMonth = null; savePrefs(); render(); window.scrollTo(0,0); }''',
    '''  goBudget: () => { prefs.tab = "budget"; prefs.budgetTab = "spending"; budgetMonth = null; savePrefs(); render(); window.scrollTo(0,0); }''')
# a phone last left on the old Family tab, or on More → Budget, opens where those now live
rep('''if(!HUMANS.includes(prefs.user)) prefs.user = "sam";''', '''if(prefs.tab === "family"){ prefs.tab = "more"; prefs.moreTab = "family"; }
if(prefs.tab === "more" && prefs.moreTab === "budget"){ prefs.tab = "budget"; prefs.moreTab = "notes"; }
if(!HUMANS.includes(prefs.user)) prefs.user = "sam";''')
open(p, 'w').write(s)
print("patched", p)

# privacy lines that were written before sync existed
s = open(p).read()
def rep2(old, new):
    global s
    assert s.count(old) == 1, (s.count(old), old[:90])
    s = s.replace(old, new)
rep2('''  <p class="private">${IC.lock} Stored only on this device for now. Nothing is uploaded.</p>''',
     '''  <p class="private">${IC.lock} ${sync.status === "on" ? "Shared only between your two Google accounts, in your private zen·dom database." : "Stored only on this device. Nothing is uploaded unless you sign in to share between phones."}</p>''')
rep2('''      <p class="small" style="margin:0">Everything is saved in this browser only. Copy a backup now and then and keep it in Notes or email it to yourself.</p>''',
     '''      <p class="small" style="margin:0">${sync.status === "on" ? "Everything is also kept in your shared database. A backup copy is still a good idea now and then: keep it in Notes or email it to yourself." : "Everything is saved in this browser only. Copy a backup now and then and keep it in Notes or email it to yourself."}</p>''')
open(p, 'w').write(s)
print("privacy lines updated")
