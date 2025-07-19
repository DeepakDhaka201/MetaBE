# MetaX Coin Backend Requirements - Flask Implementation

## Project Overview
MetaX Coin platform with admin-controlled MXC data, multi-level referral system, multiple wallet types, and admin-configurable parameters. No WebSocket, no mocked data - everything controlled by admin.

## Core Token Information (Admin Configurable)
- **Token Name**: MetaX Coin
- **Symbol**: MXC
- **Network**: BSC (BEP-20)
- **Contract Address**: `0x742d35Cc6634C0532925a3b8D0b8EFd17d1F3456`
- **Total Supply**: Admin configurable
- **Circulating Supply**: Admin configurable
- **Current Rank**: Admin configurable
- **Current Price**: Admin controlled (not from external API)

## Technology Stack

### Backend Framework
- **Python Flask** - Main web framework
- **SQLAlchemy** - ORM for database operations
- **Flask-JWT-Extended** - JWT authentication
- **Flask-CORS** - Cross-origin resource sharing
- **Flask-Mail** - Email functionality
- **APScheduler** - Background tasks for price updates

### Database
- **SQLite** for development / **PostgreSQL** for production
- **Flask-Migrate** for database migrations

### External APIs
- **CoinGecko API** - For other cryptocurrencies (Bitcoin, Ethereum, etc.)
- **SMTP** - Email notifications
- **No WebSocket** - Regular HTTP API calls only

## Database Models (SQLAlchemy)

### User Model
```python
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    sponsor_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    referral_code = db.Column(db.String(20), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    rank = db.Column(db.String(20), default='Bronze')
    total_investment = db.Column(db.Numeric(20, 8), default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    sponsor = db.relationship('User', remote_side=[id], backref='referrals')
```

### Wallet Model (Multiple Wallet Types)
```python
class Wallet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    wallet_type = db.Column(db.String(50), nullable=False)
    # Wallet types: available_fund, total_gain, level_bonus, total_referral, total_income
    balance = db.Column(db.Numeric(20, 8), default=0)
    locked_balance = db.Column(db.Numeric(20, 8), default=0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', backref='wallets')
```

### Transaction Model
```python
class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    transaction_type = db.Column(db.String(50), nullable=False)  # deposit, withdrawal, transfer
    wallet_type = db.Column(db.String(50), nullable=False)  # which wallet affected
    amount = db.Column(db.Numeric(20, 8), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, completed, failed
    description = db.Column(db.Text)
    admin_notes = db.Column(db.Text)  # Admin can add notes
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed_at = db.Column(db.DateTime)

    user = db.relationship('User', backref='transactions')
```

### Referral Model (Multi-level tracking)
```python
class Referral(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    referrer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    referred_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    level = db.Column(db.Integer, nullable=False)  # 1, 2, 3, 4, 5
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    referrer = db.relationship('User', foreign_keys=[referrer_id], backref='downline')
    referred = db.relationship('User', foreign_keys=[referred_id])
```

### Income Model (Detailed income tracking)
```python
class Income(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    income_type = db.Column(db.String(50), nullable=False)
    # Types: Direct Referral, Level Bonus, Staking Reward, Self Investment, Lifetime Reward
    amount = db.Column(db.Numeric(20, 8), nullable=False)
    from_user_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # Source of income
    level = db.Column(db.Integer)  # For level bonuses
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='completed')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', foreign_keys=[user_id], backref='incomes')
    from_user = db.relationship('User', foreign_keys=[from_user_id])
```

### Admin Configuration Model
```python
class AdminConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Keys: mxc_price, mxc_change_24h, mxc_market_cap, mxc_volume_24h, mxc_holders,
    #       referral_level_1_rate, referral_level_2_rate, etc., staking_apy_rate,
    #       min_deposit, min_withdrawal, withdrawal_fee
```

### MXC Price Model (Admin Controlled)
```python
class MXCPrice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    price = db.Column(db.Numeric(20, 8), nullable=False)
    change_24h = db.Column(db.Numeric(10, 4), nullable=False)  # Percentage
    change_amount = db.Column(db.Numeric(20, 8), nullable=False)
    market_cap = db.Column(db.BigInteger, nullable=False)
    volume_24h = db.Column(db.BigInteger, nullable=False)
    holders = db.Column(db.Integer, nullable=False)
    transactions_24h = db.Column(db.Integer, nullable=False)
    rank = db.Column(db.String(10), nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'))  # Admin who updated
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Only latest record is used, but history is maintained

### MXC Chart Data Model (For Price Graph)
```python
class MXCChartData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False)
    price = db.Column(db.Numeric(20, 8), nullable=False)
    volume = db.Column(db.BigInteger, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Store price points for chart generation
    # Admin can add historical data points or auto-generate
```

## Flask API Endpoints

### Authentication
```python
@app.route('/api/auth/register', methods=['POST'])
# Body: {username, email, password, first_name, last_name, sponsor_code}
# Creates user + initializes all wallet types with 0 balance

@app.route('/api/auth/login', methods=['POST'])
# Body: {username/email, password}
# Returns: {access_token, user_info}

@app.route('/api/auth/logout', methods=['POST'])
```

### User Profile
```python
@app.route('/api/user/profile', methods=['GET', 'PUT'])
@app.route('/api/user/settings', methods=['GET', 'PUT'])
```

### Dashboard Data (All Wallet Balances)
```python
@app.route('/api/dashboard/balances', methods=['GET'])
# Returns all 9 wallet types:
# {
#   "available_fund": 0.00,
#   "total_gain": 0.00,
#   "level_bonus": 0.00,
#   "total_referral": 0.00,
#   "total_income": 0.00
# }

@app.route('/api/dashboard/mxc-price', methods=['GET'])
# Returns admin-controlled MXC price data (not from external API)

@app.route('/api/dashboard/mxc-chart', methods=['GET'])
# Returns 24-hour price chart data for MXC
# Query params: timeframe (1h, 4h, 24h, 7d)
```

### Team Management (Multi-level Referral)
```python
@app.route('/api/team/stats', methods=['GET'])
# Returns: total_team, direct_referrals, active_members, commission_earned

@app.route('/api/team/members', methods=['GET'])
# Query params: status (active/inactive/all), level (1-5 or all)

@app.route('/api/team/tree', methods=['GET'])
# Returns hierarchical team structure up to 5 levels

@app.route('/api/team/referral-link', methods=['GET'])
# Returns: https://metaxcoin.cloud/Register/{username}
```

### Income Tracking (All Types)
```python
@app.route('/api/income/history', methods=['GET'])
# Query params: type (Direct Referral/Level Bonus/Staking Reward/Self Investment/Lifetime Reward)

@app.route('/api/income/summary', methods=['GET'])
# Returns income breakdown by type with totals
```

### Transactions (Wallet Operations)
```python
@app.route('/api/transactions/deposit', methods=['POST'])
# Body: {amount, wallet_type} - Admin approval required

@app.route('/api/transactions/withdraw', methods=['POST'])
# Body: {amount, wallet_address, wallet_type} - Admin approval required

@app.route('/api/transactions/transfer', methods=['POST'])
# Body: {amount, from_wallet, to_wallet} - Internal wallet transfers

@app.route('/api/transactions/history', methods=['GET'])
# Query params: wallet_type, status, type
```

### Crypto Price Feed (CoinGecko Proxy)
```python
@app.route('/api/crypto/prices', methods=['GET'])
# Cached proxy to CoinGecko API for other cryptocurrencies
# Updates every 60 seconds, serves cached data to frontend
```

### Admin Panel APIs
```python
@app.route('/api/admin/mxc-price', methods=['GET', 'PUT'])
# Admin can view/update MXC price, market cap, volume, etc.

@app.route('/api/admin/users', methods=['GET'])
# List all users with pagination, search, filters

@app.route('/api/admin/users/<int:user_id>/wallets', methods=['GET', 'PUT'])
# View/modify user wallet balances

@app.route('/api/admin/transactions', methods=['GET'])
@app.route('/api/admin/transactions/<int:tx_id>/approve', methods=['POST'])
@app.route('/api/admin/transactions/<int:tx_id>/reject', methods=['POST'])
# Manage pending transactions (deposits/withdrawals)

@app.route('/api/admin/config', methods=['GET', 'PUT'])
# Manage system configuration (referral rates, fees, limits)

@app.route('/api/admin/income/distribute', methods=['POST'])
# Manually distribute income to users (staking rewards, bonuses)

@app.route('/api/admin/mxc-chart', methods=['POST'])
# Admin can add chart data points for MXC price graph
# Body: {timestamp, price, volume}

@app.route('/api/admin/mxc-chart/generate', methods=['POST'])
# Auto-generate chart data based on current price and timeframe
# Body: {timeframe: '24h', data_points: 24}
```

## Flask Application Structure

### Project Structure
```
metax-backend/
├── app.py                 # Main Flask application
├── models.py             # SQLAlchemy models
├── auth.py               # Authentication routes
├── dashboard.py          # Dashboard API routes
├── team.py               # Team management routes
├── transactions.py       # Transaction routes
├── config.py             # Configuration settings
├── requirements.txt      # Python dependencies
└── migrations/           # Database migrations
```

### Key Flask Dependencies
```txt
Flask==2.3.3
Flask-SQLAlchemy==3.0.5
Flask-JWT-Extended==4.5.3
Flask-CORS==4.0.0
Flask-Mail==0.9.1
Flask-Migrate==4.0.5
requests==2.31.0
python-dotenv==1.0.0
```

### Configuration
```python
# config.py
import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///metax.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'jwt-secret'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)

    # Email settings
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
```

## Core Business Logic Implementation

### Multi-Wallet System (5 Wallet Types)
```python
WALLET_TYPES = [
    'available_fund',    # Main spending wallet
    'total_gain',        # Investment returns + staking rewards
    'level_bonus',       # Multi-level commissions
    'total_referral',    # Direct referral commissions
    'total_income',      # Sum of all income types (calculated)
]

def initialize_user_wallets(user_id):
    """Create all wallet types for new user"""
    for wallet_type in WALLET_TYPES:
        wallet = Wallet(user_id=user_id, wallet_type=wallet_type, balance=0)
        db.session.add(wallet)
    db.session.commit()

def get_user_balances(user_id):
    """Get all wallet balances for dashboard"""
    wallets = Wallet.query.filter_by(user_id=user_id).all()
    return {wallet.wallet_type: float(wallet.balance) for wallet in wallets}
```

### Admin-Controlled MXC Price
```python
def get_current_mxc_price():
    """Get latest MXC price set by admin"""
    latest_price = MXCPrice.query.order_by(MXCPrice.created_at.desc()).first()
    if not latest_price:
        # Default values if admin hasn't set any
        return {
            'price': 0.000654,
            'change_24h': 0.00,
            'change_amount': 0.000000,
            'market_cap': 15600000,
            'volume_24h': 234500,
            'holders': 12847,
            'transactions_24h': 1247,
            'rank': '#1247'
        }

    return {
        'price': float(latest_price.price),
        'change_24h': float(latest_price.change_24h),
        'change_amount': float(latest_price.change_amount),
        'market_cap': latest_price.market_cap,
        'volume_24h': latest_price.volume_24h,
        'holders': latest_price.holders,
        'transactions_24h': latest_price.transactions_24h,
        'rank': latest_price.rank
    }

def update_mxc_price(admin_id, price_data):
    """Admin updates MXC price"""
    new_price = MXCPrice(
        price=price_data['price'],
        change_24h=price_data['change_24h'],
        change_amount=price_data['change_amount'],
        market_cap=price_data['market_cap'],
        volume_24h=price_data['volume_24h'],
        holders=price_data['holders'],
        transactions_24h=price_data['transactions_24h'],
        rank=price_data['rank'],
        updated_by=admin_id
    )
    db.session.add(new_price)
    db.session.commit()
```

### MXC Chart Data Generation
```python
def get_mxc_chart_data(timeframe='24h'):
    """Get chart data for MXC price graph"""
    if timeframe == '24h':
        # Get last 24 hours of data (24 points, 1 per hour)
        start_time = datetime.utcnow() - timedelta(hours=24)
        chart_data = MXCChartData.query.filter(
            MXCChartData.timestamp >= start_time
        ).order_by(MXCChartData.timestamp).all()

        if not chart_data:
            # Generate sample data if none exists
            chart_data = generate_sample_chart_data(timeframe)

        return {
            'timeframe': timeframe,
            'data_points': [
                {
                    'timestamp': point.timestamp.isoformat(),
                    'price': float(point.price),
                    'volume': point.volume
                } for point in chart_data
            ],
            'high_24h': max([float(p.price) for p in chart_data]),
            'low_24h': min([float(p.price) for p in chart_data]),
            'volume_24h': sum([p.volume for p in chart_data])
        }

def generate_sample_chart_data(timeframe='24h'):
    """Generate sample chart data for demonstration"""
    current_price = get_current_mxc_price()['price']
    base_price = float(current_price)

    data_points = []
    hours = 24 if timeframe == '24h' else 168  # 24h or 7d

    for i in range(hours):
        timestamp = datetime.utcnow() - timedelta(hours=hours-i)

        # Generate realistic price variation (±5%)
        variation = (random.random() - 0.5) * 0.1  # ±5%
        price = base_price * (1 + variation)
        volume = random.randint(10000, 50000)

        chart_point = MXCChartData(
            timestamp=timestamp,
            price=price,
            volume=volume
        )
        data_points.append(chart_point)

    # Save to database
    for point in data_points:
        db.session.add(point)
    db.session.commit()

    return data_points

def add_chart_data_point(price, volume=None):
    """Add a new chart data point (called when admin updates price)"""
    chart_point = MXCChartData(
        timestamp=datetime.utcnow(),
        price=price,
        volume=volume or random.randint(10000, 30000)
    )
    db.session.add(chart_point)
    db.session.commit()

@app.route('/api/dashboard/mxc-chart', methods=['GET'])
def get_mxc_chart():
    """API endpoint for MXC chart data"""
    timeframe = request.args.get('timeframe', '24h')
    return jsonify(get_mxc_chart_data(timeframe))
```

### Multi-Level Referral System (5 Levels)
```python
# Admin configurable commission rates
DEFAULT_REFERRAL_RATES = {
    1: 10.0,  # 10% for direct referrals (level 1)
    2: 5.0,   # 5% for level 2
    3: 3.0,   # 3% for level 3
    4: 2.0,   # 2% for level 4
    5: 1.0    # 1% for level 5
}

def build_referral_tree(user_id, max_level=5):
    """Build referral tree up to 5 levels"""
    tree = {}

    def get_level_referrals(referrer_id, current_level):
        if current_level > max_level:
            return []

        direct_referrals = User.query.filter_by(sponsor_id=referrer_id).all()
        level_data = []

        for referral in direct_referrals:
            referral_data = {
                'user_id': referral.id,
                'username': referral.username,
                'level': current_level,
                'investment': float(referral.total_investment),
                'is_active': referral.is_active,
                'children': get_level_referrals(referral.id, current_level + 1)
            }
            level_data.append(referral_data)

        return level_data

    return get_level_referrals(user_id, 1)

def calculate_referral_commission(investment_amount, level):
    """Calculate commission based on level and admin rates"""
    rates = get_admin_config('referral_rates', DEFAULT_REFERRAL_RATES)
    rate = rates.get(level, 0)
    return (investment_amount * rate) / 100

def distribute_referral_commissions(user_id, investment_amount):
    """Distribute commissions up the referral chain"""
    current_user = User.query.get(user_id)
    level = 1

    while current_user.sponsor_id and level <= 5:
        sponsor = User.query.get(current_user.sponsor_id)
        if sponsor and sponsor.is_active:
            commission = calculate_referral_commission(investment_amount, level)

            # Add to sponsor's referral wallet
            add_to_wallet(sponsor.id, 'total_referral' if level == 1 else 'level_bonus', commission)

            # Record income
            income = Income(
                user_id=sponsor.id,
                income_type='Direct Referral' if level == 1 else 'Level Bonus',
                amount=commission,
                from_user_id=user_id,
                level=level,
                description=f"Level {level} commission from {current_user.username}"
            )
            db.session.add(income)

        current_user = sponsor
        level += 1

    db.session.commit()

def generate_referral_link(username):
    return f"https://metaxcoin.cloud/Register/{username}"
```

### Wallet Operations
```python
def add_to_wallet(user_id, wallet_type, amount):
    """Add amount to specific wallet"""
    wallet = Wallet.query.filter_by(user_id=user_id, wallet_type=wallet_type).first()
    if wallet:
        wallet.balance += Decimal(str(amount))
        wallet.updated_at = datetime.utcnow()

        # Update total_income wallet if it's an income type
        if wallet_type in ['total_gain', 'level_bonus', 'total_referral']:
            total_wallet = Wallet.query.filter_by(user_id=user_id, wallet_type='total_income').first()
            if total_wallet:
                total_wallet.balance += Decimal(str(amount))
                total_wallet.updated_at = datetime.utcnow()

def transfer_between_wallets(user_id, from_wallet, to_wallet, amount):
    """Transfer amount between user's wallets"""
    from_w = Wallet.query.filter_by(user_id=user_id, wallet_type=from_wallet).first()
    to_w = Wallet.query.filter_by(user_id=user_id, wallet_type=to_wallet).first()

    if from_w and to_w and from_w.balance >= Decimal(str(amount)):
        from_w.balance -= Decimal(str(amount))
        to_w.balance += Decimal(str(amount))

        # Record transaction
        transaction = Transaction(
            user_id=user_id,
            transaction_type='transfer',
            wallet_type=f"{from_wallet} -> {to_wallet}",
            amount=amount,
            status='completed',
            description=f"Transfer from {from_wallet} to {to_wallet}"
        )
        db.session.add(transaction)
        db.session.commit()
        return True
    return False
```

## Background Tasks (APScheduler)

### Scheduled Tasks
```python
from apscheduler.schedulers.background import BackgroundScheduler

def init_scheduler(app):
    scheduler = BackgroundScheduler()

    # Update crypto prices cache every 60 seconds
    scheduler.add_job(
        func=fetch_crypto_prices,
        trigger="interval",
        seconds=60,
        id='crypto_price_update'
    )

    # Calculate daily staking rewards
    scheduler.add_job(
        func=calculate_daily_staking_rewards,
        trigger="cron",
        hour=0,  # Run at midnight
        id='daily_staking_rewards'
    )

    scheduler.start()

def calculate_daily_staking_rewards():
    """Calculate and distribute daily staking rewards"""
    staking_apy = get_admin_config('staking_apy', 12.0)
    daily_rate = staking_apy / 365 / 100

    # Find users with gain balance (includes staking)
    gain_wallets = Wallet.query.filter(
        Wallet.wallet_type == 'total_gain',
        Wallet.balance > 0
    ).all()

    for wallet in gain_wallets:
        daily_reward = wallet.balance * Decimal(str(daily_rate))
        add_to_wallet(wallet.user_id, 'total_gain', daily_reward)

        # Record income
        income = Income(
            user_id=wallet.user_id,
            income_type='Staking Reward',
            amount=daily_reward,
            description=f"Daily staking reward ({staking_apy}% APY)"
        )
        db.session.add(income)

    db.session.commit()
```

## Environment Configuration

### .env File
```env
# Flask Settings
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-here
FLASK_ENV=development

# Database
DATABASE_URL=sqlite:///metax.db

# Email Settings
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password

# Admin Settings
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
ADMIN_EMAIL=admin@metaxcoin.cloud

# External APIs
COINGECKO_API_URL=https://api.coingecko.com/api/v3
```

## Implementation Priority & Features

### Phase 1: Core System (Week 1-2)
1. **Database Models** - All models with relationships
2. **Authentication** - Register, login, JWT tokens
3. **User Management** - Profile, settings
4. **Wallet System** - Initialize 9 wallet types for each user
5. **Admin Panel** - Basic admin authentication and MXC price control

### Phase 2: Referral System (Week 3-4)
1. **Multi-level Referral** - 5-level deep referral tracking
2. **Commission Calculation** - Admin configurable rates
3. **Team Management** - Team stats, member lists, tree view
4. **Referral Links** - Generate and track referral registrations

### Phase 3: Financial Operations (Week 5-6)
1. **Transaction System** - Deposits, withdrawals with admin approval
2. **Wallet Operations** - Internal transfers between wallets
3. **Income Tracking** - All income types with detailed history
4. **Admin Controls** - Transaction approval, manual adjustments

### Phase 4: External Integration (Week 7-8)
1. **CoinGecko Integration** - Cached crypto price feed
2. **Background Tasks** - Scheduled staking rewards
3. **Email Notifications** - Transaction alerts, welcome emails
4. **Admin Configuration** - All system parameters configurable

### Key Features Summary
- ✅ **No WebSocket** - Regular HTTP API only
- ✅ **No Mocked Data** - All data admin controlled
- ✅ **9 Wallet Types** - Complete wallet ecosystem
- ✅ **5-Level Referrals** - Deep MLM structure
- ✅ **Admin Controlled MXC** - Price, market data, all parameters
- ✅ **CoinGecko for Others** - External crypto data cached
- ✅ **Transaction Approval** - Admin approval workflow
- ✅ **Configurable Rates** - All commission rates admin controlled
- ✅ **Background Tasks** - Automated reward calculations
- ✅ **No Test Cases** - Focus on implementation only

### Admin Configuration System
```python
def get_admin_config(key, default=None):
    """Get admin configuration value"""
    config = AdminConfig.query.filter_by(key=key).first()
    if config:
        try:
            return json.loads(config.value)
        except:
            return config.value
    return default

def set_admin_config(key, value, description=None):
    """Set admin configuration value"""
    config = AdminConfig.query.filter_by(key=key).first()
    if config:
        config.value = json.dumps(value) if isinstance(value, (dict, list)) else str(value)
        config.updated_at = datetime.utcnow()
    else:
        config = AdminConfig(
            key=key,
            value=json.dumps(value) if isinstance(value, (dict, list)) else str(value),
            description=description
        )
        db.session.add(config)
    db.session.commit()

# Example admin configurations:
# referral_rates: {1: 10.0, 2: 5.0, 3: 3.0, 4: 2.0, 5: 1.0}
# min_deposit: 10.0
# min_withdrawal: 5.0
# withdrawal_fee: 2.0
# staking_apy: 12.0
```

## CoinGecko API Integration (Other Cryptocurrencies)

### Cached Crypto Price Fetching
```python
import requests
from datetime import datetime, timedelta

# Cache for 60 seconds
crypto_cache = {'data': None, 'timestamp': None}

def fetch_crypto_prices():
    """Fetch and cache crypto prices from CoinGecko API"""
    global crypto_cache

    # Check cache
    if (crypto_cache['data'] and crypto_cache['timestamp'] and
        datetime.now() - crypto_cache['timestamp'] < timedelta(seconds=60)):
        return crypto_cache['data']

    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        'vs_currency': 'usd',
        'order': 'market_cap_desc',
        'per_page': 20,
        'page': 1,
        'sparkline': False,
        'price_change_percentage': '24h'
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            crypto_cache = {'data': data, 'timestamp': datetime.now()}
            return data
    except Exception as e:
        print(f"Error fetching crypto prices: {e}")

    # Return cached data if API fails
    return crypto_cache['data'] or []

@app.route('/api/crypto/prices', methods=['GET'])
def get_crypto_prices():
    """Cached endpoint for crypto prices (excluding MXC)"""
    return jsonify(fetch_crypto_prices())
```

## Deployment & Infrastructure

### Docker Configuration
```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
EXPOSE 3000
CMD ["npm", "start"]
```

### Database Migrations
```sql
-- Migration: Add referral tracking
ALTER TABLE users ADD COLUMN total_referrals INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN total_earnings DECIMAL(20, 8) DEFAULT 0;

-- Migration: Add staking rewards tracking
CREATE INDEX idx_staking_user_status ON staking(user_id, status);
CREATE INDEX idx_transactions_user_type ON transactions(user_id, transaction_type);
```

### Monitoring & Logging
- Application performance monitoring (APM)
- Error tracking and alerting
- Database query optimization
- API response time monitoring
- Blockchain transaction monitoring
- User activity analytics

## Testing Requirements

### Unit Tests
- Authentication logic
- Wallet operations
- Commission calculations
- Staking reward algorithms
- Referral tree building

### Integration Tests
- API endpoint testing
- Database operations
- Blockchain interactions
- Email/SMS services
- WebSocket connections

### Security Tests
- Penetration testing
- Smart contract audits
- API security scanning
- Database security assessment

## Compliance & Legal

### KYC/AML Requirements
- Identity verification process
- Document upload and verification
- Risk assessment scoring
- Transaction monitoring
- Suspicious activity reporting

### Data Privacy
- GDPR compliance
- Data retention policies
- User consent management
- Right to be forgotten
- Data export functionality

## Performance Optimization

### Caching Strategy
- Redis for session data
- API response caching
- Database query result caching
- Static asset CDN
- Price data caching (30-second TTL)

### Database Optimization
- Proper indexing strategy
- Query optimization
- Connection pooling
- Read replicas for analytics
- Partitioning for large tables

## Backup & Recovery

### Database Backups
- Daily automated backups
- Point-in-time recovery
- Cross-region backup storage
- Backup verification testing

### Disaster Recovery
- Multi-region deployment
- Automated failover
- Data synchronization
- Recovery time objectives (RTO < 1 hour)
- Recovery point objectives (RPO < 15 minutes)

## Implementation Timeline

### Phase 1 (Weeks 1-4): Core Infrastructure
- Database setup and migrations
- Authentication system
- Basic user management
- Wallet functionality

### Phase 2 (Weeks 5-8): Trading & Staking
- Price feed integration
- Trading engine
- Staking system
- Smart contract integration

### Phase 3 (Weeks 9-12): MLM & Referrals
- Referral system
- Commission calculations
- Team management
- Income tracking

### Phase 4 (Weeks 13-16): Advanced Features
- Admin panel
- Notification system
- Analytics dashboard
- Mobile API optimization

### Phase 5 (Weeks 17-20): Testing & Deployment
- Security audits
- Performance testing
- Production deployment
- Monitoring setup

## Support & Maintenance

### 24/7 Monitoring
- System health checks
- Transaction processing monitoring
- Blockchain synchronization
- User activity tracking

### Regular Maintenance
- Security updates
- Database optimization
- Smart contract upgrades
- Feature enhancements

---

This comprehensive backend specification provides the foundation for building a robust, secure, and scalable MetaX Coin platform with all the required features for cryptocurrency trading, MLM operations, and user management.
