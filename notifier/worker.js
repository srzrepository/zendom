// zen·dom notifier: a Cloudflare Worker (free plan). Paste this whole file into the Worker's code editor.
//
// POST /notify   body (text/plain JSON): {idToken, title, body, test?}
// POST /recipe   body (text/plain JSON): {idToken, url} -> the recipe on that web page, read from the
//                schema.org "Recipe" data most recipe sites include for search engines.
//   1. Checks idToken with Google (Identity Toolkit accounts:lookup): must be a verified email on ALLOWED.
//   2. Lists phones in Firestore homes/zendom/devices (each phone saves itself there when someone opts in).
//   3. Sends to the OTHER person's phones that turned on "notes and nudges" (test: to the sender's own phones).
//   4. Forgets phones Firebase says are gone.
// Settings (Worker → Settings → Variables and Secrets):
//   GOOGLE_SA        secret: the Firebase service account JSON (whole file contents)
//   FIREBASE_API_KEY text:   AIzaSyAQN7j7SWw0gzZyprK45qx4-IgliQdylE4
//   ALLOWED          text:   samzenteno@gmail.com,charliepurdomva@gmail.com
//   APP_ORIGIN       text:   https://srzrepository.github.io
//   APP_URL          text:   https://srzrepository.github.io/zendom/

let cachedToken = null;   // {token, exp} — lives as long as this Worker instance

const json = (obj, status, env) => new Response(JSON.stringify(obj), {
  status: status || 200,
  headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": (env && env.APP_ORIGIN) || "*", "Vary": "Origin" }
});

function b64url(bytes) {
  let s = ""; const a = bytes instanceof Uint8Array ? bytes : new TextEncoder().encode(bytes);
  for (let i = 0; i < a.length; i++) s += String.fromCharCode(a[i]);
  return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}
function pemToBytes(pem) {
  const b = atob(pem.replace(/-----[^-]+-----/g, "").replace(/\s+/g, ""));
  const out = new Uint8Array(b.length); for (let i = 0; i < b.length; i++) out[i] = b.charCodeAt(i); return out;
}

// A short-lived Google access token for Firestore + Cloud Messaging, from the service account.
export async function googleToken(env, now = Date.now()) {
  if (cachedToken && cachedToken.exp > now + 60000) return cachedToken.token;
  const sa = JSON.parse(env.GOOGLE_SA);
  const iat = Math.floor(now / 1000);
  const head = b64url(JSON.stringify({ alg: "RS256", typ: "JWT" }));
  const claim = b64url(JSON.stringify({
    iss: sa.client_email, aud: "https://oauth2.googleapis.com/token", iat, exp: iat + 3600,
    scope: "https://www.googleapis.com/auth/datastore https://www.googleapis.com/auth/firebase.messaging"
  }));
  const key = await crypto.subtle.importKey("pkcs8", pemToBytes(sa.private_key), { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" }, false, ["sign"]);
  const sig = new Uint8Array(await crypto.subtle.sign("RSASSA-PKCS1-v1_5", key, new TextEncoder().encode(head + "." + claim)));
  const r = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: "grant_type=" + encodeURIComponent("urn:ietf:params:oauth:grant-type:jwt-bearer") + "&assertion=" + head + "." + claim + "." + b64url(sig)
  });
  if (!r.ok) throw new Error("google token " + r.status);
  const j = await r.json();
  cachedToken = { token: j.access_token, exp: now + (j.expires_in || 3600) * 1000 };
  return cachedToken.token;
}

export async function listDevices(env, token) {
  const sa = JSON.parse(env.GOOGLE_SA), out = [];
  let page = "";
  for (let i = 0; i < 10; i++) {
    const url = `https://firestore.googleapis.com/v1/projects/${sa.project_id}/databases/(default)/documents/homes/zendom/devices?pageSize=100${page ? "&pageToken=" + encodeURIComponent(page) : ""}`;
    const r = await fetch(url, { headers: { Authorization: "Bearer " + token } });
    if (!r.ok) throw new Error("firestore list " + r.status);
    const j = await r.json();
    (j.documents || []).forEach(d => {
      const f = d.fields || {};
      out.push({ name: d.name, owner: (f.owner && f.owner.stringValue || "").toLowerCase(), token: f.token && f.token.stringValue || "",
        instant: !!(f.instant && f.instant.booleanValue), morning: !!(f.morning && f.morning.booleanValue) });
    });
    if (!j.nextPageToken) break; page = j.nextPageToken;
  }
  return out;
}

// Send one notification to one phone. Returns "ok", "gone" (forget this phone) or "error".
export async function sendTo(env, token, device, title, body, link) {
  const sa = JSON.parse(env.GOOGLE_SA);
  const r = await fetch(`https://fcm.googleapis.com/v1/projects/${sa.project_id}/messages:send`, {
    method: "POST", headers: { Authorization: "Bearer " + token, "Content-Type": "application/json" },
    body: JSON.stringify({ message: {
      token: device.token,
      notification: { title, body },
      webpush: { notification: { icon: link + "icon-192.png", badge: link + "icon-192.png" }, fcm_options: { link } }
    } })
  });
  if (r.ok) return "ok";
  let err = ""; try { err = JSON.stringify(await r.json()); } catch (e) {}
  return r.status === 404 || /UNREGISTERED|registration-token-not-registered/i.test(err) ? "gone" : "error";
}

export async function whoIs(env, idToken) {
  const r = await fetch(`https://identitytoolkit.googleapis.com/v1/accounts:lookup?key=${env.FIREBASE_API_KEY}`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ idToken })
  });
  if (!r.ok) return null;
  const u = ((await r.json()).users || [])[0];
  if (!u || !u.email || u.emailVerified !== true) return null;
  return u.email.toLowerCase();
}

export default {
  async fetch(req, env) {
    try { return await handle(req, env); }
    catch (e) { return json({ error: "notifier problem: " + String(e && e.message || e).slice(0, 120) }, 500, env); }
  }
};

/* ---------- recipe links ---------- */
const ENT = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'", nbsp: " ", ndash: "–", mdash: "—", frac12: "½", frac14: "¼", frac34: "¾", deg: "°", rsquo: "’", lsquo: "‘", rdquo: "”", ldquo: "“", hellip: "…" };
export function clean(t) {
  return String(t == null ? "" : t)
    .replace(/<[^>]*>/g, " ")
    .replace(/&#x([0-9a-f]+);/gi, (_, h) => String.fromCodePoint(parseInt(h, 16)))
    .replace(/&#(\d+);/g, (_, d) => String.fromCodePoint(+d))
    .replace(/&([a-z0-9]+);/gi, (m, n) => ENT[n.toLowerCase()] ?? m)
    .replace(/\s+/g, " ").trim();
}
// "PT1H30M" -> "1 hr 30 min"
export function duration(iso) {
  const m = /^P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:\d+S)?)?$/i.exec(String(iso || "").trim());
  if (!m) return clean(iso).slice(0, 20);
  const h = (+(m[1] || 0)) * 24 + (+(m[2] || 0)), min = +(m[3] || 0);
  return [h ? h + " hr" : "", min ? min + " min" : ""].filter(Boolean).join(" ");
}
const isType = (o, t) => o && (o["@type"] === t || (Array.isArray(o["@type"]) && o["@type"].includes(t)));
function findRecipe(node, depth = 0) {
  if (!node || typeof node !== "object" || depth > 6) return null;
  if (Array.isArray(node)) { for (const x of node) { const r = findRecipe(x, depth + 1); if (r) return r; } return null; }
  if (isType(node, "Recipe")) return node;
  for (const k of ["@graph", "mainEntity", "mainEntityOfPage", "itemListElement"]) { const r = findRecipe(node[k], depth + 1); if (r) return r; }
  return null;
}
function stepsOf(ins, out = []) {
  if (!ins) return out;
  if (typeof ins === "string") { clean(ins).split(/(?<=\.)\s+(?=[A-Z])|\n/).forEach(x => x.trim() && out.push(x.trim())); return out; }
  if (Array.isArray(ins)) { ins.forEach(x => stepsOf(x, out)); return out; }
  if (isType(ins, "HowToSection")) { if (ins.name) out.push(clean(ins.name).toUpperCase() + ":"); return stepsOf(ins.itemListElement, out); }
  const t = clean(ins.text || ins.name || ""); if (t) out.push(t); return out;
}
export function recipeFromHtml(html, url) {
  const blocks = [...String(html).matchAll(/<script[^>]*type=["']?application\/ld\+json["']?[^>]*>([\s\S]*?)<\/script>/gi)].map(m => m[1]);
  let r = null;
  for (const b of blocks) { try { r = findRecipe(JSON.parse(b.trim())); } catch (e) { r = null; } if (r) break; }
  if (!r) {
    const og = /<meta[^>]+property=["']og:title["'][^>]+content=(["'])(.*?)\1/i.exec(html), tt = /<title[^>]*>([^<]+)/i.exec(html);
    return { found: false, title: clean(og ? og[2] : tt ? tt[1] : "").slice(0, 100), source: url };
  }
  const y = r.recipeYield; const yieldTxt = clean(Array.isArray(y) ? y.find(v => /\d/.test(String(v))) || y[0] : y);
  const serv = parseInt((/\d+/.exec(yieldTxt) || [""])[0], 10);
  const ings = (Array.isArray(r.recipeIngredient) ? r.recipeIngredient : Array.isArray(r.ingredients) ? r.ingredients : []).map(clean).filter(Boolean);
  const notes = clean(r.description).slice(0, 600);
  return {
    found: true, title: clean(r.name).slice(0, 100), servings: serv > 0 && serv < 100 ? serv : null,
    prep: duration(r.prepTime), cook: duration(r.cookTime) || (!r.prepTime ? duration(r.totalTime) : ""),
    ingredients: ings.slice(0, 80).map(x => x.slice(0, 200)), steps: stepsOf(r.recipeInstructions).slice(0, 80).map(x => x.slice(0, 1000)),
    notes, source: url
  };
}
function okUrl(u) {
  let x; try { x = new URL(u); } catch (e) { return null; }
  if (!/^https?:$/.test(x.protocol)) return null;
  const h = x.hostname;
  if (h === "localhost" || /^(127\.|10\.|192\.168\.|169\.254\.|0\.)/.test(h) || /^172\.(1[6-9]|2\d|3[01])\./.test(h) || h.endsWith(".local") || h.endsWith(".internal") || /^\[/.test(h)) return null;
  return x.toString();
}
async function readRecipe(env, msg) {
  const url = okUrl(String(msg.url || "").trim().slice(0, 1000));
  if (!url) return json({ error: "that doesn't look like a web link" }, 400, env);
  let res;
  try {
    res = await fetch(url, { redirect: "follow", headers: { "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1", "Accept": "text/html,application/xhtml+xml" }, signal: AbortSignal.timeout(12000) });
  } catch (e) { return json({ error: "couldn't reach that site" }, 502, env); }
  if (!res.ok) return json({ error: `the site said ${res.status}` }, 502, env);
  const html = (await res.text()).slice(0, 4000000);
  return json(recipeFromHtml(html, res.url || url), 200, env);
}

async function handle(req, env) {
    if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: {
      "Access-Control-Allow-Origin": env.APP_ORIGIN || "*", "Access-Control-Allow-Methods": "POST", "Access-Control-Allow-Headers": "Content-Type", "Access-Control-Max-Age": "86400" } });
    const url = new URL(req.url);
    if (req.method !== "POST" || (url.pathname !== "/notify" && url.pathname !== "/recipe")) return json({ error: "not found" }, 404, env);
    if (url.pathname === "/recipe") {      // reading a recipe needs a sign-in check, but not the service account
      let m; try { m = JSON.parse(await req.text()); } catch (e) { return json({ error: "bad request" }, 400, env); }
      if (!m || typeof m.idToken !== "string" || m.idToken.length > 5000) return json({ error: "sign in first" }, 401, env);
      const who = await whoIs(env, m.idToken);
      if (!who) return json({ error: "sign in again" }, 401, env);
      if (!String(env.ALLOWED || "").toLowerCase().split(",").map(x => x.trim()).includes(who)) return json({ error: "not one of us" }, 403, env);
      return readRecipe(env, m);
    }
    if (!env.GOOGLE_SA) return json({ error: "the GOOGLE_SA secret isn't set in Cloudflare yet" }, 500, env);
    try { const sa = JSON.parse(env.GOOGLE_SA); if (!sa.private_key || !sa.client_email) throw 0; }
    catch (e) { return json({ error: "GOOGLE_SA isn't the whole service account file; paste the entire .json contents" }, 500, env); }
    let msg; try { msg = JSON.parse(await req.text()); } catch (e) { return json({ error: "bad request" }, 400, env); }
    if (!msg || typeof msg.idToken !== "string" || msg.idToken.length > 5000) return json({ error: "sign in first" }, 401, env);
    const email = await whoIs(env, msg.idToken);
    if (!email) return json({ error: "sign in again" }, 401, env);
    const allowed = String(env.ALLOWED || "").toLowerCase().split(",").map(x => x.trim()).filter(Boolean);
    if (!allowed.includes(email)) return json({ error: "not one of us" }, 403, env);
    const title = String(msg.title || "zen·dom").slice(0, 60);
    const body = String(msg.body || "").slice(0, 180);
    if (!body) return json({ error: "nothing to say" }, 400, env);
    const link = env.APP_URL || "https://srzrepository.github.io/zendom/";
    const token = await googleToken(env);
    const devices = (await listDevices(env, token)).filter(d => d.token && (msg.test ? d.owner === email : d.owner !== email && allowed.includes(d.owner) && d.instant));
    let sent = 0, gone = 0;
    for (const d of devices) {
      const res = await sendTo(env, token, d, title, body, link);
      if (res === "ok") sent++;
      if (res === "gone") { gone++; await fetch("https://firestore.googleapis.com/v1/" + d.name, { method: "DELETE", headers: { Authorization: "Bearer " + token } }); }
    }
    return json({ sent, gone }, 200, env);
}
