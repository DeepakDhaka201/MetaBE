"""
Admin Configuration Model for MetaX Coin Backend
Handles all admin-configurable parameters and settings
"""

from datetime import datetime
import json

from . import db


class AdminConfig(db.Model):
    """Admin configuration model for system settings"""
    
    __tablename__ = 'admin_configs'
    
    # Primary fields
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    value = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    
    # Metadata
    category = db.Column(db.String(50), default='general', index=True)
    data_type = db.Column(db.String(20), default='string')  # string, number, boolean, json
    is_public = db.Column(db.Boolean, default=False)  # Whether this config is visible to users
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relationships
    updater = db.relationship('User', backref='config_updates')
    
    def __repr__(self):
        return f'<AdminConfig {self.key}:{self.value}>'
    
    def get_value(self):
        """Get the parsed value based on data type"""
        try:
            if self.data_type == 'json':
                parsed = json.loads(self.value)
                # Handle double-encoded JSON (string containing JSON)
                if isinstance(parsed, str):
                    try:
                        return json.loads(parsed)
                    except (json.JSONDecodeError, ValueError):
                        return parsed
                return parsed
            elif self.data_type == 'number':
                return float(self.value)
            elif self.data_type == 'boolean':
                return self.value.lower() in ['true', '1', 'yes', 'on']
            else:
                return self.value
        except (json.JSONDecodeError, ValueError):
            return self.value
    
    def set_value(self, value, updated_by=None):
        """Set the value with proper serialization"""
        if self.data_type == 'json':
            self.value = json.dumps(value)
        else:
            self.value = str(value)
        
        self.updated_at = datetime.utcnow()
        if updated_by:
            self.updated_by = updated_by
    
    @staticmethod
    def get_config(key, default=None):
        """Get configuration value by key"""
        config = AdminConfig.query.filter_by(key=key).first()
        if config:
            return config.get_value()
        return default
    
    @staticmethod
    def set_config(key, value, description=None, category='general', data_type='string', updated_by=None, is_public=False):
        """Set configuration value"""
        config = AdminConfig.query.filter_by(key=key).first()

        if config:
            config.set_value(value, updated_by)
            if description:
                config.description = description
            if is_public is not None:
                config.is_public = is_public
        else:
            # Serialize value based on type
            if data_type == 'json':
                serialized_value = json.dumps(value)
            else:
                serialized_value = str(value)

            config = AdminConfig(
                key=key,
                value=serialized_value,
                description=description,
                category=category,
                data_type=data_type,
                updated_by=updated_by,
                is_public=is_public
            )
            db.session.add(config)

        db.session.commit()
        return config
    
    @staticmethod
    def get_configs_by_category(category):
        """Get all configurations in a category"""
        configs = AdminConfig.query.filter_by(category=category).all()
        return {config.key: config.get_value() for config in configs}
    
    @staticmethod
    def get_public_configs():
        """Get all public configurations"""
        configs = AdminConfig.query.filter_by(is_public=True).all()
        return {config.key: config.get_value() for config in configs}
    
    @staticmethod
    def initialize_default_configs():
        """Initialize default configuration values"""
        default_configs = [
            # Referral System
            {
                'key': 'referral_rates',
                'value': {1: 10.0, 2: 5.0, 3: 3.0, 4: 2.0, 5: 1.0},
                'description': 'Commission rates for each referral level',
                'category': 'referral',
                'data_type': 'json'
            },
            {
                'key': 'max_referral_levels',
                'value': 5,
                'description': 'Maximum number of referral levels',
                'category': 'referral',
                'data_type': 'number'
            },
            
            # Transaction Limits
            {
                'key': 'min_deposit',
                'value': 10.0,
                'description': 'Minimum deposit amount in USDT',
                'category': 'transaction',
                'data_type': 'number'
            },
            {
                'key': 'max_deposit',
                'value': 100000.0,
                'description': 'Maximum deposit amount in USDT',
                'category': 'transaction',
                'data_type': 'number'
            },
            {
                'key': 'min_withdrawal',
                'value': 5.0,
                'description': 'Minimum withdrawal amount in USDT',
                'category': 'transaction',
                'data_type': 'number'
            },
            {
                'key': 'max_withdrawal',
                'value': 50000.0,
                'description': 'Maximum withdrawal amount in USDT',
                'category': 'transaction',
                'data_type': 'number'
            },
            {
                'key': 'withdrawal_fee',
                'value': 2.0,
                'description': 'Withdrawal fee in USDT',
                'category': 'transaction',
                'data_type': 'number'
            },
            
            # Staking Configuration
            {
                'key': 'staking_apy',
                'value': 12.0,
                'description': 'Annual percentage yield for staking',
                'category': 'staking',
                'data_type': 'number'
            },
            {
                'key': 'staking_compound_frequency',
                'value': 'daily',
                'description': 'How often staking rewards are compounded',
                'category': 'staking',
                'data_type': 'string'
            },
            {
                'key': 'min_staking_amount',
                'value': 100.0,
                'description': 'Minimum amount required for staking',
                'category': 'staking',
                'data_type': 'number'
            },
            
            # MXC Token Configuration
            {
                'key': 'mxc_total_supply',
                'value': 1000000000,
                'description': 'Total supply of MXC tokens',
                'category': 'mxc',
                'data_type': 'number',
                'is_public': True
            },
            {
                'key': 'mxc_circulating_supply',
                'value': 500000000,
                'description': 'Circulating supply of MXC tokens',
                'category': 'mxc',
                'data_type': 'number',
                'is_public': True
            },
            
            # Platform Settings
            {
                'key': 'platform_maintenance',
                'value': False,
                'description': 'Whether platform is in maintenance mode',
                'category': 'platform',
                'data_type': 'boolean',
                'is_public': True
            },
            {
                'key': 'registration_enabled',
                'value': True,
                'description': 'Whether new user registration is enabled',
                'category': 'platform',
                'data_type': 'boolean',
                'is_public': True
            },
            {
                'key': 'kyc_required',
                'value': True,
                'description': 'Whether KYC verification is required',
                'category': 'platform',
                'data_type': 'boolean',
                'is_public': True
            },
            
            # Wallet Pool Settings
            {
                'key': 'wallet_assignment_duration',
                'value': 30,
                'description': 'Wallet assignment duration in minutes',
                'category': 'wallet_pool',
                'data_type': 'number'
            },
            {
                'key': 'wallet_monitoring_interval',
                'value': 60,
                'description': 'Wallet monitoring interval in seconds',
                'category': 'wallet_pool',
                'data_type': 'number'
            },
            
            # Notification Settings
            {
                'key': 'email_notifications_enabled',
                'value': True,
                'description': 'Whether email notifications are enabled',
                'category': 'notifications',
                'data_type': 'boolean'
            },
            {
                'key': 'sms_notifications_enabled',
                'value': False,
                'description': 'Whether SMS notifications are enabled',
                'category': 'notifications',
                'data_type': 'boolean'
            },
            
            # Security Settings
            {
                'key': 'max_login_attempts',
                'value': 5,
                'description': 'Maximum login attempts before account lockout',
                'category': 'security',
                'data_type': 'number'
            },
            {
                'key': 'account_lockout_duration',
                'value': 30,
                'description': 'Account lockout duration in minutes',
                'category': 'security',
                'data_type': 'number'
            },
            {
                'key': 'password_min_length',
                'value': 8,
                'description': 'Minimum password length',
                'category': 'security',
                'data_type': 'number'
            }
        ]
        
        for config_data in default_configs:
            existing = AdminConfig.query.filter_by(key=config_data['key']).first()
            if not existing:
                AdminConfig.set_config(**config_data)
    
    def to_dict(self, include_sensitive=False):
        """Convert config to dictionary"""
        data = {
            'id': self.id,
            'key': self.key,
            'value': self.get_value(),
            'description': self.description,
            'category': self.category,
            'data_type': self.data_type,
            'is_public': self.is_public,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        
        if include_sensitive:
            data.update({
                'raw_value': self.value,
                'created_at': self.created_at.isoformat() if self.created_at else None,
                'updated_by': self.updated_by
            })
        
        return data
