# TrainSense - NYC Transit App

A real-time NYC subway app built with React Native (Expo) and a Python Flask backend. Connects to the MTA GTFS API to provide live arrival times, interactive maps, and route planning between any two stations.

## Features

- **Interactive Map**: Mapbox-powered map showing all NYC subway stations with real MTA route colors
- **Real-time Arrivals**: Live arrival times pulled from MTA GTFS real-time feeds, shown per station
- **Route Browser**: Browse all subway lines with stops and service information
- **Trip Planner**: Enter any two stations and get all viable routes — direct and with transfers — using BFS pathfinding over the MTA GTFS graph
- **Transfer-aware Routing**: Understands transfer hubs (e.g. Fulton St, Times Sq) and finds paths across connecting lines
- **Station Details**: Tap any station to see which routes serve it and upcoming arrivals

## Tech Stack

### Backend
- Python 3.9, Flask 3.0
- SQLAlchemy + SQLite
- MTA GTFS static + real-time feeds
- BFS pathfinding over stop graph with transfer hub collapsing

### Mobile
- React Native + Expo 53
- TypeScript
- Mapbox (`@rnmapbox/maps`)
- React Navigation (bottom tabs)

## Prerequisites

- Python 3.8+
- Node.js 18+
- Expo CLI
- MTA API Key — get one free at [api.mta.info](https://api.mta.info/)
- Mapbox token — get one at [mapbox.com](https://mapbox.com/)

## Setup

### 1. Backend

```bash
cd backend

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Add your MTA API key
cp .env.example .env
# Edit .env and set MTA_API_KEY=your_key_here

# Set up the database and import GTFS data
python setup_database.py

# Populate stop_routes table (required for trip planner)
python3 -c "
import csv, os
from app import create_app, db
from app.models.transit import StopRoute

app = create_app()
with app.app_context():
    gtfs_dir = 'data/gtfs'
    trip_to_route = {}
    with open(os.path.join(gtfs_dir, 'trips.txt')) as f:
        for row in csv.DictReader(f):
            trip_to_route[row['trip_id']] = row['route_id']
    pairs = set()
    with open(os.path.join(gtfs_dir, 'stop_times.txt')) as f:
        for row in csv.DictReader(f):
            r = trip_to_route.get(row['trip_id'])
            if r: pairs.add((row['stop_id'], r))
    StopRoute.query.delete()
    db.session.commit()
    from sqlalchemy.orm import Session
    batch = [StopRoute(stop_id=s, route_id=r) for s, r in pairs]
    db.session.bulk_save_objects(batch)
    db.session.commit()
    print(f'Done: {StopRoute.query.count()} rows')
"

# Start the server
python run.py
```

Backend runs at `http://localhost:5001`

### 2. Mobile

```bash
cd mobile

# Install dependencies
npm install

# Build native code (required — Mapbox needs a custom dev build, not Expo Go)
npm run ios      # or npm run android

# After the first native build, you can use:
npm start
```

> **Note:** This app uses `@rnmapbox/maps` which requires a custom development build. It will **not** work with the standard Expo Go app. You must run `npm run ios` or `npm run android` at least once to compile the native code.

## Project Structure

```
TrainSense/
├── backend/
│   ├── app/
│   │   ├── models/transit.py        # DB models: Route, Stop, StopRoute, Trip
│   │   ├── routes/transit_routes.py # All API endpoints + BFS trip planner
│   │   └── services/
│   │       ├── gtfs_service.py      # GTFS static data loader
│   │       └── realtime_service.py  # MTA real-time feed processor
│   ├── data/gtfs/                   # Downloaded MTA GTFS files
│   ├── run.py                       # Flask app entry point
│   └── setup_database.py           # DB init + GTFS import
└── mobile/
    └── src/
        ├── screens/
        │   ├── MapScreen.tsx        # Interactive Mapbox map
        │   ├── RouteScreen.tsx      # Subway line browser
        │   └── SearchScreen.tsx     # Trip planner UI
        ├── components/
        │   ├── RouteSymbol.tsx      # MTA-style route badge (circle/diamond)
        │   ├── StationModal.tsx     # Station arrivals popup
        │   └── TrainStopsModal.tsx  # Route stops list
        ├── services/api.ts          # Backend API client + TypeScript types
        └── utils/mtaColors.ts       # Official MTA brand colors
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/routes` | All subway routes |
| GET | `/api/v1/stops` | All subway stops |
| GET | `/api/v1/stops/{stop_id}/routes` | Routes for a stop |
| GET | `/api/v1/realtime/{stop_id}` | Live arrivals for a stop |
| GET | `/api/v1/service-status` | Service status all lines |
| GET | `/api/v1/map/stations` | Stations formatted for map display |
| POST | `/api/v1/plan-trip` | Trip planner — body: `{ origin_id, destination_id }` |

## How Trip Planning Works

The `/plan-trip` endpoint uses BFS (Breadth-First Search) over a graph built from MTA GTFS data:

1. **Transfer hubs** are built from `transfers.txt` — stations like Fulton St with multiple line platforms are collapsed into single nodes
2. **Route graph** maps each subway line to the set of hub/station nodes it serves
3. **BFS** finds all paths from origin to destination with up to 2 transfers
4. **Deduplication** by trunk line (A/C/E, N/Q/R/W, etc.) keeps results clean
5. Results are capped at 8 options, sorted by fewest transfers first

## Database Schema

| Table | Description |
|-------|-------------|
| `routes` | Subway lines with MTA colors and names |
| `stops` | Stations with coordinates and parent relationships |
| `stop_routes` | Many-to-many: which routes serve which stops |
| `trips` | Individual scheduled train trips |

## Troubleshooting

**Map not showing / Mapbox error**
- You must run `npm run ios` or `npm run android` first — Expo Go won't work
- Verify your Mapbox token is set in `mobile/app.config.js`

**No stations on map**
- Make sure the backend is running on port 5001
- Check the database was populated: `python setup_database.py`

**Trip planner returns no routes**
- Make sure you ran the stop_routes seeding script above
- Verify `data/gtfs/stop_times.txt` and `trips.txt` exist

**No arrival times**
- Check your MTA API key in `backend/.env`
- Verify the key has real-time feed access at [api.mta.info](https://api.mta.info/)

## Credits

This project is based on the original [TrainSense](https://github.com/pradeepg78/TrainSense) by pradeepg78. This is a personal fork maintained by [jchong06](https://github.com/jchong06).

## License

Educational use. Please respect MTA's API terms of service.
