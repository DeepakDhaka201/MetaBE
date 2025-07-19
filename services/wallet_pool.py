"""
Wallet Pool Service for MetaX Coin Backend
Handles crypto deposit monitoring and wallet management (adapted from Rupal)
"""

import traceback
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from flask import current_app
import requests

from models import db, PooledWallet, WalletAssignment, Transaction, TransactionStatus, User
from models.transaction import TransactionType
from models.wallet_pool import WalletStatus


class DepositMonitor:
    """Monitor crypto deposits on assigned wallets"""

    def __init__(self, app=None):
        if app:
            self.tron_api_url = app.config.get('TRON_API_URL', 'https://api.trongrid.io')
            self.usdt_contract = app.config.get('USDT_CONTRACT_ADDRESS', 'TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t')
        else:
            # Fallback to default values
            self.tron_api_url = 'https://api.trongrid.io'
            self.usdt_contract = 'TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t'

        # Ensure we have a valid contract address
        if not self.usdt_contract:
            self.usdt_contract = 'TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t'
    
    def monitor_active_assignments(self, app=None):
        """Monitor all active wallet assignments for deposits"""
        if app is None:
            app = current_app._get_current_object()

        with app.app_context():
            # Ensure configuration is loaded
            if not self.usdt_contract:
                self.usdt_contract = app.config.get('USDT_CONTRACT_ADDRESS', 'TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t')
                app.logger.info(f"Loaded USDT contract address: {self.usdt_contract}")

            try:
                app.logger.info("Checking active wallet assignments for deposits")

                # Get all active assignments with database locking (following Rupal pattern)
                assignments = (WalletAssignment.query
                             .filter_by(is_active=True)
                             .with_for_update()
                             .all())
                app.logger.info(f"Found {len(assignments)} active assignments to check")

                for assignment in assignments:
                    self._check_assignment(assignment, app)

                    # Handle expired assignments (following Rupal pattern)
                    if datetime.utcnow() > assignment.expires_at:
                        self._handle_expired_assignment(assignment, app)

            except Exception as e:
                app.logger.error(f"Monitor error: {str(e)}")
                traceback.print_exc()
    
    def _check_assignment(self, assignment, app):
        """Check a specific wallet assignment for deposits"""
        try:
            # Get blockchain transactions for this wallet
            blockchain_txns = self._get_blockchain_transactions(
                assignment.wallet.address,
                assignment.assigned_at,
                app
            )

            app.logger.info(f"Found {len(blockchain_txns)} blockchain transactions for wallet {assignment.wallet.address}")

            for txn in blockchain_txns:
                # Skip if transaction already processed
                existing_txn = Transaction.query.filter_by(blockchain_txn_id=txn['transaction_id']).first()
                if existing_txn:
                    app.logger.info(f"Transaction {txn['transaction_id']} already processed")
                    continue

                # Verify transaction
                if not self._verify_transaction(txn, assignment, app):
                    app.logger.info(f"Transaction {txn['transaction_id']} failed verification")
                    continue

                # Process valid transaction
                self._process_transaction(assignment, txn, app)
                return

        except Exception as e:
            app.logger.error(f"Check assignment error: {str(e)}")
            traceback.print_exc()
    
    def _verify_transaction(self, txn, assignment, app):
        """Verify if transaction is valid for this assignment"""
        try:
            # Ensure we have the contract address from config
            usdt_contract = self.usdt_contract or app.config.get('USDT_CONTRACT_ADDRESS', 'TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t')

            # Check contract address (USDT)
            if txn.get('contract_address') != usdt_contract:
                app.logger.error(f"Invalid contract address: {txn.get('contract_address')} (expected: {usdt_contract})")
                return False

            # Check transaction timestamp
            txn_timestamp = datetime.fromtimestamp(txn['block_timestamp'] / 1000)

            if txn_timestamp < assignment.assigned_at:
                app.logger.error(f"Transaction timestamp before assignment: {txn_timestamp} < {assignment.assigned_at}")
                return False

            if txn_timestamp > assignment.expires_at:
                app.logger.error(f"Transaction timestamp after expiry: {txn_timestamp} > {assignment.expires_at}")
                return False

            # Check minimum amount (optional)
            amount_usdt = float(txn['value']) / 1e6
            min_deposit = app.config.get('MIN_DEPOSIT', 10.0)
            if amount_usdt < min_deposit:
                app.logger.error(f"Amount below minimum: {amount_usdt} < {min_deposit}")
                return False

            return True

        except Exception as e:
            app.logger.error(f"Verify transaction error: {str(e)}")
            return False
    
    def _process_transaction(self, assignment, txn, app):
        """Process a valid deposit transaction"""
        try:
            amount_usdt = float(txn['value']) / 1e6
            app.logger.info(f"Processing deposit: {amount_usdt} USDT for user {assignment.user_id}")

            # Create transaction record (PENDING admin approval)
            transaction = Transaction(
                user_id=assignment.user_id,
                transaction_type=TransactionType.DEPOSIT,
                wallet_type='available_fund',  # Default deposit wallet
                amount=amount_usdt,
                status=TransactionStatus.PENDING,  # Requires admin approval
                blockchain_txn_id=txn['transaction_id'],
                from_address=txn.get('from'),
                to_address=txn.get('to'),
                wallet_assignment_id=assignment.id,
                description=f"Crypto deposit detected - requires admin approval"
            )
            db.session.add(transaction)

            # Complete the assignment (following Rupal pattern)
            assignment.is_active = False  # Deactivate assignment
            assignment.transaction_detected = True
            assignment.actual_amount = amount_usdt
            assignment.completed_at = datetime.utcnow()

            # Release the wallet back to pool (critical fix)
            assignment.wallet.status = WalletStatus.AVAILABLE
            assignment.wallet.last_checked_at = datetime.utcnow()

            # Note: Wallet crediting and referral distribution will happen
            # when admin approves the transaction via Transaction.approve() method

            db.session.commit()
            app.logger.info(f"Successfully processed deposit for user {assignment.user_id}, wallet released")

        except Exception as e:
            db.session.rollback()

            # Critical: Release wallet on error (following Rupal pattern)
            try:
                assignment.is_active = False
                assignment.wallet.status = WalletStatus.AVAILABLE
                db.session.commit()
                app.logger.info(f"Released wallet after error for assignment {assignment.id}")
            except Exception as release_error:
                app.logger.error(f"Failed to release wallet after error: {str(release_error)}")

            app.logger.error(f"Process transaction error: {str(e)}")
            traceback.print_exc()
    
    def _get_blockchain_transactions(self, address, start_time, app):
        """Get blockchain transactions for an address"""
        try:
            response = requests.get(
                f"{self.tron_api_url}/v1/accounts/{address}/transactions/trc20",
                params={
                    'only_to': True,
                    'min_timestamp': int(start_time.timestamp() * 1000),
                    'contract_address': self.usdt_contract
                },
                timeout=10
            )

            if response.ok:
                return response.json().get('data', [])
            else:
                app.logger.error(f"API request failed: {response.status_code}")
                return []

        except Exception as e:
            app.logger.error(f"Get blockchain transactions error: {str(e)}")
            return []
    
    def _handle_expired_assignment(self, assignment, app):
        """Handle expired wallet assignment"""
        try:
            app.logger.info(f"Handling expired assignment: {assignment.id}")

            # Give a grace period for final check
            blockchain_txns = self._get_blockchain_transactions(
                assignment.wallet.address,
                assignment.assigned_at,
                app
            )

            # Check for any valid transactions during assignment period
            for txn in blockchain_txns:
                txn_timestamp = datetime.fromtimestamp(txn['block_timestamp'] / 1000)

                if assignment.assigned_at <= txn_timestamp <= assignment.expires_at:
                    existing_txn = Transaction.query.filter_by(blockchain_txn_id=txn['transaction_id']).first()
                    if not existing_txn and self._verify_transaction(txn, assignment, app):
                        self._process_transaction(assignment, txn, app)
                        return

            # No valid transaction found, cancel assignment
            assignment.cancel_assignment("Assignment expired without valid transaction")
            db.session.commit()
            app.logger.info(f"Cancelled expired assignment: {assignment.id}")

        except Exception as e:
            db.session.rollback()

            # Ensure wallet is released even on error (critical fix)
            try:
                assignment.is_active = False
                assignment.wallet.status = WalletStatus.AVAILABLE
                assignment.cancelled_at = datetime.utcnow()
                assignment.cancellation_reason = f"Error during expiry handling: {str(e)}"
                db.session.commit()
                app.logger.info(f"Force-released wallet after expiry error for assignment {assignment.id}")
            except Exception as release_error:
                app.logger.error(f"Failed to force-release wallet: {str(release_error)}")

            app.logger.error(f"Handle expired assignment error: {str(e)}")
            traceback.print_exc()


def cleanup_expired_assignments(app=None):
    """Clean up expired wallet assignments"""
    if app is None:
        app = current_app._get_current_object()

    with app.app_context():
        try:
            cleaned_count = WalletAssignment.cleanup_expired_assignments()
            if cleaned_count > 0:
                app.logger.info(f"Cleaned up {cleaned_count} expired assignments")
        except Exception as e:
            app.logger.error(f"Cleanup expired assignments error: {str(e)}")


def setup_wallet_monitoring(app):
    """Setup wallet monitoring background task"""
    scheduler = BackgroundScheduler()
    monitor = DepositMonitor(app)

    # Monitor deposits frequently (following Rupal pattern)
    scheduler.add_job(
        lambda: monitor.monitor_active_assignments(app),
        'interval',
        seconds=app.config.get('WALLET_MONITORING_INTERVAL', 5),  # Changed from 60 to 5 seconds
        id='wallet_monitoring'
    )

    scheduler.start()
    return scheduler


def setup_claim_monitoring(app):
    """Setup assignment cleanup background task"""
    scheduler = BackgroundScheduler()

    # Cleanup expired assignments every 5 minutes
    scheduler.add_job(
        lambda: cleanup_expired_assignments(app),
        'interval',
        minutes=app.config.get('WALLET_CLEANUP_INTERVAL', 5),
        id='assignment_cleanup'
    )

    scheduler.start()
    return scheduler


def assign_wallet_to_user(user_id, expected_amount=None):
    """Assign a wallet to user for deposit"""
    try:
        duration_minutes = current_app.config.get('WALLET_ASSIGNMENT_DURATION', 30)
        assignment = PooledWallet.assign_wallet_to_user(user_id, duration_minutes)
        
        if assignment and expected_amount:
            assignment.expected_amount = expected_amount
            db.session.commit()
        
        return assignment
    except Exception as e:
        current_app.logger.error(f"Assign wallet error: {str(e)}")
        return None


def get_user_active_assignment(user_id):
    """Get user's active wallet assignment"""
    return WalletAssignment.query.filter_by(
        user_id=user_id,
        is_active=True
    ).first()


def get_wallet_pool_statistics():
    """Get wallet pool statistics"""
    wallet_stats = PooledWallet.get_wallet_statistics()
    assignment_stats = WalletAssignment.get_assignment_statistics()
    
    return {
        'wallets': wallet_stats,
        'assignments': assignment_stats
    }
