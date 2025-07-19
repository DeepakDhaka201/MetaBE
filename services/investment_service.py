"""
Investment Service
Handles investment return calculations, status updates, and automated processing
"""

from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy import and_, or_
import logging

from models import db, User, Wallet, Income
from models.investment import (
    InvestmentPackage, UserInvestment, InvestmentReturn, 
    InvestmentStatus, ReturnStatus, PackageStatus
)

logger = logging.getLogger(__name__)


class InvestmentService:
    """Service class for investment operations"""
    
    @staticmethod
    def calculate_daily_investment_returns():
        """Calculate and distribute daily returns for all eligible investments"""
        
        logger.info("Starting daily investment return calculation...")
        
        try:
            today = date.today()
            total_processed = 0
            total_amount = Decimal('0')
            
            # Get investments eligible for returns today
            eligible_investments = InvestmentService._get_eligible_investments(today)
            
            logger.info(f"Found {len(eligible_investments)} investments eligible for returns")
            
            for investment in eligible_investments:
                try:
                    # Calculate return amount
                    return_amount = InvestmentService._calculate_daily_return(investment, today)
                    
                    if return_amount > 0:
                        # Process the return
                        success = InvestmentService._process_investment_return(
                            investment, return_amount, today
                        )
                        
                        if success:
                            total_processed += 1
                            total_amount += return_amount
                            logger.debug(f"Processed return for investment {investment.id}: ${return_amount}")
                        else:
                            logger.error(f"Failed to process return for investment {investment.id}")
                    
                except Exception as e:
                    logger.error(f"Error processing investment {investment.id}: {str(e)}")
                    continue
            
            # Update investment statuses
            InvestmentService._update_investment_statuses()
            
            logger.info(f"Daily return calculation completed. Processed: {total_processed} investments, Total: ${total_amount}")
            
            return {
                'success': True,
                'processed_count': total_processed,
                'total_amount': float(total_amount),
                'date': today.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in daily return calculation: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def _get_eligible_investments(calculation_date):
        """Get investments eligible for returns on the given date"""
        
        return UserInvestment.query.filter(
            and_(
                # Investment must be active
                UserInvestment.status == InvestmentStatus.ACTIVE,
                # Returns must have started
                UserInvestment.returns_start_date <= calculation_date,
                # Investment must not be matured
                UserInvestment.maturity_date > calculation_date,
                # Must not have received return today already
                or_(
                    UserInvestment.last_return_date.is_(None),
                    UserInvestment.last_return_date < calculation_date
                )
            )
        ).all()
    
    @staticmethod
    def _calculate_daily_return(investment, calculation_date):
        """Calculate daily return amount for an investment"""

        package = investment.package

        # CRITICAL: Validate package data
        if not package:
            logger.error(f"Investment {investment.id} has no associated package")
            return 0

        if package.duration_days <= 0:
            logger.error(f"Package {package.id} has invalid duration: {package.duration_days}")
            return 0

        if package.total_return_percentage < 0:
            logger.error(f"Package {package.id} has negative return percentage: {package.total_return_percentage}")
            return 0

        # Calculate total return amount
        total_return = investment.amount_invested * (package.total_return_percentage / 100)

        # Calculate daily return (spread over duration)
        daily_return = total_return / package.duration_days

        # Ensure we don't exceed total expected return
        remaining_return = investment.expected_total_return - investment.total_returns_paid

        # CRITICAL: Ensure positive values only
        calculated_return = min(daily_return, remaining_return)
        return max(0, calculated_return)  # Never return negative
    
    @staticmethod
    def _process_investment_return(investment, return_amount, return_date):
        """Process a single investment return"""
        
        try:
            # Get user's gain wallet (total_gain)
            gain_wallet = Wallet.query.filter_by(
                user_id=investment.user_id,
                wallet_type='total_gain'
            ).first()

            if not gain_wallet:
                # Create gain wallet if it doesn't exist
                gain_wallet = Wallet(
                    user_id=investment.user_id,
                    wallet_type='total_gain',
                    balance=0
                )
                db.session.add(gain_wallet)
                db.session.flush()
            
            # Add return to wallet
            gain_wallet.add_balance(
                return_amount, 
                f"Investment return - {investment.package.name}"
            )
            
            # Create income record
            Income.create_bonus_income(
                user_id=investment.user_id,
                amount=return_amount,
                bonus_type='Self Investment',
                description=f"Daily return from {investment.package.name}"
            )
            
            # Update investment tracking
            investment.total_returns_paid += return_amount
            investment.last_return_date = return_date
            
            # Calculate days since returns started
            days_since_start = (return_date - investment.returns_start_date).days + 1
            
            # Create return log
            investment_return = InvestmentReturn(
                investment_id=investment.id,
                return_date=return_date,
                return_amount=return_amount,
                days_since_start=days_since_start,
                status=ReturnStatus.PAID,
                processed_at=datetime.utcnow()
            )
            
            db.session.add(investment_return)
            db.session.commit()
            
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error processing return for investment {investment.id}: {str(e)}")
            return False
    
    @staticmethod
    def _update_investment_statuses():
        """Update investment statuses based on current date"""
        
        today = date.today()
        
        # Update active investments to matured if maturity date has passed
        active_investments = UserInvestment.query.filter(
            UserInvestment.status == InvestmentStatus.ACTIVE,
            UserInvestment.maturity_date <= today
        ).all()
        
        for investment in active_investments:
            investment.status = InvestmentStatus.MATURED
            logger.info(f"Investment {investment.id} status updated to MATURED")
        
        if active_investments:
            db.session.commit()
    
    @staticmethod
    def get_user_investment_summary(user_id):
        """Get investment summary for a user"""
        
        try:
            # Get all user investments
            investments = UserInvestment.query.filter_by(user_id=user_id).all()
            
            # Calculate summary statistics
            summary = {
                'total_investments': len(investments),
                'total_invested': sum(float(inv.amount_invested) for inv in investments),
                'total_returns_earned': sum(float(inv.total_returns_paid) for inv in investments),
                'active_investments': len([inv for inv in investments if inv.status == InvestmentStatus.ACTIVE]),
                'matured_investments': len([inv for inv in investments if inv.status == InvestmentStatus.MATURED]),
                'expected_total_returns': sum(float(inv.expected_total_return) for inv in investments),
                'returns_remaining': sum(float(inv.returns_remaining) for inv in investments)
            }
            
            # Calculate ROI
            if summary['total_invested'] > 0:
                summary['roi_percentage'] = (summary['total_returns_earned'] / summary['total_invested']) * 100
            else:
                summary['roi_percentage'] = 0
            
            # Get gain wallet balance (total gains)
            gain_wallet = Wallet.query.filter_by(
                user_id=user_id,
                wallet_type='total_gain'
            ).first()
            
            summary['total_gain_balance'] = float(gain_wallet.balance) if gain_wallet else 0
            
            return summary
            
        except Exception as e:
            logger.error(f"Error calculating investment summary for user {user_id}: {str(e)}")
            return None
    
    @staticmethod
    def manual_distribute_returns(investment_id, amount, admin_user_id=None):
        """Manually distribute returns for a specific investment (admin function)"""
        
        try:
            investment = UserInvestment.query.get(investment_id)
            if not investment:
                return {'success': False, 'message': 'Investment not found'}
            
            if amount <= 0:
                return {'success': False, 'message': 'Amount must be greater than 0'}
            
            # Check if amount exceeds remaining returns
            remaining = investment.returns_remaining
            if amount > remaining:
                return {
                    'success': False, 
                    'message': f'Amount exceeds remaining returns (${remaining})'
                }
            
            # Process the return
            success = InvestmentService._process_investment_return(
                investment, Decimal(str(amount)), date.today()
            )
            
            if success:
                return {
                    'success': True,
                    'message': f'Successfully distributed ${amount} to user {investment.user_id}',
                    'investment_id': investment_id,
                    'amount': float(amount)
                }
            else:
                return {'success': False, 'message': 'Failed to process return'}
                
        except Exception as e:
            logger.error(f"Error in manual return distribution: {str(e)}")
            return {'success': False, 'message': str(e)}

    @staticmethod
    def settle_matured_investment(investment_id, settlement_option='available_fund', settlement_fee_percent=0, admin_user_id=None):
        """Settle a matured investment - return principal to user"""

        try:
            investment = UserInvestment.query.get(investment_id)
            if not investment:
                return {'success': False, 'message': 'Investment not found'}

            if investment.status != InvestmentStatus.MATURED:
                return {'success': False, 'message': 'Investment is not matured yet'}

            # Calculate settlement amounts
            principal_amount = investment.amount_invested
            settlement_fee = (principal_amount * settlement_fee_percent / 100) if settlement_fee_percent > 0 else 0
            net_principal = principal_amount - settlement_fee

            # Get user wallets
            from models.wallet import Wallet

            # Since total_investment is now calculated from UserInvestment records,
            # we don't need to check a separate investment wallet balance
            # The investment settlement just moves money to available_fund if requested

            # Destination wallet based on settlement option
            if settlement_option == 'available_fund':
                dest_wallet = Wallet.query.filter_by(
                    user_id=investment.user_id,
                    wallet_type='available_fund'
                ).first()

                if not dest_wallet:
                    # Create available_fund wallet if missing
                    dest_wallet = Wallet(
                        user_id=investment.user_id,
                        wallet_type='available_fund',
                        balance=0
                    )
                    db.session.add(dest_wallet)
                    db.session.flush()

                # Transfer principal from total_investment to available_fund
                # Note: total_investment is now calculated, so we just add to available_fund
                dest_wallet.balance += net_principal

                settlement_description = f"Investment settlement - {investment.package.name}"

            elif settlement_option == 'keep_invested':
                # Keep invested (no transfer needed, investment stays in UserInvestment records)
                settlement_description = f"Investment settlement (kept invested) - {investment.package.name}"
                net_principal = principal_amount  # No actual transfer

            else:
                return {'success': False, 'message': 'Invalid settlement option'}

            # Update investment status to settled
            investment.status = InvestmentStatus.CANCELLED  # Use CANCELLED to indicate settled

            # Note: total_investment is now calculated from UserInvestment records,
            # so no manual update needed - it will be calculated automatically

            db.session.commit()

            logger.info(f"Investment {investment_id} settled successfully. Principal: ${net_principal}, Fee: ${settlement_fee}")

            return {
                'success': True,
                'message': 'Investment settled successfully',
                'principal_returned': float(net_principal),
                'settlement_fee': float(settlement_fee),
                'settlement_option': settlement_option
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error settling investment {investment_id}: {str(e)}")
            return {'success': False, 'message': str(e)}

    @staticmethod
    def force_mature_investment(investment_id, admin_user_id=None):
        """Force mature an active investment (admin override)"""

        try:
            investment = UserInvestment.query.get(investment_id)
            if not investment:
                return {'success': False, 'message': 'Investment not found'}

            if investment.status != InvestmentStatus.ACTIVE:
                return {'success': False, 'message': 'Investment is not active'}

            # Update status to matured
            investment.status = InvestmentStatus.MATURED

            db.session.commit()

            logger.info(f"Investment {investment_id} force matured by admin {admin_user_id}")

            return {'success': True, 'message': 'Investment force matured successfully'}

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error force maturing investment {investment_id}: {str(e)}")
            return {'success': False, 'message': str(e)}

    @staticmethod
    def get_investment_analytics():
        """Get system-wide investment analytics"""
        
        try:
            # Package statistics
            packages = InvestmentPackage.query.all()
            active_packages = [p for p in packages if p.status == PackageStatus.ACTIVE]
            
            # Investment statistics
            all_investments = UserInvestment.query.all()
            active_investments = [inv for inv in all_investments if inv.status == InvestmentStatus.ACTIVE]
            
            # Return statistics
            all_returns = InvestmentReturn.query.all()
            today_returns = InvestmentReturn.query.filter_by(return_date=date.today()).all()
            
            analytics = {
                'packages': {
                    'total': len(packages),
                    'active': len(active_packages),
                    'total_capacity': sum(float(p.max_amount or 0) for p in active_packages)
                },
                'investments': {
                    'total': len(all_investments),
                    'active': len(active_investments),
                    'total_invested': sum(float(inv.amount_invested) for inv in all_investments),
                    'total_returns_paid': sum(float(inv.total_returns_paid) for inv in all_investments)
                },
                'returns': {
                    'total_distributions': len(all_returns),
                    'today_distributions': len(today_returns),
                    'today_amount': sum(float(ret.return_amount) for ret in today_returns),
                    'total_amount': sum(float(ret.return_amount) for ret in all_returns)
                },
                'users': {
                    'total_investors': len(set(inv.user_id for inv in all_investments)),
                    'active_investors': len(set(inv.user_id for inv in active_investments))
                }
            }
            
            return analytics
            
        except Exception as e:
            logger.error(f"Error calculating investment analytics: {str(e)}")
            return None
