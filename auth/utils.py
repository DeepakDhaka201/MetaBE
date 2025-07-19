"""
Authentication Utilities for MetaX Coin Backend
Helper functions for validation and authentication
"""

import re
from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required

from models import User


def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_username(username):
    """Validate username format"""
    # Username should be 3-30 characters, alphanumeric and underscores only
    pattern = r'^[a-zA-Z0-9_]{3,30}$'
    return re.match(pattern, username) is not None


def validate_password(password):
    """Validate password strength"""
    # Minimum 8 characters
    if len(password) < 8:
        return False
    
    # At least one letter and one number (optional for now)
    # has_letter = re.search(r'[a-zA-Z]', password)
    # has_number = re.search(r'\d', password)
    # return has_letter and has_number
    
    return True


def validate_phone(phone):
    """Validate phone number format"""
    if not phone:
        return True  # Phone is optional
    
    # Remove all non-digit characters
    digits_only = re.sub(r'\D', '', phone)
    
    # Should be 10-15 digits
    return 10 <= len(digits_only) <= 15


def admin_required(f):
    """Decorator to require admin privileges for API routes (JWT-based)"""
    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)

        if not user or not user.is_admin or not user.is_active:
            return jsonify({'error': 'Admin privileges required'}), 403

        return f(*args, **kwargs)

    return decorated_function


def admin_session_required(f):
    """Decorator to require admin session for web routes (Session-based)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import session, redirect, url_for, flash

        # Check if user is logged in via session
        if 'admin_user_id' not in session or 'admin_access_token' not in session:
            flash('Please log in to access the admin panel', 'warning')
            return redirect(url_for('admin_web.login'))

        # Verify user still exists and is admin
        user = User.query.get(session['admin_user_id'])
        if not user or not user.is_admin or not user.is_active:
            session.clear()
            flash('Your session has expired. Please log in again.', 'warning')
            return redirect(url_for('admin_web.login'))

        return f(*args, **kwargs)

    return decorated_function


def admin_session_required(f):
    """Decorator to require admin session for web routes (Session-based)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import session, redirect, url_for, flash

        # Check if user is logged in via session
        if 'admin_user_id' not in session or 'admin_access_token' not in session:
            flash('Please log in to access the admin panel', 'warning')
            return redirect(url_for('admin_web.login'))

        # Verify user still exists and is admin
        user = User.query.get(session['admin_user_id'])
        if not user or not user.is_admin or not user.is_active:
            session.clear()
            flash('Your session has expired. Please log in again.', 'warning')
            return redirect(url_for('admin_web.login'))

        return f(*args, **kwargs)

    return decorated_function


def active_user_required(f):
    """Decorator to require active user"""
    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or not user.is_active:
            return jsonify({'error': 'Active user account required'}), 403
        
        return f(*args, **kwargs)
    
    return decorated_function


def verified_user_required(f):
    """Decorator to require verified user"""
    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or not user.is_verified:
            return jsonify({'error': 'Account verification required'}), 403
        
        return f(*args, **kwargs)
    
    return decorated_function


def get_current_user():
    """Get current authenticated user"""
    try:
        current_user_id = get_jwt_identity()
        return User.query.get(current_user_id)
    except:
        return None


def generate_referral_code(length=8):
    """Generate a unique referral code"""
    import secrets
    import string
    
    while True:
        code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(length))
        if not User.query.filter_by(referral_code=code).first():
            return code


def sanitize_input(data):
    """Sanitize input data"""
    if isinstance(data, str):
        return data.strip()
    elif isinstance(data, dict):
        return {key: sanitize_input(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [sanitize_input(item) for item in data]
    else:
        return data


def validate_registration_data(data):
    """Validate registration data"""
    errors = []
    
    # Required fields
    required_fields = ['username', 'email', 'password', 'first_name', 'last_name']
    for field in required_fields:
        if not data.get(field):
            errors.append(f'{field} is required')
    
    if errors:
        return errors
    
    # Validate username
    if not validate_username(data['username']):
        errors.append('Username must be 3-30 characters, letters, numbers and underscores only')
    
    # Validate email
    if not validate_email(data['email']):
        errors.append('Invalid email format')
    
    # Validate password
    if not validate_password(data['password']):
        errors.append('Password must be at least 8 characters long')
    
    # Validate names
    if len(data['first_name']) < 2 or len(data['first_name']) > 50:
        errors.append('First name must be 2-50 characters')
    
    if len(data['last_name']) < 2 or len(data['last_name']) > 50:
        errors.append('Last name must be 2-50 characters')
    
    # Validate phone if provided
    if data.get('phone') and not validate_phone(data['phone']):
        errors.append('Invalid phone number format')
    
    return errors


def check_user_exists(username=None, email=None):
    """Check if user exists by username or email"""
    if username:
        user = User.query.filter_by(username=username.lower()).first()
        if user:
            return {'exists': True, 'field': 'username'}
    
    if email:
        user = User.query.filter_by(email=email.lower()).first()
        if user:
            return {'exists': True, 'field': 'email'}
    
    return {'exists': False}


def format_user_response(user, include_sensitive=False):
    """Format user data for API response"""
    data = user.to_dict(include_sensitive=include_sensitive)

    # Add additional computed fields
    data['total_team_size'] = user.get_total_team_size()
    data['active_team_size'] = user.get_active_team_size()
    data['direct_referrals_count'] = len(user.get_direct_referrals())

    # Ensure sponsor information is included
    if not data.get('sponsor_info'):
        data['sponsor_info'] = user.get_sponsor_info()

    return data


def log_user_activity(user_id, activity, details=None):
    """Log user activity (placeholder for future implementation)"""
    from flask import current_app
    
    current_app.logger.info(f'User {user_id} activity: {activity}' + 
                           (f' - {details}' if details else ''))


def rate_limit_key(user_id=None, ip_address=None):
    """Generate rate limiting key"""
    if user_id:
        return f"user:{user_id}"
    elif ip_address:
        return f"ip:{ip_address}"
    else:
        return "global"


def is_strong_password(password):
    """Check if password meets strong criteria"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character"
    
    return True, "Password is strong"


def normalize_username(username):
    """Normalize username for consistency"""
    return username.strip().lower()


def normalize_email(email):
    """Normalize email for consistency"""
    return email.strip().lower()


def validate_referral_code(code):
    """Validate referral code format"""
    if not code:
        return True  # Referral code is optional
    
    # Should be 6-20 characters, alphanumeric
    pattern = r'^[A-Z0-9]{6,20}$'
    return re.match(pattern, code.upper()) is not None
