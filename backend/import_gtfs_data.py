#!/usr/bin/env python3
"""
Script to import real GTFS data from MTA APIs and populate the database
"""
import os
import sys
import requests
import zipfile
import io
import csv
from datetime import datetime
import logging

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models.transit import Route, Stop, Trip, StopRoute

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GTFSImporter:
    def __init__(self):
        self.app = create_app()
        self.app.app_context().push()
        
        # MTA GTFS URLs
        self.gtfs_urls = {
            'subway': 'https://api-endpoint.mta.info/gtfs/subway.zip',  # Replace with actual MTA URL
            'bus': 'https://api-endpoint.mta.info/gtfs/bus.zip'  # Replace with actual MTA URL
        }
        
        # MTA API key (should be set as environment variable)
        self.api_key = os.getenv('MTA_API_KEY')
        if not self.api_key:
            logger.warning("MTA_API_KEY not found in environment variables")
    
    def download_gtfs_data(self, feed_type='subway'):
        """Download GTFS data from MTA API"""
        try:
            url = self.gtfs_urls.get(feed_type)
            if not url:
                logger.error(f"Unknown feed type: {feed_type}")
                return None
            
            headers = {}
            if self.api_key:
                headers['x-api-key'] = self.api_key
            
            logger.info(f"Downloading {feed_type} GTFS data from {url}")
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            return io.BytesIO(response.content)
        except Exception as e:
            logger.error(f"Error downloading GTFS data: {e}")
            return None
    
    def parse_gtfs_file(self, zip_data, filename):
        """Parse a specific file from GTFS zip"""
        try:
            with zipfile.ZipFile(zip_data) as zip_file:
                if filename not in zip_file.namelist():
                    logger.error(f"File {filename} not found in GTFS data")
                    return None
                
                with zip_file.open(filename) as file:
                    content = file.read().decode('utf-8')
                    reader = csv.DictReader(io.StringIO(content))
                    return list(reader)
        except Exception as e:
            logger.error(f"Error parsing {filename}: {e}")
            return None
    
    def import_routes(self, routes_data):
        """Import routes from GTFS data"""
        try:
            logger.info("Importing routes...")
            count = 0
            
            for route_data in routes_data:
                # Only import subway routes (route_type = 1)
                if route_data.get('route_type') == '1':
                    route = Route(
                        id=route_data['route_id'],
                        short_name=route_data.get('route_short_name', ''),
                        long_name=route_data.get('route_long_name', ''),
                        route_type=int(route_data['route_type']),
                        route_color=route_data.get('route_color', '000000'),
                        text_color=route_data.get('route_text_color', 'FFFFFF')
                    )
                    
                    # Check if route already exists
                    existing = Route.query.get(route.id)
                    if existing:
                        # Update existing route
                        existing.short_name = route.short_name
                        existing.long_name = route.long_name
                        existing.route_color = route.route_color
                        existing.text_color = route.text_color
                    else:
                        # Add new route
                        db.session.add(route)
                    
                    count += 1
            
            db.session.commit()
            logger.info(f"Imported {count} routes")
            return count
        except Exception as e:
            logger.error(f"Error importing routes: {e}")
            db.session.rollback()
            return 0
    
    def import_stops(self, stops_data):
        """Import stops from GTFS data"""
        try:
            logger.info("Importing stops...")
            count = 0
            
            for stop_data in stops_data:
                stop = Stop(
                    id=stop_data['stop_id'],
                    name=stop_data['stop_name'],
                    latitude=float(stop_data['stop_lat']),
                    longitude=float(stop_data['stop_lon']),
                    zone_id=stop_data.get('zone_id'),
                    location_type=int(stop_data.get('location_type', 0)),
                    parent_station=stop_data.get('parent_station')
                )
                
                # Check if stop already exists
                existing = Stop.query.get(stop.id)
                if existing:
                    # Update existing stop
                    existing.name = stop.name
                    existing.latitude = stop.latitude
                    existing.longitude = stop.longitude
                    existing.zone_id = stop.zone_id
                    existing.location_type = stop.location_type
                    existing.parent_station = stop.parent_station
                else:
                    # Add new stop
                    db.session.add(stop)
                
                count += 1
            
            db.session.commit()
            logger.info(f"Imported {count} stops")
            return count
        except Exception as e:
            logger.error(f"Error importing stops: {e}")
            db.session.rollback()
            return 0
    
    def import_stop_routes(self, trips_data, stop_times_data):
        """Import stop-route relationships from GTFS data"""
        try:
            logger.info("Importing stop-route relationships...")
            
            # Create a mapping of trip_id to route_id
            trip_route_map = {}
            for trip_data in trips_data:
                trip_route_map[trip_data['trip_id']] = trip_data['route_id']
            
            # Create a mapping of stop_id to route_ids
            stop_route_map = {}
            for stop_time_data in stop_times_data:
                trip_id = stop_time_data['trip_id']
                stop_id = stop_time_data['stop_id']
                
                if trip_id in trip_route_map:
                    route_id = trip_route_map[trip_id]
                    if stop_id not in stop_route_map:
                        stop_route_map[stop_id] = set()
                    stop_route_map[stop_id].add(route_id)
            
            # Create StopRoute records
            count = 0
            for stop_id, route_ids in stop_route_map.items():
                for route_id in route_ids:
                    # Check if relationship already exists
                    existing = StopRoute.query.filter_by(
                        stop_id=stop_id, 
                        route_id=route_id
                    ).first()
                    
                    if not existing:
                        stop_route = StopRoute(
                            stop_id=stop_id,
                            route_id=route_id
                        )
                        db.session.add(stop_route)
                        count += 1
            
            db.session.commit()
            logger.info(f"Imported {count} stop-route relationships")
            return count
        except Exception as e:
            logger.error(f"Error importing stop-route relationships: {e}")
            db.session.rollback()
            return 0
    
    def import_trips(self, trips_data):
        """Import trips from GTFS data"""
        try:
            logger.info("Importing trips...")
            count = 0
            
            for trip_data in trips_data:
                trip = Trip(
                    id=trip_data['trip_id'],
                    route_id=trip_data['route_id'],
                    service_id=trip_data['service_id'],
                    trip_headsign=trip_data.get('trip_headsign'),
                    direction_id=int(trip_data.get('direction_id', 0))
                )
                
                # Check if trip already exists
                existing = Trip.query.get(trip.id)
                if existing:
                    # Update existing trip
                    existing.route_id = trip.route_id
                    existing.service_id = trip.service_id
                    existing.trip_headsign = trip.trip_headsign
                    existing.direction_id = trip.direction_id
                else:
                    # Add new trip
                    db.session.add(trip)
                
                count += 1
            
            db.session.commit()
            logger.info(f"Imported {count} trips")
            return count
        except Exception as e:
            logger.error(f"Error importing trips: {e}")
            db.session.rollback()
            return 0
    
    def import_all_data(self):
        """Import all GTFS data"""
        try:
            logger.info("Starting GTFS data import...")
            
            # Download subway GTFS data
            gtfs_data = self.download_gtfs_data('subway')
            if not gtfs_data:
                logger.error("Failed to download GTFS data")
                return False
            
            # Parse GTFS files
            routes_data = self.parse_gtfs_file(gtfs_data, 'routes.txt')
            stops_data = self.parse_gtfs_file(gtfs_data, 'stops.txt')
            trips_data = self.parse_gtfs_file(gtfs_data, 'trips.txt')
            stop_times_data = self.parse_gtfs_file(gtfs_data, 'stop_times.txt')
            
            if not all([routes_data, stops_data, trips_data, stop_times_data]):
                logger.error("Failed to parse required GTFS files")
                return False
            
            # Import data in order
            self.import_routes(routes_data)
            self.import_stops(stops_data)
            self.import_trips(trips_data)
            self.import_stop_routes(trips_data, stop_times_data)
            
            logger.info("GTFS data import completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error during GTFS import: {e}")
            return False
    
    def get_mta_realtime_data(self, feed_id):
        """Get real-time data from MTA API"""
        try:
            # MTA real-time API endpoint
            url = f"https://api-endpoint.mta.info/feeds/{feed_id}/gtfs-realtime"
            
            headers = {}
            if self.api_key:
                headers['x-api-key'] = self.api_key
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            return response.content
        except Exception as e:
            logger.error(f"Error getting real-time data: {e}")
            return None

def main():
    """Main function to run the import"""
    importer = GTFSImporter()
    
    # Import GTFS data
    success = importer.import_all_data()
    
    if success:
        logger.info("Data import completed successfully!")
        
        # Print some statistics
        route_count = Route.query.filter_by(route_type=1).count()
        stop_count = Stop.query.count()
        stop_route_count = StopRoute.query.count()
        
        logger.info(f"Database now contains:")
        logger.info(f"  - {route_count} subway routes")
        logger.info(f"  - {stop_count} stops")
        logger.info(f"  - {stop_route_count} stop-route relationships")
    else:
        logger.error("Data import failed!")
        sys.exit(1)

if __name__ == "__main__":
    main() 