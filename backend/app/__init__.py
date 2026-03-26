"""
RAG Backend Application
"""
import logging
from flask import Flask
from flask_cors import CORS


def create_app(config=None):
    """
    Application factory pattern
    """
    app = Flask(__name__)

    # 配置日志
    setup_logging(app)

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


def setup_logging(app):
    """配置应用日志"""
    # 创建日志格式
    log_format = '[%(asctime)s] %(name)s [%(levelname)s] %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'

    # 配置根日志记录器
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.StreamHandler()  # 输出到控制台
        ]
    )

    # 为第三方库设置更低的日志级别
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('chromadb').setLevel(logging.WARNING)
    logging.getLogger('werkzeug').setLevel(logging.WARNING)

    # 应用日志
    app.logger.setLevel(logging.INFO)
