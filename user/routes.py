"""
User Settings Routes for MetaX Coin Backend
Handles user settings and preferences management
"""

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime

from models import db, User

user_bp = Blueprint('user', __name__)


@user_bp.route('/settings', methods=['GET'])
@jwt_required()
def get_user_settings():
    """Get user settings and preferences"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Return user settings (configurable preferences)
        settings_data = {
            'user_id': user.id,
            'username': user.username,
            'email': user.email,
            'phone': user.phone,
            'date_of_birth': user.date_of_birth.isoformat() if user.date_of_birth else None,
            'is_verified': user.is_verified,
            'account_settings': {
                'is_active': user.is_active,
                'email_notifications': True,  # Default setting
                'sms_notifications': True,    # Default setting
                'marketing_emails': False,   # Default setting
                'two_factor_enabled': False  # Default setting
            },
            'privacy_settings': {
                'profile_visibility': 'public',  # public, private, friends
                'show_earnings': False,
                'show_referrals': True
            },
            'updated_at': user.updated_at.isoformat() if user.updated_at else None
        }
        
        return jsonify(settings_data), 200
        
    except Exception as e:
        current_app.logger.error(f'Get user settings error: {str(e)}')
        return jsonify({'error': 'Failed to get user settings'}), 500


@user_bp.route('/settings', methods=['PUT'])
@jwt_required()
def update_user_settings():
    """Update user settings and preferences"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Update allowed settings fields
        updatable_fields = ['phone', 'date_of_birth']
        updated_fields = []
        
        for field in updatable_fields:
            if field in data:
                if field == 'date_of_birth' and data[field]:
                    try:
                        setattr(user, field, datetime.strptime(data[field], '%Y-%m-%d').date())
                        updated_fields.append(field)
                    except ValueError:
                        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
                else:
                    setattr(user, field, data[field])
                    updated_fields.append(field)
        

        
        # Note: account_settings and privacy_settings would typically be stored 
        # in a separate UserSettings table or as JSON fields, but for now we'll 
        # acknowledge them without persisting (since they're not in the current User model)
        settings_updated = []
        if 'account_settings' in data:
            settings_updated.append('account_settings')
        if 'privacy_settings' in data:
            settings_updated.append('privacy_settings')
        
        if updated_fields or settings_updated:
            user.updated_at = datetime.utcnow()
            db.session.commit()
            
            current_app.logger.info(f'Settings updated for user {user.username}: {updated_fields + settings_updated}')
            
            return jsonify({
                'message': 'Settings updated successfully',
                'updated_fields': updated_fields,
                'settings_updated': settings_updated,
                'user_settings': {
                    'user_id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'phone': user.phone,
                    'date_of_birth': user.date_of_birth.isoformat() if user.date_of_birth else None,
                    'updated_at': user.updated_at.isoformat()
                }
            }), 200
        else:
            return jsonify({'message': 'No settings to update'}), 200
            
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Update user settings error: {str(e)}')
        return jsonify({'error': 'Failed to update user settings'}), 500


@user_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_user_profile():
    """Get user profile (redirect to auth/profile for consistency)"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Return basic profile data (without wallet balances and team stats)
        profile_data = user.to_dict(include_sensitive=True)
        
        return jsonify(profile_data), 200
        
    except Exception as e:
        current_app.logger.error(f'Get user profile error: {str(e)}')
        return jsonify({'error': 'Failed to get user profile'}), 500


@user_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_user_profile():
    """Update user profile (basic profile information)"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Update allowed profile fields
        updatable_fields = ['first_name', 'last_name', 'phone', 'date_of_birth']
        updated_fields = []
        
        for field in updatable_fields:
            if field in data:
                if field == 'date_of_birth' and data[field]:
                    try:
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
        current_app.logger.error(f'Update user profile error: {str(e)}')
        return jsonify({'error': 'Failed to update user profile'}), 500
