"""
Authentication Routes for MetaX Coin Backend
Handles user registration, login, logout, and profile management
"""

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import (
    create_access_token, create_refresh_token, jwt_required, 
    get_jwt_identity, get_jwt
)
from datetime import datetime, timedelta
import re

from models import db, User, Wallet, Referral
from .utils import validate_email, validate_password, validate_username

auth_bp = Blueprint('auth', __name__)

# Blacklisted tokens (in production, use Redis or database)
blacklisted_tokens = set()


@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['username', 'email', 'password', 'first_name', 'last_name']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Validate input data
        username = data['username'].strip().lower()
        email = data['email'].strip().lower()
        password = data['password']
        first_name = data['first_name'].strip()
        last_name = data['last_name'].strip()
        sponsor_code = data.get('sponsor_code', '').strip()
        
        # Validation
        if not validate_username(username):
            return jsonify({'error': 'Invalid username format'}), 400
        
        if not validate_email(email):
            return jsonify({'error': 'Invalid email format'}), 400
        
        if not validate_password(password):
            return jsonify({'error': 'Password must be at least 8 characters long'}), 400
        
        # Check if user already exists
        if User.query.filter_by(username=username).first():
            return jsonify({'error': 'Username already exists'}), 400
        
        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Email already exists'}), 400
        
        # Find sponsor if sponsor code provided
        sponsor_id = None
        if sponsor_code:
            sponsor = User.query.filter_by(referral_code=sponsor_code).first()
            if not sponsor:
                return jsonify({'error': 'Invalid sponsor code'}), 400
            sponsor_id = sponsor.id
        
        # Create new user
        user = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            sponsor_id=sponsor_id
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.flush()  # Get user ID
        
        # Initialize user wallets
        Wallet.initialize_user_wallets(user.id)
        
        # Create referral chain if user has sponsor
        if sponsor_id:
            Referral.create_referral_chain(sponsor_id, user.id)
        
        db.session.commit()
        
        # Create access token
        access_token = create_access_token(
            identity=user.id,
            expires_delta=timedelta(hours=24)
        )
        
        current_app.logger.info(f'New user registered: {username}')
        
        return jsonify({
            'message': 'User registered successfully',
            'access_token': access_token,
            'user': user.to_dict(),
            'referral_link': user.get_referral_link()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Registration error: {str(e)}')
        return jsonify({'error': 'Registration failed'}), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    """User login"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('username') or not data.get('password'):
            return jsonify({'error': 'Username and password are required'}), 400
        
        username_or_email = data['username'].strip().lower()
        password = data['password']
        
        # Find user by username or email
        user = User.query.filter(
            (User.username == username_or_email) | 
            (User.email == username_or_email)
        ).first()
        
        if not user or not user.check_password(password):
            return jsonify({'error': 'Invalid credentials'}), 401
        
        if not user.is_active:
            return jsonify({'error': 'Account is deactivated'}), 401
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        # Create tokens
        access_token = create_access_token(
            identity=user.id,
            expires_delta=timedelta(hours=24)
        )
        refresh_token = create_refresh_token(
            identity=user.id,
            expires_delta=timedelta(days=30)
        )
        
        current_app.logger.info(f'User logged in: {user.username}')
        
        return jsonify({
            'message': 'Login successful',
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': user.to_dict(include_sensitive=True)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f'Login error: {str(e)}')
        return jsonify({'error': 'Login failed'}), 500


@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """User logout"""
    try:
        jti = get_jwt()['jti']
        blacklisted_tokens.add(jti)
        
        current_app.logger.info(f'User logged out: {get_jwt_identity()}')
        
        return jsonify({'message': 'Successfully logged out'}), 200
        
    except Exception as e:
        current_app.logger.error(f'Logout error: {str(e)}')
        return jsonify({'error': 'Logout failed'}), 500


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Refresh access token"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or not user.is_active:
            return jsonify({'error': 'User not found or inactive'}), 404
        
        new_token = create_access_token(
            identity=current_user_id,
            expires_delta=timedelta(hours=24)
        )
        
        return jsonify({
            'access_token': new_token,
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        current_app.logger.error(f'Token refresh error: {str(e)}')
        return jsonify({'error': 'Token refresh failed'}), 500


@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """Get user profile with simplified wallet structure"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)

        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Helper function to get wallet balance
        def get_wallet_balance(wallet_type):
            wallet = Wallet.query.filter_by(
                user_id=current_user_id,
                wallet_type=wallet_type
            ).first()
            return float(wallet.balance) if wallet else 0.0

        # Get simplified wallet summary (5 key values)
        # 1. Available Fund (withdrawable money)
        available_fund = get_wallet_balance('available_fund')

        # 2. Total Investment (calculated from UserInvestment records)
        total_investment = user.get_total_investment()

        # 3. Total Gain (from total_gain wallet)
        total_gain = get_wallet_balance('total_gain')

        # 4. Total Referral (from total_referral wallet)
        total_referral = get_wallet_balance('total_referral')

        # 5. Level Bonus (from level_bonus wallet)
        level_bonus = get_wallet_balance('level_bonus')

        # 6. Total Income (calculated: gain + referral + level bonus)
        total_income = total_gain + total_referral + level_bonus

        # Get team statistics
        team_stats = Referral.get_team_summary(user.id)

        profile_data = user.to_dict(include_sensitive=True)
        profile_data.update({
            'wallet_summary': {
                'available_fund': available_fund,
                'total_investment': total_investment,
                'total_gain': total_gain,
                'total_referral': total_referral,
                'level_bonus': level_bonus,
                'total_income': total_income
            },
            'withdrawal_info': {
                'withdrawable_amount': available_fund,
                'withdrawable_wallets': ['available_fund'],
                'locked_amount': total_investment
            },
            'team_statistics': team_stats
        })

        return jsonify(profile_data), 200

    except Exception as e:
        current_app.logger.error(f'Get profile error: {str(e)}')
        return jsonify({'error': 'Failed to get profile'}), 500


@auth_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """Update user profile"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        
        # Update allowed fields
        updatable_fields = ['first_name', 'last_name', 'phone', 'date_of_birth']
        updated_fields = []
        
        for field in updatable_fields:
            if field in data:
                if field == 'date_of_birth' and data[field]:
                    try:
                        from datetime import datetime
                        setattr(user, field, datetime.strptime(data[field], '%Y-%m-%d').date())
                        updated_fields.append(field)
                    except ValueError:
                        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
                else:
                    setattr(user, field, data[field])
                    updated_fields.append(field)
        
        if updated_fields:
            user.updated_at = datetime.utcnow()
            db.session.commit()
            
            current_app.logger.info(f'Profile updated for user {user.username}: {updated_fields}')
            
            return jsonify({
                'message': 'Profile updated successfully',
                'updated_fields': updated_fields,
                'user': user.to_dict(include_sensitive=True)
            }), 200
        else:
            return jsonify({'message': 'No fields to update'}), 200
            
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Update profile error: {str(e)}')
        return jsonify({'error': 'Failed to update profile'}), 500


@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """Change user password"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        
        if not data.get('current_password') or not data.get('new_password'):
            return jsonify({'error': 'Current password and new password are required'}), 400
        
        # Verify current password
        if not user.check_password(data['current_password']):
            return jsonify({'error': 'Current password is incorrect'}), 400
        
        # Validate new password
        if not validate_password(data['new_password']):
            return jsonify({'error': 'New password must be at least 8 characters long'}), 400
        
        # Update password
        user.set_password(data['new_password'])
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        current_app.logger.info(f'Password changed for user: {user.username}')
        
        return jsonify({'message': 'Password changed successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Change password error: {str(e)}')
        return jsonify({'error': 'Failed to change password'}), 500


@auth_bp.route('/verify-token', methods=['GET'])
@jwt_required()
def verify_token():
    """Verify if token is valid"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or not user.is_active:
            return jsonify({'error': 'Invalid token or user inactive'}), 401
        
        return jsonify({
            'valid': True,
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        current_app.logger.error(f'Token verification error: {str(e)}')
        return jsonify({'error': 'Token verification failed'}), 500


# JWT token blacklist checker
@auth_bp.before_app_request
def check_if_token_revoked():
    """Check if token is blacklisted"""
    try:
        if request.endpoint and 'auth' in request.endpoint:
            jti = get_jwt().get('jti')
            if jti in blacklisted_tokens:
                return jsonify({'error': 'Token has been revoked'}), 401
    except:
        pass  # No JWT in request
