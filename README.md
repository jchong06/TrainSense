# TrainSense

A NYC subway companion app — browse lines and stations, see **live train arrivals**, and **plan trips** across the MTA network. It has a Python/Flask backend that serves MTA GTFS static + real-time data, and a React Native (Expo) mobile app.

## Architecture

```
TrainSense/
├── backend/            Flask API (Python) — serves routes, stops, arrivals, trip plans
│   ├── app/
│   │   ├── routes/     API endpoints (Blueprint mounted at /api)
│   │   ├── models/     SQLAlchemy models (Route, Stop, StopRoute, Trip)
│   │   ├── services/   GTFS static loader + real-time (GTFS-RT) feed parsing
│   │   └── data/gtfs/  GTFS static feed files
│   ├── data/gtfs/      GTFS static feed (used by the loader; refreshed on import)
│   ├── setup_database.py   One-time DB setup + data import
│   └── run.py          Dev server entry point (port 5001)
└── mobile/             Expo React Native app (TypeScript)
    └── src/
        ├── screens/    Map, Lines (routes), Search (trip planning)
        ├── components/ Station/route UI
        └── services/   API client (talks to the backend at :5001)
```

- **Backend:** Flask + SQLAlchemy (SQLite), reads MTA GTFS static data into a DB and proxies the MTA GTFS-Realtime feeds for live arrivals.
- **Mobile:** Expo (React Native), React Navigation, Mapbox (`@rnmapbox/maps`) for the map.

## Prerequisites

- **Python 3.9+** (backend)
- **Node.js 18+** (mobile)
- **Mapbox access token** — optional, only needed to render the map ([account.mapbox.com](https://account.mapbox.com/))
- **MTA API key** — *not required* (the app uses the MTA's public feeds)

## Backend setup

```bash
cd backend

# Create and activate a virtualenv
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create the database and import MTA GTFS data
# (loads routes, stops, trips, and stop-route relationships)
python setup_database.py

# Start the API server
python run.py
```

The API runs at **http://localhost:5001**.

> **Note:** `setup_database.py` skips the import if the DB already has routes. To force a
> fresh re-import, delete `backend/instance/mta_subway_app.db` and run it again.

## Mobile setup

```bash
cd mobile

# Install dependencies
npm install

# (optional) enable the map — add your Mapbox token
echo "MAPBOX_ACCESS_TOKEN=pk.your_real_token_here" > .env

# Start the Expo dev server
npm start
```

Then choose how to run it:

- **Web** — press `w`. The app renders inside a centered phone-shaped frame. This is the
  easiest way to preview (no Xcode/Android Studio needed).
- **iOS Simulator** — press `i` (requires full **Xcode** installed, not just Command Line
  Tools). Uses a dev client build because of the native Mapbox module.
- **Android Emulator** — press `a`.
- **Physical device** — press `s` to switch to Expo Go, then scan the QR code. *(The Map
  screen's native Mapbox module won't render in Expo Go, but everything else works.)*

The mobile app connects to the backend at `http://127.0.0.1:5001`. Make sure the backend is
running first.

### Map without a token

If no valid `MAPBOX_ACCESS_TOKEN` is set, the Map tab shows a "Map unavailable" placeholder
instead of crashing — the rest of the app (Lines, Search, live arrivals, trip planning)
works fully.

## API

All endpoints are under `/api`. Successful responses are `{"success": true, "data": ...}`.

| Method | Endpoint | Description |
| ------ | -------- | ----------- |
| GET | `/api/health` | Health check |
| GET | `/api/routes` | All subway routes |
| GET | `/api/stops` | All stations (with the routes serving each) |
| GET | `/api/stops/nearby?lat=&lng=&radius=` | Stations near a location |
| GET | `/api/stops/<stop_id>/routes` | Routes serving a stop |
| GET | `/api/realtime/<stop_id>` | Live arrivals at a stop |
| GET | `/api/realtime/health` | Real-time feed health |
| POST | `/api/plan-trip` | Plan a trip — body: `{"origin_id","destination_id"}` |
| GET | `/api/map/stations` | Stations for the map |
| GET | `/api/service-status` | Per-line service status |
| GET | `/api/route-stations/<route_id>` | Ordered stations on a route |
| GET | `/api/route-shape/<route_id>` | Route geometry |
| GET | `/api/data/stats` | Data statistics |

Example:

```bash
curl http://localhost:5001/api/routes
curl -X POST http://localhost:5001/api/plan-trip \
  -H 'Content-Type: application/json' \
  -d '{"origin_id":"101","destination_id":"127"}'
```

## Troubleshooting

- **`Address already in use` on start** — an old server is holding port 5001:
  `lsof -tiTCP:5001 -sTCP:LISTEN | xargs kill -9`, then re-run `python run.py`.
- **Trip planning returns "No route found"** — the `stop_routes`/`trips` tables are empty.
  Re-run `python setup_database.py` (delete `backend/instance/*.db` first to force a
  re-import).
- **App can't reach the backend** — confirm the backend is running on `:5001` and, on a
  physical device, that the device can reach your machine's IP.
