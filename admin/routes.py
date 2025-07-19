"""
Admin Routes for MetaX Coin Backend
Handles admin panel operations, MXC price control, and system management
"""

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from sqlalchemy import func

from models import db, User, Transaction, TransactionStatus, AdminConfig, PooledWallet
from services.mxc_service import update_mxc_price, get_current_mxc_price, add_chart_data_point
from services.admin_config import set_config, get_config
from auth.utils import admin_required

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/mxc-price', methods=['GET'])
@admin_required
def get_mxc_price_admin():
    """Get current MXC price data for admin"""
    try:
        price_data = get_current_mxc_price()
        return jsonify(price_data), 200
        
    except Exception as e:
        current_app.logger.error(f'Admin get MXC price error: {str(e)}')
        return jsonify({'error': 'Failed to get MXC price'}), 500


@admin_bp.route('/mxc-price', methods=['PUT'])
@admin_required
def update_mxc_price_admin():
    """Update MXC price data"""
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['price']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'{field} is required'}), 400
        
        # Validate price
        try:
            price = float(data['price'])
            if price <= 0:
                return jsonify({'error': 'Price must be positive'}), 400
        except ValueError:
            return jsonify({'error': 'Invalid price format'}), 400
        
        # Prepare price data
        price_data = {
            'price': price,
            'market_cap': data.get('market_cap'),
            'volume_24h': data.get('volume_24h'),
            'holders': data.get('holders'),
            'transactions_24h': data.get('transactions_24h'),
            'rank': data.get('rank'),
            'high_24h': data.get('high_24h'),
            'low_24h': data.get('low_24h'),
            'volume_change_24h': data.get('volume_change_24h'),
            'notes': data.get('notes')
        }
        
        # Update price
        new_price = update_mxc_price(price_data, current_user_id)
        
        current_app.logger.info(f'MXC price updated by admin {current_user_id}: {price}')
        
        return jsonify({
            'message': 'MXC price updated successfully',
            'price_data': new_price.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Admin update MXC price error: {str(e)}')
        return jsonify({'error': 'Failed to update MXC price'}), 500


@admin_bp.route('/users', methods=['GET'])
@admin_required
def get_users():
    """Get all users with pagination and filtering"""
    try:
        # Get query parameters
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 20)), 100)
        search = request.args.get('search', '').strip()
        status = request.args.get('status', 'all')  # all, active, inactive
        
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
        
        # Paginate
        pagination = query.order_by(User.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        users = [user.to_dict(include_sensitive=True) for user in pagination.items]
        
        return jsonify({
            'users': users,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f'Admin get users error: {str(e)}')
        return jsonify({'error': 'Failed to get users'}), 500


@admin_bp.route('/users/<int:user_id>/wallets', methods=['GET'])
@admin_required
def get_user_wallets(user_id):
    """Get user's wallet balances"""
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        from models.wallet import Wallet
        wallet_balances = Wallet.get_user_balances(user_id)
        
        return jsonify({
            'user': user.to_dict(),
            'wallet_balances': wallet_balances
        }), 200
        
    except Exception as e:
        current_app.logger.error(f'Admin get user wallets error: {str(e)}')
        return jsonify({'error': 'Failed to get user wallets'}), 500


@admin_bp.route('/users/<int:user_id>/wallets', methods=['PUT'])
@admin_required
def update_user_wallets(user_id):
    """Update user's wallet balances"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        wallet_updates = data.get('wallets', {})
        
        if not wallet_updates:
            return jsonify({'error': 'No wallet updates provided'}), 400
        
        from models.wallet import Wallet
        updated_wallets = []
        
        for wallet_type, new_balance in wallet_updates.items():
            if wallet_type not in Wallet.get_wallet_types():
                return jsonify({'error': f'Invalid wallet type: {wallet_type}'}), 400
            
            try:
                new_balance = float(new_balance)
                if new_balance < 0:
                    return jsonify({'error': f'Balance cannot be negative for {wallet_type}'}), 400
            except ValueError:
                return jsonify({'error': f'Invalid balance format for {wallet_type}'}), 400
            
            wallet = Wallet.query.filter_by(user_id=user_id, wallet_type=wallet_type).first()
            if wallet:
                old_balance = float(wallet.balance)
                wallet.balance = new_balance
                wallet.updated_at = datetime.utcnow()
                
                # Create transaction record for audit
                from models.transaction import Transaction, TransactionType
                transaction = Transaction(
                    user_id=user_id,
                    transaction_type=TransactionType.CREDIT if new_balance > old_balance else TransactionType.DEBIT,
                    wallet_type=wallet_type,
                    amount=abs(new_balance - old_balance),
                    status=TransactionStatus.COMPLETED,
                    description=f"Admin adjustment by user {current_user_id}",
                    admin_notes=data.get('notes', 'Manual balance adjustment')
                )
                db.session.add(transaction)
                
                updated_wallets.append({
                    'wallet_type': wallet_type,
                    'old_balance': old_balance,
                    'new_balance': new_balance
                })
        
        db.session.commit()
        
        current_app.logger.info(f'Wallet balances updated for user {user_id} by admin {current_user_id}')
        
        return jsonify({
            'message': 'Wallet balances updated successfully',
            'updated_wallets': updated_wallets
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Admin update user wallets error: {str(e)}')
        return jsonify({'error': 'Failed to update wallet balances'}), 500


@admin_bp.route('/transactions', methods=['GET'])
@admin_required
def get_pending_transactions():
    """Get pending transactions for admin approval"""
    try:
        # Get query parameters
        status = request.args.get('status', 'pending')
        transaction_type = request.args.get('type', 'all')
        limit = min(int(request.args.get('limit', 50)), 100)
        offset = int(request.args.get('offset', 0))
        
        # Build query
        query = Transaction.query
        
        if status != 'all':
            try:
                txn_status = TransactionStatus(status)
                query = query.filter_by(status=txn_status)
            except ValueError:
                return jsonify({'error': 'Invalid status'}), 400
        
        if transaction_type != 'all':
            try:
                from models.transaction import TransactionType
                txn_type = TransactionType(transaction_type)
                query = query.filter_by(transaction_type=txn_type)
            except ValueError:
                return jsonify({'error': 'Invalid transaction type'}), 400
        
        # Get transactions
        transactions = query.order_by(Transaction.created_at.asc()).offset(offset).limit(limit).all()
        total_count = query.count()
        
        return jsonify({
            'transactions': [txn.to_dict(include_sensitive=True) for txn in transactions],
            'pagination': {
                'total_count': total_count,
                'limit': limit,
                'offset': offset,
                'has_more': offset + limit < total_count
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f'Admin get transactions error: {str(e)}')
        return jsonify({'error': 'Failed to get transactions'}), 500


@admin_bp.route('/transactions/<int:transaction_id>', methods=['GET'])
@admin_required
def get_transaction_detail(transaction_id):
    """Get details of a specific transaction for admin"""
    try:
        transaction = Transaction.query.get(transaction_id)
        if not transaction:
            return jsonify({'error': 'Transaction not found'}), 404

        return jsonify({
            'transaction': transaction.to_dict(include_sensitive=True)
        }), 200

    except Exception as e:
        current_app.logger.error(f'Admin get transaction detail error: {str(e)}')
        return jsonify({'error': 'Failed to get transaction details'}), 500


@admin_bp.route('/transactions/<int:transaction_id>/approve', methods=['POST'])
@admin_required
def approve_transaction(transaction_id):
    """Approve a pending transaction"""
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json() or {}
        
        transaction = Transaction.query.get(transaction_id)
        if not transaction:
            return jsonify({'error': 'Transaction not found'}), 404
        
        if transaction.status != TransactionStatus.PENDING:
            return jsonify({'error': 'Transaction is not pending'}), 400
        
        # Approve transaction
        admin_notes = data.get('notes', f'Approved by admin {current_user_id}')
        transaction.approve(admin_notes)
        
        db.session.commit()
        
        current_app.logger.info(f'Transaction {transaction.transaction_id} approved by admin {current_user_id}')
        
        return jsonify({
            'message': 'Transaction approved successfully',
            'transaction': transaction.to_dict(include_sensitive=True)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Admin approve transaction error: {str(e)}')
        return jsonify({'error': 'Failed to approve transaction'}), 500


@admin_bp.route('/transactions/<int:transaction_id>/reject', methods=['POST'])
@admin_required
def reject_transaction(transaction_id):
    """Reject a pending transaction"""
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json() or {}
        
        transaction = Transaction.query.get(transaction_id)
        if not transaction:
            return jsonify({'error': 'Transaction not found'}), 404
        
        if transaction.status != TransactionStatus.PENDING:
            return jsonify({'error': 'Transaction is not pending'}), 400
        
        # Reject transaction
        reason = data.get('reason', 'Rejected by admin')
        admin_notes = data.get('notes', f'Rejected by admin {current_user_id}')
        transaction.reject(reason, admin_notes)
        
        db.session.commit()
        
        current_app.logger.info(f'Transaction {transaction.transaction_id} rejected by admin {current_user_id}')
        
        return jsonify({
            'message': 'Transaction rejected successfully',
            'transaction': transaction.to_dict(include_sensitive=True)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Admin reject transaction error: {str(e)}')
        return jsonify({'error': 'Failed to reject transaction'}), 500


@admin_bp.route('/config', methods=['GET'])
@admin_required
def get_admin_config():
    """Get admin configuration"""
    try:
        category = request.args.get('category', 'all')
        
        if category == 'all':
            configs = AdminConfig.query.all()
        else:
            configs = AdminConfig.query.filter_by(category=category).all()
        
        config_data = {}
        for config in configs:
            config_data[config.key] = config.to_dict(include_sensitive=True)
        
        return jsonify({
            'configurations': config_data,
            'categories': list(set(config.category for config in configs))
        }), 200
        
    except Exception as e:
        current_app.logger.error(f'Admin get config error: {str(e)}')
        return jsonify({'error': 'Failed to get configuration'}), 500


@admin_bp.route('/config', methods=['PUT'])
@admin_required
def update_admin_config():
    """Update admin configuration"""
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No configuration data provided'}), 400
        
        updated_configs = []
        
        for key, value in data.items():
            if key.startswith('_'):  # Skip metadata fields
                continue
            
            config = set_config(key, value, updated_by=current_user_id)
            updated_configs.append(config.key)
        
        current_app.logger.info(f'Configuration updated by admin {current_user_id}: {updated_configs}')
        
        return jsonify({
            'message': 'Configuration updated successfully',
            'updated_keys': updated_configs
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Admin update config error: {str(e)}')
        return jsonify({'error': 'Failed to update configuration'}), 500


@admin_bp.route('/income/distribute', methods=['POST'])
@admin_required
def distribute_income():
    """Manually distribute income to users (staking rewards, bonuses)"""
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()

        # Validate required fields
        required_fields = ['income_type', 'amount', 'recipients']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400

        income_type = data['income_type']
        amount = float(data['amount'])
        recipients = data['recipients']  # List of user IDs or 'all'
        description = data.get('description', f'Manual {income_type} distribution')
        wallet_type = data.get('wallet_type', 'total_gain')

        # Validate amount
        if amount <= 0:
            return jsonify({'error': 'Amount must be positive'}), 400

        # Validate wallet type
        from models.wallet import Wallet
        if wallet_type not in Wallet.get_wallet_types():
            return jsonify({'error': 'Invalid wallet type'}), 400

        # Get recipient users
        if recipients == 'all':
            users = User.query.filter_by(is_active=True).all()
        elif isinstance(recipients, list):
            users = User.query.filter(User.id.in_(recipients)).all()
        else:
            return jsonify({'error': 'Invalid recipients format'}), 400

        if not users:
            return jsonify({'error': 'No valid recipients found'}), 400

        # Distribute income
        distributed_count = 0
        total_distributed = 0

        for user in users:
            # Add to user's wallet
            wallet = Wallet.query.filter_by(
                user_id=user.id,
                wallet_type=wallet_type
            ).first()

            if wallet:
                wallet.add_balance(amount, description)

                # Create income record
                from models.income import Income
                income = Income.create_bonus_income(
                    user_id=user.id,
                    amount=amount,
                    bonus_type=income_type,
                    description=description
                )

                distributed_count += 1
                total_distributed += amount

        db.session.commit()

        current_app.logger.info(f'Income distributed by admin {current_user_id}: {total_distributed} to {distributed_count} users')

        return jsonify({
            'message': 'Income distributed successfully',
            'distributed_count': distributed_count,
            'total_amount': total_distributed,
            'income_type': income_type,
            'wallet_type': wallet_type
        }), 200

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Admin distribute income error: {str(e)}')
        return jsonify({'error': 'Failed to distribute income'}), 500


@admin_bp.route('/mxc-chart', methods=['POST'])
@admin_required
def add_mxc_chart_data():
    """Admin can add chart data points for MXC price graph"""
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()

        # Validate required fields
        required_fields = ['price']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400

        price = float(data['price'])
        volume = data.get('volume')
        timestamp = data.get('timestamp')

        # Validate price
        if price <= 0:
            return jsonify({'error': 'Price must be positive'}), 400

        # Parse timestamp if provided
        if timestamp:
            try:
                from datetime import datetime
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except ValueError:
                return jsonify({'error': 'Invalid timestamp format. Use ISO format.'}), 400

        # Add chart data point
        from services.mxc_service import add_chart_data_point
        chart_point = add_chart_data_point(price, volume, timestamp)

        db.session.commit()

        current_app.logger.info(f'MXC chart data added by admin {current_user_id}: price={price}')

        return jsonify({
            'message': 'Chart data point added successfully',
            'chart_point': chart_point.to_dict()
        }), 201

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Admin add chart data error: {str(e)}')
        return jsonify({'error': 'Failed to add chart data'}), 500


@admin_bp.route('/mxc-chart/generate', methods=['POST'])
@admin_required
def generate_mxc_chart_data():
    """Auto-generate chart data based on current price and timeframe"""
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json() or {}

        timeframe = data.get('timeframe', '24h')
        data_points = int(data.get('data_points', 24))

        # Validate parameters
        valid_timeframes = ['1h', '4h', '24h', '7d']
        if timeframe not in valid_timeframes:
            return jsonify({'error': 'Invalid timeframe. Use: 1h, 4h, 24h, 7d'}), 400

        if data_points < 1 or data_points > 1000:
            return jsonify({'error': 'Data points must be between 1 and 1000'}), 400

        # Generate chart data
        from models.mxc import MXCChartData
        generated_data = MXCChartData.generate_sample_data(timeframe)

        current_app.logger.info(f'MXC chart data generated by admin {current_user_id}: {len(generated_data)} points for {timeframe}')

        return jsonify({
            'message': 'Chart data generated successfully',
            'timeframe': timeframe,
            'data_points_generated': len(generated_data),
            'sample_data': [point.to_dict() for point in generated_data[:5]]  # Show first 5 points
        }), 201

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Admin generate chart data error: {str(e)}')
        return jsonify({'error': 'Failed to generate chart data'}), 500


@admin_bp.route('/wallet-pool/stats', methods=['GET'])
@admin_required
def get_wallet_pool_stats():
    """Get wallet pool statistics"""
    try:
        from services.wallet_pool import get_wallet_pool_statistics
        stats = get_wallet_pool_statistics()

        return jsonify(stats), 200

    except Exception as e:
        current_app.logger.error(f'Admin get wallet pool stats error: {str(e)}')
        return jsonify({'error': 'Failed to get wallet pool statistics'}), 500


@admin_bp.route('/wallet-pool/wallets', methods=['GET'])
@admin_required
def get_pooled_wallets():
    """Get all pooled wallets with their status"""
    try:
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 20)), 100)
        status = request.args.get('status', 'all')  # all, available, in_use, disabled

        # Build query
        query = PooledWallet.query

        if status != 'all':
            from models.wallet_pool import WalletStatus
            try:
                wallet_status = WalletStatus(status.upper())
                query = query.filter_by(status=wallet_status)
            except ValueError:
                return jsonify({'error': 'Invalid status'}), 400

        # Paginate
        pagination = query.order_by(PooledWallet.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        wallets = [wallet.to_dict(include_sensitive=True) for wallet in pagination.items]

        return jsonify({
            'wallets': wallets,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
        }), 200

    except Exception as e:
        current_app.logger.error(f'Admin get pooled wallets error: {str(e)}')
        return jsonify({'error': 'Failed to get pooled wallets'}), 500


@admin_bp.route('/wallet-pool/wallets', methods=['POST'])
@admin_required
def add_pooled_wallet():
    """Add a new wallet to the pool"""
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()

        # Validate required fields
        required_fields = ['address']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400

        address = data['address'].strip()
        private_key = data.get('private_key', '').strip()
        network = data.get('network', 'TRON')
        label = data.get('label', '').strip()
        notes = data.get('notes', '').strip()

        # Check if wallet already exists
        existing_wallet = PooledWallet.query.filter_by(address=address).first()
        if existing_wallet:
            return jsonify({'error': 'Wallet address already exists in pool'}), 400

        # Create new pooled wallet
        from models.wallet_pool import WalletStatus
        new_wallet = PooledWallet(
            address=address,
            private_key=private_key,
            network=network,
            label=label,
            notes=notes,
            status=WalletStatus.AVAILABLE
        )

        db.session.add(new_wallet)
        db.session.commit()

        current_app.logger.info(f'New pooled wallet added by admin {current_user_id}: {address}')

        return jsonify({
            'message': 'Wallet added to pool successfully',
            'wallet': new_wallet.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Admin add pooled wallet error: {str(e)}')
        return jsonify({'error': 'Failed to add wallet to pool'}), 500


@admin_bp.route('/wallet-pool/wallets/<int:wallet_id>', methods=['GET'])
@admin_required
def get_pooled_wallet_details(wallet_id):
    """Get details of a specific pooled wallet"""
    try:
        wallet = PooledWallet.query.get(wallet_id)

        if not wallet:
            return jsonify({'error': 'Wallet not found'}), 404

        # Get wallet assignments with user details
        from models.wallet_pool import WalletAssignment
        assignments = WalletAssignment.query.filter_by(wallet_id=wallet_id).order_by(
            WalletAssignment.assigned_at.desc()
        ).limit(20).all()

        # Get current active assignment
        current_assignment = WalletAssignment.query.filter_by(
            wallet_id=wallet_id,
            is_active=True
        ).first()

        # Get transaction count and volume for this wallet
        # Check transactions where this wallet was the destination (deposits)
        transaction_count = Transaction.query.filter_by(
            to_address=wallet.address
        ).count()

        total_volume = db.session.query(
            func.sum(Transaction.amount)
        ).filter_by(to_address=wallet.address).scalar() or 0

        # Prepare assignment data with user information
        assignment_data = []
        for assignment in assignments:
            assignment_dict = assignment.to_dict()
            if assignment.user:
                assignment_dict['user_info'] = {
                    'id': assignment.user.id,
                    'username': assignment.user.username,
                    'email': assignment.user.email,
                    'full_name': assignment.user.get_full_name()
                }
            assignment_data.append(assignment_dict)

        wallet_data = wallet.to_dict()
        wallet_data.update({
            'transaction_count': transaction_count,
            'total_volume': float(total_volume),
            'total_assignments': len(assignments),
            'current_assignment': current_assignment.to_dict() if current_assignment else None,
            'assignment_history': assignment_data,
            'network': wallet.network,
            'label': wallet.label,
            'notes': wallet.notes
        })

        return jsonify({
            'wallet': wallet_data,
            'success': True
        }), 200

    except Exception as e:
        current_app.logger.error(f'Admin get wallet details error: {str(e)}')
        return jsonify({'error': 'Failed to get wallet details'}), 500


@admin_bp.route('/wallet-pool/wallets/<int:wallet_id>', methods=['PUT'])
@admin_required
def update_pooled_wallet(wallet_id):
    """Update a pooled wallet"""
    try:
        current_user_id = get_jwt_identity()
        wallet = PooledWallet.query.get(wallet_id)

        if not wallet:
            return jsonify({'error': 'Wallet not found'}), 404

        data = request.get_json()

        # Update allowed fields
        updatable_fields = ['status', 'label', 'notes', 'network']
        updated_fields = []

        for field in updatable_fields:
            if field in data:
                if field == 'status':
                    from models.wallet_pool import WalletStatus
                    try:
                        new_status = WalletStatus(data[field].upper())
                        wallet.status = new_status
                        updated_fields.append(field)
                    except ValueError:
                        return jsonify({'error': f'Invalid status: {data[field]}'}), 400
                else:
                    setattr(wallet, field, data[field])
                    updated_fields.append(field)

        if updated_fields:
            wallet.updated_at = datetime.utcnow()
            db.session.commit()

            current_app.logger.info(f'Pooled wallet {wallet_id} updated by admin {current_user_id}: {updated_fields}')

            return jsonify({
                'message': 'Wallet updated successfully',
                'updated_fields': updated_fields,
                'wallet': wallet.to_dict()
            }), 200
        else:
            return jsonify({'message': 'No fields to update'}), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Admin update pooled wallet error: {str(e)}')
        return jsonify({'error': 'Failed to update wallet'}), 500


@admin_bp.route('/wallet-pool/wallets/<int:wallet_id>/toggle-status', methods=['PUT'])
@admin_required
def toggle_wallet_status(wallet_id):
    """Toggle wallet status between available and maintenance"""
    try:
        current_user_id = get_jwt_identity()
        wallet = PooledWallet.query.get(wallet_id)

        if not wallet:
            return jsonify({'error': 'Wallet not found'}), 404

        # Toggle between AVAILABLE and MAINTENANCE
        from models.wallet_pool import WalletStatus
        if wallet.status == WalletStatus.AVAILABLE:
            wallet.status = WalletStatus.MAINTENANCE
            new_status = 'maintenance'
        else:
            wallet.status = WalletStatus.AVAILABLE
            new_status = 'available'

        wallet.updated_at = datetime.utcnow()
        db.session.commit()

        current_app.logger.info(f'Wallet {wallet_id} status toggled to {new_status} by admin {current_user_id}')

        return jsonify({
            'message': f'Wallet status changed to {new_status}',
            'wallet': wallet.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Admin toggle wallet status error: {str(e)}')
        return jsonify({'error': 'Failed to toggle wallet status'}), 500


@admin_bp.route('/wallet-pool/wallets/<int:wallet_id>', methods=['DELETE'])
@admin_required
def delete_pooled_wallet(wallet_id):
    """Delete a pooled wallet"""
    try:
        current_user_id = get_jwt_identity()
        wallet = PooledWallet.query.get(wallet_id)

        if not wallet:
            return jsonify({'error': 'Wallet not found'}), 404

        # Check if wallet is currently assigned
        from models.wallet_pool import WalletAssignment
        active_assignment = WalletAssignment.query.filter_by(
            wallet_id=wallet_id, is_active=True
        ).first()

        if active_assignment:
            return jsonify({'error': 'Cannot delete wallet that is currently assigned to a user'}), 400

        # Delete the wallet
        db.session.delete(wallet)
        db.session.commit()

        current_app.logger.info(f'Pooled wallet {wallet_id} deleted by admin {current_user_id}')

        return jsonify({
            'success': True,
            'message': 'Wallet deleted successfully'
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Admin delete wallet error: {str(e)}')
        return jsonify({'error': 'Failed to delete wallet'}), 500


@admin_bp.route('/wallet-pool/wallets/<int:wallet_id>/balance', methods=['GET'])
@admin_required
def check_wallet_balance(wallet_id):
    """Check balance of a specific wallet"""
    try:
        wallet = PooledWallet.query.get(wallet_id)

        if not wallet:
            return jsonify({'error': 'Wallet not found'}), 404

        # For now, return a mock balance since we don't have blockchain integration
        # In production, this would call the actual blockchain API
        balance = "0.00"  # Mock balance

        # Update last checked timestamp
        wallet.last_checked_at = datetime.utcnow()
        db.session.commit()

        return jsonify({
            'success': True,
            'balance': balance,
            'currency': 'USDT',
            'last_checked': wallet.last_checked_at.isoformat()
        }), 200

    except Exception as e:
        current_app.logger.error(f'Admin check wallet balance error: {str(e)}')
        return jsonify({'error': 'Failed to check wallet balance'}), 500


@admin_bp.route('/wallet-pool/check-balances', methods=['POST'])
@admin_required
def check_all_wallet_balances():
    """Check balances of all active wallets"""
    try:
        from models.wallet_pool import WalletStatus
        active_wallets = PooledWallet.query.filter(
            PooledWallet.status.in_([WalletStatus.AVAILABLE, WalletStatus.IN_USE])
        ).all()

        checked_count = 0
        for wallet in active_wallets:
            # Mock balance check - in production, call blockchain API
            wallet.last_checked_at = datetime.utcnow()
            checked_count += 1

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Checked balances for {checked_count} wallets',
            'checked_count': checked_count
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Admin check all balances error: {str(e)}')
        return jsonify({'error': 'Failed to check wallet balances'}), 500


@admin_bp.route('/wallet-pool/bulk-activate', methods=['POST'])
@admin_required
def bulk_activate_wallets():
    """Activate multiple wallets (set status to AVAILABLE)"""
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        wallet_ids = data.get('wallet_ids', [])

        if not wallet_ids:
            return jsonify({'error': 'No wallet IDs provided'}), 400

        from models.wallet_pool import WalletStatus
        wallets = PooledWallet.query.filter(PooledWallet.id.in_(wallet_ids)).all()
        activated_count = 0

        for wallet in wallets:
            if wallet.status != WalletStatus.AVAILABLE:
                wallet.status = WalletStatus.AVAILABLE
                wallet.updated_at = datetime.utcnow()
                activated_count += 1

        db.session.commit()

        current_app.logger.info(f'Bulk activated {activated_count} wallets by admin {current_user_id}')

        return jsonify({
            'success': True,
            'message': f'Activated {activated_count} wallets',
            'activated_count': activated_count
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Admin bulk activate error: {str(e)}')
        return jsonify({'error': 'Failed to activate wallets'}), 500


@admin_bp.route('/wallet-pool/bulk-deactivate', methods=['POST'])
@admin_required
def bulk_deactivate_wallets():
    """Deactivate multiple wallets (set status to DISABLED)"""
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        wallet_ids = data.get('wallet_ids', [])

        if not wallet_ids:
            return jsonify({'error': 'No wallet IDs provided'}), 400

        # Check if any wallets are currently assigned
        from models.wallet_pool import WalletAssignment, WalletStatus
        active_assignments = WalletAssignment.query.filter(
            WalletAssignment.wallet_id.in_(wallet_ids),
            WalletAssignment.is_active == True
        ).all()

        if active_assignments:
            assigned_wallet_ids = [a.wallet_id for a in active_assignments]
            return jsonify({
                'error': f'Cannot deactivate wallets that are currently assigned: {assigned_wallet_ids}'
            }), 400

        wallets = PooledWallet.query.filter(PooledWallet.id.in_(wallet_ids)).all()
        deactivated_count = 0

        for wallet in wallets:
            if wallet.status != WalletStatus.DISABLED:
                wallet.status = WalletStatus.DISABLED
                wallet.updated_at = datetime.utcnow()
                deactivated_count += 1

        db.session.commit()

        current_app.logger.info(f'Bulk deactivated {deactivated_count} wallets by admin {current_user_id}')

        return jsonify({
            'success': True,
            'message': f'Deactivated {deactivated_count} wallets',
            'deactivated_count': deactivated_count
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Admin bulk deactivate error: {str(e)}')
        return jsonify({'error': 'Failed to deactivate wallets'}), 500


@admin_bp.route('/wallet-pool/assignments', methods=['GET'])
@admin_required
def get_wallet_assignments():
    """Get wallet assignments with filtering"""
    try:
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 20)), 100)
        status = request.args.get('status', 'all')  # all, active, completed, cancelled

        # Build query
        from models.wallet_pool import WalletAssignment
        query = WalletAssignment.query

        if status == 'active':
            query = query.filter_by(is_active=True)
        elif status == 'completed':
            query = query.filter(WalletAssignment.completed_at.isnot(None))
        elif status == 'cancelled':
            query = query.filter(WalletAssignment.cancelled_at.isnot(None))

        # Paginate
        pagination = query.order_by(WalletAssignment.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        assignments = []
        for assignment in pagination.items:
            assignment_data = assignment.to_dict(include_wallet_info=True)

            # Add user info
            user = User.query.get(assignment.user_id)
            if user:
                assignment_data['user'] = {
                    'username': user.username,
                    'full_name': user.get_full_name(),
                    'email': user.email
                }

            assignments.append(assignment_data)

        return jsonify({
            'assignments': assignments,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
        }), 200

    except Exception as e:
        current_app.logger.error(f'Admin get wallet assignments error: {str(e)}')
        return jsonify({'error': 'Failed to get wallet assignments'}), 500
