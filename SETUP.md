# TrainSense Transit App Setup Guide

This guide will help you set up the TrainSense transit app with a connected backend API and frontend mobile app.

## Prerequisites

- Python 3.8+ (for backend)
- Node.js 16+ (for frontend)
- MTA API Key (get one from [MTA Developer Portal](https://api.mta.info/))

## Backend Setup

### 1. Install Python Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Set Environment Variables

Create a `.env` file in the `backend` directory:

```bash
# backend/.env
MTA_API_KEY=your_mta_api_key_here
FLASK_ENV=development
FLASK_DEBUG=True
```

### 3. Load Initial Data

Run the setup script to populate the database with MTA GTFS data:

```bash
cd backend
python setup_database.py
```

This will:

- Download the latest MTA GTFS data
- Extract and process the data
- Load routes and stops into the database

### 4. Start the Backend Server

```bash
cd backend
python run.py
```

The backend will start on `http://localhost:5001` with the following API endpoints:

- `GET /` - Health check
- `GET /api/v1/health` - API health check
- `GET /api/v1/routes` - Get all subway routes
- `GET /api/v1/stops` - Get all subway stops
- `GET /api/v1/stops/nearby?lat=X&lng=Y&radius=Z` - Get nearby stops
- `GET /api/v1/realtime/{route_id}` - Get real-time updates for a route
- `GET /api/v1/service-status` - Get service status
- `GET /api/v1/data/stats` - Get data statistics

## Frontend Setup

### 1. Install Dependencies

```bash
cd mobile
npm install
# or
yarn install
```

### 2. Start the Mobile App

```bash
cd mobile
npx expo start
```

This will start the Expo development server. You can:

- Press `i` to open iOS simulator
- Press `a` to open Android emulator
- Scan the QR code with Expo Go app on your phone

## Connecting Frontend to Backend

The frontend is already configured to connect to the backend at `http://localhost:5001`. The API service (`mobile/src/services/api.ts`) handles all communication with the backend.

### Key Features Now Working:

1. **Real Routes**: The app now displays actual MTA subway routes from the GTFS data
2. **Real Stops**: Search screen shows actual subway stops from the database
3. **Service Status**: Real-time service status (currently mock data, but API ready)
4. **Pull to Refresh**: All screens support pull-to-refresh to get fresh data
5. **Error Handling**: Proper error handling and user feedback

### API Integration Points:

- **HomeScreen**: Shows real routes and service status
- **RouteScreen**: Displays all available subway lines
- **SearchScreen**: Shows available stops for trip planning
- **MapScreen**: Ready for real-time location integration

## Testing the Connection

1. Start the backend server
2. Start the mobile app
3. Navigate to different screens to see real data
4. Pull to refresh to test API calls
5. Check the backend console for API request logs

## Troubleshooting

### Backend Issues:

- **MTA API Key**: Make sure you have a valid MTA API key in your `.env` file
- **Database**: If you get database errors, delete the database file and run `setup_database.py` again
- **Port conflicts**: If port 5001 is busy, change it in `run.py`

### Frontend Issues:

- **Connection errors**: Make sure the backend is running on `localhost:5001`
- **CORS errors**: The backend has CORS enabled, but check if your network allows localhost connections
- **Expo issues**: Try clearing Expo cache with `npx expo start --clear`

## Next Steps

With the basic connection working, you can now:

1. **Add Real-time Data**: Implement actual MTA real-time feed parsing
2. **Trip Planning**: Add route planning algorithms
3. **Location Services**: Integrate GPS for nearby stops
4. **Push Notifications**: Add service alerts and delays
5. **Offline Support**: Cache data for offline use
6. **User Preferences**: Save favorite routes and stops

## API Documentation

The backend provides a RESTful API with the following main endpoints:

### Routes

- `GET /api/v1/routes` - Get all subway routes
- `GET /api/v1/realtime/{route_id}` - Get real-time updates for a specific route

### Stops

- `GET /api/v1/stops` - Get all stops (with optional route filtering)
- `GET /api/v1/stops/nearby` - Get stops near a location

### Status

- `GET /api/v1/service-status` - Get overall service status
- `GET /api/v1/realtime/health` - Check real-time feed health

### Data Management

- `POST /api/v1/data/load` - Load GTFS data into database
- `GET /api/v1/data/stats` - Get data statistics

All endpoints return JSON responses with a consistent format:

```json
{
  "success": true,
  "data": {...},
  "error": null
}
```

## Development Notes

- The backend uses SQLite for simplicity, but can be easily switched to PostgreSQL or MySQL
- GTFS data is downloaded daily and cached locally
- Real-time feeds are accessed directly from MTA APIs
- The frontend uses Expo for cross-platform development
- All API calls include proper error handling and loading states
