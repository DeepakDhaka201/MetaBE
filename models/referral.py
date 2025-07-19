"""
Referral Model for MetaX Coin Backend
Handles multi-level referral tracking and commission calculations
"""

from datetime import datetime
from decimal import Decimal

from . import db


class Referral(db.Model):
    """Referral model for tracking multi-level referral relationships"""
    
    __tablename__ = 'referrals'
    
    # Primary fields
    id = db.Column(db.Integer, primary_key=True)
    referrer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    referred_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    level = db.Column(db.Integer, nullable=False, index=True)  # 1, 2, 3, 4, 5
    
    # Status and tracking
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    total_commission_earned = db.Column(db.Numeric(20, 8), default=0)
    last_commission_at = db.Column(db.DateTime)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    referrer = db.relationship('User', foreign_keys=[referrer_id], backref='downline_referrals')
    referred = db.relationship('User', foreign_keys=[referred_id], backref='upline_referrals')
    
    # Constraints
    __table_args__ = (
        db.UniqueConstraint('referrer_id', 'referred_id', name='unique_referrer_referred'),
        db.Index('idx_referrer_level', 'referrer_id', 'level'),
        db.Index('idx_referred_level', 'referred_id', 'level'),
    )
    
    def __repr__(self):
        return f'<Referral {self.referrer_id}->{self.referred_id} L{self.level}>'
    
    @staticmethod
    def create_referral_chain(sponsor_id, new_user_id, max_levels=5):
        """Create referral chain when a new user joins"""
        if not sponsor_id:
            return []

        referrals = []
        current_sponsor_id = sponsor_id
        level = 1
        visited_sponsors = set()  # Prevent circular references

        while current_sponsor_id and level <= max_levels:
            # Check for circular reference
            if current_sponsor_id in visited_sponsors:
                break
            visited_sponsors.add(current_sponsor_id)

            # Create referral record
            referral = Referral(
                referrer_id=current_sponsor_id,
                referred_id=new_user_id,
                level=level,
                is_active=True
            )
            referrals.append(referral)
            db.session.add(referral)

            # Find next level sponsor
            from .user import User
            sponsor = User.query.get(current_sponsor_id)
            current_sponsor_id = sponsor.sponsor_id if sponsor else None
            level += 1

        return referrals
    
    @staticmethod
    def get_referral_tree(user_id, max_levels=5):
        """Get complete referral tree for a user"""
        def build_tree_recursive(referrer_id, current_level):
            if current_level > max_levels:
                return []
            
            # Get direct referrals at this level
            direct_referrals = Referral.query.filter_by(
                referrer_id=referrer_id,
                level=1,
                is_active=True
            ).all()
            
            tree_data = []
            for referral in direct_referrals:
                from .user import User
                referred_user = User.query.get(referral.referred_id)
                if referred_user:
                    user_data = {
                        'user_id': referred_user.id,
                        'username': referred_user.username,
                        'full_name': referred_user.get_full_name(),
                        'level': current_level,
                        'is_active': referred_user.is_active,
                        'total_investment': referred_user.get_total_investment(),
                        'joined_at': referred_user.created_at.isoformat(),
                        'commission_earned': float(referral.total_commission_earned),
                        'children': build_tree_recursive(referred_user.id, current_level + 1)
                    }
                    tree_data.append(user_data)
            
            return tree_data
        
        return build_tree_recursive(user_id, 1)
    
    @staticmethod
    def get_level_statistics(user_id, max_levels=5):
        """Get statistics for each referral level"""
        stats = {}
        
        for level in range(1, max_levels + 1):
            referrals = Referral.query.filter_by(
                referrer_id=user_id,
                level=level,
                is_active=True
            ).all()
            
            total_members = len(referrals)
            total_commission = sum(float(r.total_commission_earned) for r in referrals)
            
            # Get active members (users who are still active)
            active_members = 0
            total_investment = 0
            
            for referral in referrals:
                from .user import User
                user = User.query.get(referral.referred_id)
                if user and user.is_active:
                    active_members += 1
                    total_investment += user.get_total_investment()
            
            stats[f'level_{level}'] = {
                'total_members': total_members,
                'active_members': active_members,
                'total_commission': total_commission,
                'total_investment': total_investment,
                'average_investment': total_investment / active_members if active_members > 0 else 0
            }
        
        return stats
    
    @staticmethod
    def calculate_commission(investment_amount, level, commission_rates=None):
        """Calculate commission for a specific level"""
        if not commission_rates:
            # Default commission rates
            commission_rates = {
                1: 10.0,  # 10% for level 1
                2: 5.0,   # 5% for level 2
                3: 3.0,   # 3% for level 3
                4: 2.0,   # 2% for level 4
                5: 1.0    # 1% for level 5
            }
        
        rate = commission_rates.get(level, 0)
        return (Decimal(str(investment_amount)) * Decimal(str(rate))) / 100
    
    @staticmethod
    def distribute_commissions(user_id, investment_amount, commission_rates=None):
        """Distribute commissions up the referral chain"""
        from .user import User
        from .wallet import Wallet
        from .income import Income
        
        # Get all upline referrals for this user
        upline_referrals = Referral.query.filter_by(
            referred_id=user_id,
            is_active=True
        ).all()
        
        commissions_distributed = []
        
        for referral in upline_referrals:
            # Calculate commission for this level
            commission_amount = Referral.calculate_commission(
                investment_amount, 
                referral.level, 
                commission_rates
            )
            
            if commission_amount > 0:
                # Get the referrer
                referrer = User.query.get(referral.referrer_id)
                if referrer and referrer.is_active:
                    # Determine wallet type based on level
                    wallet_type = 'total_referral' if referral.level == 1 else 'level_bonus'
                    
                    # Add commission to referrer's wallet (create if doesn't exist)
                    wallet = Wallet.query.filter_by(
                        user_id=referrer.id,
                        wallet_type=wallet_type
                    ).first()

                    if not wallet:
                        # Create wallet if it doesn't exist
                        wallet = Wallet(
                            user_id=referrer.id,
                            wallet_type=wallet_type,
                            balance=0
                        )
                        db.session.add(wallet)
                        db.session.flush()  # Get wallet ID

                    wallet.add_balance(
                        commission_amount,
                        f"Level {referral.level} commission from {User.query.get(user_id).username}"
                    )

                    # Update referral commission tracking
                    referral.total_commission_earned += commission_amount
                    referral.last_commission_at = datetime.utcnow()

                    # Create income record
                    income = Income(
                        user_id=referrer.id,
                        income_type='Direct Referral' if referral.level == 1 else 'Level Bonus',
                        amount=commission_amount,
                        from_user_id=user_id,
                        level=referral.level,
                        description=f"Level {referral.level} commission from investment"
                    )
                    db.session.add(income)

                    # Update referrer's total earnings
                    referrer.total_earnings += commission_amount

                    commissions_distributed.append({
                        'referrer_id': referrer.id,
                        'level': referral.level,
                        'amount': float(commission_amount),
                        'wallet_type': wallet_type
                    })
        
        return commissions_distributed
    
    @staticmethod
    def get_team_summary(user_id):
        """Get team summary statistics"""
        from .user import User
        
        # Get all downline referrals
        all_referrals = Referral.query.filter_by(
            referrer_id=user_id,
            is_active=True
        ).all()
        
        total_team = len(set(r.referred_id for r in all_referrals))
        direct_referrals = len([r for r in all_referrals if r.level == 1])
        
        # Calculate total commission earned
        total_commission = sum(float(r.total_commission_earned) for r in all_referrals)
        
        # Get active members
        active_members = 0
        total_team_investment = 0
        
        for referral in all_referrals:
            user = User.query.get(referral.referred_id)
            if user and user.is_active:
                active_members += 1
                total_team_investment += user.get_total_investment()
        
        return {
            'total_team': total_team,
            'direct_referrals': direct_referrals,
            'active_members': active_members,
            'total_commission': total_commission,
            'total_team_investment': total_team_investment,
            'level_breakdown': Referral.get_level_statistics(user_id)
        }
    
    def to_dict(self):
        """Convert referral to dictionary"""
        return {
            'id': self.id,
            'referrer_id': self.referrer_id,
            'referred_id': self.referred_id,
            'level': self.level,
            'is_active': self.is_active,
            'total_commission_earned': float(self.total_commission_earned),
            'last_commission_at': self.last_commission_at.isoformat() if self.last_commission_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
