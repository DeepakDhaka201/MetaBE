"""
Wallet Pool Models for MetaX Coin Backend
Handles pooled wallets for crypto deposits (adapted from Rupal)
"""

from datetime import datetime, timedelta
from enum import Enum

from . import db


class WalletStatus(Enum):
    """Wallet status enumeration"""
    AVAILABLE = 'AVAILABLE'
    IN_USE = 'IN_USE'
    DISABLED = 'DISABLED'
    MAINTENANCE = 'MAINTENANCE'


class PooledWallet(db.Model):
    """Pooled wallet model for crypto deposits"""
    
    __tablename__ = 'pooled_wallets'
    
    # Primary fields
    id = db.Column(db.Integer, primary_key=True)
    address = db.Column(db.String(100), unique=True, nullable=False, index=True)
    private_key = db.Column(db.Text)  # Encrypted private key (optional)
    
    # Status and tracking
    status = db.Column(db.Enum(WalletStatus), default=WalletStatus.AVAILABLE, nullable=False, index=True)
    network = db.Column(db.String(20), default='TRON', nullable=False)  # TRON, BSC, ETH, etc.
    
    # Usage statistics
    total_deposits = db.Column(db.Integer, default=0)
    total_deposit_amount = db.Column(db.Numeric(20, 8), default=0)
    last_used_at = db.Column(db.DateTime)
    last_checked_at = db.Column(db.DateTime)
    
    # Metadata
    label = db.Column(db.String(100))  # Optional label for identification
    notes = db.Column(db.Text)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    assignments = db.relationship('WalletAssignment', backref='wallet', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<PooledWallet {self.address}:{self.status.value}>'

    @property
    def is_active(self):
        """Check if wallet is active (available or in use)"""
        return self.status in [WalletStatus.AVAILABLE, WalletStatus.IN_USE]

    @property
    def assigned_to(self):
        """Get the user ID this wallet is currently assigned to"""
        active_assignment = self.assignments.filter_by(is_active=True).first()
        return active_assignment.user_id if active_assignment else None
    
    @staticmethod
    def get_available_wallet():
        """Get an available wallet for assignment with locking"""
        return (PooledWallet.query
                .filter_by(status=WalletStatus.AVAILABLE)
                .with_for_update(skip_locked=True)  # Skip locked wallets
                .order_by(PooledWallet.last_used_at.asc())  # Use least recently used
                .first())
    
    @staticmethod
    def assign_wallet_to_user(user_id, duration_minutes=30):
        """Assign an available wallet to a user"""
        # Get available wallet
        wallet = PooledWallet.get_available_wallet()
        if not wallet:
            return None
        
        # Mark wallet as in use
        wallet.status = WalletStatus.IN_USE
        wallet.last_used_at = datetime.utcnow()
        
        # Create assignment
        assignment = WalletAssignment(
            wallet_id=wallet.id,
            user_id=user_id,
            assigned_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(minutes=duration_minutes),
            is_active=True
        )
        
        db.session.add(assignment)
        db.session.commit()
        
        return assignment
    
    @staticmethod
    def release_wallet(wallet_id):
        """Release a wallet back to available pool"""
        wallet = PooledWallet.query.get(wallet_id)
        if wallet:
            wallet.status = WalletStatus.AVAILABLE
            db.session.commit()
        return wallet

    def update_usage_stats(self, deposit_amount):
        """Update wallet usage statistics"""
        self.total_deposits += 1
        self.total_deposit_amount += deposit_amount
        self.last_used_at = datetime.utcnow()
    
    @staticmethod
    def get_wallet_statistics():
        """Get wallet pool statistics"""
        total_wallets = PooledWallet.query.count()
        available_wallets = PooledWallet.query.filter_by(status=WalletStatus.AVAILABLE).count()
        in_use_wallets = PooledWallet.query.filter_by(status=WalletStatus.IN_USE).count()
        disabled_wallets = PooledWallet.query.filter_by(status=WalletStatus.DISABLED).count()
        
        return {
            'total_wallets': total_wallets,
            'available_wallets': available_wallets,
            'in_use_wallets': in_use_wallets,
            'disabled_wallets': disabled_wallets,
            'utilization_rate': (in_use_wallets / total_wallets * 100) if total_wallets > 0 else 0
        }
    
    def update_usage_stats(self, deposit_amount):
        """Update wallet usage statistics"""
        self.total_deposits += 1
        self.total_deposit_amount += deposit_amount
        self.updated_at = datetime.utcnow()
    
    def to_dict(self, include_sensitive=False):
        """Convert wallet to dictionary"""
        data = {
            'id': self.id,
            'address': self.address,
            'status': self.status.value,
            'network': self.network,
            'total_deposits': self.total_deposits,
            'total_deposit_amount': float(self.total_deposit_amount),
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None,
            'label': self.label,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
        
        if include_sensitive:
            data.update({
                'private_key': self.private_key,
                'notes': self.notes,
                'last_checked_at': self.last_checked_at.isoformat() if self.last_checked_at else None
            })
        
        return data


class WalletAssignment(db.Model):
    """Wallet assignment model for tracking user-wallet assignments"""
    
    __tablename__ = 'wallet_assignments'
    
    # Primary fields
    id = db.Column(db.Integer, primary_key=True)
    wallet_id = db.Column(db.Integer, db.ForeignKey('pooled_wallets.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Assignment details
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    
    # Transaction tracking
    expected_amount = db.Column(db.Numeric(20, 8))  # Expected deposit amount
    actual_amount = db.Column(db.Numeric(20, 8))    # Actual received amount
    transaction_detected = db.Column(db.Boolean, default=False)
    
    # Status and completion
    completed_at = db.Column(db.DateTime)
    cancelled_at = db.Column(db.DateTime)
    cancellation_reason = db.Column(db.String(255))
    
    # Metadata
    notes = db.Column(db.Text)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        db.Index('idx_user_active', 'user_id', 'is_active'),
        db.Index('idx_wallet_active', 'wallet_id', 'is_active'),
        db.Index('idx_expires_active', 'expires_at', 'is_active'),
    )
    
    def __repr__(self):
        return f'<WalletAssignment {self.user_id}:{self.wallet_id}:{self.is_active}>'
    
    @property
    def is_expired(self):
        """Check if assignment has expired"""
        return datetime.utcnow() > self.expires_at
    
    @property
    def time_remaining(self):
        """Get time remaining in assignment"""
        if self.is_expired:
            return timedelta(0)
        return self.expires_at - datetime.utcnow()
    
    def complete_assignment(self, actual_amount=None):
        """Mark assignment as completed"""
        self.is_active = False
        self.completed_at = datetime.utcnow()
        self.transaction_detected = True
        
        if actual_amount:
            self.actual_amount = actual_amount
        
        # Release the wallet
        self.wallet.status = WalletStatus.AVAILABLE
        
        # Update wallet usage statistics
        if actual_amount:
            self.wallet.update_usage_stats(actual_amount)
    
    def cancel_assignment(self, reason=None):
        """Cancel the assignment"""
        self.is_active = False
        self.cancelled_at = datetime.utcnow()
        self.cancellation_reason = reason
        
        # Release the wallet
        self.wallet.status = WalletStatus.AVAILABLE
    
    def extend_assignment(self, additional_minutes=15):
        """Extend the assignment duration"""
        if self.is_active and not self.is_expired:
            self.expires_at += timedelta(minutes=additional_minutes)
            self.updated_at = datetime.utcnow()
            return True
        return False
    
    @staticmethod
    def get_active_assignments():
        """Get all active wallet assignments"""
        return WalletAssignment.query.filter_by(is_active=True).all()
    
    @staticmethod
    def get_expired_assignments():
        """Get all expired but still active assignments"""
        now = datetime.utcnow()
        return WalletAssignment.query.filter(
            WalletAssignment.is_active == True,
            WalletAssignment.expires_at < now
        ).all()
    
    @staticmethod
    def cleanup_expired_assignments():
        """Clean up expired assignments (enhanced with Rupal pattern)"""
        try:
            # Get expired assignments with locking
            expired_assignments = (WalletAssignment.query
                                 .filter(WalletAssignment.is_active == True,
                                        WalletAssignment.expires_at < datetime.utcnow())
                                 .with_for_update()
                                 .all())

            cleaned_count = 0
            for assignment in expired_assignments:
                # Force release wallet (critical for pool management)
                assignment.is_active = False
                assignment.cancelled_at = datetime.utcnow()
                assignment.cancellation_reason = "Cleanup - assignment expired"
                assignment.wallet.status = WalletStatus.AVAILABLE
                cleaned_count += 1

            # Additional cleanup: Find wallets stuck in IN_USE without active assignments
            stuck_wallets = (PooledWallet.query
                           .filter(PooledWallet.status == WalletStatus.IN_USE)
                           .filter(~PooledWallet.assignments.any(WalletAssignment.is_active == True))
                           .all())

            for wallet in stuck_wallets:
                wallet.status = WalletStatus.AVAILABLE
                cleaned_count += 1

            if cleaned_count > 0:
                db.session.commit()

            return cleaned_count

        except Exception as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def get_user_assignment_history(user_id, limit=10):
        """Get assignment history for a user"""
        return WalletAssignment.query.filter_by(user_id=user_id).order_by(
            WalletAssignment.created_at.desc()
        ).limit(limit).all()
    
    @staticmethod
    def get_assignment_statistics():
        """Get assignment statistics"""
        total_assignments = WalletAssignment.query.count()
        active_assignments = WalletAssignment.query.filter_by(is_active=True).count()
        completed_assignments = WalletAssignment.query.filter(
            WalletAssignment.completed_at.isnot(None)
        ).count()
        cancelled_assignments = WalletAssignment.query.filter(
            WalletAssignment.cancelled_at.isnot(None)
        ).count()
        
        # Calculate success rate
        total_finished = completed_assignments + cancelled_assignments
        success_rate = (completed_assignments / total_finished * 100) if total_finished > 0 else 0
        
        return {
            'total_assignments': total_assignments,
            'active_assignments': active_assignments,
            'completed_assignments': completed_assignments,
            'cancelled_assignments': cancelled_assignments,
            'success_rate': success_rate
        }
    
    def to_dict(self, include_wallet_info=False):
        """Convert assignment to dictionary"""
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'wallet_id': self.wallet_id,
            'assigned_at': self.assigned_at.isoformat() if self.assigned_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_active': self.is_active,
            'is_expired': self.is_expired,
            'time_remaining_seconds': int(self.time_remaining.total_seconds()),
            'expected_amount': float(self.expected_amount) if self.expected_amount else None,
            'actual_amount': float(self.actual_amount) if self.actual_amount else None,
            'transaction_detected': self.transaction_detected,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'cancelled_at': self.cancelled_at.isoformat() if self.cancelled_at else None,
            'cancellation_reason': self.cancellation_reason
        }
        
        if include_wallet_info and self.wallet:
            data['wallet'] = {
                'address': self.wallet.address,
                'network': self.wallet.network,
                'status': self.wallet.status.value
            }
        
        return data
