# backend/config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Flask application configuration"""
    
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production' # Secret Key for Flask security (sessions, cookies, etc)
    FLASK_ENV = os.environ.get('FLASK_ENV') or 'development' # Development Environement
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true' # Debugger is True, to check for any errors
    
    # Database settings
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///mta_subway_app.db' # Create SQLite db called mta_subway_app
    SQLALCHEMY_TRACK_MODIFICATIONS = False # Disable feature that uses extra memory
    
    # MTA API Configuration
    MTA_API_KEY = os.environ.get('MTA_API_KEY')
    
    # MTA Data URLs
    MTA_GTFS_STATIC_URL = 'http://web.mta.info/developers/data/nyct/subway/google_transit.zip'
    
    # MTA Realtime Feed URLs (by subway line groups)
    MTA_REALTIME_FEEDS = {
        'ace': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-ace',
        'bdfm': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-bdfm', 
        'g': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-g',
        'jz': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-jz',
        'nqrw': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-nqrw',
        'l': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-l',
        '123456': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs',
        '7': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-7',
        'si': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-si'
    }
    
    # Service Alerts URL
    MTA_ALERTS_URL = 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/camsys%2Fall-alerts'
    
    # Cache settings
    CACHE_TYPE = "simple"
    CACHE_DEFAULT_TIMEOUT = 300  # 5 minutes
    
    # Static because it only reads Config.MTA_API_KEY once at startup
    # Lets me call Config.validate_config() without needing an instance of Config
    # Config values are loaded at the beginning, so we use static method here
    @staticmethod
    def validate_config():
        """Validate that required config is present"""
        if not Config.MTA_API_KEY:
            print("INFO: MTA_API_KEY not found - using public feeds (no API key required)")
            return True  # API key is now optional
        else:
            print("INFO: MTA_API_KEY configured - using authenticated feeds")
            return True