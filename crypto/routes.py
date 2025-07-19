"""
Crypto Routes for MetaX Coin Backend
Handles external cryptocurrency data from CoinGecko API
"""

from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timedelta
import requests

crypto_bp = Blueprint('crypto', __name__)

# Cache for crypto prices (in production, use Redis)
crypto_cache = {'data': None, 'timestamp': None}


@crypto_bp.route('/prices', methods=['GET'])
def get_crypto_prices():
    """Get cryptocurrency prices from CoinGecko API (cached)"""
    try:
        global crypto_cache
        
        # Check cache validity
        cache_duration = current_app.config.get('CRYPTO_CACHE_DURATION', 60)  # seconds
        
        if (crypto_cache['data'] and crypto_cache['timestamp'] and
            datetime.now() - crypto_cache['timestamp'] < timedelta(seconds=cache_duration)):
            return jsonify({
                'data': crypto_cache['data'],
                'cached': True,
                'cache_timestamp': crypto_cache['timestamp'].isoformat()
            }), 200
        
        # Fetch fresh data from CoinGecko
        fresh_data = fetch_crypto_prices_from_api()
        
        if fresh_data:
            crypto_cache = {
                'data': fresh_data,
                'timestamp': datetime.now()
            }
            
            return jsonify({
                'data': fresh_data,
                'cached': False,
                'cache_timestamp': crypto_cache['timestamp'].isoformat()
            }), 200
        else:
            # Return cached data if API fails
            if crypto_cache['data']:
                return jsonify({
                    'data': crypto_cache['data'],
                    'cached': True,
                    'cache_timestamp': crypto_cache['timestamp'].isoformat(),
                    'warning': 'Using cached data due to API failure'
                }), 200
            else:
                return jsonify({'error': 'Unable to fetch cryptocurrency data'}), 503
        
    except Exception as e:
        current_app.logger.error(f'Get crypto prices error: {str(e)}')
        return jsonify({'error': 'Failed to get cryptocurrency prices'}), 500


@crypto_bp.route('/prices/<coin_id>', methods=['GET'])
def get_coin_price(coin_id):
    """Get specific coin price and details"""
    try:
        # Get query parameters
        vs_currency = request.args.get('vs_currency', 'usd')
        include_24hr_change = request.args.get('include_24hr_change', 'true').lower() == 'true'
        include_market_cap = request.args.get('include_market_cap', 'true').lower() == 'true'
        
        # Fetch from CoinGecko API
        url = f"https://api.coingecko.com/api/v3/simple/price"
        params = {
            'ids': coin_id,
            'vs_currencies': vs_currency,
            'include_24hr_change': include_24hr_change,
            'include_market_cap': include_market_cap,
            'include_24hr_vol': True,
            'include_last_updated_at': True
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if coin_id in data:
                return jsonify({
                    'coin_id': coin_id,
                    'data': data[coin_id],
                    'timestamp': datetime.utcnow().isoformat()
                }), 200
            else:
                return jsonify({'error': f'Coin {coin_id} not found'}), 404
        else:
            return jsonify({'error': 'Failed to fetch coin data'}), 503
        
    except Exception as e:
        current_app.logger.error(f'Get coin price error: {str(e)}')
        return jsonify({'error': 'Failed to get coin price'}), 500


@crypto_bp.route('/trending', methods=['GET'])
def get_trending_coins():
    """Get trending cryptocurrencies"""
    try:
        url = "https://api.coingecko.com/api/v3/search/trending"
        
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return jsonify({
                'trending_coins': data.get('coins', []),
                'timestamp': datetime.utcnow().isoformat()
            }), 200
        else:
            return jsonify({'error': 'Failed to fetch trending coins'}), 503
        
    except Exception as e:
        current_app.logger.error(f'Get trending coins error: {str(e)}')
        return jsonify({'error': 'Failed to get trending coins'}), 500


@crypto_bp.route('/global', methods=['GET'])
def get_global_crypto_stats():
    """Get global cryptocurrency market statistics"""
    try:
        url = "https://api.coingecko.com/api/v3/global"
        
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return jsonify({
                'global_stats': data.get('data', {}),
                'timestamp': datetime.utcnow().isoformat()
            }), 200
        else:
            return jsonify({'error': 'Failed to fetch global stats'}), 503
        
    except Exception as e:
        current_app.logger.error(f'Get global crypto stats error: {str(e)}')
        return jsonify({'error': 'Failed to get global statistics'}), 500


def fetch_crypto_prices_from_api():
    """Fetch cryptocurrency prices from CoinGecko API"""
    try:
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            'vs_currency': 'usd',
            'order': 'market_cap_desc',
            'per_page': 50,  # Top 50 cryptocurrencies
            'page': 1,
            'sparkline': False,
            'price_change_percentage': '24h,7d'
        }
        
        response = requests.get(url, params=params, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            
            # Process and format the data
            processed_data = []
            for coin in data:
                processed_coin = {
                    'id': coin.get('id'),
                    'symbol': coin.get('symbol', '').upper(),
                    'name': coin.get('name'),
                    'image': coin.get('image'),
                    'current_price': coin.get('current_price'),
                    'market_cap': coin.get('market_cap'),
                    'market_cap_rank': coin.get('market_cap_rank'),
                    'fully_diluted_valuation': coin.get('fully_diluted_valuation'),
                    'total_volume': coin.get('total_volume'),
                    'high_24h': coin.get('high_24h'),
                    'low_24h': coin.get('low_24h'),
                    'price_change_24h': coin.get('price_change_24h'),
                    'price_change_percentage_24h': coin.get('price_change_percentage_24h'),
                    'price_change_percentage_7d': coin.get('price_change_percentage_7d_in_currency'),
                    'market_cap_change_24h': coin.get('market_cap_change_24h'),
                    'market_cap_change_percentage_24h': coin.get('market_cap_change_percentage_24h'),
                    'circulating_supply': coin.get('circulating_supply'),
                    'total_supply': coin.get('total_supply'),
                    'max_supply': coin.get('max_supply'),
                    'ath': coin.get('ath'),
                    'ath_change_percentage': coin.get('ath_change_percentage'),
                    'ath_date': coin.get('ath_date'),
                    'atl': coin.get('atl'),
                    'atl_change_percentage': coin.get('atl_change_percentage'),
                    'atl_date': coin.get('atl_date'),
                    'last_updated': coin.get('last_updated')
                }
                processed_data.append(processed_coin)
            
            current_app.logger.info(f'Fetched {len(processed_data)} cryptocurrency prices from CoinGecko')
            return processed_data
        
        else:
            current_app.logger.error(f'CoinGecko API error: {response.status_code}')
            return None
        
    except requests.exceptions.Timeout:
        current_app.logger.error('CoinGecko API timeout')
        return None
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f'CoinGecko API request error: {str(e)}')
        return None
    except Exception as e:
        current_app.logger.error(f'Fetch crypto prices error: {str(e)}')
        return None


@crypto_bp.route('/search', methods=['GET'])
def search_cryptocurrencies():
    """Search for cryptocurrencies"""
    try:
        query = request.args.get('q', '').strip()
        
        if not query:
            return jsonify({'error': 'Search query is required'}), 400
        
        if len(query) < 2:
            return jsonify({'error': 'Search query must be at least 2 characters'}), 400
        
        url = "https://api.coingecko.com/api/v3/search"
        params = {'query': query}
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return jsonify({
                'coins': data.get('coins', [])[:20],  # Limit to 20 results
                'exchanges': data.get('exchanges', [])[:10],  # Limit to 10 results
                'categories': data.get('categories', [])[:10],  # Limit to 10 results
                'query': query,
                'timestamp': datetime.utcnow().isoformat()
            }), 200
        else:
            return jsonify({'error': 'Search failed'}), 503
        
    except Exception as e:
        current_app.logger.error(f'Search cryptocurrencies error: {str(e)}')
        return jsonify({'error': 'Failed to search cryptocurrencies'}), 500


@crypto_bp.route('/cache/clear', methods=['POST'])
def clear_crypto_cache():
    """Clear cryptocurrency price cache (for testing/admin use)"""
    try:
        global crypto_cache
        crypto_cache = {'data': None, 'timestamp': None}
        
        current_app.logger.info('Cryptocurrency price cache cleared')
        
        return jsonify({
            'message': 'Cache cleared successfully',
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        current_app.logger.error(f'Clear crypto cache error: {str(e)}')
        return jsonify({'error': 'Failed to clear cache'}), 500


@crypto_bp.route('/cache/status', methods=['GET'])
def get_cache_status():
    """Get cryptocurrency cache status"""
    try:
        global crypto_cache
        
        cache_age = None
        if crypto_cache['timestamp']:
            cache_age = (datetime.now() - crypto_cache['timestamp']).total_seconds()
        
        return jsonify({
            'has_data': crypto_cache['data'] is not None,
            'cache_timestamp': crypto_cache['timestamp'].isoformat() if crypto_cache['timestamp'] else None,
            'cache_age_seconds': cache_age,
            'data_count': len(crypto_cache['data']) if crypto_cache['data'] else 0
        }), 200
        
    except Exception as e:
        current_app.logger.error(f'Get cache status error: {str(e)}')
        return jsonify({'error': 'Failed to get cache status'}), 500
