"""
Database Migration: Create Investment Tables
Creates investment_packages, user_investments, and investment_returns tables
"""

import os
import sys

# Add the parent directory to the path so we can import from the app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def create_investment_tables():
    """Create investment-related tables"""

    print("Creating investment tables...")

    try:
        from models import db, InvestmentPackage, UserInvestment, InvestmentReturn

        # Create all investment tables
        db.create_all()

        print("✅ Investment tables created successfully!")
        print("   - investment_packages")
        print("   - user_investments")
        print("   - investment_returns")

        # Create sample investment package for testing
        create_sample_package()

        return True

    except Exception as e:
        print(f"❌ Error creating investment tables: {str(e)}")
        return False

def create_sample_package():
    """Create a sample investment package for testing"""

    try:
        from models import db, InvestmentPackage
        from models.investment import PackageStatus
        from datetime import date, timedelta

        # Check if sample package already exists
        existing = InvestmentPackage.query.filter_by(name="MXC Launch Package").first()
        if existing:
            print("   - Sample package already exists")
            return

        # Create sample package
        sample_package = InvestmentPackage(
            name="MXC Launch Package",
            description="Early access to MXC token launch with guaranteed returns",
            min_amount=100.0,
            max_amount=10000.0,
            total_return_percentage=25.0,  # 25% total return
            duration_days=180,  # 6 months
            launch_date=date.today() + timedelta(days=30),  # Launch in 30 days
            end_date=date.today() + timedelta(days=90),     # Accept investments for 90 days
            status=PackageStatus.ACTIVE,
            is_featured=True,
            sort_order=1
        )

        db.session.add(sample_package)
        db.session.commit()

        print("   - Sample 'MXC Launch Package' created")
        print(f"     Min: $100, Max: $10,000")
        print(f"     Return: 25% over 180 days")
        print(f"     Launch Date: {sample_package.launch_date}")

    except Exception as e:
        print(f"   - Warning: Could not create sample package: {str(e)}")

def run_migration():
    """Run the investment tables migration"""

    # Import app to get database connection
    try:
        from app import create_app
        from models import db, InvestmentPackage, UserInvestment, InvestmentReturn

        app = create_app()

        with app.app_context():
            success = create_investment_tables()

            if success:
                print("\n🎉 Investment system migration completed successfully!")
                print("\nNext steps:")
                print("1. Restart your Flask server")
                print("2. Check admin panel for investment package management")
                print("3. Test investment purchase API")
            else:
                print("\n❌ Migration failed. Please check the errors above.")

    except Exception as e:
        print(f"❌ Migration error: {str(e)}")
        print("Make sure your Flask app is properly configured.")

if __name__ == "__main__":
    run_migration()
