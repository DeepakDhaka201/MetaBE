#!/usr/bin/env python3
"""
Create Admin User Script for MetaX Coin Backend
Creates a default admin user for testing the admin interface
"""

import os
import sys
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db, User

def create_admin_user():
    """Create a default admin user"""
    app = create_app()
    
    with app.app_context():
        # Check if admin user already exists
        admin_user = User.query.filter_by(is_admin=True).first()
        
        if admin_user:
            print(f"Admin user already exists: {admin_user.username} ({admin_user.email})")
            print(f"Admin ID: {admin_user.id}")
            print(f"Is Active: {admin_user.is_active}")
            return admin_user
        
        # Create new admin user
        admin_username = app.config.get('DEFAULT_ADMIN_USERNAME', 'admin')
        admin_email = app.config.get('DEFAULT_ADMIN_EMAIL', 'admin@metaxcoin.cloud')
        admin_password = app.config.get('DEFAULT_ADMIN_PASSWORD', 'admin123')
        
        # Check if username or email already exists
        existing_user = User.query.filter(
            (User.username == admin_username) | (User.email == admin_email)
        ).first()
        
        if existing_user:
            # Update existing user to be admin
            existing_user.is_admin = True
            existing_user.is_active = True
            existing_user.is_verified = True
            db.session.commit()
            
            print(f"Updated existing user to admin: {existing_user.username} ({existing_user.email})")
            print(f"Admin ID: {existing_user.id}")
            return existing_user
        
        # Create new admin user
        admin_user = User(
            username=admin_username,
            email=admin_email,
            first_name='Admin',
            last_name='User',
            is_admin=True,
            is_active=True,
            is_verified=True,
            created_at=datetime.utcnow()
        )
        
        admin_user.set_password(admin_password)
        
        db.session.add(admin_user)
        db.session.commit()
        
        print(f"Created new admin user: {admin_user.username} ({admin_user.email})")
        print(f"Admin ID: {admin_user.id}")
        print(f"Default password: {admin_password}")
        print("\n⚠️  IMPORTANT: Change the default password after first login!")
        
        return admin_user

def list_admin_users():
    """List all admin users"""
    app = create_app()
    
    with app.app_context():
        admin_users = User.query.filter_by(is_admin=True).all()
        
        if not admin_users:
            print("No admin users found.")
            return
        
        print(f"Found {len(admin_users)} admin user(s):")
        print("-" * 60)
        
        for user in admin_users:
            print(f"ID: {user.id}")
            print(f"Username: {user.username}")
            print(f"Email: {user.email}")
            print(f"Name: {user.first_name} {user.last_name}")
            print(f"Active: {user.is_active}")
            print(f"Verified: {user.is_verified}")
            print(f"Created: {user.created_at}")
            print(f"Last Login: {user.last_login or 'Never'}")
            print("-" * 60)

def reset_admin_password(username_or_email, new_password):
    """Reset admin user password"""
    app = create_app()
    
    with app.app_context():
        user = User.query.filter(
            ((User.username == username_or_email) | (User.email == username_or_email)) &
            (User.is_admin == True)
        ).first()
        
        if not user:
            print(f"Admin user not found: {username_or_email}")
            return False
        
        user.set_password(new_password)
        db.session.commit()
        
        print(f"Password reset for admin user: {user.username}")
        return True

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Admin User Management for MetaX Coin')
    parser.add_argument('action', choices=['create', 'list', 'reset-password'], 
                       help='Action to perform')
    parser.add_argument('--username', help='Username for password reset')
    parser.add_argument('--password', help='New password for reset')
    
    args = parser.parse_args()
    
    if args.action == 'create':
        create_admin_user()
    elif args.action == 'list':
        list_admin_users()
    elif args.action == 'reset-password':
        if not args.username or not args.password:
            print("Error: --username and --password are required for reset-password")
            sys.exit(1)
        reset_admin_password(args.username, args.password)
    
    print("\nDone!")
