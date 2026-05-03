from datetime import datetime
import time, requests
from flask import current_app
# from app.models.transit import Route, Stop, Trip

class RealtimeService:
    ROUTES_TO_FEED = {
        '1': '123456',
        '2': '123456', 
        '3': '123456',
        '4': '123456',
        '5': '123456', 
        '6': '123456',
        '7': '7',
        'A': 'ace',
        'C': 'ace', 
        'E': 'ace',
        'B': 'bdfm',
        'D': 'bdfm',
        'F': 'bdfm',
        'M': 'bdfm',
        'G': 'g',
        'J': 'jz',
        'Z': 'jz',
        'N': 'nqrw',
        'Q': 'nqrw', 
        'R': 'nqrw',
        'W': 'nqrw',
        'L': 'l',
        'SI': 'si'
    }
    
    def __init__(self):
        # Initialize API Key
        self.api_key = current_app.config.get('MTA_API_KEY')
        self.feed_urls = current_app.config.get('MTA_REALTIME_FEEDS')
        
        if not self.api_key:
            raise ValueError("MTA_API_KEY is not set in the configuration.")
        if not self.feed_urls:
            raise ValueError("MTA_REALTIME_FEEDS is not set in the configuration.")
        
    def get_route_updates(self, route_id):
        """Get the feed URL for a given route ID"""
        route_id = route_id.upper()  
        if route_id not in self.ROUTES_TO_FEED:
            return {
                'success': False,
                'error': f'Route {route_id} is not a valid MTA route ID.'
            }
        
        feed_key = self.ROUTES_TO_FEED[route_id.upper()]
        feed_url = self.feed_urls[feed_key]
        if not feed_url:
            return {
                'success': False,
                'error': f'Feed URL not found for {feed_key}'
            }
        
        response_data = self._make_api_request(feed_url)
        
        if response_data['success']:
            response_data['route_id'] = route_id
            response_data['feed_key'] = feed_key
        else: 
            response_data['route_id'] = route_id
            raise ValueError("get_route_updates: Failed to add feed_key to response_data")
        
        print(f"get_route_updates -> response_data: {response_data}")
        
        return response_data
    
    def _make_api_request(self, url):
        """Make a HTTP request to the MTA API"""
        start_time = time.time()
        
        try:
            headers = {'x-api-key': self.api_key}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            duration = time.time() - start_time
            
            #TODO: RESTURN AND PARSE THE RESPONSE content into a readable format
            
            return {
                'success': True,
                'data_size_bytes': len(response.content),
                'response_time_seconds': round(duration, 3),
                'status_code': response.status_code,
                'timestamp': datetime.now().isoformat(),
                'headers': dict(response.headers)
            }
            
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'error': 'MTA API request timed out',
                'response_time_seconds': round(time.time() - start_time, 3)
            }
        except requests.exceptions.HTTPError as e:
            return {
                'success': False,
                'error': f'HTTP error: {e.response.status_code}',
                'status_code': e.response.status_code,
                'response_time_seconds': round(time.time() - start_time, 3)
            }
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'Request failed: {str(e)}',
                'response_time_seconds': round(time.time() - start_time, 3)
            }
        
    def get_feed_health(self):
        """Check health of all MTA feeds"""
        results = {}
        
        for feed_key, feed_url in self.feed_urls.items():
            api_result = self._make_api_request(feed_url)
            
            if api_result['success']:
                results[feed_key] = {
                    'status': 'healthy',
                    'response_time': api_result['response_time_seconds'],
                    'data_size': api_result['data_size_bytes']
                }
            else:
                results[feed_key] = {
                    'status': 'unhealthy',
                    'error': api_result['error']
                }
        
        return {
            'timestamp': datetime.now().isoformat(),
            'feeds': results
        }
        