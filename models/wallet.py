"""
Wallet Model for MetaX Coin Backend
Handles the 9-wallet system for different income and balance types
"""

from datetime import datetime
from decimal import Decimal
from sqlalchemy import func

from . import db


class Wallet(db.Model):
    """Wallet model supporting 9 different wallet types"""
    
    __tablename__ = 'wallets'
    
    # Primary fields
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    wallet_type = db.Column(db.String(50), nullable=False, index=True)
    
    # Balance fields
    balance = db.Column(db.Numeric(20, 8), default=0, nullable=False)
    locked_balance = db.Column(db.Numeric(20, 8), default=0, nullable=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Constraints
    __table_args__ = (
        db.UniqueConstraint('user_id', 'wallet_type', name='unique_user_wallet_type'),
        db.Index('idx_user_wallet_type', 'user_id', 'wallet_type'),
    )
    
    def __repr__(self):
        return f'<Wallet {self.user_id}:{self.wallet_type}:{self.balance}>'
    
    @property
    def available_balance(self):
        """Get available balance (total - locked)"""
        return self.balance - self.locked_balance
    
    def add_balance(self, amount, description=None):
        """Add amount to wallet balance"""
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        self.balance += Decimal(str(amount))
        self.updated_at = datetime.utcnow()
        
        # Update total_income wallet if this is an income type
        if self.wallet_type in self.get_income_wallet_types():
            self._update_total_income_wallet(amount)
        
        # Log the transaction
        self._log_wallet_transaction('credit', amount, description)
    
    def subtract_balance(self, amount, description=None):
        """Subtract amount from wallet balance"""
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        if self.available_balance < Decimal(str(amount)):
            raise ValueError("Insufficient balance")
        
        self.balance -= Decimal(str(amount))
        self.updated_at = datetime.utcnow()
        
        # Log the transaction
        self._log_wallet_transaction('debit', amount, description)
    
    def lock_balance(self, amount):
        """Lock a portion of the balance"""
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        if self.available_balance < Decimal(str(amount)):
            raise ValueError("Insufficient available balance")
        
        self.locked_balance += Decimal(str(amount))
        self.updated_at = datetime.utcnow()
    
    def unlock_balance(self, amount):
        """Unlock a portion of the locked balance"""
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        if self.locked_balance < Decimal(str(amount)):
            raise ValueError("Insufficient locked balance")
        
        self.locked_balance -= Decimal(str(amount))
        self.updated_at = datetime.utcnow()
    
    def transfer_to(self, target_wallet, amount, description=None):
        """Transfer amount to another wallet"""
        if not isinstance(target_wallet, Wallet):
            raise ValueError("Target must be a Wallet instance")
        
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        if self.available_balance < Decimal(str(amount)):
            raise ValueError("Insufficient balance")
        
        # Perform the transfer
        self.subtract_balance(amount, f"Transfer to {target_wallet.wallet_type}: {description}")
        target_wallet.add_balance(amount, f"Transfer from {self.wallet_type}: {description}")
        
        # Log the transfer
        from .transaction import Transaction
        transaction = Transaction(
            user_id=self.user_id,
            transaction_type='transfer',
            wallet_type=f"{self.wallet_type} -> {target_wallet.wallet_type}",
            amount=amount,
            status='completed',
            description=description or f"Transfer from {self.wallet_type} to {target_wallet.wallet_type}"
        )
        db.session.add(transaction)
    
    def _update_total_income_wallet(self, amount):
        """Update the total_income wallet when income is added"""
        total_income_wallet = Wallet.query.filter_by(
            user_id=self.user_id, 
            wallet_type='total_income'
        ).first()
        
        if total_income_wallet and total_income_wallet.id != self.id:
            total_income_wallet.balance += Decimal(str(amount))
            total_income_wallet.updated_at = datetime.utcnow()
    
    def _log_wallet_transaction(self, transaction_type, amount, description):
        """Log wallet transaction for audit trail"""
        from .transaction import Transaction
        transaction = Transaction(
            user_id=self.user_id,
            transaction_type=transaction_type,
            wallet_type=self.wallet_type,
            amount=amount,
            status='completed',
            description=description or f"{transaction_type.title()} to {self.wallet_type}"
        )
        db.session.add(transaction)
    
    @staticmethod
    def get_wallet_types():
        """Get all available wallet types"""
        return [
            'available_fund',    # Main spending wallet
            'total_gain',        # Investment returns + staking rewards
            'level_bonus',       # Multi-level commissions
            'total_referral',    # Direct referral commissions
            'total_income',      # Sum of all income types (calculated)
        ]
    
    @staticmethod
    def get_income_wallet_types():
        """Get wallet types that count as income"""
        return [
            'total_gain',
            'level_bonus',
            'total_referral'
        ]
    
    @staticmethod
    def initialize_user_wallets(user_id):
        """Initialize all wallet types for a new user"""
        wallet_types = Wallet.get_wallet_types()
        wallets = []
        
        for wallet_type in wallet_types:
            # Check if wallet already exists
            existing_wallet = Wallet.query.filter_by(
                user_id=user_id, 
                wallet_type=wallet_type
            ).first()
            
            if not existing_wallet:
                wallet = Wallet(
                    user_id=user_id,
                    wallet_type=wallet_type,
                    balance=0
                )
                wallets.append(wallet)
                db.session.add(wallet)
        
        return wallets
    
    @staticmethod
    def get_user_balances(user_id):
        """Get all wallet balances for a user"""
        wallets = Wallet.query.filter_by(user_id=user_id).all()
        balances = {}
        
        for wallet in wallets:
            balances[wallet.wallet_type] = {
                'balance': float(wallet.balance),
                'locked_balance': float(wallet.locked_balance),
                'available_balance': float(wallet.available_balance),
                'updated_at': wallet.updated_at.isoformat() if wallet.updated_at else None
            }
        
        # Ensure all wallet types are present
        for wallet_type in Wallet.get_wallet_types():
            if wallet_type not in balances:
                balances[wallet_type] = {
                    'balance': 0.0,
                    'locked_balance': 0.0,
                    'available_balance': 0.0,
                    'updated_at': None
                }
        
        return balances
    
    @staticmethod
    def get_user_total_balance(user_id):
        """Get total balance across all wallets for a user"""
        total = db.session.query(func.sum(Wallet.balance)).filter_by(user_id=user_id).scalar()
        return float(total) if total else 0.0

    @staticmethod
    def get_total_system_balance(wallet_type=None):
        """Get total balance across all users for a specific wallet type or all wallets"""
        if wallet_type:
            total = db.session.query(func.sum(Wallet.balance)).filter_by(wallet_type=wallet_type).scalar()
        else:
            total = db.session.query(func.sum(Wallet.balance)).scalar()
        return float(total) if total else 0.0
    
    def to_dict(self):
        """Convert wallet to dictionary"""
        return {
            'id': self.id,
            'wallet_type': self.wallet_type,
            'balance': float(self.balance),
            'locked_balance': float(self.locked_balance),
            'available_balance': float(self.available_balance),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
