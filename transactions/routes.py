"""
Transaction Routes for MetaX Coin Backend
Handles deposits, withdrawals, and transaction management
"""

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from sqlalchemy import func

from models import db, User, Wallet, Transaction, TransactionType, TransactionStatus
from services.wallet_pool import assign_wallet_to_user, get_user_active_assignment
from services.admin_config import get_transaction_limits
from auth.utils import active_user_required, verified_user_required

transactions_bp = Blueprint('transactions', __name__)


@transactions_bp.route('/deposit', methods=['POST'])
@jwt_required()
@active_user_required
def deposit():
    """Create a deposit transaction (admin approval required)"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)

        if not user:
            return jsonify({'error': 'User not found'}), 404

        data = request.get_json()

        # Validate required fields
        required_fields = ['amount', 'wallet_type']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400

        amount = float(data['amount'])
        wallet_type = data['wallet_type']
        description = data.get('description', '')

        # Validate amount
        if amount <= 0:
            return jsonify({'error': 'Amount must be positive'}), 400

        # Check transaction limits
        limits = get_transaction_limits()
        if amount < limits['min_deposit']:
            return jsonify({'error': f'Minimum deposit amount is {limits["min_deposit"]} USDT'}), 400

        if amount > limits['max_deposit']:
            return jsonify({'error': f'Maximum deposit amount is {limits["max_deposit"]} USDT'}), 400

        # Validate wallet type
        if wallet_type not in Wallet.get_wallet_types():
            return jsonify({'error': 'Invalid wallet type'}), 400

        # Create deposit transaction (pending admin approval)
        transaction = Transaction(
            user_id=current_user_id,
            transaction_type=TransactionType.DEPOSIT,
            wallet_type=wallet_type,
            amount=amount,
            status=TransactionStatus.PENDING,
            description=description or f"Deposit to {wallet_type}"
        )

        db.session.add(transaction)
        db.session.commit()

        current_app.logger.info(f'Deposit transaction created: {transaction.transaction_id} for user {current_user_id}')

        return jsonify({
            'message': 'Deposit transaction created successfully',
            'transaction': transaction.to_dict(),
            'status': 'pending_admin_approval'
        }), 201

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Deposit error: {str(e)}')
        return jsonify({'error': 'Failed to create deposit'}), 500


@transactions_bp.route('/deposit/request', methods=['POST'])
@jwt_required()
@active_user_required
def request_deposit():
    """Request a crypto deposit by assigning a wallet"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        amount = data.get('amount')
        
        if not amount or amount <= 0:
            return jsonify({'error': 'Valid amount is required'}), 400
        
        # Check transaction limits
        limits = get_transaction_limits()
        if amount < limits['min_deposit']:
            return jsonify({'error': f'Minimum deposit amount is {limits["min_deposit"]} USDT'}), 400
        
        if amount > limits['max_deposit']:
            return jsonify({'error': f'Maximum deposit amount is {limits["max_deposit"]} USDT'}), 400
        
        # Check if user already has an active assignment
        existing_assignment = get_user_active_assignment(current_user_id)
        if existing_assignment:
            return jsonify({
                'error': 'You already have an active deposit request',
                'existing_assignment': existing_assignment.to_dict(include_wallet_info=True)
            }), 400
        
        # Assign a wallet
        assignment = assign_wallet_to_user(current_user_id, amount)
        if not assignment:
            return jsonify({'error': 'No wallets available. Please try again later.'}), 503
        
        current_app.logger.info(f'Deposit request created for user {current_user_id}: {amount} USDT')
        
        return jsonify({
            'message': 'Deposit wallet assigned successfully',
            'assignment': assignment.to_dict(include_wallet_info=True),
            'instructions': {
                'network': 'TRON (TRC20)',
                'token': 'USDT',
                'amount': amount,
                'wallet_address': assignment.wallet.address,
                'expires_at': assignment.expires_at.isoformat(),
                'time_remaining_minutes': int(assignment.time_remaining.total_seconds() / 60)
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f'Request deposit error: {str(e)}')
        return jsonify({'error': 'Failed to request deposit'}), 500


@transactions_bp.route('/deposit/status', methods=['GET'])
@jwt_required()
def get_deposit_status():
    """Get current deposit status"""
    try:
        current_user_id = get_jwt_identity()

        # Get active assignment
        assignment = get_user_active_assignment(current_user_id)

        if not assignment:
            return jsonify({
                'has_active_deposit': False,
                'message': 'No active deposit request'
            }), 200

        return jsonify({
            'has_active_deposit': True,
            'assignment': assignment.to_dict(include_wallet_info=True),
            'time_remaining_minutes': int(assignment.time_remaining.total_seconds() / 60),
            'is_expired': assignment.is_expired
        }), 200

    except Exception as e:
        current_app.logger.error(f'Get deposit status error: {str(e)}')
        return jsonify({'error': 'Failed to get deposit status'}), 500


@transactions_bp.route('/deposit/cancel', methods=['POST'])
@jwt_required()
@active_user_required
def cancel_deposit_assignment():
    """Cancel active deposit assignment"""
    try:
        current_user_id = get_jwt_identity()

        # Get user's active assignment
        assignment = get_user_active_assignment(current_user_id)

        if not assignment:
            return jsonify({'error': 'No active deposit assignment found'}), 404

        # Cancel the assignment
        assignment.cancel_assignment('Cancelled by user')

        db.session.commit()

        current_app.logger.info(f'Deposit assignment cancelled by user {current_user_id}: {assignment.id}')

        return jsonify({
            'message': 'Deposit assignment cancelled successfully'
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Cancel deposit assignment error: {str(e)}')
        return jsonify({'error': 'Failed to cancel deposit assignment'}), 500


@transactions_bp.route('/withdraw', methods=['POST'])
@jwt_required()
@verified_user_required
def request_withdrawal():
    """Request a withdrawal"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['amount', 'wallet_address', 'wallet_type']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        amount = float(data['amount'])
        wallet_address = data['wallet_address'].strip()
        wallet_type = data['wallet_type']
        description = data.get('description', '')
        
        # Validate amount
        if amount <= 0:
            return jsonify({'error': 'Amount must be positive'}), 400
        
        # Check transaction limits
        limits = get_transaction_limits()
        if amount < limits['min_withdrawal']:
            return jsonify({'error': f'Minimum withdrawal amount is {limits["min_withdrawal"]} USDT'}), 400
        
        if amount > limits['max_withdrawal']:
            return jsonify({'error': f'Maximum withdrawal amount is {limits["max_withdrawal"]} USDT'}), 400
        
        # CRITICAL: Only allow withdrawal from available_fund wallet
        if wallet_type != 'available_fund':
            return jsonify({
                'error': 'Withdrawals only allowed from Available Fund wallet',
                'message': 'Contact admin to move funds to Available Fund for withdrawal'
            }), 400
        
        # Get user's wallet
        wallet = Wallet.query.filter_by(
            user_id=current_user_id,
            wallet_type=wallet_type
        ).first()
        
        if not wallet:
            return jsonify({'error': 'Wallet not found'}), 404
        
        # Check balance (including withdrawal fee)
        withdrawal_fee = limits['withdrawal_fee']
        total_amount = amount + withdrawal_fee
        
        if wallet.available_balance < total_amount:
            return jsonify({
                'error': 'Insufficient balance',
                'available_balance': float(wallet.available_balance),
                'required_amount': total_amount,
                'withdrawal_fee': withdrawal_fee
            }), 400
        
        # Create withdrawal transaction
        transaction = Transaction(
            user_id=current_user_id,
            transaction_type=TransactionType.WITHDRAWAL,
            wallet_type=wallet_type,
            amount=amount,
            fee=withdrawal_fee,
            status=TransactionStatus.PENDING,
            to_address=wallet_address,
            description=description or f"Withdrawal to {wallet_address}"
        )
        
        db.session.add(transaction)
        
        # Lock the funds
        wallet.lock_balance(total_amount)
        
        db.session.commit()
        
        current_app.logger.info(f'Withdrawal request created: {transaction.transaction_id} for user {current_user_id}')
        
        return jsonify({
            'message': 'Withdrawal request submitted successfully',
            'transaction': transaction.to_dict(),
            'status': 'pending_admin_approval',
            'estimated_processing_time': '24-48 hours'
        }), 201
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Request withdrawal error: {str(e)}')
        return jsonify({'error': 'Failed to request withdrawal'}), 500


@transactions_bp.route('/history', methods=['GET'])
@jwt_required()
def get_transaction_history():
    """Get user's transaction history"""
    try:
        current_user_id = get_jwt_identity()
        
        # Get query parameters
        transaction_type = request.args.get('type')
        status = request.args.get('status')
        wallet_type = request.args.get('wallet_type')
        limit = min(int(request.args.get('limit', 50)), 100)
        offset = int(request.args.get('offset', 0))
        
        # Build query
        query = Transaction.query.filter_by(user_id=current_user_id)
        
        if transaction_type:
            try:
                txn_type = TransactionType(transaction_type)
                query = query.filter_by(transaction_type=txn_type)
            except ValueError:
                return jsonify({'error': 'Invalid transaction type'}), 400
        
        if status:
            try:
                txn_status = TransactionStatus(status)
                query = query.filter_by(status=txn_status)
            except ValueError:
                return jsonify({'error': 'Invalid status'}), 400
        
        if wallet_type:
            query = query.filter_by(wallet_type=wallet_type)
        
        # Get transactions
        transactions = query.order_by(Transaction.created_at.desc()).offset(offset).limit(limit).all()
        total_count = query.count()
        
        return jsonify({
            'transactions': [txn.to_dict() for txn in transactions],
            'pagination': {
                'total_count': total_count,
                'limit': limit,
                'offset': offset,
                'has_more': offset + limit < total_count
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f'Get transaction history error: {str(e)}')
        return jsonify({'error': 'Failed to get transaction history'}), 500


@transactions_bp.route('/<transaction_id>', methods=['GET'])
@jwt_required()
def get_transaction_details(transaction_id):
    """Get details of a specific transaction"""
    try:
        current_user_id = get_jwt_identity()
        
        transaction = Transaction.query.filter_by(
            transaction_id=transaction_id,
            user_id=current_user_id
        ).first()
        
        if not transaction:
            return jsonify({'error': 'Transaction not found'}), 404
        
        return jsonify({
            'transaction': transaction.to_dict(include_sensitive=True)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f'Get transaction details error: {str(e)}')
        return jsonify({'error': 'Failed to get transaction details'}), 500


@transactions_bp.route('/limits', methods=['GET'])
@jwt_required()
def get_transaction_limits_endpoint():
    """Get current transaction limits"""
    try:
        limits = get_transaction_limits()
        return jsonify(limits), 200

    except Exception as e:
        current_app.logger.error(f'Get transaction limits error: {str(e)}')
        return jsonify({'error': 'Failed to get transaction limits'}), 500


@transactions_bp.route('/cancel/<transaction_id>', methods=['POST'])
@jwt_required()
def cancel_transaction(transaction_id):
    """Cancel a pending transaction"""
    try:
        current_user_id = get_jwt_identity()
        
        transaction = Transaction.query.filter_by(
            transaction_id=transaction_id,
            user_id=current_user_id,
            status=TransactionStatus.PENDING
        ).first()
        
        if not transaction:
            return jsonify({'error': 'Transaction not found or cannot be cancelled'}), 404
        
        # Only allow cancellation of withdrawals
        if transaction.transaction_type != TransactionType.WITHDRAWAL:
            return jsonify({'error': 'Only withdrawal transactions can be cancelled'}), 400
        
        # Cancel the transaction
        transaction.cancel("Cancelled by user")
        
        # Unlock the funds if it was a withdrawal
        if transaction.transaction_type == TransactionType.WITHDRAWAL:
            wallet = Wallet.query.filter_by(
                user_id=current_user_id,
                wallet_type=transaction.wallet_type
            ).first()
            
            if wallet:
                total_amount = transaction.amount + transaction.fee
                wallet.unlock_balance(total_amount)
        
        db.session.commit()
        
        current_app.logger.info(f'Transaction cancelled: {transaction_id} by user {current_user_id}')
        
        return jsonify({
            'message': 'Transaction cancelled successfully',
            'transaction': transaction.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Cancel transaction error: {str(e)}')
        return jsonify({'error': 'Failed to cancel transaction'}), 500


# USER TRANSFER FUNCTIONALITY REMOVED
# Per user preference: Admin-only wallet transfers

@transactions_bp.route('/transfer', methods=['POST'])
@jwt_required()
@active_user_required
def transfer_between_wallets():
    """Transfer funds between user's wallets - DISABLED"""
    return jsonify({
        'error': 'User transfers are disabled. Only admin can manage wallet transfers.',
        'message': 'Contact admin for wallet fund movements.'
    }), 403


@transactions_bp.route('/statistics', methods=['GET'])
@jwt_required()
def get_transaction_statistics():
    """Get user's transaction statistics"""
    try:
        current_user_id = get_jwt_identity()

        # Get transaction counts by type and status
        stats = {}

        for txn_type in TransactionType:
            type_stats = {}
            for status in TransactionStatus:
                count = Transaction.query.filter_by(
                    user_id=current_user_id,
                    transaction_type=txn_type,
                    status=status
                ).count()
                type_stats[status.value] = count
            stats[txn_type.value] = type_stats

        # Get total amounts

        total_deposits = db.session.query(func.sum(Transaction.amount)).filter_by(
            user_id=current_user_id,
            transaction_type=TransactionType.DEPOSIT,
            status=TransactionStatus.COMPLETED
        ).scalar() or 0

        total_withdrawals = db.session.query(func.sum(Transaction.amount)).filter_by(
            user_id=current_user_id,
            transaction_type=TransactionType.WITHDRAWAL,
            status=TransactionStatus.COMPLETED
        ).scalar() or 0

        return jsonify({
            # Direct access format for frontend
            'deposit': stats.get('deposit', {}),
            'withdrawal': stats.get('withdrawal', {}),
            'transfer': stats.get('transfer', {}),
            'total_deposits': float(total_deposits),
            'total_withdrawals': float(total_withdrawals),
            'net_deposits': float(total_deposits - total_withdrawals),

            # Additional fields expected by frontend (with defaults)
            'total_transfers': 0.0,  # Not currently tracked
            'average_transaction_amount': 0.0,  # Not currently calculated
            'most_used_wallet': 'available_fund',  # Default
            'transaction_frequency': {
                'daily_average': 0.0,
                'weekly_average': 0.0,
                'monthly_average': 0.0
            }
        }), 200

    except Exception as e:
        current_app.logger.error(f'Get transaction statistics error: {str(e)}')
        return jsonify({'error': 'Failed to get transaction statistics'}), 500
