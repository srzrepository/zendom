"""Step 22: fix a race in combining edits. If the other phone's version of a record arrives while
this phone's save of the same record is still in flight, the finished save must not overwrite the
newer copy we keep as the merge base (that could bring back something the other phone deleted).
Instead that record is re-checked against the server on the next save.
Usage: python3 patch_step22_race.py file.html"""
import sys
p = sys.argv[1]; s = open(p).read()
def rep(old, new):
    global s
    assert s.count(old) == 1, (s.count(old), old[:90])
    s = s.replace(old, new)
rep("""const sync = {status:"off", user:null, err:"", last:{}, ever:false, unsub:null, timer:0, at:0, pending:0, offline:false, retry:0};""",
    """const sync = {status:"off", user:null, err:"", last:{}, ever:false, unsub:null, timer:0, at:0, pending:0, offline:false, retry:0, rseq:{}};""")
rep("""    applyRecord(state, c.id, data); applied.push(c.id);
  });""", """    applyRecord(state, c.id, data); applied.push(c.id); sync.rseq[c.id] = (sync.rseq[c.id] || 0) + 1;
  });""")
rep("""  const base0 = {}; writes.forEach(w => { base0[w.id] = sync.shadow ? sync.shadow[w.id] : undefined; });   // before notifyCollect moves it on""",
    """  const base0 = {}, seq0 = {}; writes.forEach(w => { base0[w.id] = sync.shadow ? sync.shadow[w.id] : undefined; seq0[w.id] = sync.rseq[w.id] || 0; });   // before notifyCollect moves it on""")
rep("""    const merged = (res || []).filter(x => x.data && x.data.merged);
    (res || []).forEach(x => { if(!sync.shadow) return; if(x.data.del) delete sync.shadow[x.id]; else sync.shadow[x.id] = x.data.j; });""",
"""    // a newer version of a record arrived while this save was in flight: keep what arrived, re-check it on the next save
    const raced = new Set((res || []).filter(x => (sync.rseq[x.id] || 0) !== seq0[x.id]).map(x => x.id));
    raced.forEach(id => { delete sync.last[id]; });
    const merged = (res || []).filter(x => x.data && x.data.merged && !raced.has(x.id));
    (res || []).forEach(x => { if(!sync.shadow || raced.has(x.id)) return; if(x.data.del) delete sync.shadow[x.id]; else sync.shadow[x.id] = x.data.j; });
    if(raced.size) syncSchedule();""")
open(p, "w").write(s); print("step 22 applied")
