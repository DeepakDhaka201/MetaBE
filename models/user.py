"""
User Model for MetaX Coin Backend
Handles user authentication, profile, and referral relationships
"""

from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func
import secrets
import string

from . import db


class User(db.Model):
    """User model with referral system support"""
    
    __tablename__ = 'users'
    
    # Primary fields
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # Profile information
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    date_of_birth = db.Column(db.Date)
    
    # Referral system
    sponsor_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    referral_code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    
    # Account status
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    
    # Financial tracking
    rank = db.Column(db.String(20), default='Bronze')
    total_investment = db.Column(db.Numeric(20, 8), default=0, nullable=False)
    total_earnings = db.Column(db.Numeric(20, 8), default=0, nullable=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    

    
    # Relationships
    sponsor = db.relationship('User', remote_side=[id], backref='referrals')
    wallets = db.relationship('Wallet', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    transactions = db.relationship('Transaction', backref='user', lazy='dynamic')
    incomes = db.relationship('Income', foreign_keys='Income.user_id', backref='user', lazy='dynamic')
    wallet_assignments = db.relationship('WalletAssignment', backref='user', lazy='dynamic')
    
    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if not self.referral_code:
            self.referral_code = self.generate_referral_code()
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    @staticmethod
    def generate_referral_code(length=8):
        """Generate a unique referral code"""
        while True:
            code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(length))
            if not User.query.filter_by(referral_code=code).first():
                return code
    
    def set_password(self, password):
        """Set password hash"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password against hash"""
        return check_password_hash(self.password_hash, password)
    
    def get_full_name(self):
        """Get user's full name"""
        return f"{self.first_name} {self.last_name}"
    
    def get_referral_link(self):
        """Get user's referral link"""
        return f"https://metaxcoin.cloud/register/{self.referral_code}"
    
    def get_direct_referrals(self):
        """Get direct referrals (level 1)"""
        return User.query.filter_by(sponsor_id=self.id).all()
    
    def get_total_team_size(self, max_level=5):
        """Get total team size up to specified levels"""
        def count_team_recursive(user_id, current_level):
            if current_level > max_level:
                return 0
            
            direct_count = User.query.filter_by(sponsor_id=user_id).count()
            total_count = direct_count
            
            if current_level < max_level:
                direct_referrals = User.query.filter_by(sponsor_id=user_id).all()
                for referral in direct_referrals:
                    total_count += count_team_recursive(referral.id, current_level + 1)
            
            return total_count
        
        return count_team_recursive(self.id, 1)
    
    def get_active_team_size(self, max_level=5):
        """Get active team size up to specified levels"""
        def count_active_team_recursive(user_id, current_level):
            if current_level > max_level:
                return 0

            direct_count = User.query.filter_by(sponsor_id=user_id, is_active=True).count()
            total_count = direct_count

            if current_level < max_level:
                direct_referrals = User.query.filter_by(sponsor_id=user_id, is_active=True).all()
                for referral in direct_referrals:
                    total_count += count_active_team_recursive(referral.id, current_level + 1)

            return total_count

        return count_active_team_recursive(self.id, 1)

    def get_sponsor_info(self):
        """Get sponsor information"""
        if self.sponsor_id and self.sponsor:
            return {
                'sponsor_id': self.sponsor_id,
                'sponsor_username': self.sponsor.username,
                'sponsor_name': self.sponsor.get_full_name(),
                'sponsor_referral_code': self.sponsor.referral_code,
                'referred_by': self.sponsor.username  # For backward compatibility
            }
        return None
    
    def get_wallet_balance(self, wallet_type):
        """Get balance for specific wallet type"""
        from .wallet import Wallet
        wallet = Wallet.query.filter_by(user_id=self.id, wallet_type=wallet_type).first()
        return float(wallet.balance) if wallet else 0.0
    
    def get_total_wallet_balance(self):
        """Get total balance across all wallets"""
        from .wallet import Wallet
        total = db.session.query(func.sum(Wallet.balance)).filter_by(user_id=self.id).scalar()
        return float(total) if total else 0.0

    def get_total_investment(self):
        """Get total investment from UserInvestment records"""
        from .investment import UserInvestment, InvestmentStatus
        total = db.session.query(func.sum(UserInvestment.amount_invested)).filter(
            UserInvestment.user_id == self.id,
            UserInvestment.status.in_([InvestmentStatus.ACTIVE, InvestmentStatus.MATURED])
        ).scalar()
        return float(total) if total else 0.0
    
    def update_rank(self):
        """Update user rank based on total investment"""
        investment = self.get_total_investment()
        
        if investment >= 100000:
            self.rank = 'Diamond'
        elif investment >= 50000:
            self.rank = 'Platinum'
        elif investment >= 25000:
            self.rank = 'Gold'
        elif investment >= 10000:
            self.rank = 'Silver'
        else:
            self.rank = 'Bronze'
    
    def to_dict(self, include_sensitive=False):
        """Convert user to dictionary"""
        data = {
            'id': self.id,
            'username': self.username,
            'email': self.email if include_sensitive else None,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.get_full_name(),
            'referral_code': self.referral_code,
            'referral_link': self.get_referral_link(),
            'is_active': self.is_active,
            'is_verified': self.is_verified,
            'rank': self.rank,
            'total_investment': self.get_total_investment(),
            'total_earnings': float(self.total_earnings),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }

        # Always include sponsor information (not sensitive)
        if self.sponsor_id and self.sponsor:
            data['sponsor_info'] = {
                'sponsor_id': self.sponsor_id,
                'sponsor_username': self.sponsor.username,
                'sponsor_name': self.sponsor.get_full_name(),
                'referred_by': self.sponsor.username  # For backward compatibility
            }
            data['referred_by'] = self.sponsor.username  # For backward compatibility
        else:
            data['sponsor_info'] = None
            data['referred_by'] = None  # For backward compatibility

        if include_sensitive:
            data.update({
                'phone': self.phone,
                'date_of_birth': self.date_of_birth.isoformat() if self.date_of_birth else None,
                'sponsor_id': self.sponsor_id,
                'is_admin': self.is_admin
            })

        return data
