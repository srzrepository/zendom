"""Step 1: monthly/yearly date drift fix (schema v6 -> v7). Usage: python3 patch_step1_dates.py file.html"""
import sys
p = sys.argv[1]; s = open(p).read()
def rep(old, new):
    global s
    assert s.count(old) == 1, (s.count(old), old[:90])
    s = s.replace(old, new)
rep('''function diffDays(a, b){''','''// Same date with the day of the month set to `day`, clamped to that month's length (31 -> 30, 28 or 29)
function withDay(s, day){ if(!day) return s; const [y, m] = s.split("-").map(Number); const last = new Date(y, m, 0).getDate(); return `${y}-${pad(m)}-${pad(Math.min(day, last))}`; }
// The k-th repeat after `first`. Monthly and yearly repeats are counted from `first` itself (not from the
// previous, possibly shortened, date), so the 31st stays the 31st and Feb 29 comes back in leap years.
function nthRepeat(first, kind, n, k, anchorDay){
  if(kind === "monthly") return withDay(addMonths(first, k), anchorDay);
  if(kind === "yearly") return withDay(addMonths(first, 12 * k), anchorDay);
  return addDays(first, k * ({daily:1, weekly:7, biweekly:14}[kind] || n || 7));
}
function diffDays(a, b){''')
rep('const SCHEMA = 6;','const SCHEMA = 7;')
rep('''  5: d => Object.assign({}, d, {version: 6})    // v6 adds the monthly plan and the Fun Fund; normalize fills defaults''',
'''  5: d => Object.assign({}, d, {version: 6}),   // v6 adds the monthly plan and the Fun Fund; normalize fills defaults
  6: d => Object.assign({}, d, {version: 7})    // v7 gives each bill a fixed day of the month (anchorDay); normalize takes it from the current due date''')
rep('''  const project = (first, kind, n, o) => { let d = first, guard = 0; while(d <= to && guard++ < 800){ push(d, o); d = stepDate(d, kind, n); } };''',
'''  const project = (first, kind, n, o, anchorDay) => { let d = first; for(let k = 1; d <= to && k < 5000; k++){ push(d, o); d = nthRepeat(first, kind, n, k, anchorDay); } };''')
rep('''    if(due < t){ push(t, Object.assign({}, o, {flag:"overdue"})); due = stepDate(t, c.freq, c.everyDays); }''',
'''    if(due < t){ push(t, Object.assign({}, o, {flag:"overdue"})); due = nthRepeat(t, c.freq, c.everyDays, 1); }''')
rep('''act:"editBill", id:b.id}));''', '''act:"editBill", id:b.id}, b.anchorDay));''')
rep('''    else { let d = e.date, guard = 0; while(d < from && guard++ < 2000) d = stepDate(d, e.repeat); project(d, e.repeat, 0, o); }''',
'''    else project(e.date, e.repeat, 0, o);''')
rep('''function nextBillDate(b){ return b.cycle === "weekly" ? addDays(b.nextDue, 7) : b.cycle === "yearly" ? addMonths(b.nextDue, 12) : addMonths(b.nextDue, 1); }''',
'''function nextBillDate(b){ return nthRepeat(b.nextDue, b.cycle, 0, 1, b.anchorDay || +b.nextDue.slice(8)); }''')
rep('''cycle: BILL_CYCLES[x.cycle] ? x.cycle : "monthly",
''', '''cycle: BILL_CYCLES[x.cycle] ? x.cycle : "monthly",
      anchorDay: clampInt(x.anchorDay, 1, 31, +x.nextDue.slice(8)),
''')
rep('''    if(b) Object.assign(b, data); else state.budget.bills.push(Object.assign({id:uid()}, data));''',
'''    if(!b || b.nextDue !== due) data.anchorDay = +due.slice(8);   // a newly typed date sets the day it repeats on
    if(b) Object.assign(b, data); else state.budget.bills.push(Object.assign({id:uid()}, data));''')
import re
s2 = re.sub(r'^function stepDate\(d, kind, n\)\{.*\n', '', s, count=1, flags=re.M)
assert s2 != s; s = s2
assert 'stepDate' not in s
open(p, 'w').write(s)
print("patched", p)
