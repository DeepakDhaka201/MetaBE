"""
Investment Models for MetaX Coin Backend
Handles investment packages, user investments, and return tracking
"""

from datetime import datetime, date, timedelta
from enum import Enum
from decimal import Decimal
from sqlalchemy import func

from . import db


class PackageStatus(Enum):
    """Investment package status enumeration"""
    ACTIVE = 'active'
    CANCELLED = 'cancelled'


class InvestmentStatus(Enum):
    """User investment status enumeration"""
    ACTIVE = 'active'
    MATURED = 'matured'
    CANCELLED = 'cancelled'


class ReturnStatus(Enum):
    """Investment return status enumeration"""
    PAID = 'paid'
    FAILED = 'failed'


class InvestmentPackage(db.Model):
    """Investment packages/plans available to users"""
    
    __tablename__ = 'investment_packages'
    
    # Primary fields
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    
    # Investment terms
    min_amount = db.Column(db.Numeric(20, 8), nullable=False)
    max_amount = db.Column(db.Numeric(20, 8))
    
    # Return calculation
    total_return_percentage = db.Column(db.Float, nullable=False)  # 25.0 = 25%
    duration_days = db.Column(db.Integer, nullable=False)  # 180 days
    
    # Important dates
    end_date = db.Column(db.Date)     # When package stops accepting investments

    # Status and metadata
    status = db.Column(db.Enum(PackageStatus), default=PackageStatus.ACTIVE, nullable=False)
    is_featured = db.Column(db.Boolean, default=False)
    sort_order = db.Column(db.Integer, default=0)
    
    # Admin tracking
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    investments = db.relationship('UserInvestment', backref='package', lazy='dynamic')
    
    def __repr__(self):
        return f'<InvestmentPackage {self.name}>'
    
    @property
    def is_available_for_investment(self):
        """Check if package is available for new investments"""
        today = date.today()
        return (
            self.status == PackageStatus.ACTIVE and
            (self.end_date is None or self.end_date >= today)
        )
    
    @property
    def daily_return_rate(self):
        """Calculate daily return rate"""
        if self.duration_days > 0:
            return self.total_return_percentage / self.duration_days
        return 0
    
    @property
    def total_invested(self):
        """Get total amount invested in this package"""
        return db.session.query(func.sum(UserInvestment.amount_invested)).filter(
            UserInvestment.package_id == self.id,
            UserInvestment.status == InvestmentStatus.ACTIVE
        ).scalar() or 0
    
    @property
    def total_investors(self):
        """Get total number of investors in this package"""
        return self.investments.filter(
            UserInvestment.status == InvestmentStatus.ACTIVE
        ).count()
    
    def calculate_daily_return(self, investment_amount):
        """Calculate daily return for a given investment amount"""
        total_return = investment_amount * (self.total_return_percentage / 100)
        return total_return / self.duration_days if self.duration_days > 0 else 0
    
    def to_dict(self, include_stats=False):
        """Convert package to dictionary"""
        data = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'min_amount': float(self.min_amount),
            'max_amount': float(self.max_amount) if self.max_amount else None,
            'total_return_percentage': self.total_return_percentage,
            'duration_days': self.duration_days,
            'daily_return_rate': self.daily_return_rate,

            'end_date': self.end_date.isoformat() if self.end_date else None,
            'status': self.status.value,
            'is_featured': self.is_featured,
            'is_available': self.is_available_for_investment,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
        
        if include_stats:
            data.update({
                'total_invested': float(self.total_invested),
                'total_investors': self.total_investors
            })
        
        return data
    
    @staticmethod
    def get_available_packages():
        """Get all packages available for investment"""
        return InvestmentPackage.query.filter(
            InvestmentPackage.status == PackageStatus.ACTIVE,
            db.or_(
                InvestmentPackage.end_date.is_(None),
                InvestmentPackage.end_date >= date.today()
            )
        ).order_by(InvestmentPackage.sort_order, InvestmentPackage.created_at.desc()).all()


class UserInvestment(db.Model):
    """Individual user investments in packages"""
    
    __tablename__ = 'user_investments'
    
    # Primary fields
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    package_id = db.Column(db.Integer, db.ForeignKey('investment_packages.id'), nullable=False, index=True)
    
    # Investment details
    amount_invested = db.Column(db.Numeric(20, 8), nullable=False)
    investment_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Calculated dates
    returns_start_date = db.Column(db.Date)  # When returns begin (package launch date)
    maturity_date = db.Column(db.Date)       # When investment matures
    
    # Return tracking
    total_returns_paid = db.Column(db.Numeric(20, 8), default=0, nullable=False)
    last_return_date = db.Column(db.Date)
    
    # Status
    status = db.Column(db.Enum(InvestmentStatus), default=InvestmentStatus.ACTIVE, nullable=False, index=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='user_investments')
    returns = db.relationship('InvestmentReturn', backref='investment', lazy='dynamic', cascade='all, delete-orphan')
    
    # Indexes
    __table_args__ = (
        db.Index('idx_user_status', 'user_id', 'status'),
        db.Index('idx_package_status', 'package_id', 'status'),
        db.Index('idx_returns_date', 'returns_start_date', 'status'),
    )
    
    def __repr__(self):
        return f'<UserInvestment {self.user_id}:{self.package_id}:{self.amount_invested}>'
    
    @property
    def days_since_investment(self):
        """Get days since investment was made"""
        return (datetime.utcnow().date() - self.investment_date.date()).days
    
    @property
    def days_since_returns_started(self):
        """Get days since returns started"""
        if not self.returns_start_date:
            return 0
        return max(0, (datetime.utcnow().date() - self.returns_start_date).days)
    
    @property
    def expected_total_return(self):
        """Calculate expected total return"""
        return self.amount_invested * (self.package.total_return_percentage / 100)
    
    @property
    def expected_daily_return(self):
        """Calculate expected daily return"""
        return self.package.calculate_daily_return(self.amount_invested)
    
    @property
    def returns_remaining(self):
        """Calculate remaining returns to be paid"""
        return max(0, self.expected_total_return - self.total_returns_paid)
    
    @property
    def is_eligible_for_return_today(self):
        """Check if investment is eligible for return today"""
        today = date.today()
        return (
            self.status == InvestmentStatus.ACTIVE and
            self.returns_start_date and
            self.returns_start_date <= today and
            self.maturity_date and
            self.maturity_date > today and
            (self.last_return_date is None or self.last_return_date < today)
        )
    
    def calculate_return_for_date(self, calculation_date):
        """Calculate return amount for a specific date"""
        if not self.returns_start_date or calculation_date < self.returns_start_date:
            return 0
        
        if self.maturity_date and calculation_date >= self.maturity_date:
            return 0
        
        return self.expected_daily_return
    
    def update_status_based_on_dates(self):
        """Update investment status based on current date"""
        today = date.today()

        # Only transition from ACTIVE to MATURED
        if self.status == InvestmentStatus.ACTIVE:
            if self.maturity_date and today >= self.maturity_date:
                self.status = InvestmentStatus.MATURED
    
    def to_dict(self, include_package=False):
        """Convert investment to dictionary"""
        data = {
            'id': self.id,
            'package_id': self.package_id,
            'amount_invested': float(self.amount_invested),
            'investment_date': self.investment_date.isoformat() if self.investment_date else None,
            'returns_start_date': self.returns_start_date.isoformat() if self.returns_start_date else None,
            'maturity_date': self.maturity_date.isoformat() if self.maturity_date else None,
            'total_returns_paid': float(self.total_returns_paid),
            'last_return_date': self.last_return_date.isoformat() if self.last_return_date else None,
            'status': self.status.value,
            'days_since_investment': self.days_since_investment,
            'days_since_returns_started': self.days_since_returns_started,
            'expected_total_return': float(self.expected_total_return),
            'expected_daily_return': float(self.expected_daily_return),
            'returns_remaining': float(self.returns_remaining),
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
        
        if include_package:
            data['package'] = self.package.to_dict()
        
        return data


class InvestmentReturn(db.Model):
    """Log of daily returns paid to users"""
    
    __tablename__ = 'investment_returns'
    
    # Primary fields
    id = db.Column(db.Integer, primary_key=True)
    investment_id = db.Column(db.Integer, db.ForeignKey('user_investments.id'), nullable=False, index=True)
    
    # Return details
    return_date = db.Column(db.Date, nullable=False, index=True)
    return_amount = db.Column(db.Numeric(20, 8), nullable=False)
    days_since_start = db.Column(db.Integer)  # Days since returns started
    
    # Status and metadata
    status = db.Column(db.Enum(ReturnStatus), default=ReturnStatus.PAID, nullable=False)
    processed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Indexes
    __table_args__ = (
        db.Index('idx_investment_date', 'investment_id', 'return_date'),
        db.Index('idx_date_status', 'return_date', 'status'),
    )
    
    def __repr__(self):
        return f'<InvestmentReturn {self.investment_id}:{self.return_date}:{self.return_amount}>'
    
    def to_dict(self):
        """Convert return to dictionary"""
        return {
            'id': self.id,
            'investment_id': self.investment_id,
            'return_date': self.return_date.isoformat() if self.return_date else None,
            'return_amount': float(self.return_amount),
            'days_since_start': self.days_since_start,
            'status': self.status.value,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @staticmethod
    def get_user_returns(user_id, start_date=None, end_date=None, limit=50):
        """Get investment returns for a user"""
        query = db.session.query(InvestmentReturn).join(UserInvestment).filter(
            UserInvestment.user_id == user_id
        )
        
        if start_date:
            query = query.filter(InvestmentReturn.return_date >= start_date)
        if end_date:
            query = query.filter(InvestmentReturn.return_date <= end_date)
        
        return query.order_by(InvestmentReturn.return_date.desc()).limit(limit).all()
