"""
Dashboard Routes for MetaX Coin Backend
Handles dashboard data, wallet balances, and MXC price information
"""

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime

from models import db, User, Wallet, Transaction, Income, Referral
from services.mxc_service import get_current_mxc_price, get_mxc_chart_data
from services.investment_service import InvestmentService
from auth.utils import active_user_required

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/balances', methods=['GET'])
@jwt_required()
def get_balances():
    """Get all wallet balances for the current user"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get all wallet balances
        wallet_balances = Wallet.get_user_balances(current_user_id)
        
        # Calculate total balance
        total_balance = sum(balance['balance'] for balance in wallet_balances.values())
        
        return jsonify({
            'wallet_balances': wallet_balances,
            'total_balance': total_balance,
            'last_updated': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        current_app.logger.error(f'Get balances error: {str(e)}')
        return jsonify({'error': 'Failed to get balances'}), 500


@dashboard_bp.route('/wallet-summary', methods=['GET'])
@jwt_required()
def get_wallet_summary():
    """Get simplified wallet summary for UI display"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)

        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Helper function to get wallet balance
        def get_wallet_balance(wallet_type):
            wallet = Wallet.query.filter_by(
                user_id=current_user_id,
                wallet_type=wallet_type
            ).first()
            return float(wallet.balance) if wallet else 0.0

        # 1. Available Fund (withdrawable money)
        available_fund = get_wallet_balance('available_fund')

        # 2. Total Investment (calculated from UserInvestment records)
        total_investment = user.get_total_investment()

        # 3. Total Gain (from total_gain wallet)
        total_gain = get_wallet_balance('total_gain')

        # 4. Total Referral (from total_referral wallet)
        total_referral = get_wallet_balance('total_referral')

        # 5. Level Bonus (from level_bonus wallet)
        level_bonus = get_wallet_balance('level_bonus')

        # 6. Total Income (calculated: gain + referral + level bonus)
        total_income = total_gain + total_referral + level_bonus

        # Get investment summary for additional details
        investment_summary = InvestmentService.get_user_investment_summary(current_user_id)

        return jsonify({
            'success': True,
            'wallet_summary': {
                'available_fund': available_fund,
                'total_investment': total_investment,
                'total_gain': total_gain,
                'total_referral': total_referral,
                'level_bonus': level_bonus,
                'total_income': total_income
            },
            'investment_details': {
                'active_investments': investment_summary['active_investments'] if investment_summary else 0,
                'total_returns_earned': investment_summary['total_returns_earned'] if investment_summary else 0,
                'roi_percentage': investment_summary['roi_percentage'] if investment_summary else 0
            },
            'withdrawal_info': {
                'withdrawable_amount': available_fund,
                'withdrawable_wallets': ['available_fund'],
                'locked_amount': total_investment
            },
            'last_updated': datetime.utcnow().isoformat()
        }), 200

    except Exception as e:
        current_app.logger.error(f'Get wallet summary error: {str(e)}')
        return jsonify({'error': 'Failed to get wallet summary'}), 500


@dashboard_bp.route('/summary', methods=['GET'])
@jwt_required()
def get_dashboard_summary():
    """Get simplified dashboard summary - only data used by frontend"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)

        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Get basic team statistics (only what's used as fallback)
        team_stats = Referral.get_team_summary(current_user_id)

        return jsonify({
            'user_info': {
                'username': user.username,
                'full_name': user.get_full_name(),
                'is_verified': user.is_verified
            },
            'team_summary': {
                'total_team_size': team_stats.get('total_team', 0),
                'total_commission': team_stats.get('total_commission', 0)
            },
            'last_updated': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        current_app.logger.error(f'Get dashboard summary error: {str(e)}')
        return jsonify({'error': 'Failed to get dashboard summary'}), 500


@dashboard_bp.route('/mxc-price', methods=['GET'])
def get_mxc_price():
    """Get current MXC price data (public endpoint)"""
    try:
        price_data = get_current_mxc_price()
        return jsonify(price_data), 200
        
    except Exception as e:
        current_app.logger.error(f'Get MXC price error: {str(e)}')
        return jsonify({'error': 'Failed to get MXC price'}), 500


@dashboard_bp.route('/mxc-chart', methods=['GET'])
def get_mxc_chart():
    """Get MXC chart data"""
    try:
        timeframe = request.args.get('timeframe', '24h')
        
        # Validate timeframe
        valid_timeframes = ['1h', '4h', '24h', '7d', '30d', '90d', '1y']
        if timeframe not in valid_timeframes:
            timeframe = '24h'
        
        chart_data = get_mxc_chart_data(timeframe)
        return jsonify(chart_data), 200
        
    except Exception as e:
        current_app.logger.error(f'Get MXC chart error: {str(e)}')
        return jsonify({'error': 'Failed to get chart data'}), 500


@dashboard_bp.route('/wallet/<wallet_type>', methods=['GET'])
@jwt_required()
def get_wallet_details(wallet_type):
    """Get detailed information for a specific wallet"""
    try:
        current_user_id = get_jwt_identity()
        
        # Validate wallet type
        if wallet_type not in Wallet.get_wallet_types():
            return jsonify({'error': 'Invalid wallet type'}), 400
        
        # Get wallet
        wallet = Wallet.query.filter_by(
            user_id=current_user_id,
            wallet_type=wallet_type
        ).first()
        
        if not wallet:
            return jsonify({'error': 'Wallet not found'}), 404
        
        # Get recent transactions for this wallet
        recent_transactions = Transaction.query.filter_by(
            user_id=current_user_id,
            wallet_type=wallet_type
        ).order_by(Transaction.created_at.desc()).limit(20).all()
        
        # Get income history if it's an income wallet
        income_history = []
        if wallet_type in Wallet.get_income_wallet_types():
            income_history = Income.get_income_history(
                current_user_id,
                income_type=wallet_type.replace('_', ' ').title(),
                limit=20
            )
        
        return jsonify({
            'wallet': wallet.to_dict(),
            'recent_transactions': [txn.to_dict() for txn in recent_transactions],
            'income_history': [income.to_dict(include_user_info=True) for income in income_history],
            'wallet_description': get_wallet_description(wallet_type)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f'Get wallet details error: {str(e)}')
        return jsonify({'error': 'Failed to get wallet details'}), 500


# USER TRANSFER FUNCTIONALITY REMOVED
# Per user preference: Admin-only wallet transfers
# Users can only withdraw from available_fund wallet

@dashboard_bp.route('/transfer', methods=['POST'])
@jwt_required()
@active_user_required
def transfer_between_wallets():
    """Transfer funds between user's wallets - DISABLED"""
    return jsonify({
        'error': 'User transfers are disabled. Only admin can manage wallet transfers.',
        'message': 'Contact admin for wallet fund movements.'
    }), 403


@dashboard_bp.route('/statistics', methods=['GET'])
@jwt_required()
def get_user_statistics():
    """Get user statistics and analytics"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get monthly income statistics
        monthly_stats = Income.get_monthly_income_stats(current_user_id)
        
        # Get income by type
        income_by_type = Income.get_total_income_by_type(current_user_id)
        
        # Get transaction statistics
        total_deposits = Transaction.query.filter_by(
            user_id=current_user_id,
            transaction_type='deposit',
            status='completed'
        ).count()
        
        total_withdrawals = Transaction.query.filter_by(
            user_id=current_user_id,
            transaction_type='withdrawal',
            status='completed'
        ).count()
        
        # Get team growth over time
        team_stats = Referral.get_level_statistics(current_user_id)
        
        return jsonify({
            'monthly_income': monthly_stats,
            'income_by_type': income_by_type,
            'transaction_stats': {
                'total_deposits': total_deposits,
                'total_withdrawals': total_withdrawals
            },
            'team_statistics': team_stats,
            'account_age_days': (datetime.utcnow() - user.created_at).days,
            'rank_progression': get_rank_progression(user)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f'Get statistics error: {str(e)}')
        return jsonify({'error': 'Failed to get statistics'}), 500


def get_wallet_description(wallet_type):
    """Get description for wallet type"""
    descriptions = {
        'available_fund': 'Main spending wallet for deposits and transfers',
        'total_gain': 'Returns from investments and staking activities',
        'level_bonus': 'Commissions from multi-level referrals (Levels 2-5)',
        'total_referral': 'Commissions from direct referrals (Level 1)',
        'total_income': 'Sum of all income types (calculated)',
        'total_investment': 'Total amount you have invested (calculated)'
    }
    return descriptions.get(wallet_type, 'Wallet for managing your funds')


def get_rank_progression(user):
    """Get user's rank progression information"""
    rank_thresholds = {
        'Bronze': 0,
        'Silver': 10000,
        'Gold': 25000,
        'Platinum': 50000,
        'Diamond': 100000
    }
    
    current_investment = float(user.total_investment)
    current_rank = user.rank
    
    # Find next rank
    next_rank = None
    next_threshold = None
    
    for rank, threshold in rank_thresholds.items():
        if current_investment < threshold:
            next_rank = rank
            next_threshold = threshold
            break
    
    progress_to_next = 0
    if next_threshold:
        previous_threshold = rank_thresholds.get(current_rank, 0)
        progress_to_next = ((current_investment - previous_threshold) / 
                           (next_threshold - previous_threshold)) * 100
    
    return {
        'current_rank': current_rank,
        'current_investment': current_investment,
        'next_rank': next_rank,
        'next_threshold': next_threshold,
        'progress_to_next_percent': min(progress_to_next, 100),
        'rank_thresholds': rank_thresholds
    }
