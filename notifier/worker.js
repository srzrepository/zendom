// zen·dom notifier: a Cloudflare Worker (free plan). Paste this whole file into the Worker's code editor.
//
// POST /notify   body (text/plain JSON): {idToken, title, body, test?}
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

async function handle(req, env) {
    if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: {
      "Access-Control-Allow-Origin": env.APP_ORIGIN || "*", "Access-Control-Allow-Methods": "POST", "Access-Control-Allow-Headers": "Content-Type", "Access-Control-Max-Age": "86400" } });
    const url = new URL(req.url);
    if (req.method !== "POST" || url.pathname !== "/notify") return json({ error: "not found" }, 404, env);
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
