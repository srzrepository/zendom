// zen·dom background worker: keeps a copy of the app so it opens without internet,
// and (via firebase-messaging-sw.js) shows notifications when the app is closed.
importScripts("firebase-messaging-sw.js");

const APP = "zendom-app-v1", FONTS = "zendom-fonts-v1";
const CORE = ["./", "index.html", "firebase-bundle.js", "manifest.json", "icon-192.png", "icon-512.png", "apple-touch-icon.png"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(APP).then(c => c.addAll(CORE)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k.startsWith("zendom-") && k !== APP && k !== FONTS).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

// The app's own files: try the internet first (so updates show up right away), and fall back to the
// saved copy if there's no connection or it takes longer than 4 seconds.
async function networkFirst(req) {
  const cache = await caches.open(APP);
  try {
    const res = await Promise.race([fetch(req), new Promise((_, no) => setTimeout(() => no(new Error("slow")), 4000))]);
    if (res && res.ok) cache.put(req, res.clone());
    return res;
  } catch (err) {
    const hit = await cache.match(req, { ignoreSearch: true }) || (req.mode === "navigate" ? await cache.match("index.html") : null);
    if (hit) return hit;
    throw err;
  }
}
// Fonts barely change: use the saved copy, fetch once.
async function cacheFirst(req) {
  const cache = await caches.open(FONTS);
  const hit = await cache.match(req); if (hit) return hit;
  const res = await fetch(req); if (res && (res.ok || res.type === "opaque")) cache.put(req, res.clone());
  return res;
}
self.addEventListener("fetch", e => {
  const req = e.request; if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin === self.location.origin) { e.respondWith(networkFirst(req)); return; }
  if (url.hostname === "fonts.googleapis.com" || url.hostname === "fonts.gstatic.com") { e.respondWith(cacheFirst(req)); return; }
  // everything else (Firebase, the notifier, recipe sites) goes straight to the internet as usual
});
