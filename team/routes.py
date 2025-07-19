"""
Team Management Routes for MetaX Coin Backend
Handles multi-level referral system, team statistics, and commission tracking
"""

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta

from models import db, User, Referral, Income
from services.admin_config import get_referral_rates
from auth.utils import active_user_required

team_bp = Blueprint('team', __name__)


@team_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_team_stats():
    """Get comprehensive team statistics"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get team summary
        team_summary = Referral.get_team_summary(current_user_id)
        
        # Get level statistics
        level_stats = Referral.get_level_statistics(current_user_id)
        
        # Get recent team activity (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_referrals = Referral.query.filter(
            Referral.referrer_id == current_user_id,
            Referral.level == 1,  # Direct referrals only
            Referral.created_at >= thirty_days_ago
        ).count()
        
        # Get commission earnings (last 30 days)
        recent_commissions = Income.query.filter(
            Income.user_id == current_user_id,
            Income.income_type.in_(['Direct Referral', 'Level Bonus']),
            Income.created_at >= thirty_days_ago,
            Income.status == 'completed'
        ).all()
        
        total_recent_commissions = sum(float(income.amount) for income in recent_commissions)
        
        return jsonify({
            'team_summary': team_summary,
            'level_statistics': level_stats,
            'recent_activity': {
                'new_referrals_30d': recent_referrals,
                'commission_earnings_30d': total_recent_commissions,
                'period': '30 days'
            },
            'referral_link': user.get_referral_link(),
            'referral_code': user.referral_code
        }), 200
        
    except Exception as e:
        current_app.logger.error(f'Get team stats error: {str(e)}')
        return jsonify({'error': 'Failed to get team statistics'}), 500


@team_bp.route('/members', methods=['GET'])
@jwt_required()
def get_team_members():
    """Get team members with filtering options"""
    try:
        current_user_id = get_jwt_identity()
        
        # Get query parameters
        status = request.args.get('status', 'all')  # active, inactive, all
        level = request.args.get('level', 'all')    # 1-5 or all
        limit = min(int(request.args.get('limit', 50)), 100)
        offset = int(request.args.get('offset', 0))
        search = request.args.get('search', '').strip()
        
        # Build base query
        query = db.session.query(Referral, User).join(
            User, Referral.referred_id == User.id
        ).filter(Referral.referrer_id == current_user_id)
        
        # Apply filters
        if status == 'active':
            query = query.filter(User.is_active == True)
        elif status == 'inactive':
            query = query.filter(User.is_active == False)
        
        if level != 'all':
            try:
                level_num = int(level)
                if 1 <= level_num <= 5:
                    query = query.filter(Referral.level == level_num)
            except ValueError:
                return jsonify({'error': 'Invalid level parameter'}), 400
        
        if search:
            query = query.filter(
                db.or_(
                    User.username.ilike(f'%{search}%'),
                    User.first_name.ilike(f'%{search}%'),
                    User.last_name.ilike(f'%{search}%'),
                    User.email.ilike(f'%{search}%')
                )
            )
        
        # Get total count
        total_count = query.count()
        
        # Apply pagination and ordering
        results = query.order_by(Referral.created_at.desc()).offset(offset).limit(limit).all()
        
        # Format results
        members = []
        for referral, user in results:
            member_data = {
                'user_id': user.id,
                'username': user.username,
                'full_name': user.get_full_name(),
                'email': user.email,
                'level': referral.level,
                'is_active': user.is_active,
                'total_investment': float(user.total_investment),
                'total_earnings': float(user.total_earnings),
                'rank': user.rank,
                'joined_at': user.created_at.isoformat(),
                'commission_earned': float(referral.total_commission_earned),
                'last_commission_at': referral.last_commission_at.isoformat() if referral.last_commission_at else None
            }
            members.append(member_data)
        
        return jsonify({
            'members': members,
            'pagination': {
                'total_count': total_count,
                'limit': limit,
                'offset': offset,
                'has_more': offset + limit < total_count
            },
            'filters_applied': {
                'status': status,
                'level': level,
                'search': search
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f'Get team members error: {str(e)}')
        return jsonify({'error': 'Failed to get team members'}), 500


@team_bp.route('/tree', methods=['GET'])
@jwt_required()
def get_team_tree():
    """Get hierarchical team structure"""
    try:
        current_user_id = get_jwt_identity()
        
        # Get max levels parameter
        max_levels = min(int(request.args.get('max_levels', 5)), 5)
        
        # Get referral tree
        tree_data = Referral.get_referral_tree(current_user_id, max_levels)
        
        return jsonify({
            'tree': tree_data,
            'max_levels': max_levels,
            'total_nodes': count_tree_nodes(tree_data)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f'Get team tree error: {str(e)}')
        return jsonify({'error': 'Failed to get team tree'}), 500


@team_bp.route('/referral-link', methods=['GET'])
@jwt_required()
def get_referral_link():
    """Get user's referral link and code"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({
            'referral_code': user.referral_code,
            'referral_link': user.get_referral_link(),
            'qr_code_url': f"/api/team/qr-code/{user.referral_code}",
            'share_message': f"Join MetaX Coin using my referral code: {user.referral_code}"
        }), 200
        
    except Exception as e:
        current_app.logger.error(f'Get referral link error: {str(e)}')
        return jsonify({'error': 'Failed to get referral link'}), 500


@team_bp.route('/commission-history', methods=['GET'])
@jwt_required()
def get_commission_history():
    """Get commission earnings history"""
    try:
        current_user_id = get_jwt_identity()
        
        # Get query parameters
        income_type = request.args.get('type', 'all')  # direct, level, all
        limit = min(int(request.args.get('limit', 50)), 100)
        offset = int(request.args.get('offset', 0))
        
        # Build query
        query = Income.query.filter_by(user_id=current_user_id)
        
        if income_type == 'direct':
            query = query.filter_by(income_type='Direct Referral')
        elif income_type == 'level':
            query = query.filter_by(income_type='Level Bonus')
        elif income_type == 'all':
            query = query.filter(Income.income_type.in_(['Direct Referral', 'Level Bonus']))
        else:
            return jsonify({'error': 'Invalid income type'}), 400
        
        # Get total count
        total_count = query.count()
        
        # Get commissions
        commissions = query.order_by(Income.created_at.desc()).offset(offset).limit(limit).all()
        
        # Calculate totals
        total_amount = sum(float(commission.amount) for commission in commissions)
        
        return jsonify({
            'commissions': [commission.to_dict(include_user_info=True) for commission in commissions],
            'summary': {
                'total_amount': total_amount,
                'total_count': total_count
            },
            'pagination': {
                'limit': limit,
                'offset': offset,
                'has_more': offset + limit < total_count
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f'Get commission history error: {str(e)}')
        return jsonify({'error': 'Failed to get commission history'}), 500


@team_bp.route('/commission-rates', methods=['GET'])
def get_commission_rates():
    """Get current commission rates (public endpoint)"""
    try:
        rates = get_referral_rates()
        
        return jsonify({
            'commission_rates': rates,
            'description': {
                'level_1': 'Direct referrals',
                'level_2': 'Second level referrals',
                'level_3': 'Third level referrals',
                'level_4': 'Fourth level referrals',
                'level_5': 'Fifth level referrals'
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f'Get commission rates error: {str(e)}')
        return jsonify({'error': 'Failed to get commission rates'}), 500


@team_bp.route('/performance', methods=['GET'])
@jwt_required()
def get_team_performance():
    """Get team performance analytics"""
    try:
        current_user_id = get_jwt_identity()
        
        # Get time period parameter
        period = request.args.get('period', '30d')  # 7d, 30d, 90d, 1y
        
        # Calculate date range
        if period == '7d':
            start_date = datetime.utcnow() - timedelta(days=7)
        elif period == '30d':
            start_date = datetime.utcnow() - timedelta(days=30)
        elif period == '90d':
            start_date = datetime.utcnow() - timedelta(days=90)
        elif period == '1y':
            start_date = datetime.utcnow() - timedelta(days=365)
        else:
            return jsonify({'error': 'Invalid period'}), 400
        
        # Get new referrals in period
        new_referrals = Referral.query.filter(
            Referral.referrer_id == current_user_id,
            Referral.level == 1,
            Referral.created_at >= start_date
        ).count()
        
        # Get commission earnings in period
        commission_earnings = Income.query.filter(
            Income.user_id == current_user_id,
            Income.income_type.in_(['Direct Referral', 'Level Bonus']),
            Income.created_at >= start_date,
            Income.status == 'completed'
        ).all()
        
        total_commissions = sum(float(income.amount) for income in commission_earnings)
        
        # Get team investment in period
        team_members = db.session.query(User).join(
            Referral, Referral.referred_id == User.id
        ).filter(
            Referral.referrer_id == current_user_id,
            User.created_at >= start_date
        ).all()
        
        team_investment = sum(float(member.total_investment) for member in team_members)
        
        # Calculate growth rates
        previous_period_start = start_date - (datetime.utcnow() - start_date)
        
        previous_referrals = Referral.query.filter(
            Referral.referrer_id == current_user_id,
            Referral.level == 1,
            Referral.created_at >= previous_period_start,
            Referral.created_at < start_date
        ).count()
        
        referral_growth = 0
        if previous_referrals > 0:
            referral_growth = ((new_referrals - previous_referrals) / previous_referrals) * 100
        
        return jsonify({
            'period': period,
            'performance_metrics': {
                'new_referrals': new_referrals,
                'total_commissions': total_commissions,
                'team_investment': team_investment,
                'referral_growth_percent': referral_growth
            },
            'commission_breakdown': {
                'direct_referral': sum(float(income.amount) for income in commission_earnings if income.income_type == 'Direct Referral'),
                'level_bonus': sum(float(income.amount) for income in commission_earnings if income.income_type == 'Level Bonus')
            },
            'top_performers': get_top_team_performers(current_user_id, start_date)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f'Get team performance error: {str(e)}')
        return jsonify({'error': 'Failed to get team performance'}), 500


def count_tree_nodes(tree_data):
    """Recursively count nodes in tree structure"""
    count = len(tree_data)
    for node in tree_data:
        count += count_tree_nodes(node.get('children', []))
    return count


def get_top_team_performers(user_id, start_date, limit=5):
    """Get top performing team members"""
    try:
        # Get team members with their investment in the period
        team_members = db.session.query(User, Referral).join(
            Referral, Referral.referred_id == User.id
        ).filter(
            Referral.referrer_id == user_id,
            Referral.level == 1  # Direct referrals only
        ).all()
        
        performers = []
        for user, referral in team_members:
            # Calculate performance metrics
            member_commissions = Income.query.filter(
                Income.from_user_id == user.id,
                Income.created_at >= start_date,
                Income.status == 'completed'
            ).all()
            
            total_generated_commissions = sum(float(income.amount) for income in member_commissions)
            
            performers.append({
                'user_id': user.id,
                'username': user.username,
                'full_name': user.get_full_name(),
                'total_investment': float(user.total_investment),
                'generated_commissions': total_generated_commissions,
                'rank': user.rank,
                'is_active': user.is_active
            })
        
        # Sort by generated commissions
        performers.sort(key=lambda x: x['generated_commissions'], reverse=True)
        
        return performers[:limit]
        
    except Exception as e:
        current_app.logger.error(f'Get top performers error: {str(e)}')
        return []
