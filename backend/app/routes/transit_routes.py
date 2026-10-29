# backend/app/routes/transit_routes.py
from flask import Blueprint, jsonify, request, current_app
from app import db
from app.models.transit import Route, Stop, Trip, StopRoute
from app.services.gtfs_service import GTFSService
from app.services.realtime_service import RealtimeDataService
from datetime import datetime, timedelta
import json
import math
import logging
import csv
import os
from collections import defaultdict, deque
from functools import lru_cache
from sqlalchemy.orm import joinedload

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

transit_bp = Blueprint('transit', __name__)

@transit_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'MTA Transit API'
    })

@transit_bp.route('/routes', methods=['GET'])
def get_routes():
    """Get all subway routes"""
    try:
        # Get only subway routes (route_type = 1)
        routes = Route.query.filter_by(route_type=1).all()
        return jsonify({
            'success': True,
            'data': [route.to_dict() for route in routes]
        })
    except Exception as e:
        logger.error(f"Error fetching routes: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch routes'
        }), 500

@transit_bp.route('/stops', methods=['GET'])
def get_stops():
    """Get all subway stops"""
    try:
        return jsonify({
            'success': True,
            'data': _station_list()
        })
    except Exception as e:
        logger.error(f"Error fetching stops: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch stops'
        }), 500

@transit_bp.route('/stops/nearby', methods=['GET'])
def get_nearby_stops():
    """Get stops near a location"""
    try:
        lat = request.args.get('lat', type=float)
        lng = request.args.get('lng', type=float)
        radius = request.args.get('radius', 1.0, type=float)  # Default 1km radius
        
        if not lat or not lng:
            return jsonify({
                'success': False,
                'error': 'Latitude and longitude are required'
            }), 400
        
        # Simple distance calculation (in a real app, use proper geospatial queries)
        stops = Stop.query.filter_by(location_type=0).all()
        nearby_stops = []
        
        for stop in stops:
            # Calculate distance using Haversine formula (simplified)
            R = 6371  # Earth's radius in km
            
            lat1, lng1 = math.radians(lat), math.radians(lng)
            lat2, lng2 = math.radians(stop.latitude), math.radians(stop.longitude)
            
            dlat = lat2 - lat1
            dlng = lng2 - lng1
            
            a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
            c = 2 * math.asin(math.sqrt(a))
            distance = R * c
            
            if distance <= radius:
                nearby_stops.append({
                    'id': stop.id,
                    'name': stop.name,
                    'latitude': stop.latitude,
                    'longitude': stop.longitude,
                    'distance_km': round(distance, 2)
                })
        
        # Sort by distance
        nearby_stops.sort(key=lambda x: x['distance_km'])
        
        return jsonify({
            'success': True,
            'data': nearby_stops[:20]  # Limit to 20 closest stops
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@transit_bp.route('/stops/<stop_id>/routes', methods=['GET'])
def get_stop_routes(stop_id):
    """Get routes that serve a specific stop"""
    try:
        stop = Stop.query.get(stop_id)
        if not stop:
            return jsonify({
                'success': False,
                'error': 'Stop not found'
            }), 404
        
        routes = stop.get_routes()
        return jsonify({
            'success': True,
            'data': [route.to_dict() for route in routes]
        })
    except Exception as e:
        logger.error(f"Error fetching stop routes: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch stop routes'
        }), 500

@transit_bp.route('/realtime/<stop_id>', methods=['GET'])
def get_realtime_updates(stop_id):
    """Get real-time arrival data for a specific stop or station (aggregates all child stops and transfer hub stops)"""
    try:
        # Get the stop
        stop = Stop.query.get(stop_id)
        if not stop:
            return jsonify({
                'success': False,
                'error': 'Stop not found'
            }), 404
        
        # --- 1. Transfer groups (cached; static GTFS data) ---
        stop_to_hub = _build_transfer_groups()
        
        # --- 2. Gather all relevant stop IDs ---
        stop_ids = [stop_id]
        
        # Check if this stop is part of a transfer hub
        hub_id = stop_to_hub.get(stop_id)
        if hub_id:
            # Add all other stops in the same hub
            for s, h in stop_to_hub.items():
                if h == hub_id and s != stop_id:
                    stop_ids.append(s)
        
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
        
        # Remove duplicates
        stop_ids = list(set(stop_ids))
        
        # Get all unique routes that serve any of these stops
        route_ids = set()
        for sid in stop_ids:
            s = Stop.query.get(sid)
            if s:
                for route in s.get_routes():
                    route_ids.add(route.id)
        route_ids = list(route_ids)
        
        # Get real-time data for all these stop IDs
        realtime_service = RealtimeDataService()
        all_arrivals = []
        for sid in stop_ids:
            arrivals = realtime_service.get_arrivals_for_stop(sid, route_ids)
            for arr in arrivals:
                arr['stop_id'] = sid  # Tag which platform this arrival is for
            all_arrivals.extend(arrivals)
        
        # Sort by soonest arrival
        all_arrivals.sort(key=lambda x: x.get('arrival_time', 0))
        
        return jsonify({
            'success': True,
            'data': {
                'stop': stop.to_dict(),
                'arrivals': all_arrivals
            }
        })
    except Exception as e:
        logger.error(f"Error fetching real-time updates: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch real-time updates'
        }), 500

def _get_parent_id(stop):
    """Return the canonical station ID (parent if available, else stop ID)."""
    return stop.parent_station if stop.parent_station else stop.id


def _find_gtfs_dir():
    """Return the first gtfs directory that contains trips.txt."""
    candidates = [
        os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'gtfs'),
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'gtfs'),
    ]
    for d in candidates:
        if os.path.exists(os.path.join(d, 'trips.txt')):
            return d
    return candidates[0]


# The helpers below derive data from the static GTFS feed / database, which doesn't
# change while the server runs, so each is computed once per process and cached.

@lru_cache(maxsize=None)
def _build_transfer_groups():
    """
    Read transfers.txt and return a dict: station_id -> hub_id (int).
    Stations connected by transfers share the same hub_id.
    """
    gtfs_dir = _find_gtfs_dir()
    transfers_file = os.path.join(gtfs_dir, 'transfers.txt')
    transfer_graph = defaultdict(set)
    if os.path.exists(transfers_file):
        with open(transfers_file, 'r', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                a = row['from_stop_id']
                b = row['to_stop_id']
                transfer_graph[a].add(b)
                transfer_graph[b].add(a)

    stop_to_hub = {}
    hub_counter = 0
    for start in list(transfer_graph):
        if start in stop_to_hub:
            continue
        hub_counter += 1
        q = deque([start])
        while q:
            s = q.popleft()
            if s in stop_to_hub:
                continue
            stop_to_hub[s] = hub_counter
            for neighbor in transfer_graph[s]:
                if neighbor not in stop_to_hub:
                    q.append(neighbor)
    return stop_to_hub


@lru_cache(maxsize=None)
def _build_route_stations_map():
    """
    Return a dict: route_id -> set of canonical node IDs served by that route.
    Collapses all platforms at a transfer hub into one node.
    """
    stop_to_hub = _build_transfer_groups()
    route_stations = defaultdict(set)
    for sr in StopRoute.query.options(joinedload(StopRoute.stop)).all():
        stop = sr.stop
        if not stop:
            continue
        parent = _get_parent_id(stop)
        node = f"hub_{stop_to_hub[parent]}" if parent in stop_to_hub else parent
        route_stations[sr.route_id].add(node)
    return dict(route_stations)


@lru_cache(maxsize=None)
def _build_node_routes_map():
    """Return a dict: node -> set of route IDs serving it (inverse of the route stations map)."""
    node_routes = defaultdict(set)
    for route_id, nodes in _build_route_stations_map().items():
        for node in nodes:
            node_routes[node].add(route_id)
    return dict(node_routes)


@lru_cache(maxsize=None)
def _routes_by_stop():
    """Return a dict: stop_id -> [Route, ...] in a single query."""
    routes = defaultdict(list)
    for sr in StopRoute.query.options(joinedload(StopRoute.route)).all():
        routes[sr.stop_id].append(sr.route)
    return routes


@lru_cache(maxsize=None)
def _station_list():
    """All stations (one per parent station) with the routes serving them."""
    stops = Stop.query.filter(
        (Stop.location_type == 1) | (Stop.parent_station.isnot(None))
    ).all()

    # Group stops by parent station to avoid duplicates
    station_dict = {}
    for stop in stops:
        station_id = stop.parent_station or stop.id
        if station_id not in station_dict:
            station_dict[station_id] = stop

    routes_by_stop = _routes_by_stop()
    stations = []
    for stop in station_dict.values():
        stop_data = stop.to_dict()
        routes = list(routes_by_stop.get(stop.id, []))
        # If no routes found for the main stop, check directional stops (N/S suffixes)
        if not routes:
            for dir_id in (stop.id + 'N', stop.id + 'S'):
                for route in routes_by_stop.get(dir_id, []):
                    if not any(r.id == route.id for r in routes):
                        routes.append(route)
        stop_data['routes'] = [route.to_dict() for route in routes]
        stations.append(stop_data)
    return stations


@lru_cache(maxsize=None)
def _map_station_list():
    """Station list for the map, with each station tagged by its transfer hub."""
    stop_to_hub = _build_transfer_groups()
    stations = []
    for station in _station_list():
        hub = stop_to_hub.get(station['id'])
        if hub is None and station.get('parent_station'):
            hub = stop_to_hub.get(station['parent_station'])
        stations.append({**station, 'hub_id': f"hub_{hub}" if hub is not None else f"hub_{station['id']}"})
    return stations


@lru_cache(maxsize=None)
def _build_stop_count_lookup():
    """
    Return a dict: (route_id, node_a, node_b) -> stop_count between them.
    Built from stop_times.txt by finding the median stop count across all trips
    for that route that serve both stops. node_a/node_b are parent station IDs
    (not hub IDs — we resolve those at call time).
    """
    gtfs_dir = _find_gtfs_dir()

    # Build trip_id -> route_id
    trip_to_route = {}
    with open(os.path.join(gtfs_dir, 'trips.txt'), encoding='utf-8') as f:
        for row in csv.DictReader(f):
            trip_to_route[row['trip_id']] = row['route_id']

    # Collect every sequence number seen for each stop on each route, across all trips
    route_stop_seqs = defaultdict(lambda: defaultdict(list))
    with open(os.path.join(gtfs_dir, 'stop_times.txt'), encoding='utf-8') as f:
        for row in csv.DictReader(f):
            route_id = trip_to_route.get(row['trip_id'])
            if route_id:
                route_stop_seqs[route_id][row['stop_id']].append(int(row['stop_sequence']))

    # route_id -> {stop_id -> median sequence position}; count = |seq_a - seq_b|
    route_stop_seq = defaultdict(dict)
    for route_id, stop_seqs in route_stop_seqs.items():
        for stop_id, seqs in stop_seqs.items():
            route_stop_seq[route_id][stop_id] = sorted(seqs)[len(seqs) // 2]  # median

    return route_stop_seq


def _get_stop_count(route_id, from_stop_ids, to_stop_ids, route_stop_seq):
    """
    Return the number of stops between two sets of stop IDs on a route.
    from_stop_ids / to_stop_ids are lists of candidate stop IDs (N/S variants).
    Returns None if not computable.
    """
    seq_map = route_stop_seq.get(route_id, {})
    from_seqs = [seq_map[s] for s in from_stop_ids if s in seq_map]
    to_seqs = [seq_map[s] for s in to_stop_ids if s in seq_map]
    if not from_seqs or not to_seqs:
        return None
    return abs(from_seqs[0] - to_seqs[0])


def _get_station_node(station_id, stop_to_hub):
    """Return the graph node for a station (hub node or station ID)."""
    return f"hub_{stop_to_hub[station_id]}" if station_id in stop_to_hub else station_id


def _get_node_routes(node):
    """Return all route IDs that serve a node."""
    return _build_node_routes_map().get(node, set())


# Routes that share the same physical track and are interchangeable for planning
_ROUTE_TRUNK = {
    'A': 'ACE', 'C': 'ACE', 'E': 'ACE',
    'B': 'BDFM', 'D': 'BDFM', 'F': 'BDFM', 'FX': 'BDFM', 'M': 'BDFM',
    'N': 'NQRW', 'Q': 'NQRW', 'R': 'NQRW', 'W': 'NQRW',
    '1': '123', '2': '123', '3': '123',
    '4': '456', '5': '456', '6': '456', '6X': '456',
    '7': '7', '7X': '7',
    'J': 'JZ', 'Z': 'JZ',
    'L': 'L', 'G': 'G', 'S': 'S', 'GS': 'S', 'FS': 'S',
    'H': 'H', 'SI': 'SI',
}

def _trunk(route_id):
    return _ROUTE_TRUNK.get(route_id, route_id)


def _bfs_all_paths(origin_node, dest_node, route_stations_map):
    """
    BFS that collects distinct paths. Strategy:
    - Collect all direct (0-transfer) paths, deduplicated by trunk.
    - If no direct paths exist, collect 1-transfer paths deduplicated by trunk pair.
    - If still none, try 2-transfer paths.
    - Cap at 8 results total. Never show 2-transfer options when 1-transfer exist.
    - Reject paths that loop back to the same trunk (e.g. 3 -> R -> 3).
    """
    MAX_OPTIONS = 8

    for max_legs in [1, 2, 3]:
        found_paths = []
        seen_trunk_combos = set()

        queue = deque()
        queue.append((origin_node, None, []))
        visited = set()
        visited.add((origin_node, None))

        while queue:
            node, last_route, legs = queue.popleft()

            if len(legs) >= max_legs:
                continue

            for route_id in _get_node_routes(node):
                for next_node in route_stations_map.get(route_id, set()):
                    if next_node == node:
                        continue
                    new_leg = {'route_id': route_id, 'from_node': node, 'to_node': next_node}
                    new_legs = legs + [new_leg]

                    if next_node == dest_node:
                        merged = _merge_legs(new_legs)
                        trunks = [_trunk(l['route_id']) for l in merged]
                        # Reject paths that visit the same trunk twice (loop)
                        if len(trunks) != len(set(trunks)):
                            continue
                        trunk_combo = tuple(trunks)
                        if trunk_combo not in seen_trunk_combos:
                            seen_trunk_combos.add(trunk_combo)
                            found_paths.append(merged)
                        continue

                    state = (next_node, route_id)
                    if state not in visited:
                        visited.add(state)
                        queue.append((next_node, route_id, new_legs))

        if found_paths:
            return found_paths[:MAX_OPTIONS]

    return []


def _merge_legs(legs):
    """Merge consecutive legs on the same route into one leg."""
    merged = []
    for leg in legs:
        if merged and merged[-1]['route_id'] == leg['route_id']:
            merged[-1]['to_node'] = leg['to_node']
        else:
            merged.append(dict(leg))
    return merged


@transit_bp.route('/plan-trip', methods=['POST'])
def plan_trip():
    """Plan a trip and return ALL viable routes with real stop-count-based time estimates."""
    try:
        data = request.get_json()
        origin_id = data.get('origin_id')
        destination_id = data.get('destination_id')

        if not origin_id or not destination_id:
            return jsonify({'success': False, 'error': 'Origin and destination IDs are required'}), 400

        origin = Stop.query.get(origin_id)
        destination = Stop.query.get(destination_id)

        if not origin or not destination:
            return jsonify({'success': False, 'error': 'Origin or destination stop not found'}), 404

        origin_parent = _get_parent_id(origin)
        dest_parent = _get_parent_id(destination)

        stop_to_hub = _build_transfer_groups()
        hub_to_stops = defaultdict(list)
        for stop_id, hub_id in stop_to_hub.items():
            hub_to_stops[hub_id].append(stop_id)

        route_stations_map = _build_route_stations_map()
        route_stop_seq = _build_stop_count_lookup()

        origin_node = _get_station_node(origin_parent, stop_to_hub)
        dest_node = _get_station_node(dest_parent, stop_to_hub)

        all_paths = _bfs_all_paths(origin_node, dest_node, route_stations_map)

        if not all_paths:
            return jsonify({'success': False, 'error': 'No route found between these stations'}), 404

        # Resolve a graph node to a Stop dict for display
        def stop_dict_for_node(node):
            if node.startswith('hub_'):
                hub_id = int(node[4:])
                for sid in hub_to_stops.get(hub_id, []):
                    s = Stop.query.get(sid)
                    if s and s.location_type == 1:  # prefer parent stations
                        return s.to_dict()
                for sid in hub_to_stops.get(hub_id, []):
                    s = Stop.query.get(sid)
                    if s:
                        return s.to_dict()
            s = Stop.query.get(node)
            return s.to_dict() if s else {'id': node, 'name': node}

        # Get stop IDs associated with a node for time lookup
        def stop_ids_for_node(node):
            if node.startswith('hub_'):
                hub_id = int(node[4:])
                return hub_to_stops.get(hub_id, [])
            return [node, node + 'N', node + 'S']

        def estimate_minutes(legs):
            total_stops = 0
            for leg in legs:
                from_ids = stop_ids_for_node(leg['from_node'])
                to_ids = stop_ids_for_node(leg['to_node'])
                count = _get_stop_count(leg['route_id'], from_ids, to_ids, route_stop_seq)
                total_stops += count if count is not None else 5  # fallback 5 stops
            transfers = len(legs) - 1
            # ~2.5 min per stop + 4 min per transfer + 2 min base
            return int(2.5 * total_stops + 4 * transfers + 2)

        options = []
        for path in all_paths:
            transfers = len(path) - 1
            est = estimate_minutes(path)
            response_legs = []
            for leg in path:
                route = Route.query.get(leg['route_id'])
                response_legs.append({
                    'route': route.to_dict() if route else {'id': leg['route_id']},
                    'from_stop': stop_dict_for_node(leg['from_node']),
                    'to_stop': stop_dict_for_node(leg['to_node']),
                })
            options.append({
                'legs': response_legs,
                'transfers': transfers,
                'estimated_minutes': est,
                'estimated_time': f"~{est} min",
            })

        # Sort by estimated time
        options.sort(key=lambda o: o['estimated_minutes'])

        return jsonify({
            'success': True,
            'data': {
                'origin': origin.to_dict(),
                'destination': destination.to_dict(),
                'options': options,
            }
        })

    except Exception as e:
        logger.error(f"Error planning trip: {e}")
        return jsonify({'success': False, 'error': 'Failed to plan trip'}), 500

@transit_bp.route('/map/stations', methods=['GET'])
def get_map_stations():
    """Get all stations for the map view, with transfer hub grouping"""
    try:
        return jsonify({
            'success': True,
            'data': _map_station_list()
        })
    except Exception as e:
        logger.error(f"Error fetching map stations: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch map stations'
        }), 500

@transit_bp.route('/realtime/health', methods=['GET'])
def get_realtime_health():
    """Get health status of all real-time feeds"""
    try:
        realtime_service = RealtimeDataService()
        result = realtime_service.get_feed_health()
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@transit_bp.route('/service-status', methods=['GET'])
def get_service_status():
    """Get current service status for all routes"""
    try:
        # Get all subway routes
        routes = Route.query.filter_by(route_type=1).all()
        
        # For demonstration, return mock service status with realistic issues
        status_data = []
        
        # Mock service issues for demonstration
        mock_issues = {
            '4': {'status': 'some_delays', 'message': 'Some Delays', 'color': '#ffbb33'},
            '5': {'status': 'significant_delays', 'message': 'Significant Delays', 'color': '#ff4444'},
            '6': {'status': 'stops_skipped', 'message': 'Stops Skipped', 'color': '#ff4444'},
            '7': {'status': 'rerouted', 'message': 'Rerouted', 'color': '#ff8800'},
            'A': {'status': 'some_delays', 'message': 'Some Delays', 'color': '#ffbb33'},
            'C': {'status': 'good_service', 'message': 'Good Service', 'color': '#00C851'},
            'E': {'status': 'good_service', 'message': 'Good Service', 'color': '#00C851'},
            'F': {'status': 'station_notice', 'message': 'Station Notice', 'color': '#ff8800'},
            'M': {'status': 'good_service', 'message': 'Good Service', 'color': '#00C851'},
            'N': {'status': 'some_delays', 'message': 'Some Delays', 'color': '#ffbb33'},
            'Q': {'status': 'good_service', 'message': 'Good Service', 'color': '#00C851'},
            'R': {'status': 'good_service', 'message': 'Good Service', 'color': '#00C851'},
            'W': {'status': 'good_service', 'message': 'Good Service', 'color': '#00C851'},
            'L': {'status': 'good_service', 'message': 'Good Service', 'color': '#00C851'},
            'G': {'status': 'good_service', 'message': 'Good Service', 'color': '#00C851'},
            'J': {'status': 'good_service', 'message': 'Good Service', 'color': '#00C851'},
            'Z': {'status': 'good_service', 'message': 'Good Service', 'color': '#00C851'},
            '1': {'status': 'good_service', 'message': 'Good Service', 'color': '#00C851'},
            '2': {'status': 'good_service', 'message': 'Good Service', 'color': '#00C851'},
            '3': {'status': 'good_service', 'message': 'Good Service', 'color': '#00C851'},
            '6X': {'status': 'good_service', 'message': 'Good Service', 'color': '#00C851'},
            '7X': {'status': 'good_service', 'message': 'Good Service', 'color': '#00C851'},
            'FX': {'status': 'good_service', 'message': 'Good Service', 'color': '#00C851'},
        }
        
        for route in routes:
            route_data = route.to_dict()
            
            # Use mock status if available, otherwise use unknown
            if route.short_name in mock_issues:
                route_data['status'] = mock_issues[route.short_name]
            else:
                route_data['status'] = {
                    'status': 'unknown',
                    'message': 'Unable to determine status',
                    'color': '#999999'
                }
            
            status_data.append(route_data)
        
        return jsonify({
            'success': True,
            'data': status_data
        })
    except Exception as e:
        logger.error(f"Error fetching service status: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch service status'
        }), 500

@transit_bp.route('/data/load', methods=['POST'])
def load_gtfs_data():
    """Load GTFS data into the database"""
    try:
        force_download = request.args.get('force', 'false').lower() == 'true'
        gtfs_service = GTFSService()
        
        # Download and extract GTFS data
        zip_path = gtfs_service.download_gtfs_data(force_download=force_download)
        txt_files = gtfs_service.extract_gtfs_data(zip_path)
        
        # Load data into database
        routes_loaded, routes_updated = gtfs_service.load_routes_to_db()
        stops_loaded, stops_updated = gtfs_service.load_stops_to_db()
        
        return jsonify({
            'success': True,
            'data': {
                'routes_loaded': routes_loaded,
                'routes_updated': routes_updated,
                'stops_loaded': stops_loaded,
                'stops_updated': stops_updated,
                'files_processed': txt_files
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@transit_bp.route('/data/stats', methods=['GET'])
def get_data_stats():
    """Get statistics about loaded data"""
    try:
        gtfs_service = GTFSService()
        stats = gtfs_service.get_data_stats()
        
        # Add database counts
        route_count = Route.query.count()
        stop_count = Stop.query.count()
        trip_count = Trip.query.count()
        
        stats.update({
            'database': {
                'routes': route_count,
                'stops': stop_count,
                'trips': trip_count
            }
        })
        
        return jsonify({
            'success': True,
            'data': stats
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@lru_cache(maxsize=None)
def _route_shape_payload(route_id):
    """Return the ordered shape points for a route (using shapes.txt)"""
    # Find a representative shape_id for this route from trips.txt
    gtfs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'gtfs')
    trips_file = os.path.join(gtfs_dir, 'trips.txt')
    shapes_file = os.path.join(gtfs_dir, 'shapes.txt')
    shape_id = None
    try:
        with open(trips_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['route_id'] == route_id and row.get('shape_id'):
                    shape_id = row['shape_id']
                    break
    except Exception as e:
        return {'success': False, 'error': f'Error reading trips.txt: {e}'}

    if not shape_id:
        return {'success': False, 'error': 'No shape_id found for this route'}

    # Get all shape points for this shape_id, ordered by shape_pt_sequence
    shape_points = []
    try:
        with open(shapes_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['shape_id'] == shape_id:
                    shape_points.append({
                        'lat': float(row['shape_pt_lat']),
                        'lon': float(row['shape_pt_lon']),
                        'seq': int(row['shape_pt_sequence'])
                    })
        shape_points.sort(key=lambda x: x['seq'])
    except Exception as e:
        return {'success': False, 'error': f'Error reading shapes.txt: {e}'}

    return {'success': True, 'data': [{'latitude': pt['lat'], 'longitude': pt['lon']} for pt in shape_points]}

@transit_bp.route('/route-shape/<route_id>', methods=['GET'])
def get_route_shape(route_id):
    return jsonify(_route_shape_payload(route_id))


@lru_cache(maxsize=None)
def _longest_trip_stops_by_route():
    """
    Return a dict: route_id -> ordered stop IDs of that route's longest trip (most stops).
    Two passes over stop_times.txt so only the chosen trips are held in memory.
    """
    gtfs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'gtfs')
    trip_to_route = {}
    with open(os.path.join(gtfs_dir, 'trips.txt'), 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            trip_to_route[row['trip_id']] = row['route_id']

    stop_times_file = os.path.join(gtfs_dir, 'stop_times.txt')
    trip_counts = defaultdict(int)
    with open(stop_times_file, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if row['trip_id'] in trip_to_route:
                trip_counts[row['trip_id']] += 1

    longest = {}  # route_id -> trip_id (first trip seen wins ties)
    for trip_id, count in trip_counts.items():
        route_id = trip_to_route[trip_id]
        if route_id not in longest or count > trip_counts[longest[route_id]]:
            longest[route_id] = trip_id

    chosen = {trip_id: route_id for route_id, trip_id in longest.items()}
    route_stops = defaultdict(list)
    with open(stop_times_file, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            route_id = chosen.get(row['trip_id'])
            if route_id:
                route_stops[route_id].append((int(row['stop_sequence']), row['stop_id']))
    return {route_id: [sid for _, sid in sorted(stops)] for route_id, stops in route_stops.items()}


@lru_cache(maxsize=None)
def _route_stations_payload(route_id):
    """
    Return the ordered list of consecutive stations for a route using stop_times.txt and trips.txt.
    Combines stops from all trip patterns for the route to show the complete route.
    """
    gtfs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'gtfs')
    stops_file = os.path.join(gtfs_dir, 'stops.txt')

    # 1-2. Ordered stop IDs of the route's longest trip (precomputed for all routes)
    stop_ids = _longest_trip_stops_by_route().get(route_id)
    if not stop_ids:
        return {'success': False, 'error': 'No trip_ids found for this route'}

    # 3. Get full stop information for each stop_id
    stop_info = {}
    try:
        with open(stops_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                stop_info[row['stop_id']] = {
                    'id': row['stop_id'],
                    'name': row['stop_name'],
                    'latitude': float(row['stop_lat']),
                    'longitude': float(row['stop_lon']),
                    'parent_station': row.get('parent_station') or row['stop_id']
                }
    except Exception as e:
        return {'success': False, 'error': f'Error reading stops.txt: {e}'}

    # 4. Only include unique parent stations in order (to avoid platform duplicates)
    seen = set()
    ordered_stops = []
    
    for stop_id in stop_ids:
        info = stop_info.get(stop_id)
        if not info:
            continue
        parent = info['parent_station']
        if parent not in seen:
            ordered_stops.append(info)
            seen.add(parent)

    return {'success': True, 'data': ordered_stops}

@transit_bp.route('/route-stations/<route_id>', methods=['GET'])
def get_route_stations(route_id):
    return jsonify(_route_stations_payload(route_id))


@transit_bp.route('/trunk-shapes', methods=['GET'])
def get_trunk_shapes():
    """
    Return trunk segments for known shared routes using representative shapes.
    """
    gtfs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'gtfs')
    trips_file = os.path.join(gtfs_dir, 'trips.txt')
    shapes_file = os.path.join(gtfs_dir, 'shapes.txt')
    routes_file = os.path.join(gtfs_dir, 'routes.txt')

    # Define known trunk routes that share tracks
    trunk_definitions = {
        'queens_blvd': ['E', 'F', 'M', 'R'],
        'sixth_ave': ['B', 'D', 'F', 'M'],
        'eighth_ave': ['A', 'C', 'E'],
        'broadway': ['N', 'Q', 'R', 'W'],
        'lexington': ['4', '5', '6'],
        'seventh_ave': ['1', '2', '3'],
        'canarsie': ['L'],
        'flushing': ['7'],
        'franklin': ['S'],
        'rockaway': ['A'],
        'staten_island': ['SI'],
        'shuttle': ['S'],
        'g': ['G'],
        'j_z': ['J', 'Z'],
        'nassau': ['J', 'Z'],
        'crosstown': ['G'],
        'queens_blvd_express': ['E', 'F'],
        'queens_blvd_local': ['M', 'R'],
        'sixth_ave_express': ['B', 'D'],
        'sixth_ave_local': ['F', 'M'],
        'eighth_ave_express': ['A'],
        'eighth_ave_local': ['C', 'E'],
        'broadway_express': ['N', 'Q'],
        'broadway_local': ['R', 'W'],
        'lexington_express': ['4', '5'],
        'lexington_local': ['6'],
        'seventh_ave_express': ['2', '3'],
        'seventh_ave_local': ['1'],
        'sixth_ave': ['B', 'D', 'F', 'M'],  # Make sure B is here
        'shuttle_42': ['S'],  # 42nd St Shuttle
        'shuttle_franklin': ['S'],  # Franklin Ave Shuttle  
        'shuttle_rockaway': ['S'],  # Rockaway Shuttle
    }

    # 1. Map route_id -> color
    route_to_color = {}
    try:
        with open(routes_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('route_id') and row.get('route_color'):
                    route_to_color[row['route_id']] = row['route_color']
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error reading routes.txt: {e}'})

    # 2. Map route_id -> all shape_ids (not just the first one)
    route_to_shapes = defaultdict(list)
    try:
        with open(trips_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('route_id') and row.get('shape_id'):
                    route_id = row['route_id']
                    shape_id = row['shape_id']
                    if shape_id not in route_to_shapes[route_id]:
                        route_to_shapes[route_id].append(shape_id)
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error reading trips.txt: {e}'})

    # 3. Map shape_id -> polyline
    shape_to_polyline = defaultdict(list)
    try:
        with open(shapes_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('shape_id') and row.get('shape_pt_lat') and row.get('shape_pt_lon'):
                    shape_to_polyline[row['shape_id']].append({
                        'lat': float(row['shape_pt_lat']),
                        'lon': float(row['shape_pt_lon']),
                        'seq': int(row['shape_pt_sequence'])
                    })
        # Sort each polyline by sequence
        for shape_id in shape_to_polyline:
            shape_to_polyline[shape_id].sort(key=lambda x: x['seq'])
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error reading shapes.txt: {e}'})

    # 4. For each trunk, return segments for each route using all their shapes
    trunk_segments = []
    for trunk_name, routes in trunk_definitions.items():
        # Get all shapes for all routes in this trunk
        all_shapes = set()
        for route_id in routes:
            if route_id in route_to_shapes:
                all_shapes.update(route_to_shapes[route_id])
        
        # For each shape, create segments for all routes that use it
        for shape_id in all_shapes:
            if shape_id in shape_to_polyline:
                polyline = [
                    {'latitude': pt['lat'], 'longitude': pt['lon']} for pt in shape_to_polyline[shape_id]
                ]
                # Create a segment for each route in this trunk that uses this shape
                for route_id in routes:
                    if route_id in route_to_color and shape_id in route_to_shapes[route_id]:
                        color = route_to_color[route_id]
                        trunk_segments.append({
                            'route': route_id,
                            'color': f'#{color}',
                            'polyline': polyline
                        })
    
    return jsonify({'success': True, 'data': trunk_segments}) 

def warm_caches(app):
    """Precompute the cached station lists and trip-planning graph so first requests are fast."""
    with app.app_context():
        try:
            _map_station_list()
            _build_node_routes_map()
            _build_stop_count_lookup()
            _longest_trip_stops_by_route()
            logger.info("Transit caches warmed")
        except Exception as e:
            logger.error(f"Error warming caches: {e}")
