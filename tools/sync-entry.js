// zen·dom ⇄ Firebase. Bundled into firebase-bundle.js (esbuild) and loaded next to index.html.
// It only exposes a small window.zdBackend; all sync decisions live in index.html.
// If a page already defines window.zdBackend (the test suite's stand-in server), this file does nothing.
import { initializeApp } from "firebase/app";
import { getAuth, GoogleAuthProvider, signInWithPopup, signOut, onAuthStateChanged } from "firebase/auth";
import { initializeFirestore, persistentLocalCache, persistentMultipleTabManager, collection, doc, getDocsFromServer, onSnapshot, writeBatch, serverTimestamp, setDoc, deleteDoc } from "firebase/firestore";
import { getMessaging, getToken, deleteToken, isSupported, onMessage } from "firebase/messaging";

const firebaseConfig = {
  apiKey: "AIzaSyAQN7j7SWw0gzZyprK45qx4-IgliQdylE4",
  authDomain: "zendom-4ed52.firebaseapp.com",
  projectId: "zendom-4ed52",
  storageBucket: "zendom-4ed52.firebasestorage.app",
  messagingSenderId: "273022571314",
  appId: "1:273022571314:web:f2af0750ee647ba38a3d2b"
};

if (!window.zdBackend) {
  const app = initializeApp(firebaseConfig);
  const auth = getAuth(app);
  let db;
  try {
    // keeps a copy on the phone so the app works offline and catches up later
    db = initializeFirestore(app, { localCache: persistentLocalCache({ tabManager: persistentMultipleTabManager() }) });
  } catch (e) {
    db = initializeFirestore(app, {});
  }
  const records = collection(db, "homes", "zendom", "records");
  const asRec = d => ({ id: d.id, del: !!d.get("del"), j: d.get("j") || "" });

  window.zdBackend = {
    onUser(cb) { return onAuthStateChanged(auth, u => cb(u ? { email: (u.email || "").toLowerCase(), name: u.displayName || "" } : null)); },
    async signIn() {
      const p = new GoogleAuthProvider();
      p.setCustomParameters({ prompt: "select_account" });
      await signInWithPopup(auth, p);
    },
    signOut() { return signOut(auth); },
    // the first sync must see the real server, never just this phone's cache
    async fetchAll() { const snap = await getDocsFromServer(records); return snap.docs.map(asRec); },
    // resolves when the server has the writes; offline it waits and Firestore sends them later
    async write(list) {
      for (let i = 0; i < list.length; i += 400) {
        const b = writeBatch(db);
        list.slice(i, i + 400).forEach(w => b.set(doc(records, w.id), Object.assign({}, w.data, { ts: serverTimestamp() })));
        await b.commit();
      }
    },
    // ---- notifications (only used after someone turns them on in Settings) ----
    async idToken() { return auth.currentUser ? auth.currentUser.getIdToken() : null; },
    push: {
      async supported() { try { return ("serviceWorker" in navigator) && ("Notification" in window) && await isSupported(); } catch (e) { return false; } },
      permission() { return ("Notification" in window) ? Notification.permission : "unsupported"; },
      // must be called straight from a tap: iPhone only shows the permission prompt for a direct tap
      async enable(vapidKey) {
        const perm = await Notification.requestPermission();
        if (perm !== "granted") { const e = new Error("Notifications weren't allowed"); e.code = "denied"; throw e; }
        const reg = await navigator.serviceWorker.register("firebase-messaging-sw.js");
        await navigator.serviceWorker.ready;
        return await getToken(getMessaging(app), { vapidKey, serviceWorkerRegistration: reg });
      },
      async disable() { try { await deleteToken(getMessaging(app)); } catch (e) {} },
      async saveDevice(id, data) { await setDoc(doc(db, "homes", "zendom", "devices", id), Object.assign({}, data, { updated: serverTimestamp() })); },
      async removeDevice(id) { await deleteDoc(doc(db, "homes", "zendom", "devices", id)); },
      onForeground(cb) { try { return onMessage(getMessaging(app), p => cb(p)); } catch (e) { return () => {}; } }
    },
    listen(onChanges, onError) {
      return onSnapshot(records, { includeMetadataChanges: false }, snap => {
        const ch = snap.docChanges().filter(c => !c.doc.metadata.hasPendingWrites)
          .map(c => c.type === "removed" ? { id: c.doc.id, del: true, j: "" } : asRec(c.doc));
        if (ch.length) onChanges(ch);
      }, err => onError && onError(err));
    }
  };
}
