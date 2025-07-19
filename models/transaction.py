"""
Transaction Model for MetaX Coin Backend
Handles all types of transactions including deposits, withdrawals, and transfers
"""

from datetime import datetime
from enum import Enum
import secrets
import string

from . import db


class TransactionType(Enum):
    """Transaction type enumeration"""
    DEPOSIT = 'deposit'
    WITHDRAWAL = 'withdrawal'
    TRANSFER = 'transfer'
    CREDIT = 'credit'
    DEBIT = 'debit'
    COMMISSION = 'commission'
    STAKING_REWARD = 'staking_reward'
    BONUS = 'bonus'
    INVESTMENT_PURCHASE = 'investment_purchase'


class TransactionStatus(Enum):
    """Transaction status enumeration"""
    PENDING = 'pending'
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'
    REJECTED = 'rejected'


class Transaction(db.Model):
    """Transaction model for all financial operations"""
    
    __tablename__ = 'transactions'
    
    # Primary fields
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Transaction details
    transaction_type = db.Column(db.Enum(TransactionType), nullable=False, index=True)
    wallet_type = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Numeric(20, 8), nullable=False)
    fee = db.Column(db.Numeric(20, 8), default=0)
    
    # Status and processing
    status = db.Column(db.Enum(TransactionStatus), default=TransactionStatus.PENDING, nullable=False, index=True)
    description = db.Column(db.Text)
    admin_notes = db.Column(db.Text)
    error_message = db.Column(db.Text)
    
    # Blockchain related (for crypto transactions)
    blockchain_txn_id = db.Column(db.String(100), index=True)
    from_address = db.Column(db.String(100))
    to_address = db.Column(db.String(100))
    confirmations = db.Column(db.Integer, default=0)
    
    # Wallet assignment (for deposits)
    wallet_assignment_id = db.Column(db.Integer, db.ForeignKey('wallet_assignments.id'))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    processed_at = db.Column(db.DateTime)
    confirmed_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    wallet_assignment = db.relationship('WalletAssignment', backref='transactions')
    
    def __init__(self, **kwargs):
        super(Transaction, self).__init__(**kwargs)
        if not self.transaction_id:
            self.transaction_id = self.generate_transaction_id()
    
    def __repr__(self):
        return f'<Transaction {self.transaction_id}:{self.transaction_type.value}:{self.amount}>'
    
    @staticmethod
    def generate_transaction_id(prefix='MXC'):
        """Generate a unique transaction ID"""
        while True:
            # Format: MXC + timestamp + random
            timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
            random_part = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
            txn_id = f"{prefix}{timestamp}{random_part}"
            
            if not Transaction.query.filter_by(transaction_id=txn_id).first():
                return txn_id
    
    def approve(self, admin_notes=None):
        """Approve a pending transaction"""
        if self.status != TransactionStatus.PENDING:
            raise ValueError(f"Cannot approve transaction with status: {self.status.value}")
        
        self.status = TransactionStatus.PROCESSING
        self.processed_at = datetime.utcnow()
        if admin_notes:
            self.admin_notes = admin_notes
        
        # Process the transaction based on type
        if self.transaction_type == TransactionType.DEPOSIT:
            self._process_deposit()
        elif self.transaction_type == TransactionType.WITHDRAWAL:
            self._process_withdrawal()
        elif self.transaction_type == TransactionType.TRANSFER:
            self._process_transfer()
        
        self.status = TransactionStatus.COMPLETED
        self.confirmed_at = datetime.utcnow()
    
    def reject(self, reason=None, admin_notes=None):
        """Reject a pending transaction"""
        if self.status != TransactionStatus.PENDING:
            raise ValueError(f"Cannot reject transaction with status: {self.status.value}")

        # For withdrawals, unlock the locked funds
        if self.transaction_type == TransactionType.WITHDRAWAL:
            self._unlock_withdrawal_funds()

        self.status = TransactionStatus.REJECTED
        self.processed_at = datetime.utcnow()
        if reason:
            self.error_message = reason
        if admin_notes:
            self.admin_notes = admin_notes
    
    def cancel(self, reason=None):
        """Cancel a transaction"""
        if self.status in [TransactionStatus.COMPLETED, TransactionStatus.REJECTED]:
            raise ValueError(f"Cannot cancel transaction with status: {self.status.value}")
        
        self.status = TransactionStatus.CANCELLED
        self.processed_at = datetime.utcnow()
        if reason:
            self.error_message = reason
    
    def fail(self, error_message=None):
        """Mark transaction as failed"""
        self.status = TransactionStatus.FAILED
        self.processed_at = datetime.utcnow()
        if error_message:
            self.error_message = error_message
    
    def _process_deposit(self):
        """Process a deposit transaction"""
        from .wallet import Wallet
        
        # Find or create the target wallet
        wallet = Wallet.query.filter_by(
            user_id=self.user_id,
            wallet_type=self.wallet_type
        ).first()
        
        if not wallet:
            wallet = Wallet(
                user_id=self.user_id,
                wallet_type=self.wallet_type,
                balance=0
            )
            db.session.add(wallet)
        
        # Add the amount to the wallet
        wallet.add_balance(self.amount, f"Deposit - {self.transaction_id}")

        # Note: Referral commissions are distributed during investment purchases,
        # not during deposits to avoid double commission distribution

        # Note: total_investment is now calculated from UserInvestment records
        # Deposits only add to wallet balance, not total_investment
    
    def _process_withdrawal(self):
        """Process a withdrawal transaction"""
        from .wallet import Wallet
        
        # Find the source wallet
        wallet = Wallet.query.filter_by(
            user_id=self.user_id,
            wallet_type=self.wallet_type
        ).first()
        
        if not wallet:
            raise ValueError(f"Wallet {self.wallet_type} not found for user {self.user_id}")
        
        # Check if sufficient balance
        total_amount = self.amount + self.fee
        if wallet.available_balance < total_amount:
            raise ValueError("Insufficient balance for withdrawal")
        
        # Subtract the amount and fee from the wallet
        wallet.subtract_balance(total_amount, f"Withdrawal - {self.transaction_id}")

    def _unlock_withdrawal_funds(self):
        """Unlock funds that were locked for a withdrawal"""
        from .wallet import Wallet

        # Find the source wallet
        wallet = Wallet.query.filter_by(
            user_id=self.user_id,
            wallet_type=self.wallet_type
        ).first()

        if wallet:
            total_amount = self.amount + self.fee
            wallet.unlock_balance(total_amount)

    def _process_transfer(self):
        """Process an internal transfer transaction"""
        # Transfer logic is handled in the wallet model
        pass
    
    @staticmethod
    def get_user_transactions(user_id, transaction_type=None, status=None, limit=50, offset=0):
        """Get transactions for a user with optional filters"""
        query = Transaction.query.filter_by(user_id=user_id)
        
        if transaction_type:
            query = query.filter_by(transaction_type=transaction_type)
        
        if status:
            query = query.filter_by(status=status)
        
        return query.order_by(Transaction.created_at.desc()).offset(offset).limit(limit).all()
    
    @staticmethod
    def get_pending_transactions(limit=100):
        """Get all pending transactions for admin review"""
        return Transaction.query.filter_by(
            status=TransactionStatus.PENDING
        ).order_by(Transaction.created_at.asc()).limit(limit).all()
    
    def to_dict(self, include_sensitive=False):
        """Convert transaction to dictionary"""
        data = {
            'id': self.id,
            'transaction_id': self.transaction_id,
            'transaction_type': self.transaction_type.value,
            'wallet_type': self.wallet_type,
            'amount': float(self.amount),
            'fee': float(self.fee),
            'status': self.status.value,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
            'confirmed_at': self.confirmed_at.isoformat() if self.confirmed_at else None
        }
        
        if include_sensitive:
            data.update({
                'user_id': self.user_id,
                'admin_notes': self.admin_notes,
                'error_message': self.error_message,
                'blockchain_txn_id': self.blockchain_txn_id,
                'from_address': self.from_address,
                'to_address': self.to_address,
                'confirmations': self.confirmations,
                'wallet_assignment_id': self.wallet_assignment_id
            })
        
        return data
