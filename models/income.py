"""
Income Model for MetaX Coin Backend
Tracks all types of income including referral commissions, staking rewards, and bonuses
"""

from datetime import datetime
from enum import Enum
from sqlalchemy import func

from . import db


class IncomeType(Enum):
    """Income type enumeration"""
    DIRECT_REFERRAL = 'Direct Referral'
    LEVEL_BONUS = 'Level Bonus'
    STAKING_REWARD = 'Staking Reward'
    SELF_INVESTMENT = 'Self Investment'
    LIFETIME_REWARD = 'Lifetime Reward'
    BONUS = 'Bonus'
    PROMOTION_BONUS = 'Promotion Bonus'
    LEADERSHIP_BONUS = 'Leadership Bonus'


class IncomeStatus(Enum):
    """Income status enumeration"""
    PENDING = 'pending'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'


class Income(db.Model):
    """Income model for tracking all types of earnings"""
    
    __tablename__ = 'incomes'
    
    # Primary fields
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    income_type = db.Column(db.Enum(IncomeType), nullable=False, index=True)
    
    # Amount and details
    amount = db.Column(db.Numeric(20, 8), nullable=False)
    description = db.Column(db.Text)
    
    # Source information
    from_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    level = db.Column(db.Integer)  # For level bonuses
    transaction_id = db.Column(db.String(50))  # Reference to related transaction
    
    # Status and processing
    status = db.Column(db.Enum(IncomeStatus), default=IncomeStatus.COMPLETED, nullable=False)
    processed_at = db.Column(db.DateTime)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    from_user = db.relationship('User', foreign_keys=[from_user_id], backref='generated_incomes')
    
    # Indexes
    __table_args__ = (
        db.Index('idx_user_income_type', 'user_id', 'income_type'),
        db.Index('idx_user_created_at', 'user_id', 'created_at'),
        db.Index('idx_income_type_created_at', 'income_type', 'created_at'),
    )
    
    def __repr__(self):
        return f'<Income {self.user_id}:{self.income_type.value}:{self.amount}>'
    
    @staticmethod
    def create_referral_income(user_id, from_user_id, amount, level, description=None):
        """Create referral commission income"""
        income_type = IncomeType.DIRECT_REFERRAL if level == 1 else IncomeType.LEVEL_BONUS
        
        income = Income(
            user_id=user_id,
            income_type=income_type,
            amount=amount,
            from_user_id=from_user_id,
            level=level,
            description=description or f"Level {level} referral commission",
            status=IncomeStatus.COMPLETED,
            processed_at=datetime.utcnow()
        )
        
        db.session.add(income)
        return income
    
    @staticmethod
    def create_staking_income(user_id, amount, description=None):
        """Create staking reward income"""
        income = Income(
            user_id=user_id,
            income_type=IncomeType.STAKING_REWARD,
            amount=amount,
            description=description or "Daily staking reward",
            status=IncomeStatus.COMPLETED,
            processed_at=datetime.utcnow()
        )
        
        db.session.add(income)
        return income
    
    @staticmethod
    def create_bonus_income(user_id, amount, bonus_type='Bonus', description=None):
        """Create bonus income"""
        # Map bonus type to income type
        income_type_map = {
            'Bonus': IncomeType.BONUS,
            'Promotion Bonus': IncomeType.PROMOTION_BONUS,
            'Leadership Bonus': IncomeType.LEADERSHIP_BONUS,
            'Lifetime Reward': IncomeType.LIFETIME_REWARD
        }
        
        income_type = income_type_map.get(bonus_type, IncomeType.BONUS)
        
        income = Income(
            user_id=user_id,
            income_type=income_type,
            amount=amount,
            description=description or f"{bonus_type} payment",
            status=IncomeStatus.COMPLETED,
            processed_at=datetime.utcnow()
        )
        
        db.session.add(income)
        return income
    
    @staticmethod
    def get_user_income_summary(user_id, start_date=None, end_date=None):
        """Get income summary for a user"""
        query = Income.query.filter_by(user_id=user_id, status=IncomeStatus.COMPLETED)
        
        if start_date:
            query = query.filter(Income.created_at >= start_date)
        if end_date:
            query = query.filter(Income.created_at <= end_date)
        
        incomes = query.all()
        
        summary = {
            'total_income': 0.0,
            'by_type': {},
            'by_level': {},
            'recent_incomes': []
        }
        
        # Calculate totals by type
        for income in incomes:
            amount = float(income.amount)
            summary['total_income'] += amount
            
            income_type = income.income_type.value
            if income_type not in summary['by_type']:
                summary['by_type'][income_type] = 0.0
            summary['by_type'][income_type] += amount
            
            # Track by level for referral incomes
            if income.level:
                level_key = f'level_{income.level}'
                if level_key not in summary['by_level']:
                    summary['by_level'][level_key] = 0.0
                summary['by_level'][level_key] += amount
        
        # Get recent incomes (last 10)
        recent_incomes = Income.query.filter_by(
            user_id=user_id, 
            status=IncomeStatus.COMPLETED
        ).order_by(Income.created_at.desc()).limit(10).all()
        
        summary['recent_incomes'] = [income.to_dict() for income in recent_incomes]
        
        return summary
    
    @staticmethod
    def get_income_history(user_id, income_type=None, limit=50, offset=0):
        """Get income history for a user"""
        query = Income.query.filter_by(user_id=user_id)
        
        if income_type:
            if isinstance(income_type, str):
                # Convert string to enum
                income_type_enum = None
                for enum_val in IncomeType:
                    if enum_val.value == income_type:
                        income_type_enum = enum_val
                        break
                if income_type_enum:
                    query = query.filter_by(income_type=income_type_enum)
            else:
                query = query.filter_by(income_type=income_type)
        
        return query.order_by(Income.created_at.desc()).offset(offset).limit(limit).all()
    
    @staticmethod
    def get_total_income_by_type(user_id):
        """Get total income grouped by type"""
        results = db.session.query(
            Income.income_type,
            func.sum(Income.amount).label('total_amount'),
            func.count(Income.id).label('count')
        ).filter_by(
            user_id=user_id,
            status=IncomeStatus.COMPLETED
        ).group_by(Income.income_type).all()
        
        income_by_type = {}
        for result in results:
            income_by_type[result.income_type.value] = {
                'total_amount': float(result.total_amount),
                'count': result.count
            }
        
        return income_by_type
    
    @staticmethod
    def get_monthly_income_stats(user_id, year=None, month=None):
        """Get monthly income statistics"""
        if not year:
            year = datetime.utcnow().year
        if not month:
            month = datetime.utcnow().month
        
        # Get start and end of month
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
        
        incomes = Income.query.filter(
            Income.user_id == user_id,
            Income.status == IncomeStatus.COMPLETED,
            Income.created_at >= start_date,
            Income.created_at < end_date
        ).all()
        
        stats = {
            'total_income': sum(float(income.amount) for income in incomes),
            'income_count': len(incomes),
            'by_type': {},
            'daily_breakdown': {}
        }
        
        # Group by type
        for income in incomes:
            income_type = income.income_type.value
            if income_type not in stats['by_type']:
                stats['by_type'][income_type] = 0.0
            stats['by_type'][income_type] += float(income.amount)
            
            # Daily breakdown
            day = income.created_at.day
            if day not in stats['daily_breakdown']:
                stats['daily_breakdown'][day] = 0.0
            stats['daily_breakdown'][day] += float(income.amount)
        
        return stats
    
    @staticmethod
    def get_top_earners(income_type=None, limit=10, start_date=None, end_date=None):
        """Get top earners by income type"""
        query = db.session.query(
            Income.user_id,
            func.sum(Income.amount).label('total_income'),
            func.count(Income.id).label('income_count')
        ).filter_by(status=IncomeStatus.COMPLETED)
        
        if income_type:
            query = query.filter_by(income_type=income_type)
        
        if start_date:
            query = query.filter(Income.created_at >= start_date)
        if end_date:
            query = query.filter(Income.created_at <= end_date)
        
        results = query.group_by(Income.user_id).order_by(
            func.sum(Income.amount).desc()
        ).limit(limit).all()
        
        top_earners = []
        for result in results:
            from .user import User
            user = User.query.get(result.user_id)
            if user:
                top_earners.append({
                    'user_id': user.id,
                    'username': user.username,
                    'full_name': user.get_full_name(),
                    'total_income': float(result.total_income),
                    'income_count': result.income_count
                })
        
        return top_earners
    
    def to_dict(self, include_user_info=False):
        """Convert income to dictionary"""
        data = {
            'id': self.id,
            'income_type': self.income_type.value,
            'amount': float(self.amount),
            'description': self.description,
            'level': self.level,
            'transaction_id': self.transaction_id,
            'status': self.status.value,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None
        }
        
        if include_user_info and self.from_user_id:
            from .user import User
            from_user = User.query.get(self.from_user_id)
            if from_user:
                data['from_user'] = {
                    'id': from_user.id,
                    'username': from_user.username,
                    'full_name': from_user.get_full_name()
                }
        
        return data
