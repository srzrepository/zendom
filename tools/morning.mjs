// zen·dom morning reminders. Run by .github/workflows/morning.yml (or by hand: GOOGLE_SA=... node tools/morning.mjs).
// Sends once per day, between 8 and 11:59 am Pacific, to phones that turned on "Morning reminders".
// The summary is worked out by the app itself (index.html in a headless browser), so it matches what the app shows.
// Env: GOOGLE_SA (service account JSON). Optional: FORCE=1 (ignore the time window and the once-a-day check),
//      DRY_RUN=1 (print, don't send), ZD_NOW (ISO time, for tests), ZD_FIRESTORE (base URL, for tests).
import { chromium } from "playwright";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { googleToken, listDevices, sendTo } from "../notifier/worker.js";

const TZ = "America/Los_Angeles";
const APP_URL = "https://srzrepository.github.io/zendom/";
const env = { GOOGLE_SA: process.env.GOOGLE_SA || "" };
if (!env.GOOGLE_SA) { console.log("GOOGLE_SA is not set: nothing to do."); process.exit(0); }
const sa = JSON.parse(env.GOOGLE_SA);
const base = process.env.ZD_FIRESTORE || `https://firestore.googleapis.com/v1/projects/${sa.project_id}/databases/(default)/documents`;
const now = process.env.ZD_NOW ? new Date(process.env.ZD_NOW) : new Date();
const local = Object.fromEntries(new Intl.DateTimeFormat("en-CA", { timeZone: TZ, year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", hourCycle: "h23" })
  .formatToParts(now).map(p => [p.type, p.value]));
const today = `${local.year}-${local.month}-${local.day}`, hour = +local.hour;
const force = process.env.FORCE === "1";

if (!force && (hour < 8 || hour > 11)) { console.log(`It's ${hour}:00 in ${TZ}; reminders go out between 8 and noon.`); process.exit(0); }
const token = await googleToken(env, now.getTime());
const auth = { Authorization: "Bearer " + token };
const meta = await fetch(`${base}/homes/zendom/meta/morning`, { headers: auth });
if (!force && meta.ok) { const m = await meta.json(); if (m.fields && m.fields.date && m.fields.date.stringValue === today) { console.log("Already sent today."); process.exit(0); } }

const devices = (await listDevices(env, token)).filter(d => d.morning && d.token);
if (!devices.length) { console.log("No phones have morning reminders on."); process.exit(0); }

const records = []; let page = "";
for (let i = 0; i < 50; i++) {
  const r = await fetch(`${base}/homes/zendom/records?pageSize=300${page ? "&pageToken=" + encodeURIComponent(page) : ""}`, { headers: auth });
  if (!r.ok) throw new Error("records " + r.status);
  const j = await r.json();
  (j.documents || []).forEach(d => { const f = d.fields || {}; if (!(f.del && f.del.booleanValue) && f.j && f.j.stringValue) records.push({ id: d.name.split("/").pop(), j: f.j.stringValue }); });
  if (!j.nextPageToken) break; page = j.nextPageToken;
}

// Ask the app what's due
const browser = await chromium.launch();
const ctx = await browser.newContext({ timezoneId: TZ });
await ctx.addInitScript("window.zdBackend = {onUser(){}, push:null};");   // the app runs offline here
const pg = await ctx.newPage();
await pg.clock.setFixedTime(now);
const indexFile = path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "index.html");
await pg.goto("file://" + indexFile);
const summary = await pg.evaluate(recs => {
  const st = emptyHousehold();
  recs.forEach(r => { try { applyRecord(st, r.id, JSON.parse(r.j)); } catch (e) {} });
  state = normalize(st);
  const t = todayStr();
  const chores = state.chores.filter(c => !(c.freq === "once" && c.done) && !doneToday(c) && dueInfo(c).rank <= 1)
    .map(c => ({ title: c.title, owner: c.owner, late: dueInfo(c).rank === 0 }));
  const items = calendarItems(t, t).filter(x => ["bill", "event", "health", "bday"].includes(x.type)).map(x => {
    const bill = x.type === "bill" && state.budget.bills.find(b => b.id === x.id);
    return { type: x.type, text: (bill ? bill.name + " due" : x.title) + (x.time ? " " + fmtTime(x.time) : ""), late: x.flag === "overdue" };
  });
  return { chores, items, names: { sam: nameOf("sam"), charlie: nameOf("charlie") }, accounts: ACCOUNTS };
}, records);
await browser.close();

const cap = (s, n) => s.length > n ? s.slice(0, n - 1) + "…" : s;
function message(who) {
  const mine = summary.chores.filter(c => c.owner === who), theirs = summary.chores.filter(c => c.owner !== who);
  const late = [...mine, ...theirs, ...summary.items].filter(x => x.late);
  const parts = [];
  const today = [...mine.filter(c => !c.late).map(c => c.title)];
  if (today.length) parts.push("Yours: " + today.join(", "));
  const shared = [...theirs.filter(c => !c.late).map(c => c.owner ? `${c.title} (${summary.names[c.owner]})` : c.title), ...summary.items.filter(x => !x.late).map(x => x.text)];
  if (shared.length) parts.push("Also: " + shared.join(", "));
  if (late.length) parts.push("Overdue: " + late.map(x => x.title || x.text).join(", "));
  return parts.length ? cap(parts.join(". ") + ".", 178) : null;
}
let sent = 0;
for (const d of devices) {
  const who = Object.keys(summary.accounts).find(k => summary.accounts[k].includes(d.owner));
  if (!who) continue;
  const body = message(who);
  if (!body) { console.log(`Nothing due for ${who}; no message.`); continue; }
  const title = `Good morning, ${summary.names[who]}`;
  if (process.env.DRY_RUN === "1") { console.log(`[dry run] ${d.owner}: ${title} — ${body}`); continue; }
  const res = await sendTo(env, token, d, title, body, APP_URL);
  if (res === "ok") sent++;
  if (res === "gone") await fetch("https://firestore.googleapis.com/v1/" + d.name, { method: "DELETE", headers: auth });
  console.log(`${d.owner}: ${res}`);
}
if (process.env.DRY_RUN !== "1") {
  await fetch(`${base}/homes/zendom/meta/morning?updateMask.fieldPaths=date`, { method: "PATCH", headers: Object.assign({ "Content-Type": "application/json" }, auth),
    body: JSON.stringify({ fields: { date: { stringValue: today } } }) });
}
console.log(`Sent ${sent} morning reminder(s) for ${today}.`);
