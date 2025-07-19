#!/usr/bin/env python3
"""
MetaX Coin Backend - Development Server
Run this file to start the development server
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from app import create_app

if __name__ == '__main__':
    # Create Flask app
    app = create_app()
    
    # Get configuration from environment
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5000))
    debug = os.environ.get('FLASK_ENV', 'development') == 'development'
    
    print("=" * 60)
    print("           MetaX Coin Backend")
    print("=" * 60)
    print(f"🚀 Server starting on http://{host}:{port}")
    print(f"📊 Environment: {os.environ.get('FLASK_ENV', 'development')}")
    print(f"🗄️ Database: {app.config.get('SQLALCHEMY_DATABASE_URI', 'Not configured')}")
    print(f"📧 Email: {app.config.get('MAIL_USERNAME', 'Not configured')}")
    print()
    print("API Endpoints:")
    print("• /api/health - Health check")
    print("• /api/auth/* - Authentication")
    print("• /api/dashboard/* - Dashboard & wallets")
    print("• /api/team/* - Referral system")
    print("• /api/transactions/* - Deposits & withdrawals")
    print("• /api/admin/* - Admin panel")
    print("• /api/crypto/* - External crypto data")
    print("• /api/income/* - Income tracking")
    print()
    print("Press Ctrl+C to stop the server")
    print("=" * 60)
    
    # Run the development server
    app.run(
        host=host,
        port=port,
        debug=debug,
        threaded=True
    )
