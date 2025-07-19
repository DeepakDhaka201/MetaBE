# MetaX Coin Backend

A comprehensive Flask-based backend for the MetaX Coin platform featuring admin-controlled MXC data, multi-level referral system, multiple wallet types, and crypto deposit management.

## 🚀 Features

### Core Features
- **9-Wallet System**: Complete wallet ecosystem with different balance types
- **5-Level Referral System**: Deep MLM structure with configurable commission rates
- **Admin-Controlled MXC**: Price, market data, and chart generation
- **Crypto Deposits**: Wallet pool system for TRON/USDT deposits
- **External API Integration**: CoinGecko for other cryptocurrencies
- **Background Tasks**: Automated staking rewards and system maintenance

### Wallet Types
1. **Available Fund** - Main spending wallet
2. **Total Gain** - Investment returns + staking rewards
3. **Level Bonus** - Multi-level commissions
4. **Total Referral** - Direct referral commissions
5. **Total Income** - Sum of all income types (calculated)
6. **Total Investment** - Total invested amount (calculated from UserInvestment records)

### API Endpoints

#### Authentication (`/api/auth/`)
- `POST /register` - User registration with referral support
- `POST /login` - User authentication
- `POST /logout` - User logout
- `POST /refresh` - Token refresh
- `GET /profile` - Get user profile
- `PUT /profile` - Update user profile
- `POST /change-password` - Change password

#### Dashboard (`/api/dashboard/`)
- `GET /balances` - Get all wallet balances
- `GET /summary` - Comprehensive dashboard data
- `GET /mxc-price` - Current MXC price (public)
- `GET /mxc-chart` - MXC chart data
- `GET /wallet/<type>` - Specific wallet details
- `POST /transfer` - Transfer between wallets
- `GET /statistics` - User analytics

#### Team Management (`/api/team/`)
- `GET /stats` - Team statistics
- `GET /members` - Team members with filtering
- `GET /tree` - Hierarchical team structure
- `GET /referral-link` - Referral link and code
- `GET /commission-history` - Commission earnings
- `GET /commission-rates` - Current rates (public)
- `GET /performance` - Team performance analytics

#### Transactions (`/api/transactions/`)
- `POST /deposit` - Create deposit transaction (admin approval)
- `POST /deposit/request` - Request crypto deposit via wallet pool
- `GET /deposit/status` - Check deposit status
- `POST /withdraw` - Request withdrawal
- `POST /transfer` - Transfer between wallets
- `GET /history` - Transaction history
- `GET /<id>` - Transaction details
- `POST /cancel/<id>` - Cancel transaction
- `GET /limits` - Transaction limits
- `GET /statistics` - Transaction stats

#### Admin Panel (`/api/admin/`)
- `GET|PUT /mxc-price` - Manage MXC price
- `POST /mxc-chart` - Add chart data points
- `POST /mxc-chart/generate` - Auto-generate chart data
- `GET /users` - User management
- `GET|PUT /users/<id>/wallets` - Wallet management
- `GET /transactions` - Pending transactions
- `POST /transactions/<id>/approve` - Approve transaction
- `POST /transactions/<id>/reject` - Reject transaction
- `GET|PUT /config` - System configuration
- `POST /income/distribute` - Manual income distribution
- `GET /wallet-pool/stats` - Wallet pool statistics
- `GET|POST /wallet-pool/wallets` - Manage pooled wallets
- `PUT /wallet-pool/wallets/<id>` - Update pooled wallet
- `GET /wallet-pool/assignments` - View wallet assignments

#### Income Tracking (`/api/income/`)
- `GET /history` - Income history with filtering
- `GET /summary` - Comprehensive income summary
- `GET /types` - Available income types (public)
- `GET /analytics` - Detailed income analytics

#### Crypto Data (`/api/crypto/`)
- `GET /prices` - Cryptocurrency prices (cached)
- `GET /prices/<coin>` - Specific coin data
- `GET /trending` - Trending cryptocurrencies
- `GET /global` - Global market stats
- `GET /search` - Search cryptocurrencies

## 🛠️ Installation

### Prerequisites
- Python 3.8+
- pip
- Virtual environment (recommended)

### Setup

1. **Clone the repository**
```bash
git clone <repository-url>
cd MetaBE
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Environment configuration**
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. **Initialize database**
```bash
python -c "from app import create_app; from models import db; app = create_app(); app.app_context().push(); db.create_all()"
```

6. **Run the application**
```bash
python run.py
```

The server will start on `http://localhost:5000`

## 🔧 Configuration

### Environment Variables

Key environment variables in `.env`:

```env
# Flask Settings
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-here
FLASK_ENV=development

# Database
DATABASE_URL=sqlite:///metax.db

# Email
MAIL_SERVER=smtp.gmail.com
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password

# Blockchain (TRON/USDT)
TRON_API_URL=https://api.trongrid.io
USDT_CONTRACT_ADDRESS=TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t

# Admin
DEFAULT_ADMIN_USERNAME=admin
DEFAULT_ADMIN_PASSWORD=admin123
```

### Admin Configuration

The system includes configurable parameters:

- **Referral Rates**: Commission percentages for each level
- **Transaction Limits**: Min/max deposit and withdrawal amounts
- **Staking Configuration**: APY rates and compounding frequency
- **Platform Settings**: Maintenance mode, registration controls
- **Wallet Pool Settings**: Assignment duration and monitoring intervals

## 🏗️ Architecture

### Project Structure
```
MetaBE/
├── app.py                 # Main Flask application
├── config.py             # Configuration settings
├── run.py                # Development server
├── requirements.txt      # Python dependencies
├── models/               # Database models
│   ├── __init__.py
│   ├── user.py          # User model
│   ├── wallet.py        # Wallet system
│   ├── transaction.py   # Transaction handling
│   ├── referral.py      # Referral system
│   ├── income.py        # Income tracking
│   ├── admin.py         # Admin configuration
│   ├── mxc.py           # MXC price & charts
│   └── wallet_pool.py   # Crypto deposit wallets
├── auth/                # Authentication
├── dashboard/           # Dashboard APIs
├── team/               # Team management
├── transactions/       # Transaction APIs
├── admin/              # Admin panel
├── crypto/             # External crypto data
└── services/           # Business logic
    ├── admin_config.py
    ├── mxc_service.py
    ├── wallet_pool.py
    └── scheduler.py
```

### Database Models

- **User**: Authentication, profile, referral relationships
- **Wallet**: 5-wallet system with balance management
- **Transaction**: All financial operations
- **Referral**: Multi-level referral tracking
- **Income**: Detailed income tracking
- **AdminConfig**: System configuration
- **MXCPrice**: Admin-controlled MXC data
- **MXCChartData**: Price chart generation
- **PooledWallet**: Crypto deposit wallet pool
- **WalletAssignment**: Wallet-user assignments

## 🔄 Background Tasks

Automated tasks handled by APScheduler:

- **Daily Staking Rewards** (midnight UTC)
- **User Rank Updates** (1 AM UTC)
- **Chart Data Generation** (hourly)
- **Weekly Bonuses** (Sundays 2 AM UTC)
- **Data Cleanup** (Mondays 3 AM UTC)
- **System Health Checks** (every 6 hours)
- **Wallet Monitoring** (every 60 seconds)
- **Assignment Cleanup** (every 5 minutes)

## 🔐 Security Features

- JWT-based authentication
- Password hashing with bcrypt
- Input validation and sanitization
- SQL injection prevention
- Rate limiting support
- Admin privilege separation
- Transaction approval workflow
- Audit logging

## 📊 Monitoring & Logging

- Comprehensive logging with rotation
- Transaction audit trails
- User activity tracking
- System health monitoring
- Performance metrics
- Error tracking and alerting

## 🚀 Deployment

### Production Setup

1. **Environment**: Set `FLASK_ENV=production`
2. **Database**: Use PostgreSQL instead of SQLite
3. **Web Server**: Use Gunicorn or uWSGI
4. **Reverse Proxy**: Nginx for static files and SSL
5. **Process Manager**: Supervisor or systemd
6. **Monitoring**: Set up logging and monitoring
7. **Backup**: Regular database backups

### Docker Deployment

```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:create_app()"]
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is proprietary software for MetaX Coin platform.

## 🆘 Support

For support and questions:
- Email: support@metaxcoin.cloud
- Documentation: [Internal Wiki]
- Issues: [GitHub Issues]

---

**MetaX Coin Backend** - Built with Flask, designed for scalability and security.
