"""
MetaX Coin Backend Configuration
All configuration settings for the Flask application
"""

import os
from datetime import timedelta


class Config:
    """Base configuration class"""
    
    # Basic Flask Config
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'metax-dev-secret-key-change-in-production'
    
    # Database Configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///metax.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_POOL_SIZE = 10
    SQLALCHEMY_MAX_OVERFLOW = 20
    SQLALCHEMY_POOL_TIMEOUT = 30
    
    # JWT Configuration
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'metax-jwt-secret-change-in-production'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)

    # Session Configuration
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Email Configuration
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.gmail.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or 'noreply@metaxcoin.cloud'
    
    # MetaX Coin Configuration
    MXC_TOKEN_NAME = 'MetaX Coin'
    MXC_SYMBOL = 'MXC'
    MXC_NETWORK = 'BSC (BEP-20)'
    MXC_CONTRACT_ADDRESS = '0x742d35Cc6634C0532925a3b8D0b8EFd17d1F3456'
    
    # Wallet Types Configuration
    WALLET_TYPES = [
        'available_fund',    # Main spending wallet
        'total_gain',        # Investment returns + staking rewards
        'level_bonus',       # Multi-level commissions
        'total_referral',    # Direct referral commissions
        'total_income',      # Sum of all income types (calculated)
    ]
    
    # Referral System Configuration
    MAX_REFERRAL_LEVELS = 5
    DEFAULT_REFERRAL_RATES = {
        1: 10.0,  # 10% for direct referrals (level 1)
        2: 5.0,   # 5% for level 2
        3: 3.0,   # 3% for level 3
        4: 2.0,   # 2% for level 4
        5: 1.0    # 1% for level 5
    }
    
    # Transaction Limits
    MIN_DEPOSIT = 10.0
    MAX_DEPOSIT = 100000.0
    MIN_WITHDRAWAL = 5.0
    MAX_WITHDRAWAL = 50000.0
    WITHDRAWAL_FEE = 2.0  # USDT
    
    # Staking Configuration
    DEFAULT_STAKING_APY = 12.0  # 12% annual percentage yield
    STAKING_COMPOUND_FREQUENCY = 'daily'  # daily, weekly, monthly
    
    # Blockchain Configuration (TRON/USDT)
    TRON_API_URL = os.environ.get('TRON_API_URL') or 'https://api.trongrid.io'
    USDT_CONTRACT_ADDRESS = os.environ.get('USDT_CONTRACT_ADDRESS') or 'TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t'
    PLATFORM_WALLET_ADDRESS = os.environ.get('PLATFORM_WALLET_ADDRESS')
    MIN_CONFIRMATIONS = 1
    
    # Wallet Pool Configuration
    WALLET_ASSIGNMENT_DURATION = 30  # minutes
    WALLET_CLEANUP_INTERVAL = 5  # minutes
    WALLET_MONITORING_INTERVAL = 60  # seconds
    
    # External APIs
    COINGECKO_API_URL = 'https://api.coingecko.com/api/v3'
    CRYPTO_CACHE_DURATION = 60  # seconds
    
    # Admin Configuration
    DEFAULT_ADMIN_USERNAME = 'admin'
    DEFAULT_ADMIN_EMAIL = 'admin@metaxcoin.cloud'
    DEFAULT_ADMIN_PASSWORD = 'admin123'  # Change in production
    
    # File Upload Configuration
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
    
    # Security Configuration
    BCRYPT_LOG_ROUNDS = 12
    PASSWORD_MIN_LENGTH = 8
    
    # Rate Limiting
    RATELIMIT_STORAGE_URL = 'memory://'
    RATELIMIT_DEFAULT = '100 per hour'
    
    # Pagination
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100
    
    # Background Tasks
    SCHEDULER_TIMEZONE = 'UTC'
    STAKING_REWARD_HOUR = 0  # Run at midnight UTC
    PRICE_UPDATE_INTERVAL = 300  # 5 minutes
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL') or 'INFO'
    LOG_FILE = 'logs/metax_backend.log'
    LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 5


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or 'sqlite:///metax_dev.db'


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=5)
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://user:password@localhost/metax_prod'
    
    # Enhanced security for production
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
