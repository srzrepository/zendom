# zen·dom

A calm household app for Sam and Charlie: chores (Fair Play cards), kitchen (recipes, meal plan, groceries, pantry), family health profiles, notes with drawings, calendar and budget with Jeff the money pig.

- `index.html` — the whole app (one file, no build step). The first and last lines are the website wrapper; everything between is the app.
- `firebase-bundle.js` — Firebase 12.19.0 (app, auth, Firestore) bundled from `tools/sync-entry.js` with esbuild. Sync is optional: without it the app works on one device.
- `firestore.rules` — database rules: only our two Google accounts.
- `tests/run_tests.py` and `tests/sync_tests.py` — end-to-end checks in headless Chromium.
- `tests/patch_step*.py` — each change, applied in order.
