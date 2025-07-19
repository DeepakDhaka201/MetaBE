"""
MXC Price and Chart Data Models for MetaX Coin Backend
Handles admin-controlled MXC price data and chart generation
"""

from datetime import datetime, timedelta
from decimal import Decimal
import random

from . import db


class MXCPrice(db.Model):
    """MXC price model for admin-controlled price data"""
    
    __tablename__ = 'mxc_prices'
    
    # Primary fields
    id = db.Column(db.Integer, primary_key=True)
    price = db.Column(db.Numeric(20, 8), nullable=False)
    change_24h = db.Column(db.Numeric(10, 4), nullable=False)  # Percentage
    change_amount = db.Column(db.Numeric(20, 8), nullable=False)
    
    # Market data
    market_cap = db.Column(db.BigInteger, nullable=False)
    volume_24h = db.Column(db.BigInteger, nullable=False)
    holders = db.Column(db.Integer, nullable=False)
    transactions_24h = db.Column(db.Integer, nullable=False)
    rank = db.Column(db.String(10), nullable=False)
    
    # Additional metrics
    high_24h = db.Column(db.Numeric(20, 8))
    low_24h = db.Column(db.Numeric(20, 8))
    volume_change_24h = db.Column(db.Numeric(10, 4), default=0)
    
    # Admin tracking
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    notes = db.Column(db.Text)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    updater = db.relationship('User', backref='mxc_price_updates')
    
    def __repr__(self):
        return f'<MXCPrice {self.price} ({self.change_24h}%)>'
    
    @staticmethod
    def get_current_price():
        """Get the latest MXC price data"""
        latest = MXCPrice.query.order_by(MXCPrice.created_at.desc()).first()
        
        if not latest:
            # Return default values if no price data exists
            return {
                'price': 0.000654,
                'change_24h': 0.00,
                'change_amount': 0.000000,
                'price_change_24h': 0.00,
                'price_change_percentage_24h': 0.00,
                'market_cap': 15600000,
                'volume_24h': 234500,
                'holders': 12847,
                'transactions_24h': 1247,
                'rank': '#1247',
                'high_24h': 0.000654,
                'low_24h': 0.000654,
                'volume_change_24h': 0.00,
                'last_updated': datetime.utcnow().isoformat(),
                'updated_by': None,
                'notes': None,
                'currency': 'USD'
            }
        
        return latest.to_dict()
    
    @staticmethod
    def update_price(price_data, updated_by=None):
        """Update MXC price with new data"""
        # Calculate change from previous price
        previous_price = MXCPrice.get_current_price()
        previous_price_value = Decimal(str(previous_price['price']))
        new_price_value = Decimal(str(price_data['price']))
        
        if previous_price_value > 0:
            change_amount = new_price_value - previous_price_value
            change_24h = (change_amount / previous_price_value) * 100
        else:
            change_amount = 0
            change_24h = 0
        
        # Create new price record
        new_price = MXCPrice(
            price=new_price_value,
            change_24h=change_24h,
            change_amount=change_amount,
            market_cap=price_data.get('market_cap', previous_price['market_cap']),
            volume_24h=price_data.get('volume_24h', previous_price['volume_24h']),
            holders=price_data.get('holders', previous_price['holders']),
            transactions_24h=price_data.get('transactions_24h', previous_price['transactions_24h']),
            rank=price_data.get('rank', previous_price['rank']),
            high_24h=price_data.get('high_24h', new_price_value),
            low_24h=price_data.get('low_24h', new_price_value),
            volume_change_24h=price_data.get('volume_change_24h', 0),
            updated_by=updated_by,
            notes=price_data.get('notes')
        )
        
        db.session.add(new_price)
        
        # Also add a chart data point
        MXCChartData.add_data_point(
            price=new_price_value,
            volume=price_data.get('volume_24h', previous_price['volume_24h'])
        )
        
        db.session.commit()
        return new_price
    
    @staticmethod
    def get_price_history(limit=100):
        """Get price history"""
        prices = MXCPrice.query.order_by(MXCPrice.created_at.desc()).limit(limit).all()
        return [price.to_dict() for price in prices]
    
    def to_dict(self):
        """Convert price to dictionary"""
        return {
            'price': float(self.price),
            'change_24h': float(self.change_24h),
            'change_amount': float(self.change_amount),
            'price_change_24h': float(self.change_24h),  # Alias for compatibility
            'price_change_percentage_24h': float(self.change_24h),  # Alias for compatibility
            'market_cap': self.market_cap,
            'volume_24h': self.volume_24h,
            'holders': self.holders,
            'transactions_24h': self.transactions_24h,
            'rank': self.rank,
            'high_24h': float(self.high_24h) if self.high_24h else float(self.price),
            'low_24h': float(self.low_24h) if self.low_24h else float(self.price),
            'volume_change_24h': float(self.volume_change_24h),
            'last_updated': self.created_at.isoformat() if self.created_at else None,
            'updated_by': self.updated_by,
            'notes': self.notes,
            'currency': 'USD'
        }


class MXCChartData(db.Model):
    """MXC chart data model for price graphs"""
    
    __tablename__ = 'mxc_chart_data'
    
    # Primary fields
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, index=True)
    price = db.Column(db.Numeric(20, 8), nullable=False)
    volume = db.Column(db.BigInteger, default=0)
    
    # Additional OHLC data for advanced charts
    open_price = db.Column(db.Numeric(20, 8))
    high_price = db.Column(db.Numeric(20, 8))
    low_price = db.Column(db.Numeric(20, 8))
    close_price = db.Column(db.Numeric(20, 8))
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Indexes
    __table_args__ = (
        db.Index('idx_timestamp_price', 'timestamp', 'price'),
    )
    
    def __repr__(self):
        return f'<MXCChartData {self.timestamp}:{self.price}>'
    
    @staticmethod
    def add_data_point(price, volume=None, timestamp=None, ohlc_data=None):
        """Add a new chart data point"""
        if not timestamp:
            timestamp = datetime.utcnow()
        
        if not volume:
            volume = random.randint(10000, 50000)  # Generate random volume
        
        chart_point = MXCChartData(
            timestamp=timestamp,
            price=price,
            volume=volume,
            open_price=ohlc_data.get('open') if ohlc_data else price,
            high_price=ohlc_data.get('high') if ohlc_data else price,
            low_price=ohlc_data.get('low') if ohlc_data else price,
            close_price=ohlc_data.get('close') if ohlc_data else price
        )
        
        db.session.add(chart_point)
        return chart_point
    
    @staticmethod
    def get_chart_data(timeframe='24h'):
        """Get chart data for specified timeframe"""
        now = datetime.utcnow()
        
        # Define timeframe mappings
        timeframe_map = {
            '1h': timedelta(hours=1),
            '4h': timedelta(hours=4),
            '24h': timedelta(hours=24),
            '7d': timedelta(days=7),
            '30d': timedelta(days=30),
            '90d': timedelta(days=90),
            '1y': timedelta(days=365)
        }
        
        if timeframe not in timeframe_map:
            timeframe = '24h'
        
        start_time = now - timeframe_map[timeframe]
        
        # Get data points
        chart_data = MXCChartData.query.filter(
            MXCChartData.timestamp >= start_time
        ).order_by(MXCChartData.timestamp).all()
        
        if not chart_data:
            # Generate sample data if none exists
            chart_data = MXCChartData.generate_sample_data(timeframe)
        
        # Calculate statistics
        prices = [float(point.price) for point in chart_data]
        volumes = [point.volume for point in chart_data]
        
        return {
            'timeframe': timeframe,
            'data_points': [point.to_dict() for point in chart_data],
            'statistics': {
                'high': max(prices) if prices else 0,
                'low': min(prices) if prices else 0,
                'volume_total': sum(volumes),
                'price_change': prices[-1] - prices[0] if len(prices) > 1 else 0,
                'price_change_percent': ((prices[-1] - prices[0]) / prices[0] * 100) if len(prices) > 1 and prices[0] > 0 else 0
            }
        }
    
    @staticmethod
    def generate_sample_data(timeframe='24h'):
        """Generate sample chart data for demonstration"""
        current_price_data = MXCPrice.get_current_price()
        base_price = Decimal(str(current_price_data['price']))
        
        # Define data point intervals
        interval_map = {
            '1h': (60, timedelta(minutes=1)),    # 60 points, 1 minute apart
            '4h': (48, timedelta(minutes=5)),    # 48 points, 5 minutes apart
            '24h': (24, timedelta(hours=1)),     # 24 points, 1 hour apart
            '7d': (168, timedelta(hours=1)),     # 168 points, 1 hour apart
            '30d': (30, timedelta(days=1)),      # 30 points, 1 day apart
            '90d': (90, timedelta(days=1)),      # 90 points, 1 day apart
            '1y': (365, timedelta(days=1))       # 365 points, 1 day apart
        }
        
        points_count, interval = interval_map.get(timeframe, (24, timedelta(hours=1)))
        
        data_points = []
        current_time = datetime.utcnow() - (interval * points_count)
        
        for i in range(points_count):
            # Generate realistic price variation (±5%)
            variation = (random.random() - 0.5) * 0.1  # ±5%
            price = base_price * (1 + Decimal(str(variation)))
            volume = random.randint(10000, 100000)
            
            chart_point = MXCChartData(
                timestamp=current_time,
                price=price,
                volume=volume,
                open_price=price,
                high_price=price * Decimal('1.02'),  # 2% higher
                low_price=price * Decimal('0.98'),   # 2% lower
                close_price=price
            )
            data_points.append(chart_point)
            current_time += interval
        
        # Save to database
        for point in data_points:
            db.session.add(point)
        db.session.commit()
        
        return data_points
    
    @staticmethod
    def cleanup_old_data(days_to_keep=90):
        """Clean up old chart data to prevent database bloat"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        old_data = MXCChartData.query.filter(
            MXCChartData.timestamp < cutoff_date
        ).delete()
        
        db.session.commit()
        return old_data
    
    def to_dict(self):
        """Convert chart data to dictionary"""
        return {
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'price': float(self.price),
            'volume': self.volume,
            'open': float(self.open_price) if self.open_price else float(self.price),
            'high': float(self.high_price) if self.high_price else float(self.price),
            'low': float(self.low_price) if self.low_price else float(self.price),
            'close': float(self.close_price) if self.close_price else float(self.price)
        }
