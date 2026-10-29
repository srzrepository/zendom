// Checks for the notifier with a stand-in for Google's servers. Run: node notifier/worker.test.mjs
import { generateKeyPairSync, createVerify } from "node:crypto";
import worker, { googleToken } from "./worker.js";

let pass = 0, fail = 0;
const check = (name, ok, detail) => { if (ok) pass++; else fail++; console.log((ok ? "PASS " : "FAIL ") + name + (!ok && detail ? "  [" + detail + "]" : "")); };

const { privateKey, publicKey } = generateKeyPairSync("rsa", { modulusLength: 2048 });
const SA = { project_id: "zendom-4ed52", client_email: "fb@zendom.iam.gserviceaccount.com", private_key: privateKey.export({ type: "pkcs8", format: "pem" }) };
const env = { GOOGLE_SA: JSON.stringify(SA), FIREBASE_API_KEY: "KEY", ALLOWED: "samzenteno@gmail.com,charliepurdomva@gmail.com", APP_ORIGIN: "https://srzrepository.github.io", APP_URL: "https://srzrepository.github.io/zendom/" };

const USERS = { "tok-sam": "samzenteno@gmail.com", "tok-charlie": "charliepurdomva@gmail.com", "tok-stranger": "x@example.com", "tok-unverified": "charliepurdomva@gmail.com" };
let devices, calls;
function reset() {
  calls = [];
  devices = [
    { id: "d1", owner: "charliepurdomva@gmail.com", token: "fcm-charlie-pixel", instant: true, morning: false },
    { id: "d2", owner: "charliepurdomva@gmail.com", token: "fcm-charlie-old", instant: true, morning: true },
    { id: "d3", owner: "samzenteno@gmail.com", token: "fcm-sam-iphone", instant: true, morning: true },
    { id: "d4", owner: "charliepurdomva@gmail.com", token: "fcm-charlie-optout", instant: false, morning: true }
  ];
}
let jwtSeen = null;
globalThis.fetch = async (url, opt = {}) => {
  url = String(url); calls.push({ url, opt });
  const res = (status, body) => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
  if (url.startsWith("https://identitytoolkit.googleapis.com/v1/accounts:lookup?key=KEY")) {
    const t = JSON.parse(opt.body).idToken; if (!USERS[t]) return res(400, { error: { message: "INVALID_ID_TOKEN" } });
    return res(200, { users: [{ email: USERS[t].toUpperCase(), emailVerified: t !== "tok-unverified" }] });
  }
  if (url === "https://oauth2.googleapis.com/token") { jwtSeen = new URLSearchParams(opt.body).get("assertion"); return res(200, { access_token: "ya29.test", expires_in: 3600 }); }
  if (url.includes("/documents/homes/zendom/devices") && (!opt.method || opt.method === "GET")) {
    return res(200, { documents: devices.map(d => ({ name: `projects/zendom-4ed52/databases/(default)/documents/homes/zendom/devices/${d.id}`,
      fields: { owner: { stringValue: d.owner }, token: { stringValue: d.token }, instant: { booleanValue: d.instant }, morning: { booleanValue: d.morning } } })) });
  }
  if (url.endsWith("/messages:send")) {
    const m = JSON.parse(opt.body).message;
    if (m.token === "fcm-charlie-old") return res(404, { error: { status: "NOT_FOUND", details: [{ errorCode: "UNREGISTERED" }] } });
    return res(200, { name: "projects/zendom-4ed52/messages/1" });
  }
  if (opt.method === "DELETE") { devices = devices.filter(d => !url.endsWith("/" + d.id)); return res(200, {}); }
  return res(500, { error: "unexpected " + url });
};
const post = (body, method = "POST", path = "/notify") => worker.fetch(new Request("https://zendom-notify.example.workers.dev" + path, { method, body: method === "POST" ? (typeof body === "string" ? body : JSON.stringify(body)) : undefined }), env);

reset();
let r = await post({ idToken: "tok-sam", title: "zen·dom", body: "Sam left a note: “tacos?”" });
let j = await r.json();
const sends = calls.filter(c => c.url.endsWith("/messages:send")).map(c => JSON.parse(c.opt.body).message);
check("Sam's note goes to Charlie's opted-in phones only", r.status === 200 && sends.map(m => m.token).sort().join() === "fcm-charlie-old,fcm-charlie-pixel", JSON.stringify(sends.map(m => m.token)));
check("never to the sender's own phone or an opted-out phone", !sends.some(m => m.token === "fcm-sam-iphone" || m.token === "fcm-charlie-optout"));
check("counts what was sent and what was gone", j.sent === 1 && j.gone === 1, JSON.stringify(j));
check("a phone Firebase says is gone is forgotten", !devices.some(d => d.id === "d2"));
check("message carries the text, icon and a link back to the app", sends[0].notification.body === "Sam left a note: “tacos?”" && sends[0].webpush.fcm_options.link === env.APP_URL && sends[0].webpush.notification.icon.endsWith("icon-192.png"));
check("answers allow the app's website", r.headers.get("Access-Control-Allow-Origin") === "https://srzrepository.github.io");

// the signed request to Google is a valid RS256 token for this service account
const [h, c, sig] = jwtSeen.split(".");
const v = createVerify("RSA-SHA256"); v.update(h + "." + c);
const claim = JSON.parse(Buffer.from(c, "base64url").toString());
check("Google sign-in request is correctly signed", v.verify(publicKey, Buffer.from(sig, "base64url")));
check("and asks only for Firestore and Cloud Messaging", claim.iss === SA.client_email && claim.aud === "https://oauth2.googleapis.com/token" && claim.scope === "https://www.googleapis.com/auth/datastore https://www.googleapis.com/auth/firebase.messaging" && claim.exp - claim.iat === 3600);
const before = calls.filter(x => x.url === "https://oauth2.googleapis.com/token").length;
await post({ idToken: "tok-charlie", body: "Charlie finished “Water the plants”" });
check("reuses the Google token instead of signing again", calls.filter(x => x.url === "https://oauth2.googleapis.com/token").length === before);

reset();
r = await post({ idToken: "tok-charlie", body: "Charlie finished “Water the plants”" });
check("Charlie's nudge reaches Sam", (await r.json()).sent === 1 && calls.some(x => x.url.endsWith("/messages:send") && JSON.parse(x.opt.body).message.token === "fcm-sam-iphone"));

reset();
r = await post({ idToken: "tok-sam", test: true, body: "Test" });
j = await r.json();
const ts = calls.filter(x => x.url.endsWith("/messages:send")).map(x => JSON.parse(x.opt.body).message.token);
check("test goes only to the sender's own phones", j.sent === 1 && ts.join() === "fcm-sam-iphone", JSON.stringify(ts));

for (const [name, body, code] of [["no sign-in", { body: "hi" }, 401], ["bad sign-in", { idToken: "nope", body: "hi" }, 401],
  ["unverified email", { idToken: "tok-unverified", body: "hi" }, 401], ["someone else's account", { idToken: "tok-stranger", body: "hi" }, 403],
  ["empty message", { idToken: "tok-sam", body: "" }, 400], ["not JSON", "{oops", 400]]) {
  reset(); r = await post(body);
  check(`refuses: ${name}`, r.status === code && !calls.some(x => x.url.endsWith("/messages:send")), r.status);
}
reset(); r = await post({ idToken: "tok-sam", body: "x".repeat(500), title: "t".repeat(200) });
const m = JSON.parse(calls.find(x => x.url.endsWith("/messages:send")).opt.body).message;
check("long text is trimmed", m.notification.body.length === 180 && m.notification.title.length === 60);
r = await worker.fetch(new Request("https://x.workers.dev/notify", { method: "OPTIONS" }), env);
check("answers the browser's pre-check", r.status === 204 && r.headers.get("Access-Control-Allow-Methods") === "POST");
r = await post(null, "GET", "/");
check("anything else is not found", r.status === 404);

console.log(`\n${pass} of ${pass + fail} notifier checks passed`);
process.exit(fail ? 1 : 0);
