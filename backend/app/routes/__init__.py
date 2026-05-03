from flask import Blueprint
from .transit_routes import transit_bp

def init_app(app):
    """Register all blueprints with the Flask app"""
    app.register_blueprint(transit_bp, url_prefix='/api')
