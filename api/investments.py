"""
Investment API Routes
Handles investment package listing, purchase, and user investment management
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, date, timedelta
from decimal import Decimal, InvalidOperation
from sqlalchemy import func

from models import db, User, Wallet, Transaction, Income
from models.transaction import TransactionType
from models.investment import InvestmentPackage, UserInvestment, InvestmentStatus, PackageStatus

# Create blueprint
investments_bp = Blueprint('investments', __name__, url_prefix='/api/investments')


@investments_bp.route('/packages', methods=['GET'])
@jwt_required()
def get_investment_packages():
    """Get all available investment packages"""
    
    try:
        # Get available packages
        packages = InvestmentPackage.get_available_packages()
        
        # Convert to dict with stats
        packages_data = [package.to_dict(include_stats=True) for package in packages]
        
        return jsonify({
            'success': True,
            'packages': packages_data,
            'total': len(packages_data)
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching packages: {str(e)}'
        }), 500


@investments_bp.route('/packages/<int:package_id>', methods=['GET'])
@jwt_required()
def get_package_details(package_id):
    """Get detailed information about a specific package"""
    
    try:
        package = InvestmentPackage.query.get_or_404(package_id)
        
        # Check if user has existing investments in this package
        user_id = get_jwt_identity()
        user_investments = UserInvestment.query.filter_by(
            user_id=user_id,
            package_id=package_id
        ).all()
        
        package_data = package.to_dict(include_stats=True)
        package_data['user_investments'] = [inv.to_dict() for inv in user_investments]
        package_data['user_total_invested'] = sum(float(inv.amount_invested) for inv in user_investments)
        
        return jsonify({
            'success': True,
            'package': package_data
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching package details: {str(e)}'
        }), 500


@investments_bp.route('/purchase', methods=['POST'])
@jwt_required()
def purchase_investment():
    """Purchase an investment package"""
    
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        # Validate input
        if not data:
            return jsonify({
                'success': False,
                'message': 'No data provided'
            }), 400
        
        package_id = data.get('package_id')
        amount = data.get('amount')
        
        if not package_id or not amount:
            return jsonify({
                'success': False,
                'message': 'Package ID and amount are required'
            }), 400
        
        try:
            amount = Decimal(str(amount))
        except (InvalidOperation, ValueError):
            return jsonify({
                'success': False,
                'message': 'Invalid amount format'
            }), 400
        
        if amount <= 0:
            return jsonify({
                'success': False,
                'message': 'Amount must be greater than 0'
            }), 400
        
        # Get package and validate
        package = InvestmentPackage.query.get(package_id)
        if not package:
            return jsonify({
                'success': False,
                'message': 'Investment package not found'
            }), 404
        
        if not package.is_available_for_investment:
            return jsonify({
                'success': False,
                'message': 'Investment package is not available'
            }), 400

        # CRITICAL: Check if package is still accepting investments
        if package.end_date and package.end_date < date.today():
            return jsonify({
                'success': False,
                'message': 'Package is no longer accepting new investments'
            }), 400
        
        # Validate amount limits
        if amount < package.min_amount:
            return jsonify({
                'success': False,
                'message': f'Minimum investment amount is ${package.min_amount}'
            }), 400
        
        if package.max_amount and amount > package.max_amount:
            return jsonify({
                'success': False,
                'message': f'Maximum investment amount is ${package.max_amount}'
            }), 400

        # CRITICAL: Check package capacity (if there's a total limit)
        if hasattr(package, 'total_capacity') and package.total_capacity:
            current_total = package.total_invested
            if current_total + amount > package.total_capacity:
                return jsonify({
                    'success': False,
                    'message': f'Package capacity exceeded. Available: ${package.total_capacity - current_total}'
                }), 400
        
        # Get user and validate status
        user = User.query.get(user_id)
        if not user:
            return jsonify({
                'success': False,
                'message': 'User not found'
            }), 404

        # CRITICAL: Validate user status
        if not user.is_active:
            return jsonify({
                'success': False,
                'message': 'Account is deactivated'
            }), 403

        # Optional: Require verification for investments
        # if not user.is_verified:
        #     return jsonify({
        #         'success': False,
        #         'message': 'Account verification required for investments'
        #     }), 403
        
        # CRITICAL: Initialize user wallets if missing
        from models.wallet import Wallet
        Wallet.initialize_user_wallets(user_id)

        # Get available fund wallet with database lock for concurrency protection
        available_wallet = Wallet.query.filter_by(
            user_id=user_id,
            wallet_type='available_fund'
        ).with_for_update().first()

        if not available_wallet:
            return jsonify({
                'success': False,
                'message': 'Available fund wallet not found'
            }), 500

        if available_wallet.balance < amount:
            return jsonify({
                'success': False,
                'message': 'Insufficient available funds'
            }), 400
        
        # Note: With the new system, we don't need a separate investment wallet
        # total_investment is calculated from UserInvestment records

        # CRITICAL: Check daily investment limits
        from datetime import date
        today_investments = db.session.query(func.sum(UserInvestment.amount_invested)).filter(
            UserInvestment.user_id == user_id,
            func.date(UserInvestment.investment_date) == date.today()
        ).scalar() or 0

        daily_limit = 50000  # $50,000 daily limit
        if today_investments + amount > daily_limit:
            return jsonify({
                'success': False,
                'message': f'Daily investment limit exceeded. Limit: ${daily_limit}, Today: ${today_investments}'
            }), 400
        
        # Calculate investment dates - SIMPLIFIED
        investment_date = datetime.utcnow()
        returns_start_date = date.today() + timedelta(days=1)  # Returns start next day
        maturity_date = returns_start_date + timedelta(days=package.duration_days)

        # Always start as ACTIVE (simplified)
        initial_status = InvestmentStatus.ACTIVE
        
        # Create investment record
        investment = UserInvestment(
            user_id=user_id,
            package_id=package_id,
            amount_invested=amount,
            investment_date=investment_date,
            returns_start_date=returns_start_date,
            maturity_date=maturity_date,
            status=initial_status
        )
        
        db.session.add(investment)
        db.session.flush()
        
        # Deduct money from available_fund
        available_wallet.balance -= amount

        # Note: total_investment is now calculated from UserInvestment records
        # No need to manually update user.total_investment
        
        # Create transaction record
        # Debit from available_fund
        debit_transaction = Transaction(
            user_id=user_id,
            wallet_type='available_fund',
            transaction_type=TransactionType.INVESTMENT_PURCHASE,
            amount=amount,  # Positive amount for record keeping
            description=f'Investment purchase - {package.name}'
        )

        db.session.add(debit_transaction)

        # Distribute referral commissions with error handling
        try:
            from models.referral import Referral
            Referral.distribute_commissions(user_id, amount)
        except Exception as e:
            # Log error but don't fail the investment
            import logging
            logging.error(f"Referral distribution failed for user {user_id}, investment {investment.id}: {str(e)}")
            # Continue with investment - referrals can be processed later

        # Commit all changes
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Investment purchased successfully',
            'investment': investment.to_dict(include_package=True),
            'new_available_balance': float(available_wallet.balance),
            'new_total_investment': user.get_total_investment()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error processing investment: {str(e)}'
        }), 500


@investments_bp.route('/my-investments', methods=['GET'])
@jwt_required()
def get_user_investments():
    """Get current user's investments"""
    
    try:
        user_id = get_jwt_identity()
        
        # Get query parameters
        status = request.args.get('status')
        package_id = request.args.get('package_id')
        
        # Build query
        query = UserInvestment.query.filter_by(user_id=user_id)
        
        if status:
            query = query.filter_by(status=InvestmentStatus(status))
        
        if package_id:
            query = query.filter_by(package_id=int(package_id))
        
        # Get all investments (no pagination)
        investments = query.order_by(
            UserInvestment.created_at.desc()
        ).all()
        
        # Convert to dict
        investments_data = [inv.to_dict(include_package=True) for inv in investments]

        # Get ALL user investments for accurate summary (ignore filters)
        all_investments = UserInvestment.query.filter_by(user_id=user_id).all()

        # Calculate summary from ALL investments (not filtered ones)
        total_invested = sum(float(inv.amount_invested) for inv in all_investments)
        total_returns = sum(float(inv.total_returns_paid) for inv in all_investments)
        active_investments = len([inv for inv in all_investments if inv.status == InvestmentStatus.ACTIVE])
        
        return jsonify({
            'success': True,
            'investments': investments_data,
            'summary': {
                'total_invested': total_invested,
                'total_returns': total_returns,
                'active_investments': active_investments,
                'total_investments': len(all_investments)
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching investments: {str(e)}'
        }), 500


@investments_bp.route('/my-investments/<int:investment_id>', methods=['GET'])
@jwt_required()
def get_investment_details(investment_id):
    """Get detailed information about a specific investment"""
    
    try:
        user_id = get_jwt_identity()
        
        investment = UserInvestment.query.filter_by(
            id=investment_id,
            user_id=user_id
        ).first()
        
        if not investment:
            return jsonify({
                'success': False,
                'message': 'Investment not found'
            }), 404
        
        # Get return history
        returns = investment.returns.order_by(
            investment.returns.return_date.desc()
        ).limit(30).all()
        
        investment_data = investment.to_dict(include_package=True)
        investment_data['return_history'] = [ret.to_dict() for ret in returns]
        
        return jsonify({
            'success': True,
            'investment': investment_data
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching investment details: {str(e)}'
        }), 500



