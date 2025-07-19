"""
Scheduler Service for MetaX Coin Backend
Handles background tasks and scheduled operations
"""

from apscheduler.schedulers.background import BackgroundScheduler
from flask import current_app
from datetime import datetime, timedelta
from decimal import Decimal

from models import db, User, Wallet, Income, MXCChartData
from services.admin_config import get_config
from services.investment_service import InvestmentService


def calculate_daily_staking_rewards(app=None):
    """Calculate and distribute daily staking rewards"""
    if app is None:
        app = current_app._get_current_object()

    with app.app_context():
        try:
            app.logger.info("Starting daily staking rewards calculation")

            # Get staking configuration
            staking_apy = get_config('staking_apy', 12.0)
            daily_rate = Decimal(str(staking_apy)) / 365 / 100

            app.logger.info(f"Using staking APY: {staking_apy}%, daily rate: {daily_rate}")

            # Find users with gain balance (includes staking)
            gain_wallets = Wallet.query.filter(
                Wallet.wallet_type == 'total_gain',
                Wallet.balance > 0
            ).all()

            total_rewards = 0
            users_rewarded = 0

            for wallet in gain_wallets:
                if wallet.balance > 0:
                    # Calculate daily reward
                    daily_reward = wallet.balance * daily_rate

                    # Add reward to staking wallet
                    wallet.add_balance(
                        daily_reward,
                        f"Daily staking reward ({staking_apy}% APY)"
                    )

                    # Create income record
                    income = Income.create_staking_income(
                        user_id=wallet.user_id,
                        amount=daily_reward,
                        description=f"Daily staking reward ({staking_apy}% APY)"
                    )

                    total_rewards += float(daily_reward)
                    users_rewarded += 1

            db.session.commit()
            app.logger.info(f"Distributed {total_rewards:.8f} USDT in staking rewards to {users_rewarded} users")

        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Daily staking rewards error: {str(e)}")


def calculate_daily_investment_returns(app=None):
    """Calculate and distribute daily investment returns"""
    if app is None:
        app = current_app._get_current_object()

    with app.app_context():
        try:
            app.logger.info("Starting daily investment returns calculation")

            # Use investment service to calculate returns
            result = InvestmentService.calculate_daily_investment_returns()

            if result['success']:
                app.logger.info(
                    f"Investment returns completed: {result['processed_count']} investments, "
                    f"${result['total_amount']} distributed"
                )
            else:
                app.logger.error(f"Investment returns failed: {result.get('error', 'Unknown error')}")

        except Exception as e:
            app.logger.error(f"Investment returns calculation error: {str(e)}")


def update_user_ranks(app=None):
    """Update user ranks based on total investment"""
    if app is None:
        app = current_app._get_current_object()

    with app.app_context():
        try:
            app.logger.info("Starting user rank updates")

            users = User.query.filter_by(is_active=True).all()
            updated_count = 0

            for user in users:
                old_rank = user.rank
                user.update_rank()

                if user.rank != old_rank:
                    updated_count += 1
                    app.logger.info(f"User {user.username} rank updated: {old_rank} -> {user.rank}")

            if updated_count > 0:
                db.session.commit()
                app.logger.info(f"Updated ranks for {updated_count} users")

        except Exception as e:
            db.session.rollback()
            app.logger.error(f"User rank update error: {str(e)}")


def cleanup_old_chart_data(app=None):
    """Clean up old chart data to prevent database bloat"""
    if app is None:
        app = current_app._get_current_object()

    with app.app_context():
        try:
            app.logger.info("Starting chart data cleanup")

            days_to_keep = get_config('chart_data_retention_days', 90)
            deleted_count = MXCChartData.cleanup_old_data(days_to_keep)

            if deleted_count > 0:
                app.logger.info(f"Cleaned up {deleted_count} old chart data records")

        except Exception as e:
            app.logger.error(f"Chart data cleanup error: {str(e)}")


def generate_hourly_chart_data(app=None):
    """Generate hourly chart data points for MXC"""
    if app is None:
        app = current_app._get_current_object()

    with app.app_context():
        try:
            from services.mxc_service import get_current_mxc_price, add_chart_data_point

            current_price_data = get_current_mxc_price()
            current_price = current_price_data['price']

            # Add slight variation to make chart more realistic
            import random
            variation = (random.random() - 0.5) * 0.02  # ±1% variation
            adjusted_price = current_price * (1 + variation)

            # Generate random volume
            base_volume = current_price_data.get('volume_24h', 100000)
            hourly_volume = int(base_volume / 24 * (0.5 + random.random()))  # 50-150% of average hourly volume

            add_chart_data_point(adjusted_price, hourly_volume)
            app.logger.info(f"Added chart data point: price={adjusted_price:.8f}, volume={hourly_volume}")

        except Exception as e:
            app.logger.error(f"Generate chart data error: {str(e)}")


def calculate_weekly_bonuses(app=None):
    """Calculate and distribute weekly bonuses"""
    if app is None:
        app = current_app._get_current_object()

    with app.app_context():
        try:
            app.logger.info("Starting weekly bonus calculation")

            # This is a placeholder for weekly bonus logic
            # You can implement specific bonus criteria here

            # Example: Give bonus to top performers
            from models.income import Income
            from sqlalchemy import func

            # Get top earners this week
            week_ago = datetime.utcnow() - timedelta(days=7)
            top_earners = db.session.query(
                Income.user_id,
                func.sum(Income.amount).label('total_income')
            ).filter(
                Income.created_at >= week_ago,
                Income.status == 'completed'
            ).group_by(Income.user_id).order_by(
                func.sum(Income.amount).desc()
            ).limit(10).all()

            bonus_amount = get_config('weekly_top_earner_bonus', 50.0)

            for i, (user_id, total_income) in enumerate(top_earners):
                # Give decreasing bonus based on rank
                rank_bonus = bonus_amount * (1 - i * 0.1)  # 100%, 90%, 80%, etc.

                # Add to lifetime reward wallet
                wallet = Wallet.query.filter_by(
                    user_id=user_id,
                    wallet_type='lifetime_reward'
                ).first()

                if wallet:
                    wallet.add_balance(
                        rank_bonus,
                        f"Weekly top earner bonus (Rank #{i+1})"
                    )

                    # Create income record
                    Income.create_bonus_income(
                        user_id=user_id,
                        amount=rank_bonus,
                        bonus_type='Weekly Performance Bonus',
                        description=f"Top earner rank #{i+1} weekly bonus"
                    )

            if top_earners:
                db.session.commit()
                app.logger.info(f"Distributed weekly bonuses to {len(top_earners)} top earners")

        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Weekly bonus calculation error: {str(e)}")


def system_health_check(app=None):
    """Perform system health checks"""
    if app is None:
        app = current_app._get_current_object()

    with app.app_context():
        try:
            app.logger.info("Performing system health check")

            # Check database connectivity
            user_count = User.query.count()

            # Check wallet pool status
            from services.wallet_pool import get_wallet_pool_statistics
            pool_stats = get_wallet_pool_statistics()

            # Log system status
            app.logger.info(f"System health: {user_count} users, {pool_stats['wallets']['available_wallets']} available wallets")

            # Check for any critical issues
            if pool_stats['wallets']['available_wallets'] == 0:
                app.logger.warning("No available wallets in pool!")

            if pool_stats['wallets']['utilization_rate'] > 90:
                app.logger.warning(f"High wallet utilization: {pool_stats['wallets']['utilization_rate']:.1f}%")

        except Exception as e:
            app.logger.error(f"System health check error: {str(e)}")


def init_scheduler(app):
    """Initialize and configure the scheduler"""
    scheduler = BackgroundScheduler(timezone='UTC')

    # Daily staking rewards at midnight UTC
    scheduler.add_job(
        lambda: calculate_daily_staking_rewards(app),
        'cron',
        hour=0,
        minute=0,
        id='daily_staking_rewards'
    )

    # Daily investment returns at 12:30 AM UTC (30 minutes after staking)
    scheduler.add_job(
        lambda: calculate_daily_investment_returns(app),
        'cron',
        hour=0,
        minute=30,
        id='daily_investment_returns'
    )

    # Update user ranks daily at 1 AM UTC
    scheduler.add_job(
        lambda: update_user_ranks(app),
        'cron',
        hour=1,
        minute=0,
        id='daily_rank_update'
    )

    # Generate chart data every hour
    scheduler.add_job(
        lambda: generate_hourly_chart_data(app),
        'interval',
        hours=1,
        id='hourly_chart_data'
    )

    # Weekly bonuses on Sundays at 2 AM UTC
    scheduler.add_job(
        lambda: calculate_weekly_bonuses(app),
        'cron',
        day_of_week='sun',
        hour=2,
        minute=0,
        id='weekly_bonuses'
    )

    # Clean up old chart data weekly
    scheduler.add_job(
        lambda: cleanup_old_chart_data(app),
        'cron',
        day_of_week='mon',
        hour=3,
        minute=0,
        id='weekly_cleanup'
    )

    # System health check every 6 hours
    scheduler.add_job(
        lambda: system_health_check(app),
        'interval',
        hours=6,
        id='health_check'
    )

    scheduler.start()
    app.logger.info("Background scheduler initialized")

    return scheduler
