import json, subprocess, os, sys, tempfile
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
ROOT = "/home/claude/zendom-gh"
key = rsa.generate_private_key(public_exponent=65537, key_size=2048).private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
SA = json.dumps({"project_id": "zendom-4ed52", "client_email": "x@y", "private_key": key})
res = []
def check(n, ok, d=""): res.append(ok); print(("PASS " if ok else "FAIL ") + n + (f"  [{d}]" if d and not ok else ""))
chore = lambda id, title, owner, start, last=None, freq="weekly": {"id": id, "data": {"title": title, "owner": owner, "freq": freq, "everyDays": None, "start": start, "lastDone": last, "history": [], "done": False, "standard": "", "cpe": {"c": "", "p": "", "e": ""}, "example": False}}
records = [
  chore("chore~c1", "Water the plants", "sam", "2026-10-29"),
  chore("chore~c2", "Scoop the litter box", "charlie", "2026-10-29", freq="daily"),
  chore("chore~c3", "Take out the trash", "charlie", "2026-10-20"),
  chore("chore~c4", "Change the bedsheets", "sam", "2026-11-02"),
  chore("chore~c5", "Already done today", "sam", "2026-10-29", last="2026-10-29", freq="daily"),
  {"id": "bill~b1", "data": {"name": "Rent", "amount": 250000, "cycle": "monthly", "nextDue": "2026-10-29", "anchorDay": 29, "categoryId": None, "paidBy": "sam", "shared": True, "autopay": False}},
  {"id": "event~e1", "data": {"title": "Vet: Paprika", "date": "2026-10-29", "time": "14:30", "who": "", "repeat": "none", "note": ""}},
  {"id": "chore~gone", "del": True, "data": {}},
]
devices = [{"owner": "samzenteno@gmail.com", "token": "fcm-sam", "morning": True}, {"owner": "charliepurdomva@gmail.com", "token": "fcm-charlie", "morning": True},
           {"owner": "charliepurdomva@gmail.com", "token": "fcm-charlie-off", "morning": False}]
def run(now, meta=None, devs=devices, recs=records, extra=None):
    d = tempfile.mkdtemp(); f = os.path.join(d, "s.json"); out = os.path.join(d, "out.jsonl")
    json.dump({"records": recs, "devices": devs, "metaDate": meta}, open(f, "w")); open(out, "w").close()
    e = dict(os.environ, GOOGLE_SA=SA, ZD_NOW=now, ZD_FAKE=f, ZD_FAKE_OUT=out, NODE_PATH="/opt/npm-tools/node_modules", **(extra or {}))
    p = subprocess.run(["node", "--import", ROOT + "/tools/test/fake-google.mjs", ROOT + "/tools/morning.mjs"], env=e, capture_output=True, text=True, timeout=90)
    return p, [json.loads(l) for l in open(out) if l.strip()]
p, out = run("2026-10-29T15:20:00Z")          # 8:20 am PDT
sends = {m["to"]: m for m in out if "to" in m}
check("runs cleanly", p.returncode == 0, p.stderr[-600:])
check("sends to both opted-in phones, not the opted-out one", set(sends) == {"fcm-sam", "fcm-charlie"}, str(list(sends)))
s, c = sends.get("fcm-sam", {}), sends.get("fcm-charlie", {})
check("Sam's title greets Sam", s.get("title") == "Good morning, Sam")
check("Sam's own chores first", s.get("body", "").startswith("Yours: Water the plants."), s.get("body"))
check("shared items: Charlie's chore, rent (no amount), vet with time", "Scoop the litter box (Charlie)" in s.get("body", "") and "Rent due" in s.get("body", "") and "2,500" not in s.get("body", "") and "Vet: Paprika 2:30" in s.get("body", ""), s.get("body"))
check("overdue listed", "Overdue: Take out the trash" in s.get("body", ""), s.get("body"))
check("skips done and future chores", "Already done" not in s.get("body", "") and "bedsheets" not in s.get("body", ""))
check("Charlie's version leads with his chore", c.get("body", "").startswith("Yours: Scoop the litter box."), c.get("body"))
check("remembers it sent today", {"meta": "2026-10-29"} in out)
p2, out2 = run("2026-10-29T15:20:00Z", recs=records + [{"id": "txn~t1", "data": {"kind": "expense", "amount": 200000, "date": "2026-10-28", "categoryId": None, "paidBy": "charlie", "shared": True, "note": "Rent"}}])
s2 = {m["to"]: m for m in out2 if "to" in m}
check("Sam owes half of rent Charlie paid: her morning says to pay him back, no amount", "Pay Charlie back for shared spending" in s2.get("fcm-sam", {}).get("body", "") and "1,000" not in s2.get("fcm-sam", {}).get("body", ""), s2.get("fcm-sam", {}).get("body"))
check("…and Charlie's doesn't", "Pay" not in s2.get("fcm-charlie", {}).get("body", ""), s2.get("fcm-charlie", {}).get("body"))
check("fits on a lock screen", all(len(m["body"]) <= 178 for m in sends.values()))
p, out = run("2026-10-29T16:20:00Z", meta="2026-10-29")
check("second run the same day sends nothing", not [m for m in out if "to" in m] and "Already sent" in p.stdout, p.stdout)
p, out = run("2026-10-29T14:20:00Z")          # 7:20 am PDT
check("too early: sends nothing", not out and "between 8 and noon" in p.stdout, p.stdout)
p, out = run("2026-12-03T16:20:00Z", recs=[])  # 8:20 am PST, nothing due
check("winter time window works and nothing due means no message", p.returncode == 0 and not [m for m in out if "to" in m] and "Nothing due" in p.stdout, p.stdout + p.stderr[-300:])
p, out = run("2026-10-29T15:20:00Z", devs=[{"owner": "samzenteno@gmail.com", "token": "fcm-sam", "morning": False}])
check("nobody opted in: nothing sent", not out and "No phones" in p.stdout)
p, out = run("2026-10-29T03:00:00Z", extra={"FORCE": "1"})
check("manual 'send now' ignores the time window", len([m for m in out if "to" in m]) == 2, p.stdout + p.stderr[-300:])
print(f"\n{sum(res)} of {len(res)} morning checks passed"); sys.exit(0 if all(res) else 1)
