# backend/app/__init__.py
from flask import Flask # Main Frame Webwork Class
from flask_cors import CORS # Allows mobile app to make requests to the API
from flask_sqlalchemy import SQLAlchemy # Database Objext Relational Mapping
from flask_migrate import Migrate # Database Schemma Versioning
from config import Config

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()

def create_app(config_class=Config):
    """Application factory pattern"""
    app = Flask(__name__) # Tells Flask where to find its resources
    
    # app.config: dictionary object from Flask
    # from_object(): loads all uppercase attributes from a given class or object into app.config
    # config_class: the class Config imported from config.py, set in the parameter
    # This function allows me to call current_app.config.get('KEY') anywhere in the app to get configuration values
    app.config.from_object(config_class) # Load configuration from Config class
    
    # Initialize Flask extensions
    
    # Connect SQL Alchemy to this specific Flask app
    db.init_app(app) 
    
    # Add schema versioning
    # Keeps track of changes to models (like adding columns or tables)
    migrate.init_app(app, db) 
    
    # Allow requests from other domains
    CORS(app)
    
    # Register API routes
    from app.routes import init_app as init_routes
    init_routes(app)
    
    # Add a simple health check route
    @app.route('/')
    def health_check():
        return {
            'status': 'healthy',
            'message': 'MTA Transit Companion API is running!',
            'version': '1.0.0'
        }
    
    return app