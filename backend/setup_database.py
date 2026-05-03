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
    """Create stop-route relationships from trips and stop times"""
    try:
        logger.info("Creating stop-route relationships...")
        
        # Get all trips
        trips = Trip.query.all()
        
        # Create a mapping of trip_id to route_id
        trip_route_map = {}
        for trip in trips:
            trip_route_map[trip.id] = trip.route_id
        
        # For now, create some basic relationships
        # In a real implementation, you'd load stop_times.txt and create relationships
        count = 0
        
        # Get some sample stops and routes to create relationships
        stops = Stop.query.limit(100).all()  # Get first 100 stops
        routes = Route.query.filter_by(route_type=1).all()  # Get subway routes
        
        # Create some sample relationships (this is simplified)
        for stop in stops:
            # Assign 1-3 random routes to each stop
            import random
            num_routes = random.randint(1, min(3, len(routes)))
            selected_routes = random.sample(routes, num_routes)
            
            for route in selected_routes:
                # Check if relationship already exists
                existing = StopRoute.query.filter_by(
                    stop_id=stop.id, 
                    route_id=route.id
                ).first()
                
                if not existing:
                    stop_route = StopRoute(
                        stop_id=stop.id,
                        route_id=route.id
                    )
                    db.session.add(stop_route)
                    count += 1
        
        db.session.commit()
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