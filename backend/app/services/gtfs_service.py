# backend/app/services/gtfs_service.py
import os
import requests
import zipfile
import csv
# import pandas as pd
from datetime import datetime, timedelta
from flask import current_app
from app import db
from app.models.transit import Route, Stop, Trip

class GTFSService:
    """Service for downloading and processing MTA GTFS static data"""
    
    def __init__(self):
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data') # create the data directory
        self.gtfs_dir = os.path.join(self.data_dir, 'gtfs') # create the gtfs directory inside data
        self.processed_dir = os.path.join(self.data_dir, 'processed') # create the processed directory inside data
        
        # Ensure directories exist
        os.makedirs(self.gtfs_dir, exist_ok=True)
        os.makedirs(self.processed_dir, exist_ok=True)
    
    def download_gtfs_data(self, force_download=False):
        """Download GTFS static data from MTA"""
        zip_path = os.path.join(self.gtfs_dir, 'google_transit.zip')
        
        # Check if we already have recent data (unless forced)
        if not force_download and os.path.exists(zip_path):
            file_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(zip_path))
            if file_age < timedelta(days=1):  # Data is less than 1 day old
                print(f"✅ Using existing GTFS data (downloaded {file_age} ago)")
                return zip_path
        
        print("📥 Downloading GTFS static data from MTA...")
        
        try:
            url = current_app.config['MTA_GTFS_STATIC_URL'] # grab url defined in config.py
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            with open(zip_path, 'wb') as f:
                f.write(response.content)
            
            print(f"✅ Downloaded GTFS data to {zip_path}")
            return zip_path
            
        except Exception as e:
            print(f"❌ Error downloading GTFS data: {e}")
            raise
    
    def extract_gtfs_data(self, zip_path):
        """Extract GTFS zip file"""
        print("📦 Extracting GTFS data...")
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(self.gtfs_dir)
            
            # List extracted files
            files = os.listdir(self.gtfs_dir)
            
            # Create the files for the data we just pulled
            txt_files = [f for f in files if f.endswith('.txt')]
            print(f"✅ Extracted {len(txt_files)} GTFS files: {txt_files}")
            
            return txt_files
            
        except Exception as e:
            print(f"❌ Error extracting GTFS data: {e}")
            raise
    
    def load_routes_to_db(self):
        """Load routes from GTFS to database with better error handling"""
        routes_file = os.path.join(self.gtfs_dir, 'routes.txt')
        
        if not os.path.exists(routes_file):
            raise FileNotFoundError("routes.txt not found. Download GTFS data first.")
        
        print("🚇 Loading routes to database...")
        
        routes_loaded = 0
        routes_updated = 0
        errors = 0
        
        # Open the file and parse it row by row like a dictionary
        # the encoding parameter tells python to decode the file's bytes into characters
        with open(routes_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row_num, row in enumerate(reader, 1):
                try:
                    # Handle empty or invalid fields
                    route_id = row.get('route_id', '').strip()
                    if not route_id:
                        print(f"⚠️  Skipping row {row_num}: Missing route_id")
                        continue
                    
                    def safe_int(value, default=1):
                        if not value or value.strip() == '':
                            return default
                        try:
                            return int(value)
                        except (ValueError, TypeError):
                            return default
                    
                    route_type = safe_int(row.get('route_type'), 1)  # Default to subway
                    
                    # Check if route already exists
                    route = Route.query.get(route_id)
                    
                    if route:
                        # Update existing route
                        route.short_name = row.get('route_short_name', '').strip()
                        route.long_name = row.get('route_long_name', '').strip()
                        route.route_type = route_type
                        route.route_color = row.get('route_color', '000000').strip()
                        route.text_color = row.get('route_text_color', 'FFFFFF').strip()
                        routes_updated += 1
                    else:
                        # Create new route
                        route = Route(
                            id=route_id,
                            short_name=row.get('route_short_name', '').strip(),
                            long_name=row.get('route_long_name', '').strip(),
                            route_type=route_type,
                            route_color=row.get('route_color', '000000').strip(),
                            text_color=row.get('route_text_color', 'FFFFFF').strip()
                        )
                        db.session.add(route)
                        routes_loaded += 1
                        
                except Exception as e:
                    errors += 1
                    print(f"⚠️  Error processing route row {row_num}: {e}")
                    if errors > 10:
                        print("❌ Too many errors, stopping route processing")
                        break
                    continue
        
        try:
            db.session.commit()
            print(f"✅ Routes processed: {routes_loaded} new, {routes_updated} updated")
            if errors > 0:
                print(f"⚠️  {errors} rows had errors and were skipped")
            return routes_loaded, routes_updated
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error committing routes to database: {e}")
            raise
    
    def load_stops_to_db(self):
        """Load stops from GTFS to database with better error handling"""
        stops_file = os.path.join(self.gtfs_dir, 'stops.txt')
        
        if not os.path.exists(stops_file):
            raise FileNotFoundError("stops.txt not found. Download GTFS data first.")
        
        print("🚏 Loading stops to database...")
        
        stops_loaded = 0
        stops_updated = 0
        errors = 0
        
        with open(stops_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row_num, row in enumerate(reader, 1):
                try:
                    # Handle empty or invalid numeric fields
                    def safe_int(value, default=0):
                        if not value or value.strip() == '':
                            return default
                        try:
                            return int(value)
                        except (ValueError, TypeError):
                            return default
                    
                    def safe_float(value, default=0.0):
                        if not value or value.strip() == '':
                            return default
                        try:
                            return float(value)
                        except (ValueError, TypeError):
                            return default
                    
                    # Parse fields with error handling
                    stop_id = row.get('stop_id', '').strip()
                    if not stop_id:
                        print(f"⚠️  Skipping row {row_num}: Missing stop_id")
                        continue
                    
                    stop_name = row.get('stop_name', '').strip()
                    if not stop_name:
                        print(f"⚠️  Skipping row {row_num}: Missing stop_name for {stop_id}")
                        continue
                    
                    latitude = safe_float(row.get('stop_lat'))
                    longitude = safe_float(row.get('stop_lon'))
                    location_type = safe_int(row.get('location_type'), 0)
                    
                    # Skip stops with invalid coordinates
                    if latitude == 0.0 and longitude == 0.0:
                        print(f"⚠️  Skipping {stop_id}: Invalid coordinates")
                        continue
                    
                    # Check if stop already exists
                    stop = Stop.query.get(stop_id)
                    
                    if stop:
                        # Update existing stop
                        stop.name = stop_name
                        stop.latitude = latitude
                        stop.longitude = longitude
                        stop.zone_id = row.get('zone_id', '').strip() or None
                        stop.location_type = location_type
                        stop.parent_station = row.get('parent_station', '').strip() or None
                        stops_updated += 1
                    else:
                        # Create new stop
                        stop = Stop(
                            id=stop_id,
                            name=stop_name,
                            latitude=latitude,
                            longitude=longitude,
                            zone_id=row.get('zone_id', '').strip() or None,
                            location_type=location_type,
                            parent_station=row.get('parent_station', '').strip() or None
                        )
                        db.session.add(stop)
                        stops_loaded += 1
                        
                except Exception as e:
                    errors += 1
                    print(f"⚠️  Error processing row {row_num}: {e}")
                    if errors > 10:  # Stop if too many errors
                        print("❌ Too many errors, stopping stop processing")
                        break
                    continue
        
        try:
            db.session.commit()
            print(f"✅ Stops processed: {stops_loaded} new, {stops_updated} updated")
            if errors > 0:
                print(f"⚠️  {errors} rows had errors and were skipped")
            return stops_loaded, stops_updated
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error committing stops to database: {e}")
            raise
    
    def load_all_gtfs_data(self, force_download=False):
        """Download and load all GTFS data"""
        try:
            # Download and extract
            zip_path = self.download_gtfs_data(force_download)
            self.extract_gtfs_data(zip_path)
            
            # Load to database
            routes_new, routes_updated = self.load_routes_to_db()
            stops_new, stops_updated = self.load_stops_to_db()
            
            print(f"""
🎉 GTFS Data Loading Complete!
📊 Routes: {routes_new} new, {routes_updated} updated
🚏 Stops: {stops_new} new, {stops_updated} updated
💾 Data stored in: {self.gtfs_dir}
            """)
            
            return {
                'success': True,
                'routes': {'new': routes_new, 'updated': routes_updated},
                'stops': {'new': stops_new, 'updated': stops_updated}
            }
            
        except Exception as e:
            print(f"❌ Error loading GTFS data: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_data_stats(self):
        """Get statistics about loaded data"""
        try:
            routes_count = Route.query.count()
            stops_count = Stop.query.count()
            
            # Check file dates
            zip_path = os.path.join(self.gtfs_dir, 'google_transit.zip')
            last_download = None
            if os.path.exists(zip_path):
                last_download = datetime.fromtimestamp(os.path.getmtime(zip_path))
            
            return {
                'routes_count': routes_count,
                'stops_count': stops_count,
                'last_download': last_download,
                'data_directory': self.gtfs_dir
            }
        except Exception as e:
            return {'error': str(e)}