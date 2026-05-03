from datetime import datetime, timedelta
import time
import requests
import logging
from flask import current_app
from google.transit import gtfs_realtime_pb2
from app.models.transit import Route, Stop, Trip, StopRoute

logger = logging.getLogger(__name__)

class RealtimeDataService:
    """Service for handling MTA real-time data"""
    
    # MTA feed mappings - Updated to use direct URLs without API key requirement
    FEED_MAPPINGS = {
        '123456': ['1', '2', '3', '4', '5', '6', '6X'],
        'ace': ['A', 'C', 'E'],
        'bdfm': ['B', 'D', 'F', 'M', 'FX'],
        'g': ['G'],
        'jz': ['J', 'Z'],
        'nqrw': ['N', 'Q', 'R', 'W'],
        'l': ['L'],
        'si': ['SI'],
        '7': ['7', '7X']
    }
    
    # Direct MTA feed URLs (no API key required)
    FEED_URLS = {
        '123456': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs',
        'ace': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-ace',
        'bdfm': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-bdfm',
        'g': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-g',
        'jz': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-jz',
        'nqrw': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-nqrw',
        'l': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-l',
        'si': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-si',
        '7': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs'
    }
    
    def __init__(self):
        self.api_key = current_app.config.get('MTA_API_KEY')  # Optional now
        self.base_url = "https://api-endpoint.mta.info/feeds"
        
        if not self.api_key:
            logger.info("No MTA API key configured - using public feeds")
    
    def get_arrivals_for_stop(self, stop_id, route_ids=None):
        """Get real-time arrivals for a specific stop, searching all relevant feeds and child stops"""
        try:
            from app.models.transit import Stop
            arrivals = []
            seen_trips = set()  # Track unique trips to avoid duplicates
            logger.info(f"Getting arrivals for stop {stop_id} with routes {route_ids}")

            # Gather all relevant stop IDs: the stop itself and any child stops (directional platforms)
            stop_ids = [stop_id]
            # If this is a parent station, add all child stops
            child_stops = Stop.query.filter(Stop.parent_station == stop_id).all()
            stop_ids += [child.id for child in child_stops]
            # Also add directional stops (N/S/E/W suffixes) if not already included
            for suffix in ['N', 'S', 'E', 'W']:
                dir_stop_id = stop_id + suffix
                if dir_stop_id not in stop_ids:
                    dir_stop = Stop.query.get(dir_stop_id)
                    if dir_stop:
                        stop_ids.append(dir_stop_id)
            
            logger.info(f"Checking stop IDs: {stop_ids}")

            # Get all unique routes that serve any of these stops
            all_route_ids = set()
            for sid in stop_ids:
                s = Stop.query.get(sid)
                if s:
                    for route in s.get_routes():
                        all_route_ids.add(route.id)
            if route_ids:
                all_route_ids.update(route_ids)
            route_ids = list(all_route_ids)

            # Determine which feeds to check based on route_ids
            feeds_to_check = set()
            for feed_id, routes in self.FEED_MAPPINGS.items():
                if any(route in routes for route in route_ids):
                    feeds_to_check.add(feed_id)
            if not feeds_to_check:
                feeds_to_check = set(self.FEED_MAPPINGS.keys())  # fallback: check all feeds

            logger.info(f"Checking feeds: {feeds_to_check}")
            found_stop_ids = set()
            
            # Process all feeds and collect all potential arrivals
            all_potential_arrivals = []
            
            for feed_id in feeds_to_check:
                feed_data = self._get_feed_data(feed_id)
                if feed_data:
                    # Log all stop IDs found in this feed for debugging
                    for entity in feed_data.entity:
                        if entity.HasField('trip_update'):
                            for stu in entity.trip_update.stop_time_update:
                                found_stop_ids.add(stu.stop_id)
                    
                    # For each relevant stop_id, get arrivals
                    for sid in stop_ids:
                        arrivals_for_sid = self._process_trip_updates_for_stop(feed_data, sid, route_ids)
                        for arr in arrivals_for_sid:
                            arr['stop_id'] = sid
                        all_potential_arrivals.extend(arrivals_for_sid)
            
            # Only keep the soonest arrival per (trip_id, route, direction, parent_station)
            trip_arrivals = {}
            for arrival in all_potential_arrivals:
                stop_id = arrival['stop_id']
                stop = Stop.query.get(stop_id)
                parent_station = stop.parent_station if stop and stop.parent_station else stop_id
                key = (arrival['trip_id'], arrival['route'], arrival['direction'], parent_station)
                if key not in trip_arrivals or arrival['arrival_time'] < trip_arrivals[key]['arrival_time']:
                    trip_arrivals[key] = arrival
            arrivals = list(trip_arrivals.values())
            
            logger.info(f"Sample stop IDs in feeds: {list(found_stop_ids)[:20]}")
            logger.info(f"Total arrivals found: {len(arrivals)}")
            arrivals.sort(key=lambda x: x.get('arrival_time', 0))
            return arrivals
        except Exception as e:
            logger.error(f"Error getting arrivals for stop {stop_id}: {e}")
            return []
    
    def get_route_status(self, route_id):
        """Get service status for a specific route"""
        try:
            # Find which feed contains this route
            feed_id = None
            for feed, routes in self.FEED_MAPPINGS.items():
                if route_id in routes:
                    feed_id = feed
                    break
            
            if not feed_id:
                return {
                    'status': 'unknown',
                    'message': 'Route not found in feed mappings',
                    'color': '#999999'
                }
            
            # Get feed data
            feed_data = self._get_feed_data(feed_id)
            if not feed_data:
                return {
                    'status': 'unknown',
                    'message': 'Unable to fetch feed data',
                    'color': '#999999'
                }
            
            # Analyze feed for service status
            status = self._analyze_route_status(feed_data, route_id)
            return status
            
        except Exception as e:
            logger.error(f"Error getting status for route {route_id}: {e}")
            return {
                'status': 'unknown',
                'message': 'Error fetching status',
                'color': '#999999'
            }
    
    def _get_feed_data(self, feed_id):
        """Get GTFS real-time data from MTA API"""
        try:
            # Use direct feed URL if available, otherwise fall back to old method
            if feed_id in self.FEED_URLS:
                url = self.FEED_URLS[feed_id]
            else:
                url = f"{self.base_url}/{feed_id}/gtfs-realtime"
            
            headers = {}
            # API key is now optional
            if self.api_key:
                headers['x-api-key'] = self.api_key
            
            logger.info(f"Fetching feed {feed_id} from {url}")
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Parse protobuf data
            feed = gtfs_realtime_pb2.FeedMessage()
            feed.ParseFromString(response.content)
            
            logger.info(f"Successfully parsed feed {feed_id} with {len(feed.entity)} entities")
            return feed
            
        except Exception as e:
            logger.error(f"Error fetching feed {feed_id}: {e}")
            return None
    
    def _parse_arrivals_from_feed(self, feed, stop_id, route_ids=None):
        """Parse arrival times from GTFS real-time feed"""
        arrivals = []
        current_time = int(time.time())
        
        try:
            for entity in feed.entity:
                if entity.HasField('trip_update'):
                    trip_update = entity.trip_update
                    
                    # Get route ID from trip
                    route_id = None
                    if trip_update.trip.HasField('route_id'):
                        route_id = trip_update.trip.route_id
                    
                    # Filter by route if specified
                    if route_ids and route_id not in route_ids:
                        continue
                    
                    # Parse stop time updates
                    for stop_time_update in trip_update.stop_time_update:
                        if stop_time_update.stop_id == stop_id:
                            arrival_time = None
                            
                            if stop_time_update.HasField('arrival'):
                                arrival_time = stop_time_update.arrival.time
                            elif stop_time_update.HasField('arrival_time'):
                                arrival_time = stop_time_update.arrival_time
                            
                            if arrival_time:
                                # Calculate minutes until arrival
                                minutes_until = (arrival_time - current_time) // 60
                                
                                if 0 <= minutes_until <= 30:  # Only show arrivals within 30 minutes
                                    arrival = {
                                        'route': route_id,
                                        'minutes': minutes_until,
                                        'arrival_time': arrival_time,
                                        'direction': self._get_direction(trip_update.trip),
                                        'status': self._get_status(minutes_until),
                                        'trip_id': trip_update.trip.trip_id
                                    }
                                    arrivals.append(arrival)
            
            return arrivals
            
        except Exception as e:
            logger.error(f"Error parsing arrivals from feed: {e}")
            return []
    
    def _get_direction(self, trip):
        """Get direction from trip information"""
        try:
            if trip.HasField('trip_id'):
                trip_id = trip.trip_id.lower()
                if 'north' in trip_id or 'uptown' in trip_id:
                    return 'Northbound'
                elif 'south' in trip_id or 'downtown' in trip_id:
                    return 'Southbound'
                elif 'east' in trip_id:
                    return 'Eastbound'
                elif 'west' in trip_id:
                    return 'Westbound'
            
            # Default direction based on trip ID pattern
            return 'Northbound'  # Default fallback
            
        except Exception as e:
            logger.error(f"Error getting direction: {e}")
            return 'Unknown'
    
    def _get_status(self, minutes_until):
        """Get status based on arrival time"""
        if minutes_until <= 1:
            return 'Arriving'
        elif minutes_until <= 3:
            return 'Approaching'
        else:
            return 'On Time'
    
    def _analyze_route_status(self, feed, route_id):
        """Analyze feed data to determine route status"""
        try:
            # Count delays and issues
            total_trips = 0
            delayed_trips = 0
            rerouted_trips = 0
            skipped_stops = 0
            
            for entity in feed.entity:
                if entity.HasField('trip_update'):
                    trip_update = entity.trip_update
                    
                    if trip_update.trip.HasField('route_id') and trip_update.trip.route_id == route_id:
                        total_trips += 1
                        
                        # Check for delays and issues
                        for stop_time_update in trip_update.stop_time_update:
                            # Check for delays
                            if stop_time_update.HasField('delay'):
                                if stop_time_update.delay > 300:  # 5 minutes or more
                                    delayed_trips += 1
                                    break
                            
                            # Check for skipped stops
                            if stop_time_update.HasField('schedule_relationship'):
                                if stop_time_update.schedule_relationship == 2:  # SKIPPED
                                    skipped_stops += 1
                        
                        # Check for reroutes (different from scheduled route)
                        if trip_update.trip.HasField('schedule_relationship'):
                            if trip_update.trip.schedule_relationship == 1:  # ADDED
                                rerouted_trips += 1
            
            # Determine status based on various factors
            if total_trips == 0:
                return {
                    'status': 'unknown',
                    'message': 'No trip data available',
                    'color': '#999999'
                }
            
            # Calculate percentages
            delay_percentage = (delayed_trips / total_trips) * 100 if total_trips > 0 else 0
            reroute_percentage = (rerouted_trips / total_trips) * 100 if total_trips > 0 else 0
            
            # Determine status based on issues
            if skipped_stops > 0:
                return {
                    'status': 'stops_skipped',
                    'message': 'Stops Skipped',
                    'color': '#ff4444'
                }
            elif reroute_percentage > 20:
                return {
                    'status': 'rerouted',
                    'message': 'Rerouted',
                    'color': '#ff8800'
                }
            elif delay_percentage > 50:
                return {
                    'status': 'significant_delays',
                    'message': 'Significant Delays',
                    'color': '#ff4444'
                }
            elif delay_percentage > 20:
                return {
                    'status': 'some_delays',
                    'message': 'Some Delays',
                    'color': '#ffbb33'
                }
            else:
                return {
                    'status': 'good_service',
                    'message': 'Good Service',
                    'color': '#00C851'
                }
                
        except Exception as e:
            logger.error(f"Error analyzing route status for {route_id}: {e}")
            return {
                'status': 'unknown',
                'message': 'Unable to determine status',
                'color': '#999999'
            }
    
    def _get_feed_health(self):
        """Get health status of all feeds"""
        health_status = {}
        
        for feed_id, feed_url in self.FEED_URLS.items():
            try:
                response = requests.get(feed_url, timeout=5)
                health_status[feed_id] = {
                    'status': 'healthy' if response.status_code == 200 else 'unhealthy',
                    'status_code': response.status_code,
                    'last_check': datetime.now().isoformat()
                }
            except Exception as e:
                health_status[feed_id] = {
                    'status': 'error',
                    'error': str(e),
                    'last_check': datetime.now().isoformat()
                }
        
        return health_status

    def get_feed_health(self):
        """Get health status of all feeds"""
        return self._get_feed_health()

    def _process_trip_updates_for_stop(self, trip_updates, stop_id, route_ids=None):
        """Process trip updates to find arrivals for a specific stop"""
        arrivals = []
        current_time = int(time.time())
        found_stops = set()
        
        try:
            logger.info(f"Processing trip updates for stop {stop_id}")
            
            for entity in trip_updates.entity:
                if not entity.HasField('trip_update'):
                    continue
                
                trip_update = entity.trip_update
                trip = trip_update.trip
                
                # Check if this trip is for a route we're interested in
                if route_ids and trip.route_id not in route_ids:
                    continue
                
                # Process stop time updates
                for stop_time_update in trip_update.stop_time_update:
                    found_stops.add(stop_time_update.stop_id)
                    
                    if stop_time_update.stop_id == stop_id:
                        logger.info(f"Found matching stop {stop_id} in trip {trip.trip_id}")
                        
                        # Calculate arrival time
                        if stop_time_update.HasField('arrival'):
                            arrival_time = stop_time_update.arrival.time
                            minutes = max(0, (arrival_time - current_time) // 60)
                            
                            # Only include arrivals in the next 30 minutes
                            if 0 <= minutes <= 30:
                                # Determine direction based on stop ID suffix
                                direction = self._get_direction_from_stop_id(stop_id, trip)
                                
                                # Determine status based on arrival time
                                if minutes == 0:
                                    status = 'Arriving'
                                elif minutes <= 3:
                                    status = 'Approaching'
                                else:
                                    status = self._get_status_from_delay(stop_time_update)
                                
                                arrival = {
                                    'route': trip.route_id,
                                    'minutes': minutes,
                                    'arrival_time': arrival_time,
                                    'direction': direction,
                                    'status': status,
                                    'trip_id': trip.trip_id
                                }
                                arrivals.append(arrival)
                                logger.info(f"Added arrival: {arrival}")
            
            # Log some sample stop IDs for debugging
            sample_stops = list(found_stops)[:10]
            logger.info(f"Sample stop IDs in real-time data: {sample_stops}")
            logger.info(f"Looking for stop {stop_id}, found {len(arrivals)} arrivals")
        
        except Exception as e:
            logger.error(f"Error processing trip updates: {e}")
        
        return arrivals

    def _process_vehicle_positions_for_stop(self, vehicle_positions, stop_id, route_ids=None):
        """Process vehicle positions to estimate arrivals for a specific stop"""
        arrivals = []
        current_time = int(time.time())
        
        try:
            # Get stop location
            from app.models.transit import Stop
            stop = Stop.query.get(stop_id)
            if not stop:
                return arrivals
            
            stop_lat = stop.latitude
            stop_lon = stop.longitude
            
            for entity in vehicle_positions.entity:
                if not entity.HasField('vehicle'):
                    continue
                
                vehicle = entity.vehicle
                trip = vehicle.trip
                
                # Check if this vehicle is for a route we're interested in
                if route_ids and trip.route_id not in route_ids:
                    continue
                
                # Calculate distance to stop
                if vehicle.HasField('position'):
                    vehicle_lat = vehicle.position.latitude
                    vehicle_lon = vehicle.position.longitude
                    
                    distance = self._calculate_distance(
                        vehicle_lat, vehicle_lon, 
                        stop_lat, stop_lon
                    )
                    
                    # Estimate arrival time based on distance and average speed
                    # Assume average speed of 20 mph (about 0.0055 degrees per minute)
                    estimated_minutes = max(1, int(distance / 0.0055))
                    
                    if estimated_minutes <= 30:  # Only show arrivals within 30 minutes
                        arrival = {
                            'route': trip.route_id,
                            'minutes': estimated_minutes,
                            'arrival_time': current_time + (estimated_minutes * 60),
                            'direction': self._get_direction_from_trip(trip),
                            'status': 'Estimated',
                            'trip_id': trip.trip_id
                        }
                        arrivals.append(arrival)
        
        except Exception as e:
            logger.error(f"Error processing vehicle positions: {e}")
        
        return arrivals

    def _get_direction_from_trip(self, trip):
        """Get direction from trip information"""
        # First try to get direction from trip headsign
        if hasattr(trip, 'trip_headsign') and trip.trip_headsign:
            headsign = trip.trip_headsign.lower()
            if any(word in headsign for word in ['north', 'uptown', 'manhattan', 'bronx']):
                return 'Northbound'
            elif any(word in headsign for word in ['south', 'downtown', 'brooklyn', 'queens']):
                return 'Southbound'
            elif any(word in headsign for word in ['east', 'queens', 'flushing']):
                return 'Eastbound'
            elif any(word in headsign for word in ['west', 'manhattan', 'times square']):
                return 'Westbound'
        
        # Fallback to direction_id if available
        if hasattr(trip, 'direction_id'):
            if trip.direction_id == 0:
                return 'Northbound'
            elif trip.direction_id == 1:
                return 'Southbound'
        
        return 'Unknown'

    def _get_direction_from_stop_id(self, stop_id, trip):
        """Get direction based on stop ID suffix and route terminus"""
        # Check if stop ID has direction suffix
        if stop_id.endswith('N'):
            return self._get_north_terminus(trip.route_id)
        elif stop_id.endswith('S'):
            return self._get_south_terminus(trip.route_id)
        elif stop_id.endswith('E'):
            return self._get_east_terminus(trip.route_id)
        elif stop_id.endswith('W'):
            return self._get_west_terminus(trip.route_id)
        
        # Fallback to trip headsign or direction_id
        return self._get_direction_from_trip(trip)

    def _get_north_terminus(self, route_id):
        """Get the north terminus for a route"""
        termini = {
            '1': 'Van Cortlandt Park',
            '2': 'Wakefield-241 St',
            '3': 'Harlem-148 St',
            '4': 'Woodlawn',
            '5': 'Eastchester-Dyre Av',
            '6': 'Pelham Bay Park',
            '7': 'Flushing-Main St',
            'A': 'Inwood-207 St',
            'B': 'Bedford Park Blvd',
            'C': '168 St',
            'D': 'Norwood-205 St',
            'E': 'Jamaica Center',
            'F': 'Jamaica-179 St',
            'G': 'Court Sq',
            'J': 'Jamaica Center',
            'L': 'Canarsie-Rockaway Pkwy',
            'M': 'Forest Hills-71 Av',
            'N': 'Astoria-Ditmars Blvd',
            'Q': '96 St',
            'R': 'Forest Hills-71 Av',
            'W': 'Astoria-Ditmars Blvd',
            'Z': 'Jamaica Center'
        }
        return termini.get(route_id, 'Northbound')

    def _get_south_terminus(self, route_id):
        """Get the south terminus for a route"""
        termini = {
            '1': 'South Ferry',
            '2': 'Flatbush Av-Brooklyn College',
            '3': 'New Lots Av',
            '4': 'Crown Hts-Utica Av',
            '5': 'Flatbush Av-Brooklyn College',
            '6': 'Brooklyn Bridge-City Hall',
            '7': '34 St-Hudson Yards',
            'A': 'Far Rockaway',
            'B': 'Brighton Beach',
            'C': 'Euclid Av',
            'D': 'Coney Island-Stillwell Av',
            'E': 'World Trade Center',
            'F': 'Coney Island-Stillwell Av',
            'G': 'Church Av',
            'J': 'Broad St',
            'L': '8 Av',
            'M': 'Middle Village-Metropolitan Av',
            'N': 'Coney Island-Stillwell Av',
            'Q': 'Coney Island-Stillwell Av',
            'R': 'Bay Ridge-95 St',
            'W': 'Whitehall St-South Ferry',
            'Z': 'Broad St'
        }
        return termini.get(route_id, 'Southbound')

    def _get_east_terminus(self, route_id):
        """Get the east terminus for a route"""
        termini = {
            '7': 'Flushing-Main St',
            'G': 'Court Sq',
            'L': 'Canarsie-Rockaway Pkwy'
        }
        return termini.get(route_id, 'Eastbound')

    def _get_west_terminus(self, route_id):
        """Get the west terminus for a route"""
        termini = {
            '7': '34 St-Hudson Yards',
            'G': 'Church Av',
            'L': '8 Av'
        }
        return termini.get(route_id, 'Westbound')

    def _get_status_from_delay(self, stop_time_update):
        """Get status from delay information"""
        if stop_time_update.HasField('arrival') and stop_time_update.arrival.HasField('delay'):
            delay = stop_time_update.arrival.delay
            if delay < -60:  # More than 1 minute early
                return 'Early'
            elif delay > 60:  # More than 1 minute late
                return 'Delayed'
            else:
                return 'On Time'
        
        return 'On Time'

    def _calculate_distance(self, lat1, lon1, lat2, lon2):
        """Calculate distance between two points in degrees"""
        import math
        return math.sqrt((lat2 - lat1)**2 + (lon2 - lon1)**2) 