# Deploying TrainSense

Live demo = **backend on Render** + **frontend (Expo web) on Vercel**. Deploy the backend
first (you need its URL for the frontend build). Both have free tiers. Total time ~15 min.

---

## 1. Backend → Render

The repo already contains `render.yaml` (a Render Blueprint) and `backend/Procfile`.

1. Go to **https://render.com** and sign up / log in (use "Sign in with GitHub").
2. **New +** → **Blueprint**.
3. Connect your GitHub and pick the **`TrainSense`** repo. Render reads `render.yaml` and
   proposes a web service **`trainsense-api`**.
4. Click **Apply**. Render will:
   - `pip install -r requirements.txt`
   - `python setup_database.py` → builds the SQLite DB (routes, stops, trips, stop-route
     relationships) from the committed GTFS feed
   - start `gunicorn run:app`
5. Wait for the build to finish (a few minutes). You'll get a URL like
   **`https://trainsense-api.onrender.com`**.
6. Verify: open `https://trainsense-api.onrender.com/api/health` → should return
   `{"status":"healthy",...}`.

> **Free-tier note:** the service sleeps after ~15 min idle; the first request afterward
> takes ~30–50s to wake. Fine for a demo.

### Optional: enable authenticated MTA feeds
Not required (the app uses public feeds). If you have an MTA API key, add an env var
`MTA_API_KEY` in the Render dashboard.

---

## 2. Frontend → Vercel

`mobile/vercel.json` builds the Expo web export (`npx expo export -p web` → `dist/`).

1. Go to **https://vercel.com** and sign up / log in with GitHub.
2. **Add New… → Project** → import the **`TrainSense`** repo.
3. Set **Root Directory** to **`mobile`** (important — the app isn't at the repo root).
   Vercel will pick up `mobile/vercel.json` automatically.
4. Add **Environment Variables** (Settings → Environment Variables):
   | Name | Value |
   | ---- | ----- |
   | `EXPO_PUBLIC_API_URL` | `https://trainsense-api.onrender.com/api` (your Render URL + `/api`) |
   | `MAPBOX_ACCESS_TOKEN` | your Mapbox public token (`pk....`) |
5. **Deploy.** You'll get a URL like **`https://train-sense.vercel.app`**.

### Or deploy the frontend from this session via CLI
If you'd rather I drive it, log in once in your terminal, then I'll run the deploy:
```
! npx vercel login
```
Then tell me and I'll run `vercel --prod` from `mobile/` with the env vars set.

---

## 3. After deploy

- Open the Vercel URL → the app loads in the phone frame, Search works (talks to Render),
  and the Map tab renders with your Mapbox token.
- Add both links to your resume/project entry:
  - **Live demo:** the Vercel URL
  - **Source:** `https://github.com/jchong06/TrainSense`
- Consider putting the live URL at the top of the README (I can add a badge once it's live).

## Troubleshooting

- **Frontend loads but Search/arrivals fail** — `EXPO_PUBLIC_API_URL` is wrong or missing
  the `/api` suffix, or the Render service is still waking up. Check the browser console and
  `…/api/health`.
- **Map tab blank** — `MAPBOX_ACCESS_TOKEN` not set in Vercel, or the token has URL
  restrictions that exclude the Vercel domain (add it in your Mapbox account).
- **Render build fails on `setup_database.py`** — check the build log; the GTFS files are
  committed so it shouldn't need to download, but if it does and times out, re-run the deploy.
