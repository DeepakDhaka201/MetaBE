"""
MetaX Coin Backend Models
Database models initialization
"""

from flask_sqlalchemy import SQLAlchemy

# Initialize SQLAlchemy instance
db = SQLAlchemy()

# Import all models to ensure they are registered
from .user import User
from .wallet import Wallet
from .transaction import Transaction, TransactionType, TransactionStatus
from .referral import Referral
from .income import Income
from .admin import AdminConfig
from .mxc import MXCPrice, MXCChartData
from .wallet_pool import PooledWallet, WalletAssignment
from .investment import InvestmentPackage, UserInvestment, InvestmentReturn, PackageStatus, InvestmentStatus, ReturnStatus

# Export commonly used models
__all__ = [
    'db',
    'User',
    'Wallet',
    'Transaction',
    'TransactionType',
    'TransactionStatus',
    'Referral',
    'Income',
    'AdminConfig',
    'MXCPrice',
    'MXCChartData',
    'PooledWallet',
    'WalletAssignment',
    'InvestmentPackage',
    'UserInvestment',
    'InvestmentReturn',
    'PackageStatus',
    'InvestmentStatus',
    'ReturnStatus'
]
