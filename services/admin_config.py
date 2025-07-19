"""
Admin Configuration Service for MetaX Coin Backend
Handles initialization and management of admin configurations
"""

from models import db, AdminConfig


def initialize_default_config():
    """Initialize default admin configuration values"""
    AdminConfig.initialize_default_configs()


def get_config(key, default=None):
    """Get configuration value by key"""
    return AdminConfig.get_config(key, default)


def set_config(key, value, description=None, category='general', data_type='string', updated_by=None):
    """Set configuration value"""
    return AdminConfig.set_config(key, value, description, category, data_type, updated_by)


def get_referral_rates():
    """Get referral commission rates"""
    return get_config('referral_rates', {1: 10.0, 2: 5.0, 3: 3.0, 4: 2.0, 5: 1.0})


def get_transaction_limits():
    """Get transaction limits"""
    return {
        'min_deposit': get_config('min_deposit', 10.0),
        'max_deposit': get_config('max_deposit', 100000.0),
        'min_withdrawal': get_config('min_withdrawal', 5.0),
        'max_withdrawal': get_config('max_withdrawal', 50000.0),
        'withdrawal_fee': get_config('withdrawal_fee', 2.0)
    }


def get_staking_config():
    """Get staking configuration"""
    return {
        'apy': get_config('staking_apy', 12.0),
        'compound_frequency': get_config('staking_compound_frequency', 'daily'),
        'min_amount': get_config('min_staking_amount', 100.0)
    }


def get_platform_settings():
    """Get platform settings"""
    return {
        'maintenance': get_config('platform_maintenance', False),
        'registration_enabled': get_config('registration_enabled', True),
        'kyc_required': get_config('kyc_required', True)
    }
