# Investment System API Documentation

## Overview

This document describes the new investment system APIs and wallet structure changes for the MetaX Coin platform. The system implements package-based investments with date-tracked gains, automated daily returns, referral commissions, and simplified wallet management.

## Key Changes

### 🎯 Simplified Wallet UI Structure

The frontend now displays 6 key wallet values instead of 9 separate wallets:

1. **Available Fund** - Withdrawable money (deposits + admin transfers + settled investments)
2. **Total Investment** - Total amount currently invested (read-only)
3. **Total Gain** - Daily investment returns + staking rewards (read-only)
4. **Total Referral** - Direct referral commissions (read-only)
5. **Level Bonus** - Multi-level commissions (read-only)
6. **Total Income** - Calculated sum (Gain + Referral + Level Bonus)

### 💰 Investment & Withdrawal Rules

- **Investment Flow**: Available Fund → My Investment (locked until maturity)
- **Daily Returns**: Automatically distributed to Total Gain wallet
- **Referral Commissions**: Distributed on investment purchases (10%, 5%, 3%, 2%, 1% for levels 1-5)
- **Withdrawal Rules**: Only Available Fund is withdrawable
- **Settlement**: Admin settles matured investments back to Available Fund or keeps invested
- **Investment Timing**: Returns start the day after investment (simplified)

---

## API Endpoints

### 1. Wallet Summary API

**Endpoint:** `GET /api/dashboard/wallet-summary`

**Description:** Get simplified wallet summary for UI display

**Headers:**
```
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

**Response:**
```json
{
  "success": true,
  "wallet_summary": {
    "available_fund": 1250.00,
    "total_investment": 5000.00,
    "total_gain": 125.00,
    "total_referral": 300.00,
    "level_bonus": 75.00,
    "total_income": 500.00
  },
  "investment_details": {
    "active_investments": 3,
    "total_returns_earned": 125.00,
    "roi_percentage": 2.5
  },
  "withdrawal_info": {
    "withdrawable_amount": 1250.00,
    "withdrawable_wallets": ["available_fund"],
    "locked_amount": 5000.00
  },
  "last_updated": "2025-07-06T10:30:00Z"
}
```

**Error Response:**
```json
{
  "error": "Failed to get wallet summary"
}
```

---

### 2. Investment Packages API

**Endpoint:** `GET /api/investments/packages`

**Description:** Get all available investment packages

**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "success": true,
  "packages": [
    {
      "id": 1,
      "name": "MXC Launch Package",
      "description": "Early access to MXC token launch with guaranteed returns",
      "min_amount": 100.0,
      "max_amount": 10000.0,
      "total_return_percentage": 25.0,
      "duration_days": 180,
      "daily_return_rate": 0.139,
      "launch_date": "2025-08-01",
      "end_date": "2025-12-01",
      "status": "active",
      "is_featured": true,
      "is_available": true,
      "total_invested": 50000.0,
      "total_investors": 25,
      "created_at": "2025-07-06T10:00:00Z"
    }
  ],
  "total": 1
}
```

**Package Status Values:**
- `draft` - Package is being prepared
- `active` - Available for investment
- `launched` - Returns are being distributed (same as active)
- `completed` - Package has ended
- `cancelled` - Package was cancelled

**Package Availability:**
- Packages are available for investment when status is `active`
- Investment timing is simplified: returns start the day after investment
- No complex launch dates or waiting periods

---

### 3. Purchase Investment API

**Endpoint:** `POST /api/investments/purchase`

**Description:** Purchase an investment package

**Headers:**
```
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "package_id": 1,
  "amount": 1000.0
}
```

**Success Response:**
```json
{
  "success": true,
  "message": "Investment purchased successfully",
  "investment": {
    "id": 123,
    "package_id": 1,
    "amount_invested": 1000.0,
    "investment_date": "2025-07-06T10:30:00Z",
    "returns_start_date": "2025-07-07",
    "maturity_date": "2026-01-04",
    "status": "active",
    "expected_total_return": 250.0,
    "expected_daily_return": 1.39,
    "package": {
      "name": "MXC Launch Package",
      "total_return_percentage": 25.0,
      "duration_days": 180
    }
  },
  "new_available_balance": 250.0,
  "new_investment_balance": 1000.0,
  "new_total_investment": 5000.0
}
```

**Error Responses:**
```json
{
  "success": false,
  "message": "Insufficient available funds"
}
```

```json
{
  "success": false,
  "message": "Minimum investment amount is $100"
}
```

```json
{
  "success": false,
  "message": "Investment package is not available"
}
```

```json
{
  "success": false,
  "message": "Account is deactivated"
}
```

```json
{
  "success": false,
  "message": "Daily investment limit exceeded. Limit: $50000, Today: $25000"
}
```

**Investment Validation:**
- User account must be active
- Sufficient balance in available_fund wallet
- Investment amount within package min/max limits
- Daily investment limit: $50,000 per user
- Package must be available for investment
- Automatic wallet initialization if missing

---

### 4. User Investments API

**Endpoint:** `GET /api/investments/my-investments`

**Description:** Get current user's investments

**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Query Parameters:**
- `status` (optional) - Filter by investment status
- `package_id` (optional) - Filter by package ID
- `limit` (optional) - Number of results (default: 50, max: 100)
- `offset` (optional) - Pagination offset (default: 0)

**Response:**
```json
{
  "success": true,
  "investments": [
    {
      "id": 123,
      "package_id": 1,
      "amount_invested": 1000.0,
      "investment_date": "2025-07-06T10:30:00Z",
      "returns_start_date": "2025-07-07",
      "maturity_date": "2026-01-04",
      "total_returns_paid": 45.0,
      "last_return_date": "2025-07-15",
      "status": "active",
      "days_since_investment": 15,
      "days_since_returns_started": 8,
      "expected_total_return": 250.0,
      "expected_daily_return": 1.39,
      "returns_remaining": 205.0,
      "package": {
        "name": "MXC Launch Package",
        "total_return_percentage": 25.0,
        "duration_days": 180
      }
    }
  ],
  "pagination": {
    "total": 3,
    "limit": 50,
    "offset": 0,
    "has_more": false
  },
  "summary": {
    "total_invested": 5000.0,
    "total_returns": 125.0,
    "active_investments": 3,
    "total_investments": 3
  }
}
```

**Investment Status Values:**
- `pending` - Investment is being processed (rare)
- `active` - Returns are being distributed (most common)
- `matured` - Investment has completed, awaiting admin settlement
- `cancelled` - Investment was cancelled or settled

**Investment Lifecycle:**
1. **Purchase** → Status: `active`, Returns start next day
2. **Daily Returns** → Distributed automatically to `self_coin_bonus` wallet
3. **Maturity** → Status: `matured`, Admin settles investment
4. **Settlement** → Status: `cancelled`, Principal returned to user

---

### 5. Investment Statistics API

**Endpoint:** `GET /api/investments/stats`

**Description:** Get investment statistics for current user

**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "success": true,
  "stats": {
    "total_investments": 3,
    "total_invested": 5000.0,
    "total_returns_earned": 125.0,
    "active_investments": 2,
    "waiting_launch": 1,
    "matured_investments": 0,
    "expected_total_returns": 1250.0,
    "returns_remaining": 1125.0,
    "roi_percentage": 2.5
  }
}
```

---

### 6. Package Details API

**Endpoint:** `GET /api/investments/packages/{package_id}`

**Description:** Get detailed information about a specific package

**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "success": true,
  "package": {
    "id": 1,
    "name": "MXC Launch Package",
    "description": "Early access to MXC token launch with guaranteed returns",
    "min_amount": 100.0,
    "max_amount": 10000.0,
    "total_return_percentage": 25.0,
    "duration_days": 180,
    "daily_return_rate": 0.139,
    "launch_date": "2025-08-01",
    "end_date": "2025-12-01",
    "status": "active",
    "is_featured": true,
    "is_available": true,
    "total_invested": 50000.0,
    "total_investors": 25,
    "user_investments": [
      {
        "id": 123,
        "amount_invested": 1000.0,
        "status": "waiting_launch"
      }
    ],
    "user_total_invested": 1000.0
  }
}
```

---

### 7. Investment Details API

**Endpoint:** `GET /api/investments/my-investments/{investment_id}`

**Description:** Get detailed information about a specific investment

**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "success": true,
  "investment": {
    "id": 123,
    "package_id": 1,
    "amount_invested": 1000.0,
    "investment_date": "2025-07-06T10:30:00Z",
    "returns_start_date": "2025-08-01",
    "maturity_date": "2026-01-28",
    "total_returns_paid": 45.0,
    "last_return_date": "2025-08-15",
    "status": "active",
    "expected_total_return": 250.0,
    "expected_daily_return": 1.39,
    "returns_remaining": 205.0,
    "package": {
      "name": "MXC Launch Package",
      "total_return_percentage": 25.0,
      "duration_days": 180
    },
    "return_history": [
      {
        "id": 456,
        "return_date": "2025-07-15",
        "return_amount": 1.39,
        "days_since_start": 8,
        "status": "paid",
        "processed_at": "2025-07-15T00:30:00Z"
      }
    ]
  }
}
```

---

## Error Handling

All API endpoints follow consistent error response format:

**HTTP Status Codes:**
- `200` - Success
- `400` - Bad Request (validation errors)
- `401` - Unauthorized (invalid/missing JWT)
- `404` - Not Found (resource doesn't exist)
- `500` - Internal Server Error

**Error Response Format:**
```json
{
  "success": false,
  "message": "Error description"
}
```

**Common Error Messages:**
- `"User not found"` - Invalid user ID
- `"Investment package not found"` - Invalid package ID
- `"Investment not found"` - Invalid investment ID
- `"Insufficient available funds"` - Not enough balance
- `"Investment package is not available"` - Package not accepting investments
- `"Minimum investment amount is $X"` - Below minimum threshold
- `"Maximum investment amount is $X"` - Above maximum threshold
- `"Account is deactivated"` - User account is not active
- `"Daily investment limit exceeded"` - User exceeded $50,000 daily limit

---

## Complete System Flow

### **🔄 Investment Lifecycle:**

#### **Step 1: Investment Purchase**
```
1. User deposits $1000 → available_fund wallet
2. User sees "MXC Launch Package" (25% return, 180 days)
3. User invests $1000 → money moves to my_investment wallet
4. Investment status: "active" (simplified - no waiting)
5. Referral commissions distributed to sponsors:
   - Level 1 (Direct): $100 (10%) → direct_referral wallet
   - Level 2: $50 (5%) → level_bonus wallet
   - Level 3: $30 (3%) → level_bonus wallet
   - Level 4: $20 (2%) → level_bonus wallet
   - Level 5: $10 (1%) → level_bonus wallet
```

#### **Step 2: Daily Returns**
```
Day 1 (Investment): No returns yet
Day 2: First return $1.39 → total_gain wallet
Day 3: Second return $1.39 → total_gain wallet
...
Day 181: Final return $1.39 → total_gain wallet
Total Returns: $250 (25% of $1000)
```

#### **Step 3: Investment Maturity**
```
After 180 days:
1. Investment status → "matured"
2. Admin settles investment:
   Option A: Return to Available Fund (user can withdraw)
   Option B: Keep in Investment Wallet (user can reinvest)
3. Investment status → "cancelled" (settled)
```

#### **Wallet Display Throughout:**
```
Initial State:
💰 Available Fund: $1000.00
💼 Total Investment: $0.00
🎁 Total Gain: $0.00
👥 Total Referral: $0.00
🌟 Level Bonus: $0.00
📈 Total Income: $0.00

After Investment:
💰 Available Fund: $0.00
💼 Total Investment: $1000.00
🎁 Total Gain: $0.00
👥 Total Referral: $0.00 (user's own referrals)
🌟 Level Bonus: $0.00 (user's own level bonuses)
📈 Total Income: $0.00

After 30 Days (example):
💰 Available Fund: $0.00
💼 Total Investment: $1000.00
🎁 Total Gain: $41.70 (30 × $1.39)
👥 Total Referral: $0.00
🌟 Level Bonus: $0.00
📈 Total Income: $41.70

After Settlement (180 days):
💰 Available Fund: $1000.00 (principal returned)
💼 Total Investment: $0.00
🎁 Total Gain: $250.00 (total returns earned)
👥 Total Referral: $0.00
🌟 Level Bonus: $0.00
📈 Total Income: $250.00
```

---

## Frontend Integration Guide

### 1. Display Wallet Summary

```javascript
// Fetch wallet summary
const response = await fetch('/api/dashboard/wallet-summary', {
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
});

const data = await response.json();

if (data.success) {
  // Update UI with wallet summary
  document.getElementById('available-fund').textContent = `$${data.wallet_summary.available_fund.toFixed(2)}`;
  document.getElementById('total-investment').textContent = `$${data.wallet_summary.total_investment.toFixed(2)}`;
  document.getElementById('total-gain').textContent = `$${data.wallet_summary.total_gain.toFixed(2)}`;
  document.getElementById('total-referral').textContent = `$${data.wallet_summary.total_referral.toFixed(2)}`;
  document.getElementById('level-bonus').textContent = `$${data.wallet_summary.level_bonus.toFixed(2)}`;
  document.getElementById('total-income').textContent = `$${data.wallet_summary.total_income.toFixed(2)}`;
}
```

### 2. Purchase Investment

```javascript
// Purchase investment
const purchaseData = {
  package_id: 1,
  amount: 1000.0
};

const response = await fetch('/api/investments/purchase', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(purchaseData)
});

const result = await response.json();

if (result.success) {
  alert('Investment purchased successfully!');
  // Refresh wallet summary and investment list
} else {
  alert(`Error: ${result.message}`);
}
```

### 3. Display Investment Packages

```javascript
// Fetch available packages
const response = await fetch('/api/investments/packages', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});

const data = await response.json();

if (data.success) {
  data.packages.forEach(package => {
    // Create package card UI
    const packageCard = `
      <div class="package-card">
        <h3>${package.name}</h3>
        <p>${package.description}</p>
        <div class="package-details">
          <span>Min: $${package.min_amount}</span>
          <span>Return: ${package.total_return_percentage}%</span>
          <span>Duration: ${package.duration_days} days</span>
        </div>
        <button onclick="purchasePackage(${package.id})">
          Invest Now
        </button>
      </div>
    `;
    document.getElementById('packages-container').innerHTML += packageCard;
  });
}
```

---

## Database Migration

To implement this system, run the migration script:

```bash
python migrations/create_investment_tables.py
```

This creates:
- `investment_packages` table
- `user_investments` table  
- `investment_returns` table

---

## Automated Processes

The system includes automated daily processes:

1. **Daily Return Calculation** - Runs at 12:30 AM UTC
   - Calculates returns for active investments
   - Distributes returns to user `total_gain` wallets
   - Updates investment tracking
   - Automatic status transitions: `active` → `matured` on maturity date

2. **Investment Validation** - Real-time checks
   - User account status (must be active)
   - Package availability
   - Investment limits ($50,000 daily per user)
   - User balance verification
   - Automatic wallet initialization

3. **Referral Commission Distribution** - On investment purchase
   - Level 1: 10% to `direct_referral` wallet
   - Levels 2-5: 5%, 3%, 2%, 1% to `level_bonus` wallet
   - Automatic upline chain traversal

---

## Key Features Summary

### **✅ For Users:**
- **Simple Investment Flow**: One-click investment purchase
- **Automated Returns**: Daily returns without user action
- **Referral Earnings**: Automatic commission distribution
- **Simplified Wallet UI**: 6 clear wallet values
- **Transparent Tracking**: Complete investment history

### **✅ For Developers:**
- **RESTful APIs**: Clean, consistent API design
- **Comprehensive Validation**: Built-in security and limits
- **Error Handling**: Detailed error messages and codes
- **Real-time Updates**: Live wallet balance updates
- **Audit Trail**: Complete transaction logging

### **✅ System Benefits:**
- **Automated Processing**: No manual intervention needed for returns
- **Scalable Architecture**: Handles multiple investments and users
- **Security First**: User validation, balance checks, transaction safety
- **Admin Control**: Complete admin oversight and settlement control
- **Simplified UX**: Complex backend, simple frontend integration

This investment system provides a complete package-based investment platform with automated returns, referral commissions, and simplified wallet management optimized for user experience and developer integration.
