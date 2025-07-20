"""
Admin Web Routes for MetaX Coin Backend
Flask UI routes that render HTML templates for admin operations
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token, create_refresh_token
from datetime import datetime, timedelta
from sqlalchemy import desc, func
from functools import wraps

from models import db, User, Transaction, TransactionStatus, AdminConfig, PooledWallet
from models.wallet_pool import WalletAssignment
from models.mxc import MXCPrice, MXCChartData
from models.income import Income
from services.mxc_service import get_current_mxc_price, update_mxc_price
from services.admin_config import get_config, set_config
from auth.utils import admin_required, admin_session_required

admin_web_bp = Blueprint('admin_web', __name__, url_prefix='/admin')


# ============================================================================
# ADMIN API ROUTES (for frontend AJAX calls)
# ============================================================================

@admin_web_bp.route('/api/user/<int:user_id>/toggle-status', methods=['POST'])
@admin_required
def api_toggle_user_status(user_id):
    """Toggle user active status (API endpoint for admin frontend)"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404

        # Toggle status
        user.is_active = not user.is_active
        user.updated_at = datetime.utcnow()
        db.session.commit()

        status_text = 'activated' if user.is_active else 'deactivated'
        current_app.logger.info(f'User {user_id} {status_text} by admin {current_user_id}')

        return jsonify({
            'success': True,
            'message': f'User {status_text} successfully',
            'is_active': user.is_active
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Admin toggle user status error: {str(e)}')
        return jsonify({'success': False, 'message': 'Failed to update user status'}), 500


@admin_web_bp.route('/api/transaction/<int:transaction_id>/approve', methods=['POST'])
@admin_required
def api_approve_transaction(transaction_id):
    """Approve transaction (API endpoint for admin frontend)"""
    try:
        current_user_id = get_jwt_identity()
        transaction = Transaction.query.get(transaction_id)

        if not transaction:
            return jsonify({'success': False, 'message': 'Transaction not found'}), 404

        if transaction.status != TransactionStatus.PENDING:
            return jsonify({'success': False, 'message': 'Transaction is not pending'}), 400

        # Update transaction status
        transaction.status = TransactionStatus.COMPLETED
        transaction.admin_notes = f'Approved by admin {current_user_id}'
        transaction.updated_at = datetime.utcnow()
        db.session.commit()

        current_app.logger.info(f'Transaction {transaction_id} approved by admin {current_user_id}')

        return jsonify({
            'success': True,
            'message': 'Transaction approved successfully'
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Admin approve transaction error: {str(e)}')
        return jsonify({'success': False, 'message': 'Failed to approve transaction'}), 500


@admin_web_bp.route('/api/transaction/<int:transaction_id>/reject', methods=['POST'])
@admin_required
def api_reject_transaction(transaction_id):
    """Reject transaction (API endpoint for admin frontend)"""
    try:
        current_user_id = get_jwt_identity()
        transaction = Transaction.query.get(transaction_id)

        if not transaction:
            return jsonify({'success': False, 'message': 'Transaction not found'}), 404

        if transaction.status != TransactionStatus.PENDING:
            return jsonify({'success': False, 'message': 'Transaction is not pending'}), 400

        # Update transaction status
        transaction.status = TransactionStatus.FAILED
        transaction.admin_notes = f'Rejected by admin {current_user_id}'
        transaction.updated_at = datetime.utcnow()
        db.session.commit()

        current_app.logger.info(f'Transaction {transaction_id} rejected by admin {current_user_id}')

        return jsonify({
            'success': True,
            'message': 'Transaction rejected successfully'
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Admin reject transaction error: {str(e)}')
        return jsonify({'success': False, 'message': 'Failed to reject transaction'}), 500


@admin_web_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Admin login page"""
    if request.method == 'POST':
        try:
            # Handle both JSON and form data
            if request.is_json:
                data = request.get_json()
            else:
                data = request.form.to_dict()

            # Validate required fields
            if not data.get('username') or not data.get('password'):
                if request.is_json:
                    return jsonify({'success': False, 'message': 'Username and password are required'}), 400
                flash('Username and password are required', 'error')
                return render_template('admin/login.html')

            username_or_email = data['username'].strip().lower()
            password = data['password']

            # Find user by username or email
            user = User.query.filter(
                (User.username == username_or_email) |
                (User.email == username_or_email)
            ).first()

            if not user or not user.check_password(password):
                if request.is_json:
                    return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
                flash('Invalid credentials', 'error')
                return render_template('admin/login.html')

            if not user.is_active:
                if request.is_json:
                    return jsonify({'success': False, 'message': 'Account is deactivated'}), 401
                flash('Account is deactivated', 'error')
                return render_template('admin/login.html')

            if not user.is_admin:
                if request.is_json:
                    return jsonify({'success': False, 'message': 'Admin privileges required'}), 403
                flash('Admin privileges required', 'error')
                return render_template('admin/login.html')

            # Update last login
            user.last_login = datetime.utcnow()

            # Create tokens
            access_token = create_access_token(
                identity=user.id,
                expires_delta=timedelta(hours=24)
            )
            refresh_token = create_refresh_token(
                identity=user.id,
                expires_delta=timedelta(days=30)
            )

            # Store user info and tokens in session
            session.permanent = True  # Make session permanent
            session['admin_user_id'] = user.id
            session['admin_username'] = user.username
            session['admin_full_name'] = f"{user.first_name} {user.last_name}" if user.first_name and user.last_name else user.username
            session['admin_access_token'] = access_token
            session['admin_refresh_token'] = refresh_token

            # Commit the database changes
            db.session.commit()

            if request.is_json:
                return jsonify({
                    'success': True,
                    'message': 'Login successful',
                    'access_token': access_token,
                    'refresh_token': refresh_token,
                    'redirect_url': url_for('admin_web.dashboard')
                }), 200
            else:
                flash('Login successful! Welcome to the admin panel.', 'success')
                return redirect(url_for('admin_web.dashboard'))

        except Exception as e:
            db.session.rollback()
            if request.is_json:
                return jsonify({'success': False, 'message': f'Login failed: {str(e)}'}), 500
            flash(f'Login failed: {str(e)}', 'error')
            return render_template('admin/login.html')

    # GET request - show login form
    return render_template('admin/login.html')


@admin_web_bp.route('/logout')
def logout():
    """Admin logout"""
    # Clear session
    session.clear()
    flash('You have been logged out successfully', 'info')
    return redirect(url_for('admin_web.login'))





@admin_web_bp.route('/demo')
def demo_dashboard():
    """Demo admin dashboard without authentication for testing"""
    try:
        from models.wallet import Wallet
        # Get basic statistics (mock data for demo)
        stats = {
            'total_users': User.query.count(),
            'active_users': User.query.filter_by(is_active=True).count(),
            'total_transactions': Transaction.query.count(),
            'pending_transactions': Transaction.query.filter_by(status=TransactionStatus.PENDING).count(),
            'total_wallets': PooledWallet.query.count() if PooledWallet.query.first() else 0,
            'active_wallets': PooledWallet.query.filter_by(is_active=True).count() if PooledWallet.query.first() else 0,
            'total_usdt_balance': Wallet.get_total_system_balance('available_fund') + Wallet.get_total_system_balance('main_balance'),
            'total_mxc_balance': 0,  # MXC balance would be calculated separately if needed
            'mxc_price': get_current_mxc_price()
        }

        # Get recent transactions
        recent_transactions = Transaction.query.order_by(desc(Transaction.created_at)).limit(10).all()

        # Get recent users
        recent_users = User.query.order_by(desc(User.created_at)).limit(5).all()

        return render_template('admin/dashboard.html',
                             stats=stats,
                             recent_transactions=recent_transactions,
                             recent_users=recent_users)

    except Exception as e:
        flash(f'Error loading dashboard: {str(e)}', 'error')
        return render_template('admin/dashboard.html', stats={}, recent_transactions=[], recent_users=[])


@admin_web_bp.route('/')
@admin_web_bp.route('/dashboard')
@admin_session_required
def dashboard():
    """Admin dashboard with overview statistics"""
    try:
        # Get basic statistics
        total_users = User.query.count()
        active_users = User.query.filter_by(is_active=True).count()
        total_transactions = Transaction.query.count()
        pending_transactions = Transaction.query.filter_by(status=TransactionStatus.PENDING).count()
        
        # Get recent transactions
        recent_transactions = Transaction.query.order_by(desc(Transaction.created_at)).limit(10).all()
        
        # Get MXC price
        mxc_price = get_current_mxc_price()
        
        # Get wallet pool stats using the correct status field
        from models.wallet_pool import WalletStatus
        total_wallets = PooledWallet.query.count()
        active_wallets = PooledWallet.query.filter(
            PooledWallet.status.in_([WalletStatus.AVAILABLE, WalletStatus.IN_USE])
        ).count()
        
        # Calculate total balances using wallet system
        from models.wallet import Wallet
        total_usdt_balance = Wallet.get_total_system_balance('available_fund') + Wallet.get_total_system_balance('main_balance')
        total_mxc_balance = 0  # MXC balance would be calculated separately if needed
        
        # Get recent users
        recent_users = User.query.order_by(desc(User.created_at)).limit(5).all()
        
        stats = {
            'total_users': total_users,
            'active_users': active_users,
            'total_transactions': total_transactions,
            'pending_transactions': pending_transactions,
            'total_wallets': total_wallets,
            'active_wallets': active_wallets,
            'total_usdt_balance': total_usdt_balance,
            'total_mxc_balance': total_mxc_balance,
            'mxc_price': mxc_price
        }
        
        return render_template('admin/dashboard.html', 
                             stats=stats,
                             recent_transactions=recent_transactions,
                             recent_users=recent_users)
        
    except Exception as e:
        flash(f'Error loading dashboard: {str(e)}', 'error')
        # Provide default stats structure
        default_stats = {
            'total_users': 0,
            'active_users': 0,
            'total_transactions': 0,
            'pending_transactions': 0,
            'total_wallets': 0,
            'active_wallets': 0,
            'total_usdt_balance': 0,
            'total_mxc_balance': 0,
            'mxc_price': None
        }
        return render_template('admin/dashboard.html',
                             stats=default_stats,
                             recent_transactions=[],
                             recent_users=[])


@admin_web_bp.route('/users')
@admin_session_required
def users():
    """User management page"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 20
        search = request.args.get('search', '').strip()
        status = request.args.get('status', 'all')
        
        # Build query
        query = User.query
        
        if search:
            query = query.filter(
                db.or_(
                    User.username.ilike(f'%{search}%'),
                    User.email.ilike(f'%{search}%'),
                    User.first_name.ilike(f'%{search}%'),
                    User.last_name.ilike(f'%{search}%')
                )
            )
        
        if status == 'active':
            query = query.filter_by(is_active=True)
        elif status == 'inactive':
            query = query.filter_by(is_active=False)
        
        users_pagination = query.order_by(desc(User.created_at)).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return render_template('admin/users.html', 
                             users=users_pagination,
                             search=search,
                             status=status)
        
    except Exception as e:
        flash(f'Error loading users: {str(e)}', 'error')
        return render_template('admin/users.html', users=None, search='', status='all')


@admin_web_bp.route('/users/<int:user_id>')
@admin_session_required
def user_detail(user_id):
    """User detail page"""
    try:
        user = User.query.get_or_404(user_id)

        # Initialize user wallets if they don't exist
        from models.wallet import Wallet
        Wallet.initialize_user_wallets(user_id)
        db.session.commit()

        # Get user transactions
        transactions = Transaction.query.filter_by(user_id=user_id).order_by(desc(Transaction.created_at)).limit(20).all()

        # Get user referrals (users who have this user as sponsor)
        referrals = User.query.filter_by(sponsor_id=user_id).all()

        # Get wallet balances for debugging
        wallet_balances = Wallet.get_user_balances(user_id)

        return render_template('admin/user_detail.html',
                             user=user,
                             transactions=transactions,
                             referrals=referrals,
                             wallet_balances=wallet_balances)

    except Exception as e:
        flash(f'Error loading user details: {str(e)}', 'error')
        return redirect(url_for('admin_web.users'))


@admin_web_bp.route('/transactions')
@admin_session_required
def transactions():
    """Transaction management page"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 20
        status = request.args.get('status', 'all')
        transaction_type = request.args.get('type', 'all')
        
        # Build query
        query = Transaction.query
        
        if status != 'all':
            if status == 'pending':
                query = query.filter_by(status=TransactionStatus.PENDING)
            elif status == 'completed':
                query = query.filter_by(status=TransactionStatus.COMPLETED)
            elif status == 'failed':
                query = query.filter_by(status=TransactionStatus.FAILED)
        
        if transaction_type != 'all':
            query = query.filter_by(transaction_type=transaction_type)
        
        transactions_pagination = query.order_by(desc(Transaction.created_at)).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return render_template('admin/transactions.html', 
                             transactions=transactions_pagination,
                             status=status,
                             transaction_type=transaction_type)
        
    except Exception as e:
        flash(f'Error loading transactions: {str(e)}', 'error')
        return render_template('admin/transactions.html', transactions=None, status='all', transaction_type='all')


@admin_web_bp.route('/mxc-price')
@admin_session_required
def mxc_price():
    """MXC price management page"""
    try:
        current_price = get_current_mxc_price()

        # Get recent chart data and convert to dictionaries
        chart_data_objects = MXCChartData.query.order_by(desc(MXCChartData.timestamp)).limit(100).all()
        chart_data = [chart_point.to_dict() for chart_point in chart_data_objects]

        return render_template('admin/mxc_price.html',
                             current_price=current_price,
                             chart_data=chart_data)

    except Exception as e:
        flash(f'Error loading MXC price data: {str(e)}', 'error')
        return render_template('admin/mxc_price.html', current_price=None, chart_data=[])


@admin_web_bp.route('/wallet-pool')
@admin_session_required
def wallet_pool():
    """Wallet pool management page"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        wallets_pagination = PooledWallet.query.order_by(desc(PooledWallet.created_at)).paginate(
            page=page, per_page=per_page, error_out=False
        )

        # Add assignment statistics to each wallet
        from sqlalchemy import func
        from models.wallet_pool import WalletAssignment

        for wallet in wallets_pagination.items:
            # Get assignment count for this wallet
            assignment_stats = db.session.query(
                func.count(WalletAssignment.id).label('total_assignments'),
                func.sum(func.coalesce(WalletAssignment.actual_amount, 0)).label('total_volume')
            ).filter_by(wallet_id=wallet.id).first()

            wallet.total_assignments = assignment_stats.total_assignments or 0
            wallet.total_assignment_volume = float(assignment_stats.total_volume or 0)
        
        # Get statistics
        from models.wallet_pool import WalletStatus

        total_wallets = PooledWallet.query.count()
        available_wallets = PooledWallet.query.filter_by(status=WalletStatus.AVAILABLE).count()
        in_use_wallets = PooledWallet.query.filter_by(status=WalletStatus.IN_USE).count()
        maintenance_wallets = PooledWallet.query.filter_by(status=WalletStatus.MAINTENANCE).count()

        # Get active assignments count
        active_assignments = WalletAssignment.query.filter_by(is_active=True).count()

        stats = {
            'total_wallets': total_wallets,
            'active_wallets': available_wallets + in_use_wallets,  # Active = Available + In Use
            'available_wallets': available_wallets,
            'assigned_wallets': active_assignments,  # Currently assigned wallets
            'maintenance_wallets': maintenance_wallets
        }
        
        return render_template('admin/wallet_pool.html', 
                             wallets=wallets_pagination,
                             stats=stats)
        
    except Exception as e:
        flash(f'Error loading wallet pool: {str(e)}', 'error')
        return render_template('admin/wallet_pool.html', wallets=None, stats={})


@admin_web_bp.route('/wallet-pool/wallets/<int:wallet_id>')
@admin_session_required
def wallet_details(wallet_id):
    """View detailed information for a specific wallet"""
    try:
        wallet = PooledWallet.query.get_or_404(wallet_id)

        # Get assignment statistics
        from sqlalchemy import func
        from models.wallet_pool import WalletAssignment

        assignment_stats = db.session.query(
            func.count(WalletAssignment.id).label('total_assignments'),
            func.sum(func.coalesce(WalletAssignment.actual_amount, 0)).label('total_volume')
        ).filter_by(wallet_id=wallet_id).first()

        wallet.total_assignments = assignment_stats.total_assignments or 0
        wallet.total_assignment_volume = float(assignment_stats.total_volume or 0)

        # Get current active assignment
        current_assignment = WalletAssignment.query.filter_by(
            wallet_id=wallet_id,
            is_active=True
        ).first()

        # Get recent assignments (last 10)
        recent_assignments = WalletAssignment.query.filter_by(wallet_id=wallet_id).order_by(
            desc(WalletAssignment.assigned_at)
        ).limit(10).all()

        # Get transaction count and volume for this wallet
        transaction_count = Transaction.query.filter_by(
            to_address=wallet.address
        ).count()

        total_volume = db.session.query(
            func.sum(Transaction.amount)
        ).filter_by(to_address=wallet.address).scalar() or 0

        return render_template('admin/wallet_details.html',
                             wallet=wallet,
                             current_assignment=current_assignment,
                             recent_assignments=recent_assignments,
                             transaction_count=transaction_count,
                             total_volume=float(total_volume))

    except Exception as e:
        flash(f'Error loading wallet details: {str(e)}', 'error')
        return redirect(url_for('admin_web.wallet_pool'))


@admin_web_bp.route('/wallet-pool/wallets/<int:wallet_id>/assignments')
@admin_session_required
def wallet_assignments(wallet_id):
    """View assignment history for a specific wallet"""
    try:
        wallet = PooledWallet.query.get_or_404(wallet_id)
        page = request.args.get('page', 1, type=int)
        per_page = 20

        assignments_pagination = WalletAssignment.query.filter_by(wallet_id=wallet_id).order_by(
            desc(WalletAssignment.assigned_at)
        ).paginate(page=page, per_page=per_page, error_out=False)

        return render_template('admin/wallet_assignments.html',
                             wallet=wallet,
                             assignments=assignments_pagination)

    except Exception as e:
        flash(f'Error loading wallet assignments: {str(e)}', 'error')
        return redirect(url_for('admin_web.wallet_pool'))


@admin_web_bp.route('/config')
@admin_session_required
def config():
    """System configuration page"""
    try:
        category = request.args.get('category', 'all')
        
        if category == 'all':
            configs = AdminConfig.query.all()
        else:
            configs = AdminConfig.query.filter_by(category=category).all()
        
        # Group configs by category
        config_groups = {}
        for config in configs:
            if config.category not in config_groups:
                config_groups[config.category] = []
            config_groups[config.category].append(config)
        
        # Get all categories
        categories = list(set(config.category for config in configs))
        
        return render_template('admin/config.html', 
                             config_groups=config_groups,
                             categories=categories,
                             selected_category=category)
        
    except Exception as e:
        flash(f'Error loading configuration: {str(e)}', 'error')
        return render_template('admin/config.html', config_groups={}, categories=[], selected_category='all')


# AJAX endpoints for admin operations
@admin_web_bp.route('/api/user/<int:user_id>/toggle-status', methods=['POST'])
@jwt_required()
@admin_required
def toggle_user_status(user_id):
    """Toggle user active status"""
    try:
        user = User.query.get_or_404(user_id)
        user.is_active = not user.is_active
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'User {"activated" if user.is_active else "deactivated"} successfully',
            'is_active': user.is_active
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_web_bp.route('/api/transaction/<int:transaction_id>/approve', methods=['POST'])
@jwt_required()
@admin_required
def approve_transaction(transaction_id):
    """Approve a pending transaction"""
    try:
        transaction = Transaction.query.get_or_404(transaction_id)
        
        if transaction.status != TransactionStatus.PENDING:
            return jsonify({'success': False, 'message': 'Transaction is not pending'}), 400
        
        transaction.status = TransactionStatus.COMPLETED
        transaction.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Transaction approved successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_web_bp.route('/api/transaction/<int:transaction_id>/reject', methods=['POST'])
@jwt_required()
@admin_required
def reject_transaction(transaction_id):
    """Reject a pending transaction"""
    try:
        transaction = Transaction.query.get_or_404(transaction_id)

        if transaction.status != TransactionStatus.PENDING:
            return jsonify({'success': False, 'message': 'Transaction is not pending'}), 400

        transaction.status = TransactionStatus.FAILED
        transaction.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Transaction rejected successfully'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_web_bp.route('/api/mxc-price', methods=['PUT'])
@jwt_required()
@admin_required
def update_mxc_price_api():
    """Update MXC price via API"""
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()

        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400

        # Get current price for defaults
        current_price = get_current_mxc_price()

        # Helper function to safely convert to int
        def safe_int(value, default):
            if value is None or value == '':
                return default
            try:
                return int(float(value))
            except (ValueError, TypeError):
                return default

        # Helper function to safely convert to float
        def safe_float(value, default):
            if value is None or value == '':
                return default
            try:
                return float(value)
            except (ValueError, TypeError):
                return default

        # Update MXC price
        price_data = {
            'price': safe_float(data.get('price'), 0),
            'market_cap': safe_int(data.get('market_cap'), current_price.get('market_cap', 15600000)),
            'volume_24h': safe_int(data.get('volume_24h'), current_price.get('volume_24h', 234500)),
            'holders': safe_int(data.get('holders'), current_price.get('holders', 12847)),
            'transactions_24h': safe_int(data.get('transactions_24h'), current_price.get('transactions_24h', 1247)),
            'rank': data.get('rank') or current_price.get('rank', '#1247'),
            'high_24h': safe_float(data.get('high_24h'), None),
            'low_24h': safe_float(data.get('low_24h'), None),
            'volume_change_24h': safe_float(data.get('volume_change_24h'), 0),
            'notes': data.get('notes')
        }

        result = update_mxc_price(price_data, current_user_id)

        # Add to chart data if requested
        if data.get('add_to_chart', False):
            from models.mxc import MXCChartData
            chart_point = MXCChartData(
                price=price_data['price'],
                volume=price_data.get('volume_24h'),
                timestamp=datetime.utcnow()
            )
            db.session.add(chart_point)
            db.session.commit()

        return jsonify({
            'success': True,
            'message': 'MXC price updated successfully',
            'price': result.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_web_bp.route('/api/mxc-chart/generate', methods=['POST'])
@jwt_required()
@admin_required
def generate_chart_data_api():
    """Generate MXC chart data via API"""
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()

        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400

        timeframe = data.get('timeframe', '24h')
        data_points = int(data.get('data_points', 24))
        base_price = float(data.get('base_price', 0.001))
        volatility = float(data.get('volatility', 5))

        # Generate chart data
        from models.mxc import MXCChartData
        generated_data = MXCChartData.generate_sample_data(timeframe=timeframe)

        return jsonify({
            'success': True,
            'message': f'Generated {len(generated_data)} chart data points',
            'data_points_generated': len(generated_data)
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_web_bp.route('/api/config', methods=['PUT'])
@jwt_required()
@admin_required
def update_config_api():
    """Update configuration via API"""
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()

        if not data:
            return jsonify({'success': False, 'message': 'No configuration data provided'}), 400

        updated_configs = []

        for key, value in data.items():
            if key.startswith('_'):  # Skip metadata fields
                continue

            config = set_config(key, value, updated_by=current_user_id)
            updated_configs.append(config.key)

        return jsonify({
            'success': True,
            'message': 'Configuration updated successfully',
            'updated_keys': updated_configs
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
