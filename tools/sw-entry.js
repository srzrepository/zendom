// zen·dom background helper (service worker). Shows notifications when the app is closed.
// Bundled to firebase-messaging-sw.js. Firebase shows messages that carry a "notification" part by itself;
// this file adds: tap a notification -> open (or focus) zen·dom.
import { initializeApp } from "firebase/app";
import { getMessaging, onBackgroundMessage } from "firebase/messaging/sw";

const app = initializeApp({
  apiKey: "AIzaSyAQN7j7SWw0gzZyprK45qx4-IgliQdylE4",
  authDomain: "zendom-4ed52.firebaseapp.com",
  projectId: "zendom-4ed52",
  storageBucket: "zendom-4ed52.firebasestorage.app",
  messagingSenderId: "273022571314",
  appId: "1:273022571314:web:f2af0750ee647ba38a3d2b"
});
onBackgroundMessage(getMessaging(app), () => {});
self.addEventListener("notificationclick", event => {
  event.notification.close();
  const url = new URL("./", self.registration.scope).href;
  event.waitUntil(self.clients.matchAll({ type: "window", includeUncontrolled: true }).then(list => {
    for (const c of list) if (c.url.startsWith(url) && "focus" in c) return c.focus();
    return self.clients.openWindow(url);
  }));
});
