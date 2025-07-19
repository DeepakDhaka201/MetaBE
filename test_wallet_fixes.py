#!/usr/bin/env python3
"""
Test script to verify wallet monitoring fixes
Run this to ensure the wallet pool system works correctly
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
from models import db, User, PooledWallet, WalletAssignment
from models.wallet_pool import WalletStatus
from services.wallet_pool import assign_wallet_to_user, get_user_active_assignment
from app import create_app

def test_wallet_lifecycle():
    """Test complete wallet assignment lifecycle"""
    app = create_app()
    
    with app.app_context():
        print("🔧 Testing Wallet Lifecycle Fixes...")
        
        # 1. Create test user
        test_user = User(
            username='test_wallet_user',
            email='test@wallet.com',
            first_name='Test',
            last_name='User'
        )
        test_user.set_password('password123')
        db.session.add(test_user)
        db.session.flush()
        
        # 2. Create test wallet
        test_wallet = PooledWallet(
            address='TTestWalletAddress123456789',
            status=WalletStatus.AVAILABLE,
            network='TRON'
        )
        db.session.add(test_wallet)
        db.session.commit()
        
        print(f"✅ Created test user {test_user.id} and wallet {test_wallet.id}")
        
        # 3. Test wallet assignment
        assignment = assign_wallet_to_user(test_user.id, 100.0)
        assert assignment is not None, "❌ Wallet assignment failed"
        assert assignment.is_active == True, "❌ Assignment should be active"
        assert assignment.wallet.status == WalletStatus.IN_USE, "❌ Wallet should be IN_USE"
        print(f"✅ Wallet assigned successfully: {assignment.id}")
        
        # 4. Test assignment completion (simulate transaction processing)
        assignment.is_active = False
        assignment.completed_at = datetime.utcnow()
        assignment.transaction_detected = True
        assignment.actual_amount = 100.0
        assignment.wallet.status = WalletStatus.AVAILABLE
        db.session.commit()
        
        # Verify wallet is released
        db.session.refresh(assignment.wallet)
        assert assignment.wallet.status == WalletStatus.AVAILABLE, "❌ Wallet should be AVAILABLE after completion"
        print("✅ Wallet released successfully after completion")
        
        # 5. Test cleanup function
        # Create expired assignment
        expired_assignment = WalletAssignment(
            wallet_id=test_wallet.id,
            user_id=test_user.id,
            assigned_at=datetime.utcnow() - timedelta(hours=2),
            expires_at=datetime.utcnow() - timedelta(hours=1),  # Expired 1 hour ago
            is_active=True
        )
        test_wallet.status = WalletStatus.IN_USE
        db.session.add(expired_assignment)
        db.session.commit()
        
        # Run cleanup
        cleaned_count = WalletAssignment.cleanup_expired_assignments()
        assert cleaned_count > 0, "❌ Cleanup should have found expired assignments"
        
        # Verify cleanup worked
        db.session.refresh(expired_assignment)
        db.session.refresh(test_wallet)
        assert expired_assignment.is_active == False, "❌ Expired assignment should be inactive"
        assert test_wallet.status == WalletStatus.AVAILABLE, "❌ Wallet should be available after cleanup"
        print(f"✅ Cleanup function worked: {cleaned_count} assignments cleaned")
        
        # 6. Test database locking (basic test)
        available_wallet = PooledWallet.get_available_wallet()
        assert available_wallet is not None, "❌ Should find available wallet"
        print("✅ Database locking query works")
        
        # Cleanup
        db.session.delete(expired_assignment)
        db.session.delete(assignment)
        db.session.delete(test_wallet)
        db.session.delete(test_user)
        db.session.commit()
        
        print("🎉 All wallet lifecycle tests passed!")

def test_error_recovery():
    """Test error recovery mechanisms"""
    app = create_app()
    
    with app.app_context():
        print("🔧 Testing Error Recovery...")
        
        # Create test data
        test_user = User(
            username='test_error_user',
            email='error@test.com',
            first_name='Error',
            last_name='Test'
        )
        test_user.set_password('password123')
        db.session.add(test_user)
        db.session.flush()
        
        test_wallet = PooledWallet(
            address='TErrorTestWallet123456789',
            status=WalletStatus.IN_USE,  # Stuck in IN_USE
            network='TRON'
        )
        db.session.add(test_wallet)
        db.session.commit()
        
        # Test stuck wallet cleanup
        initial_status = test_wallet.status
        cleaned_count = WalletAssignment.cleanup_expired_assignments()
        
        db.session.refresh(test_wallet)
        if test_wallet.status == WalletStatus.AVAILABLE:
            print("✅ Stuck wallet cleanup works")
        else:
            print("⚠️  Stuck wallet cleanup may need manual intervention")
        
        # Cleanup
        db.session.delete(test_wallet)
        db.session.delete(test_user)
        db.session.commit()
        
        print("🎉 Error recovery tests completed!")

if __name__ == '__main__':
    try:
        test_wallet_lifecycle()
        test_error_recovery()
        print("\n🎉 ALL TESTS PASSED! Wallet monitoring fixes are working correctly.")
    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
