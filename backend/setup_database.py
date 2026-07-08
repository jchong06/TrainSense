#!/usr/bin/env python3
"""
Script to set up the database and import real MTA data
"""
import os
import sys
import logging
from datetime import datetime

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models.transit import Route, Stop, Trip, StopRoute
from app.services.gtfs_service import GTFSService

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_database():
    """Set up the database tables"""
    try:
        app = create_app()
        with app.app_context():
            logger.info("Creating database tables...")
            db.create_all()
            logger.info("Database tables created successfully")
            return True
    except Exception as e:
        logger.error(f"Error setting up database: {e}")
        return False

def import_mta_data():
    """Import MTA data using the GTFS service"""
    try:
        logger.info("Starting MTA data import...")
        
        app = create_app()
        with app.app_context():
            gtfs_service = GTFSService()
            
            # Download and extract GTFS data
            logger.info("Downloading GTFS data...")
            zip_path = gtfs_service.download_gtfs_data()
            txt_files = gtfs_service.extract_gtfs_data(zip_path)
            
            # Load data into database
            logger.info("Loading routes to database...")
            routes_loaded, routes_updated = gtfs_service.load_routes_to_db()
            
            logger.info("Loading stops to database...")
            stops_loaded, stops_updated = gtfs_service.load_stops_to_db()
            
            logger.info("Loading trips to database...")
            trips_loaded, trips_updated = gtfs_service.load_trips_to_db()
            
            logger.info("Creating stop-route relationships...")
            stop_routes_created = create_stop_route_relationships()
            
            logger.info(f"Import completed:")
            logger.info(f"  - Routes: {routes_loaded} new, {routes_updated} updated")
            logger.info(f"  - Stops: {stops_loaded} new, {stops_updated} updated")
            logger.info(f"  - Trips: {trips_loaded} new, {trips_updated} updated")
            logger.info(f"  - Stop-Route relationships: {stop_routes_created}")
            
            return True
            
    except Exception as e:
        logger.error(f"Error during MTA data import: {e}")
        return False

def create_stop_route_relationships():
    """Create real stop-route relationships from stop_times.txt joined with trips.

    Reads which stops each trip visits (stop_times.txt) and maps each trip to its
    route (trips table), producing the distinct set of (route_id, stop_id) pairs
    that the trip planner uses to build its graph.
    """
    try:
        logger.info("Creating stop-route relationships...")

        gtfs_dir = GTFSService().gtfs_dir
        stop_times_file = os.path.join(gtfs_dir, 'stop_times.txt')
        if not os.path.exists(stop_times_file):
            logger.error("stop_times.txt not found; cannot build stop-route relationships")
            return 0

        # trip_id -> route_id (from the trips already loaded into the DB)
        trip_route_map = {t.id: t.route_id for t in Trip.query.all()}
        if not trip_route_map:
            logger.error("No trips in database; load trips before building relationships")
            return 0

        # Only reference stops/routes that exist, to satisfy foreign keys.
        valid_stop_ids = {s.id for s in Stop.query.with_entities(Stop.id).all()}
        valid_route_ids = {r.id for r in Route.query.with_entities(Route.id).all()}

        # Collect the distinct (route_id, stop_id) pairs actually served.
        import csv
        pairs = set()
        with open(stop_times_file, 'r', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                route_id = trip_route_map.get(row['trip_id'])
                if not route_id or route_id not in valid_route_ids:
                    continue
                stop_id = row['stop_id'].strip()
                if stop_id in valid_stop_ids:
                    pairs.add((route_id, stop_id))

        # Replace any existing relationships with the freshly computed set.
        StopRoute.query.delete()
        db.session.commit()

        mappings = [{'stop_id': s, 'route_id': r} for (r, s) in pairs]
        for i in range(0, len(mappings), 10000):
            db.session.bulk_insert_mappings(StopRoute, mappings[i:i + 10000])
            db.session.commit()

        count = len(mappings)
        logger.info(f"Created {count} stop-route relationships")
        return count

    except Exception as e:
        logger.error(f"Error creating stop-route relationships: {e}")
        db.session.rollback()
        return 0

def check_database_status():
    """Check the current status of the database"""
    try:
        app = create_app()
        with app.app_context():
            route_count = Route.query.filter_by(route_type=1).count()
            stop_count = Stop.query.count()
            stop_route_count = StopRoute.query.count()
            trip_count = Trip.query.count()
            
            logger.info("Database Status:")
            logger.info(f"  - Routes: {route_count}")
            logger.info(f"  - Stops: {stop_count}")
            logger.info(f"  - Stop-Route relationships: {stop_route_count}")
            logger.info(f"  - Trips: {trip_count}")
            
            return {
                'routes': route_count,
                'stops': stop_count,
                'stop_routes': stop_route_count,
                'trips': trip_count
            }
    except Exception as e:
        logger.error(f"Error checking database status: {e}")
        return None

def main():
    """Main setup function"""
    logger.info("Starting database setup process...")
    
    # Step 1: Set up database tables
    if not setup_database():
        logger.error("Failed to set up database tables")
        sys.exit(1)
    
    # Step 2: Check if we need to import data
    status = check_database_status()
    if status and status['routes'] > 0:
        logger.info("Database already contains data. Skipping import.")
        logger.info("To force re-import, delete the database file and run again.")
    else:
        # Step 3: Import MTA data
        if not import_mta_data():
            logger.error("Failed to import MTA data")
            sys.exit(1)
    
    # Step 4: Final status check
    final_status = check_database_status()
    if final_status:
        logger.info("Database setup completed successfully!")
        logger.info(f"Ready to serve {final_status['routes']} routes and {final_status['stops']} stops")
    else:
        logger.error("Failed to verify database setup")
        sys.exit(1)

if __name__ == "__main__":
    main() 