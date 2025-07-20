"""
Admin Investment Management Routes
Handles admin operations for investment packages and user investments
"""

from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash
from datetime import datetime, date, timedelta
from decimal import Decimal, InvalidOperation

from models import db, User
from models.investment import InvestmentPackage, UserInvestment, InvestmentReturn, PackageStatus, InvestmentStatus
from services.investment_service import InvestmentService
from auth.utils import admin_required, admin_session_required



# Create blueprint
admin_investment_bp = Blueprint('admin_investment', __name__, url_prefix='/admin/investments')


# ============================================================================
# INVESTMENT PACKAGE MANAGEMENT
# ============================================================================

@admin_investment_bp.route('/packages', methods=['GET'])
@admin_session_required
def list_packages():
    """List all investment packages"""
    
    packages = InvestmentPackage.query.order_by(
        InvestmentPackage.sort_order, 
        InvestmentPackage.created_at.desc()
    ).all()
    
    return render_template('admin/investment_packages.html', packages=packages)


@admin_investment_bp.route('/packages/create', methods=['GET', 'POST'])
@admin_session_required
def create_package():
    """Create new investment package"""
    
    if request.method == 'POST':
        try:
            data = request.form
            
            # Validate required fields
            required_fields = ['name', 'min_amount', 'total_return_percentage', 'duration_days']
            for field in required_fields:
                if not data.get(field):
                    flash(f'{field.replace("_", " ").title()} is required', 'error')
                    return render_template('admin/create_package.html')
            
            # Create package
            package = InvestmentPackage(
                name=data['name'],
                description=data.get('description', ''),
                min_amount=Decimal(data['min_amount']),
                max_amount=Decimal(data['max_amount']) if data.get('max_amount') else None,
                total_return_percentage=float(data['total_return_percentage']),
                duration_days=int(data['duration_days']),
                end_date=datetime.strptime(data['end_date'], '%Y-%m-%d').date() if data.get('end_date') else None,
                status=PackageStatus(data.get('status', 'active')),
                is_featured=bool(data.get('is_featured')),
                sort_order=int(data.get('sort_order', 0))
            )
            
            db.session.add(package)
            db.session.commit()
            
            flash(f'Investment package "{package.name}" created successfully!', 'success')
            return redirect(url_for('admin_investment.list_packages'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating package: {str(e)}', 'error')
    
    return render_template('admin/create_package.html')


@admin_investment_bp.route('/packages/<int:package_id>/edit', methods=['GET', 'POST'])
@admin_session_required
def edit_package(package_id):
    """Edit investment package"""
    
    package = InvestmentPackage.query.get_or_404(package_id)
    
    if request.method == 'POST':
        try:
            data = request.form
            
            # Update package fields
            package.name = data['name']
            package.description = data.get('description', '')
            package.min_amount = Decimal(data['min_amount'])
            package.max_amount = Decimal(data['max_amount']) if data.get('max_amount') else None
            package.total_return_percentage = float(data['total_return_percentage'])
            package.duration_days = int(data['duration_days'])
            package.end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date() if data.get('end_date') else None
            package.status = PackageStatus(data.get('status', 'active'))
            package.is_featured = bool(data.get('is_featured'))
            package.sort_order = int(data.get('sort_order', 0))
            package.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            flash(f'Package "{package.name}" updated successfully!', 'success')
            return redirect(url_for('admin_investment.list_packages'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating package: {str(e)}', 'error')
    
    return render_template('admin/edit_package.html', package=package)


@admin_investment_bp.route('/packages/<int:package_id>/delete', methods=['POST'])
@admin_session_required
def delete_package(package_id):
    """Delete investment package"""
    
    try:
        package = InvestmentPackage.query.get_or_404(package_id)
        
        # Check if package has active investments
        active_investments = UserInvestment.query.filter_by(
            package_id=package_id,
            status=InvestmentStatus.ACTIVE
        ).count()
        
        if active_investments > 0:
            flash(f'Cannot delete package with {active_investments} active investments', 'error')
            return redirect(url_for('admin_investment.list_packages'))
        
        package_name = package.name
        db.session.delete(package)
        db.session.commit()
        
        flash(f'Package "{package_name}" deleted successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting package: {str(e)}', 'error')
    
    return redirect(url_for('admin_investment.list_packages'))


# ============================================================================
# USER INVESTMENT TRACKING
# ============================================================================

@admin_investment_bp.route('/user-investments', methods=['GET'])
@admin_session_required
def list_user_investments():
    """List all user investments with filtering"""
    
    # Get query parameters
    status = request.args.get('status')
    package_id = request.args.get('package_id')
    user_id = request.args.get('user_id')
    page = int(request.args.get('page', 1))
    per_page = 50
    
    # Build query
    query = UserInvestment.query
    
    if status:
        query = query.filter_by(status=InvestmentStatus(status))
    
    if package_id:
        query = query.filter_by(package_id=int(package_id))
    
    if user_id:
        query = query.filter_by(user_id=int(user_id))
    
    # Get paginated results
    investments = query.order_by(
        UserInvestment.created_at.desc()
    ).paginate(
        page=page, 
        per_page=per_page, 
        error_out=False
    )
    
    # Get packages for filter dropdown
    packages = InvestmentPackage.query.all()
    
    # Calculate summary statistics
    total_invested = db.session.query(db.func.sum(UserInvestment.amount_invested)).scalar() or 0
    total_returns_paid = db.session.query(db.func.sum(UserInvestment.total_returns_paid)).scalar() or 0
    active_investments = UserInvestment.query.filter_by(status=InvestmentStatus.ACTIVE).count()
    
    summary = {
        'total_invested': float(total_invested),
        'total_returns_paid': float(total_returns_paid),
        'active_investments': active_investments,
        'total_investments': UserInvestment.query.count()
    }
    
    return render_template(
        'admin/user_investments.html',
        investments=investments,
        packages=packages,
        summary=summary,
        current_status=status,
        current_package_id=package_id,
        current_user_id=user_id
    )


@admin_investment_bp.route('/user-investments/<int:investment_id>', methods=['GET'])
@admin_session_required
def view_investment_details(investment_id):
    """View detailed information about a specific investment"""
    
    investment = UserInvestment.query.get_or_404(investment_id)
    
    # Get return history
    returns = investment.returns.order_by(
        InvestmentReturn.return_date.desc()
    ).limit(100).all()
    
    return render_template(
        'admin/investment_details.html',
        investment=investment,
        returns=returns
    )


@admin_investment_bp.route('/user-investments/<int:investment_id>/manual-return', methods=['POST'])
@admin_session_required
def manual_return_distribution(investment_id):
    """Manually distribute return for an investment"""

    try:
        data = request.form
        amount = Decimal(data['amount'])

        result = InvestmentService.manual_distribute_returns(investment_id, amount)

        if result['success']:
            flash(f'Successfully distributed ${amount} return', 'success')
        else:
            flash(f'Error: {result["message"]}', 'error')

    except Exception as e:
        flash(f'Error processing manual return: {str(e)}', 'error')

    return redirect(url_for('admin_investment.view_investment_details', investment_id=investment_id))


@admin_investment_bp.route('/user-investments/<int:investment_id>/settle', methods=['POST'])
@admin_session_required
def settle_investment(investment_id):
    """Settle a matured investment - return principal to user"""

    try:
        data = request.form
        settlement_option = data.get('settlement_option', 'available_fund')  # available_fund or keep_invested
        settlement_fee_percent = float(data.get('settlement_fee', 0))  # Optional settlement fee

        result = InvestmentService.settle_matured_investment(
            investment_id,
            settlement_option,
            settlement_fee_percent,
            admin_user_id=session.get('admin_user_id')
        )

        if result['success']:
            flash(f'Investment settled successfully! ${result["principal_returned"]} returned to {settlement_option}', 'success')
        else:
            flash(f'Settlement error: {result["message"]}', 'error')

    except Exception as e:
        flash(f'Error settling investment: {str(e)}', 'error')

    return redirect(url_for('admin_investment.view_investment_details', investment_id=investment_id))


@admin_investment_bp.route('/user-investments/<int:investment_id>/force-mature', methods=['POST'])
@admin_session_required
def force_mature_investment(investment_id):
    """Force mature an active investment (admin override)"""

    try:
        result = InvestmentService.force_mature_investment(
            investment_id,
            admin_user_id=session.get('admin_user_id')
        )

        if result['success']:
            flash('Investment force matured successfully!', 'success')
        else:
            flash(f'Error: {result["message"]}', 'error')

    except Exception as e:
        flash(f'Error force maturing investment: {str(e)}', 'error')

    return redirect(url_for('admin_investment.view_investment_details', investment_id=investment_id))


# ============================================================================
# ANALYTICS AND REPORTS
# ============================================================================

@admin_investment_bp.route('/analytics', methods=['GET'])
@admin_session_required
def investment_analytics():
    """Investment system analytics dashboard"""
    
    analytics = InvestmentService.get_investment_analytics()
    
    if not analytics:
        flash('Error loading analytics data', 'error')
        analytics = {}
    
    return render_template('admin/investment_analytics.html', analytics=analytics)


@admin_investment_bp.route('/daily-returns/run', methods=['POST'])
@admin_session_required
def run_daily_returns():
    """Manually trigger daily return calculation"""
    
    try:
        result = InvestmentService.calculate_daily_investment_returns()
        
        if result['success']:
            flash(
                f'Daily returns processed successfully! '
                f'{result["processed_count"]} investments, '
                f'${result["total_amount"]} distributed',
                'success'
            )
        else:
            flash(f'Error processing daily returns: {result.get("error", "Unknown error")}', 'error')
            
    except Exception as e:
        flash(f'Error running daily returns: {str(e)}', 'error')
    
    return redirect(url_for('admin_investment.investment_analytics'))


# ============================================================================
# API ENDPOINTS FOR ADMIN
# ============================================================================

@admin_investment_bp.route('/api/packages', methods=['GET'])
@admin_required
def api_get_packages():
    """API endpoint to get all packages"""
    
    packages = InvestmentPackage.query.order_by(
        InvestmentPackage.sort_order,
        InvestmentPackage.created_at.desc()
    ).all()
    
    return jsonify({
        'success': True,
        'packages': [package.to_dict(include_stats=True) for package in packages]
    })


@admin_investment_bp.route('/api/investments/stats', methods=['GET'])
@admin_required
def api_investment_stats():
    """API endpoint for investment statistics"""
    
    analytics = InvestmentService.get_investment_analytics()
    
    return jsonify({
        'success': True,
        'analytics': analytics
    })


@admin_investment_bp.route('/api/users/<int:user_id>/investments', methods=['GET'])
@admin_required
def api_user_investments(user_id):
    """API endpoint to get investments for a specific user"""
    
    investments = UserInvestment.query.filter_by(user_id=user_id).all()
    summary = InvestmentService.get_user_investment_summary(user_id)
    
    return jsonify({
        'success': True,
        'investments': [inv.to_dict(include_package=True) for inv in investments],
        'summary': summary
    })
