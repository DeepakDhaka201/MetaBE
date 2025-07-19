"""
MXC Service for MetaX Coin Backend
Handles MXC price management and chart data
"""

from models import db, MXCPrice, MXCChartData


def initialize_default_mxc_price():
    """Initialize default MXC price if none exists"""
    existing_price = MXCPrice.query.first()
    if not existing_price:
        default_price_data = {
            'price': 0.000654,
            'market_cap': 15600000,
            'volume_24h': 234500,
            'holders': 12847,
            'transactions_24h': 1247,
            'rank': '#1247'
        }
        MXCPrice.update_price(default_price_data)


def get_current_mxc_price():
    """Get current MXC price data"""
    return MXCPrice.get_current_price()


def update_mxc_price(price_data, updated_by=None):
    """Update MXC price"""
    return MXCPrice.update_price(price_data, updated_by)


def get_mxc_chart_data(timeframe='24h'):
    """Get MXC chart data"""
    return MXCChartData.get_chart_data(timeframe)


def add_chart_data_point(price, volume=None, timestamp=None):
    """Add chart data point"""
    return MXCChartData.add_data_point(price, volume, timestamp)
