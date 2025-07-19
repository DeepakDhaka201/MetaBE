"""
Income Routes for MetaX Coin Backend
Handles income tracking, history, and summaries for all income types
"""

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta

from models import db, User, Income
from auth.utils import active_user_required

income_bp = Blueprint('income', __name__)


@income_bp.route('/history', methods=['GET'])
@jwt_required()
def get_income_history():
    """Get user's income history with filtering options"""
    try:
        current_user_id = get_jwt_identity()
        
        # Get query parameters
        income_type = request.args.get('type', 'all')  # Direct Referral, Level Bonus, etc.
        limit = min(int(request.args.get('limit', 50)), 100)
        offset = int(request.args.get('offset', 0))
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Build base query
        query = Income.query.filter_by(user_id=current_user_id)
        
        # Apply income type filter
        if income_type != 'all':
            # Map string to enum
            income_type_map = {
                'Direct Referral': 'DIRECT_REFERRAL',
                'Level Bonus': 'LEVEL_BONUS', 
                'Staking Reward': 'STAKING_REWARD',
                'Self Investment': 'SELF_INVESTMENT',
                'Lifetime Reward': 'LIFETIME_REWARD',
                'Bonus': 'BONUS',
                'Promotion Bonus': 'PROMOTION_BONUS',
                'Leadership Bonus': 'LEADERSHIP_BONUS'
            }
            
            if income_type in income_type_map:
                from models.income import IncomeType
                try:
                    enum_type = IncomeType(income_type)
                    query = query.filter_by(income_type=enum_type)
                except ValueError:
                    # Try direct string match
                    query = query.filter(Income.income_type.has(value=income_type))
            else:
                return jsonify({'error': 'Invalid income type'}), 400
        
        # Apply date filters
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                query = query.filter(Income.created_at >= start_dt)
            except ValueError:
                return jsonify({'error': 'Invalid start_date format. Use ISO format.'}), 400
        
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                query = query.filter(Income.created_at <= end_dt)
            except ValueError:
                return jsonify({'error': 'Invalid end_date format. Use ISO format.'}), 400
        
        # Get total count
        total_count = query.count()
        
        # Apply pagination and ordering
        incomes = query.order_by(Income.created_at.desc()).offset(offset).limit(limit).all()
        
        # Calculate totals for the filtered results
        total_amount = sum(float(income.amount) for income in incomes)
        
        return jsonify({
            'income_history': [income.to_dict(include_user_info=True) for income in incomes],
            'summary': {
                'total_amount': total_amount,
                'total_count': total_count,
                'filtered_count': len(incomes)
            },
            'pagination': {
                'limit': limit,
                'offset': offset,
                'has_more': offset + limit < total_count
            },
            'filters_applied': {
                'income_type': income_type,
                'start_date': start_date,
                'end_date': end_date
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f'Get income history error: {str(e)}')
        return jsonify({'error': 'Failed to get income history'}), 500


@income_bp.route('/summary', methods=['GET'])
@jwt_required()
def get_income_summary():
    """Get comprehensive income summary with breakdown by type"""
    try:
        current_user_id = get_jwt_identity()
        
        # Get query parameters for date range
        period = request.args.get('period', '30d')  # 7d, 30d, 90d, 1y, all
        
        # Calculate date range
        end_date = datetime.utcnow()
        if period == '7d':
            start_date = end_date - timedelta(days=7)
        elif period == '30d':
            start_date = end_date - timedelta(days=30)
        elif period == '90d':
            start_date = end_date - timedelta(days=90)
        elif period == '1y':
            start_date = end_date - timedelta(days=365)
        elif period == 'all':
            start_date = None
        else:
            return jsonify({'error': 'Invalid period. Use: 7d, 30d, 90d, 1y, all'}), 400
        
        # Get income summary
        income_summary = Income.get_user_income_summary(current_user_id, start_date, end_date)
        
        # Get income by type
        income_by_type = Income.get_total_income_by_type(current_user_id)
        
        # Get monthly breakdown for the current year
        current_year = datetime.utcnow().year
        monthly_breakdown = {}
        
        for month in range(1, 13):
            monthly_stats = Income.get_monthly_income_stats(current_user_id, current_year, month)
            monthly_breakdown[f'{current_year}-{month:02d}'] = {
                'total_income': monthly_stats['total_income'],
                'income_count': monthly_stats['income_count']
            }
        
        # Get recent top income sources
        recent_incomes = Income.query.filter_by(
            user_id=current_user_id,
            status='completed'
        ).order_by(Income.amount.desc()).limit(5).all()
        
        top_income_sources = []
        for income in recent_incomes:
            source_info = {
                'income_type': income.income_type.value,
                'amount': float(income.amount),
                'date': income.created_at.isoformat(),
                'description': income.description
            }
            
            # Add source user info if available
            if income.from_user_id:
                from models.user import User
                from_user = User.query.get(income.from_user_id)
                if from_user:
                    source_info['from_user'] = {
                        'username': from_user.username,
                        'full_name': from_user.get_full_name()
                    }
            
            top_income_sources.append(source_info)
        
        # Calculate growth metrics
        if start_date:
            # Compare with previous period
            period_length = end_date - start_date
            previous_start = start_date - period_length
            previous_summary = Income.get_user_income_summary(
                current_user_id, previous_start, start_date
            )
            
            current_total = income_summary['total_income']
            previous_total = previous_summary['total_income']
            
            growth_rate = 0
            if previous_total > 0:
                growth_rate = ((current_total - previous_total) / previous_total) * 100
        else:
            growth_rate = None
        
        return jsonify({
            'period': period,
            'date_range': {
                'start_date': start_date.isoformat() if start_date else None,
                'end_date': end_date.isoformat()
            },
            'total_income': income_summary['total_income'],
            'income_by_type': income_by_type,
            'breakdown_by_type': income_summary['by_type'],
            'breakdown_by_level': income_summary['by_level'],
            'monthly_breakdown': monthly_breakdown,
            'top_income_sources': top_income_sources,
            'growth_metrics': {
                'growth_rate_percent': growth_rate,
                'period_comparison': period if growth_rate is not None else None
            },
            'statistics': {
                'total_transactions': len(income_summary['recent_incomes']),
                'average_income': income_summary['total_income'] / len(income_summary['recent_incomes']) if income_summary['recent_incomes'] else 0,
                'highest_single_income': max([float(income['amount']) for income in income_summary['recent_incomes']]) if income_summary['recent_incomes'] else 0
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f'Get income summary error: {str(e)}')
        return jsonify({'error': 'Failed to get income summary'}), 500


@income_bp.route('/types', methods=['GET'])
def get_income_types():
    """Get all available income types (public endpoint)"""
    try:
        from models.income import IncomeType
        
        income_types = {}
        for income_type in IncomeType:
            income_types[income_type.name] = {
                'value': income_type.value,
                'description': get_income_type_description(income_type.value)
            }
        
        return jsonify({
            'income_types': income_types,
            'categories': {
                'referral': ['Direct Referral', 'Level Bonus'],
                'investment': ['Self Investment', 'Staking Reward'],
                'rewards': ['Lifetime Reward', 'Bonus', 'Promotion Bonus', 'Leadership Bonus']
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f'Get income types error: {str(e)}')
        return jsonify({'error': 'Failed to get income types'}), 500


@income_bp.route('/analytics', methods=['GET'])
@jwt_required()
def get_income_analytics():
    """Get detailed income analytics and trends"""
    try:
        current_user_id = get_jwt_identity()
        
        # Get query parameters
        timeframe = request.args.get('timeframe', '30d')  # 7d, 30d, 90d
        
        # Calculate date range
        end_date = datetime.utcnow()
        if timeframe == '7d':
            start_date = end_date - timedelta(days=7)
            interval = 'day'
        elif timeframe == '30d':
            start_date = end_date - timedelta(days=30)
            interval = 'day'
        elif timeframe == '90d':
            start_date = end_date - timedelta(days=90)
            interval = 'week'
        else:
            return jsonify({'error': 'Invalid timeframe. Use: 7d, 30d, 90d'}), 400
        
        # Get income data for the period
        incomes = Income.query.filter(
            Income.user_id == current_user_id,
            Income.created_at >= start_date,
            Income.status == 'completed'
        ).order_by(Income.created_at).all()
        
        # Group by time intervals
        income_trends = {}
        income_by_type_trends = {}
        
        for income in incomes:
            # Determine the time key based on interval
            if interval == 'day':
                time_key = income.created_at.strftime('%Y-%m-%d')
            else:  # week
                # Get the start of the week (Monday)
                week_start = income.created_at - timedelta(days=income.created_at.weekday())
                time_key = week_start.strftime('%Y-%m-%d')
            
            # Aggregate total income
            if time_key not in income_trends:
                income_trends[time_key] = 0
            income_trends[time_key] += float(income.amount)
            
            # Aggregate by type
            income_type = income.income_type.value
            if income_type not in income_by_type_trends:
                income_by_type_trends[income_type] = {}
            if time_key not in income_by_type_trends[income_type]:
                income_by_type_trends[income_type][time_key] = 0
            income_by_type_trends[income_type][time_key] += float(income.amount)
        
        # Calculate performance metrics
        total_income = sum(float(income.amount) for income in incomes)
        income_count = len(incomes)
        average_income = total_income / income_count if income_count > 0 else 0
        
        # Find peak performance day/week
        peak_period = max(income_trends.items(), key=lambda x: x[1]) if income_trends else (None, 0)
        
        return jsonify({
            'timeframe': timeframe,
            'interval': interval,
            'date_range': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            },
            'income_trends': income_trends,
            'income_by_type_trends': income_by_type_trends,
            'performance_metrics': {
                'total_income': total_income,
                'income_count': income_count,
                'average_income': average_income,
                'peak_period': {
                    'date': peak_period[0],
                    'amount': peak_period[1]
                } if peak_period[0] else None
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f'Get income analytics error: {str(e)}')
        return jsonify({'error': 'Failed to get income analytics'}), 500


def get_income_type_description(income_type):
    """Get description for income type"""
    descriptions = {
        'Direct Referral': 'Commission from direct referrals (Level 1)',
        'Level Bonus': 'Commission from multi-level referrals (Levels 2-5)',
        'Staking Reward': 'Daily rewards from staking activities',
        'Self Investment': 'Returns from your own investments',
        'Lifetime Reward': 'Special lifetime achievement rewards',
        'Bonus': 'General bonus payments',
        'Promotion Bonus': 'Promotional and marketing bonuses',
        'Leadership Bonus': 'Leadership and performance bonuses'
    }
    return descriptions.get(income_type, 'Income from platform activities')
