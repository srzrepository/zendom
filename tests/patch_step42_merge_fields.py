"""Step 42: fix sync stopping with "The database turned this account away".
When both phones changed the same item, the combined version went to the database with an extra
internal field ("merged"). The database rules only accept del, j, t, by and ts, so it refused the
whole save, and every save after it in that batch: syncing stopped until something changed.
Now that flag stays on this phone (it's not an enumerable field, so it's never sent).
No data change. Usage: python3 patch_step42_merge_fields.py file.html"""
import sys
p = sys.argv[1]; s = open(p).read()
def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (s.count(old), old[:100])
    s = s.replace(old, new)
rep("""  return Object.assign({}, w.data, {j: JSON.stringify(merge3(b, l, r)), merged: true});""",
    """  const out = Object.assign({}, w.data, {j: JSON.stringify(merge3(b, l, r))});
  // "merged" is for this phone only: the database accepts just del, j, t, by and ts, and refuses the whole
  // save if anything else is sent. A non-enumerable property isn't copied into what's written.
  Object.defineProperty(out, "merged", {value: true, enumerable: false});
  return out;""")
rep('const BUILD = "2026-10-30 · 41";', 'const BUILD = "2026-10-30 · 42";')
rep("""const CHANGELOG = [""", """const CHANGELOG = [
  ["42", "2026-10-30", ["Fixed: syncing could stop with “The database turned this account away” after you both edited the same thing. Your edits were kept on the phone and go out once both phones update."]],""")
open(p, "w").write(s)
print("patched")
