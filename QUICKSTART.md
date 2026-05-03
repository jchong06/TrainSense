# TrainSense - Quick Start Guide

## Prerequisites

- Python 3.8+ 
- Node.js 16+
- MTA API Key from [MTA Developer Portal](https://api.mta.info/)

## Quick Setup

### 1. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Install Python dependencies
pip install -r requirements.txt

# Create .env file with your MTA API key
echo "MTA_API_KEY=your_api_key_here" > .env
echo "FLASK_ENV=development" >> .env
echo "FLASK_DEBUG=True" >> .env

# Set up database and load MTA data
python setup_database.py

# Start the backend server
python run.py
```

The backend will run on `http://localhost:5001`

### 2. Mobile App Setup

```bash
# Navigate to mobile directory (in a new terminal)
cd mobile

# Install dependencies
npm install

# Start Expo development server
npm start
```

Then:
- Press `i` for iOS simulator
- Press `a` for Android emulator  
- Scan QR code with Expo Go app on your phone

## That's it!

Your backend is running on port 5001 and your mobile app is ready to connect to it.

For more detailed information, see [SETUP.md](./SETUP.md) or [README.md](./README.md).


