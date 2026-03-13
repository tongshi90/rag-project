"""
RAG Backend Application
"""
from flask import Flask
from flask_cors import CORS


def create_app(config=None):
    """
    Application factory pattern
    """
    app = Flask(__name__)

    # Load configuration
    if config:
        app.config.update(config)

    # Enable CORS for all routes
    CORS(app, resources={
        r"/api/*": {
            "origins": "*",  # 允许所有源（开发环境）
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })

    # Register blueprints
    from app.api import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')

    # Health check endpoint
    @app.route('/health')
    def health_check():
        return {'status': 'healthy', 'message': 'RAG Backend is running'}

    return app
