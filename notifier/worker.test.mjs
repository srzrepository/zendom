// Checks for the notifier with a stand-in for Google's servers. Run: node notifier/worker.test.mjs
import { generateKeyPairSync, createVerify } from "node:crypto";
import worker, { googleToken, recipeFromHtml, duration, clean } from "./worker.js";

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
const PAGES = {
  // WordPress-style: Recipe inside @graph, sections, entities, ISO durations, yield as a list
  tacos: `<html><head><title>Tacos | Blog</title><script type="application/ld+json">{"@context":"https://schema.org","@graph":[{"@type":"WebPage","name":"x"},
    {"@type":["Recipe"],"name":"Weeknight Fish Tacos &amp; Slaw","recipeYield":["4","4 servings"],"prepTime":"PT15M","cookTime":"PT1H5M",
     "description":"Crispy &#8220;fish&#8221; tacos.","recipeIngredient":["1 lb cod","2 cups cabbage, <b>shredded</b>","&frac12; cup crema"],
     "recipeInstructions":[{"@type":"HowToSection","name":"Slaw","itemListElement":[{"@type":"HowToStep","text":"Toss the cabbage."}]},
       {"@type":"HowToSection","name":"Fish","itemListElement":[{"@type":"HowToStep","text":"Season the cod."},{"@type":"HowToStep","text":"Fry 4 minutes a side."}]}]}]}</script></head><body>...</body></html>`,
  // plain: instructions as one string, only totalTime
  soup: `<script type=application/ld+json>[{"@type":"Recipe","name":"Miso Soup","recipeYield":"Serves 2","totalTime":"PT20M","recipeIngredient":["4 cups dashi","3 tbsp miso"],"recipeInstructions":"Warm the dashi. Whisk in the miso. Do not boil."}]</script>`,
  plain: `<html><head><meta property="og:title" content="My Grandma's Pie"></head><body>no structured data</body></html>`
};
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
  if (url.startsWith("https://recipes.test/")) {
    if (url.endsWith("/gone")) return new Response("nope", { status: 404 });
    const page = PAGES[url.split("/").pop()]; return new Response(page, { status: 200, headers: { "Content-Type": "text/html" } });
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

r = await worker.fetch(new Request("https://x.workers.dev/notify", { method: "POST", body: JSON.stringify({ idToken: "tok-sam", body: "hi" }) }), Object.assign({}, env, { GOOGLE_SA: undefined }));
j = await r.json();
check("a missing secret is explained, with CORS so the app can show it", r.status === 500 && /GOOGLE_SA secret/.test(j.error) && r.headers.get("Access-Control-Allow-Origin") === env.APP_ORIGIN, JSON.stringify(j));
r = await worker.fetch(new Request("https://x.workers.dev/notify", { method: "POST", body: JSON.stringify({ idToken: "tok-sam", body: "hi" }) }), Object.assign({}, env, { GOOGLE_SA: "{\"project_id\":\"x\"" }));
check("a half-pasted secret is explained", /entire \.json/.test((await r.json()).error));
const realFetch = globalThis.fetch; globalThis.fetch = async () => { throw new Error("network down"); };
r = await post({ idToken: "tok-sam", body: "hi" }); j = await r.json(); globalThis.fetch = realFetch;
check("any other failure comes back as a readable message", r.status === 500 && /notifier problem: network down/.test(j.error) && r.headers.get("Access-Control-Allow-Origin") === env.APP_ORIGIN, JSON.stringify(j));

// ---------- recipe links ----------
const rpost = body => worker.fetch(new Request("https://x.workers.dev/recipe", { method: "POST", body: JSON.stringify(body) }), env);
r = await rpost({ idToken: "tok-sam", url: "https://recipes.test/tacos" }); j = await r.json();
check("recipe: reads a recipe inside @graph", r.status === 200 && j.found && j.title === "Weeknight Fish Tacos & Slaw", JSON.stringify(j));
check("recipe: servings, prep and cook times", j.servings === 4 && j.prep === "15 min" && j.cook === "1 hr 5 min", JSON.stringify([j.servings, j.prep, j.cook]));
check("recipe: ingredients cleaned of tags and entities", JSON.stringify(j.ingredients) === JSON.stringify(["1 lb cod", "2 cups cabbage, shredded", "½ cup crema"]), JSON.stringify(j.ingredients));
check("recipe: steps keep their section headings", JSON.stringify(j.steps) === JSON.stringify(["SLAW:", "Toss the cabbage.", "FISH:", "Season the cod.", "Fry 4 minutes a side."]), JSON.stringify(j.steps));
check("recipe: keeps the description and the link", j.notes === "Crispy “fish” tacos." && j.source === "https://recipes.test/tacos");
r = await rpost({ idToken: "tok-charlie", url: "https://recipes.test/soup" }); j = await r.json();
check("recipe: one-paragraph instructions split into steps", JSON.stringify(j.steps) === JSON.stringify(["Warm the dashi.", "Whisk in the miso.", "Do not boil."]) && j.servings === 2 && j.cook === "20 min", JSON.stringify(j));
r = await rpost({ idToken: "tok-sam", url: "https://recipes.test/plain" }); j = await r.json();
check("recipe: a page without recipe data says so, with the page title", r.status === 200 && j.found === false && j.title === "My Grandma's Pie", JSON.stringify(j));
r = await rpost({ idToken: "tok-sam", url: "https://recipes.test/gone" });
check("recipe: a missing page is reported", r.status === 502 && /404/.test((await r.json()).error));
for (const [name, body, code] of [["not signed in", { url: "https://recipes.test/tacos" }, 401], ["someone else", { idToken: "tok-stranger", url: "https://recipes.test/tacos" }, 403],
  ["not a link", { idToken: "tok-sam", url: "tacos please" }, 400], ["a local address", { idToken: "tok-sam", url: "http://127.0.0.1/admin" }, 400], ["a file", { idToken: "tok-sam", url: "file:///etc/passwd" }, 400]]) {
  r = await rpost(body); check(`recipe: refuses ${name}`, r.status === code, r.status);
}
check("recipe: works without the notification secret", (await (await worker.fetch(new Request("https://x.workers.dev/recipe", { method: "POST", body: JSON.stringify({ idToken: "tok-sam", url: "https://recipes.test/soup" }) }), Object.assign({}, env, { GOOGLE_SA: undefined }))).json()).found === true);
check("recipe: duration helper", duration("PT2H") === "2 hr" && duration("PT45M") === "45 min" && duration("P0DT1H30M") === "1 hr 30 min" && duration("") === "");
console.log(`\n${pass} of ${pass + fail} notifier checks passed`);
process.exit(fail ? 1 : 0);
