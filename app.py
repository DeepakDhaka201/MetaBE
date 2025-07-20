"""
MetaX Coin Backend - Flask Application
Main application entry point with all configurations and blueprints
"""

from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_mail import Mail
from flask_migrate import Migrate
import logging
from logging.handlers import RotatingFileHandler
import os
import atexit
from datetime import datetime

# Import configuration
from config import Config

# Import database
from models import db

# Import blueprints
from auth.routes import auth_bp
from dashboard.routes import dashboard_bp
from team.routes import team_bp
from transactions.routes import transactions_bp
from admin.routes import admin_bp
from admin.web_routes import admin_web_bp
from admin.investment_routes import admin_investment_bp
from crypto.routes import crypto_bp
from income.routes import income_bp
from user.routes import user_bp
from api.investments import investments_bp
from public_config.routes import config_bp

# Import services
from services.wallet_pool import setup_wallet_monitoring, setup_claim_monitoring
from services.scheduler import init_scheduler


def create_app(config_class=Config):
    """Application factory pattern"""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions
    db.init_app(app)
    CORS(app)
    jwt = JWTManager(app)
    mail = Mail(app)
    migrate = Migrate(app, db)
    
    # Setup logging
    setup_logging(app)
    
    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
    app.register_blueprint(team_bp, url_prefix='/api/team')
    app.register_blueprint(transactions_bp, url_prefix='/api/transactions')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(admin_web_bp)  # Admin web UI routes
    app.register_blueprint(admin_investment_bp)  # Admin investment management
    app.register_blueprint(crypto_bp, url_prefix='/api/crypto')
    app.register_blueprint(income_bp, url_prefix='/api/income')
    app.register_blueprint(user_bp, url_prefix='/api/user')
    app.register_blueprint(investments_bp)  # Investment API routes
    app.register_blueprint(config_bp, url_prefix='/api/config')  # Public config routes
    
    # Health check endpoint
    @app.route('/api/health')
    def health_check():
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0'
        })
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500
    
    # JWT error handlers
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({'error': 'Token has expired'}), 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({'error': 'Invalid token'}), 401
    
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({'error': 'Authorization token is required'}), 401
    
    # Initialize database tables
    with app.app_context():
        try:
            db.create_all()
            app.logger.info('Database tables created successfully')
        except Exception as e:
            app.logger.warning(f'Database tables may already exist: {e}')

        # Initialize admin configuration if not exists
        try:
            from models.admin import AdminConfig
            from services.admin_config import initialize_default_config
            initialize_default_config()
        except Exception as e:
            app.logger.warning(f'Admin config initialization warning: {e}')

        # Initialize default MXC price if not exists
        try:
            from models.mxc import MXCPrice
            from services.mxc_service import initialize_default_mxc_price
            initialize_default_mxc_price()
        except Exception as e:
            app.logger.warning(f'MXC price initialization warning: {e}')
    
    # Setup background tasks
    if not app.debug and not app.testing:
        init_scheduler(app)
        setup_wallet_monitoring(app)
        setup_claim_monitoring(app)
    
    app.logger.info('MetaX Coin Backend startup complete')
    
    return app


def setup_logging(app):
    """Configure application logging"""
    if not app.debug and not app.testing:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        file_handler = RotatingFileHandler(
            'logs/metax_backend.log',
            maxBytes=10240000,  # 10MB
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('MetaX Backend startup')


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5001)
