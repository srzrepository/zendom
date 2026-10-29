// Stand-in for Google's servers, loaded with: node --import ./tools/test/fake-google.mjs tools/morning.mjs
import fs from "node:fs";
const S = JSON.parse(fs.readFileSync(process.env.ZD_FAKE, "utf8"));
const log = m => fs.appendFileSync(process.env.ZD_FAKE_OUT, JSON.stringify(m) + "\n");
const res = (status, body) => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
globalThis.fetch = async (url, opt = {}) => {
  url = String(url);
  if (url === "https://oauth2.googleapis.com/token") return res(200, { access_token: "ya29.t", expires_in: 3600 });
  if (url.includes("/homes/zendom/meta/morning")) {
    if (opt.method === "PATCH") { log({ meta: JSON.parse(opt.body).fields.date.stringValue }); return res(200, {}); }
    return S.metaDate ? res(200, { fields: { date: { stringValue: S.metaDate } } }) : res(404, {});
  }
  if (url.includes("/homes/zendom/devices")) return res(200, { documents: S.devices.map((d, i) => ({ name: "projects/p/databases/(default)/documents/homes/zendom/devices/d" + i,
    fields: { owner: { stringValue: d.owner }, token: { stringValue: d.token }, instant: { booleanValue: !!d.instant }, morning: { booleanValue: !!d.morning } } })) });
  if (url.includes("/homes/zendom/records")) return res(200, { documents: S.records.map(r => ({ name: "projects/p/databases/(default)/documents/homes/zendom/records/" + r.id,
    fields: { del: { booleanValue: !!r.del }, j: { stringValue: JSON.stringify(r.data) } } })) });
  if (url.endsWith("/messages:send")) { const m = JSON.parse(opt.body).message; log({ to: m.token, title: m.notification.title, body: m.notification.body }); return res(200, {}); }
  return res(500, { error: url });
};
