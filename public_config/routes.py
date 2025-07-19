"""
Config Routes for MetaX Coin Backend
Handles public configuration endpoints for frontend consumption
"""

from flask import Blueprint, jsonify, current_app
from services.admin_config import get_referral_rates

config_bp = Blueprint('config', __name__)


@config_bp.route('/referral', methods=['GET'])
def get_referral_config():
    """Get referral commission structure configuration"""
    try:
        # Get referral rates from admin config
        referral_rates_raw = get_referral_rates()

        # Handle case where config might be a string or already a dict
        if isinstance(referral_rates_raw, dict):
            # Convert string keys to integers if needed
            referral_rates = {}
            for key, value in referral_rates_raw.items():
                # Handle both string and integer keys
                level_key = int(key) if isinstance(key, str) and key.isdigit() else key
                referral_rates[level_key] = float(value)
        else:
            # Use default rates if config is not properly formatted
            referral_rates = {1: 10.0, 2: 5.0, 3: 3.0, 4: 2.0, 5: 1.0}

        # Define color scheme for each level
        level_colors = {
            1: "from-green-500 to-green-600",
            2: "from-blue-500 to-blue-600",
            3: "from-purple-500 to-purple-600",
            4: "from-orange-500 to-orange-600",
            5: "from-red-500 to-red-600"
        }

        # Build commission structure
        levels = []
        total_commission = 0.0

        for level in range(1, 6):  # Levels 1-5
            rate = referral_rates.get(level, 0.0)
            total_commission += rate

            levels.append({
                "level": level,
                "rate": rate,
                "color": level_colors.get(level, "from-gray-500 to-gray-600")
            })

        commission_structure = {
            "levels": levels,
            "total_commission": total_commission,
            "max_levels": 5
        }

        return jsonify({
            "commission_structure": commission_structure
        }), 200

    except Exception as e:
        current_app.logger.error(f'Get referral config error: {str(e)}')
        return jsonify({'error': 'Failed to get referral configuration'}), 500
