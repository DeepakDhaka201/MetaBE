# Crypto Deposit Flow - Frontend Integration Guide

## Overview
This document provides complete details for implementing the crypto deposit functionality in the frontend. The system uses a wallet pool approach where users are assigned temporary TRC-20 addresses for deposits.

## Complete Deposit Flow

### 1. User Initiates Deposit Request

**Endpoint:** `POST /api/transactions/deposit/request`

**Headers:**
```
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "amount": 100.50
}
```

**Success Response (200):**
```json
{
  "message": "Deposit wallet assigned successfully",
  "assignment": {
    "id": 123,
    "user_id": 456,
    "wallet_id": 789,
    "expected_amount": 100.50,
    "assigned_at": "2024-01-15T10:30:00Z",
    "expires_at": "2024-01-15T11:00:00Z",
    "is_active": true,
    "is_expired": false,
    "time_remaining": "0:29:45",
    "wallet": {
      "id": 789,
      "address": "TRx1234567890abcdef...",
      "network": "TRON",
      "status": "IN_USE"
    }
  },
  "instructions": {
    "network": "TRON (TRC20)",
    "token": "USDT",
    "amount": 100.50,
    "wallet_address": "TRx1234567890abcdef...",
    "expires_at": "2024-01-15T11:00:00Z",
    "time_remaining_minutes": 29
  }
}
```

**Error Responses:**
```json
// User already has active deposit
{
  "error": "You already have an active deposit request",
  "existing_assignment": {
    // Same assignment object as above
  }
}

// Amount validation errors
{
  "error": "Minimum deposit amount is 10 USDT"
}

{
  "error": "Maximum deposit amount is 10000 USDT"
}

// No wallets available
{
  "error": "No wallets available. Please try again later."
}
```

### 2. Check Deposit Status

**Endpoint:** `GET /api/transactions/deposit/status`

**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Success Response - Active Deposit (200):**
```json
{
  "has_active_deposit": true,
  "assignment": {
    "id": 123,
    "user_id": 456,
    "wallet_id": 789,
    "expected_amount": 100.50,
    "assigned_at": "2024-01-15T10:30:00Z",
    "expires_at": "2024-01-15T11:00:00Z",
    "is_active": true,
    "is_expired": false,
    "time_remaining": "0:25:30",
    "wallet": {
      "address": "TRx1234567890abcdef...",
      "network": "TRON"
    }
  },
  "time_remaining_minutes": 25,
  "is_expired": false
}
```

**Success Response - No Active Deposit (200):**
```json
{
  "has_active_deposit": false,
  "message": "No active deposit request"
}
```

### 3. Get Transaction History

**Endpoint:** `GET /api/transactions/history`

**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Query Parameters:**
- `type` (optional): Filter by transaction type (`deposit`, `withdrawal`, `transfer`)
- `status` (optional): Filter by status (`pending`, `completed`, `failed`)
- `wallet_type` (optional): Filter by wallet type (`available_fund`, etc.)
- `limit` (optional): Number of records (max 100, default 50)
- `offset` (optional): Pagination offset (default 0)

**Success Response (200):**
```json
{
  "transactions": [
    {
      "transaction_id": "TXN_ABC123",
      "transaction_type": "deposit",
      "wallet_type": "available_fund",
      "amount": 100.50,
      "status": "completed",
      "blockchain_txn_id": "0x1234567890abcdef...",
      "from_address": "TUser123...",
      "to_address": "TRx1234567890abcdef...",
      "description": "Crypto deposit via wallet pool",
      "created_at": "2024-01-15T10:30:00Z",
      "processed_at": "2024-01-15T10:35:00Z",
      "confirmed_at": "2024-01-15T10:35:00Z"
    }
  ],
  "pagination": {
    "total_count": 25,
    "limit": 50,
    "offset": 0,
    "has_more": false
  }
}
```

### 4. Get Transaction Limits

**Endpoint:** `GET /api/transactions/limits`

**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Success Response (200):**
```json
{
  "min_deposit": 10.0,
  "max_deposit": 10000.0,
  "min_withdrawal": 20.0,
  "max_withdrawal": 5000.0,
  "withdrawal_fee": 5.0,
  "daily_deposit_limit": 50000.0,
  "monthly_deposit_limit": 200000.0
}
```

### 5. Get Wallet Summary

**Endpoint:** `GET /api/dashboard/wallet-summary`

**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Success Response (200):**
```json
{
  "success": true,
  "wallet_summary": {
    "available_fund": 1250.75,
    "total_investment": 5000.00,
    "total_gain": 750.50,
    "total_referral": 125.25,
    "level_bonus": 85.00,
    "total_income": 960.75
  },
  "investment_details": {
    "active_investments": 3,
    "total_returns_earned": 750.50,
    "roi_percentage": 15.01
  },
  "withdrawal_info": {
    "withdrawable_amount": 1250.75,
    "withdrawable_wallets": ["available_fund"],
    "locked_amount": 5000.00
  },
  "last_updated": "2024-01-15T10:45:00Z"
}
```

## Frontend Implementation Guide

### Step 1: Deposit Request Flow
```javascript
// 1. Validate amount on frontend
const amount = parseFloat(depositAmount);
if (amount < limits.min_deposit || amount > limits.max_deposit) {
  showError(`Amount must be between ${limits.min_deposit} and ${limits.max_deposit} USDT`);
  return;
}

// 2. Request deposit
const response = await fetch('/api/transactions/deposit/request', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ amount })
});

const data = await response.json();

if (response.ok) {
  // Show deposit instructions
  showDepositInstructions(data.instructions);
  startStatusPolling();
} else {
  showError(data.error);
}
```

### Step 2: Status Polling
```javascript
// Poll status every 30 seconds
const pollInterval = setInterval(async () => {
  const response = await fetch('/api/transactions/deposit/status', {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  
  const data = await response.json();
  
  if (!data.has_active_deposit) {
    // Deposit completed or expired
    clearInterval(pollInterval);
    refreshWalletBalance();
    showDepositComplete();
  } else {
    // Update countdown timer
    updateTimeRemaining(data.time_remaining_minutes);
    
    if (data.is_expired) {
      clearInterval(pollInterval);
      showDepositExpired();
    }
  }
}, 30000);
```

### Step 3: Display Deposit Instructions
```javascript
function showDepositInstructions(instructions) {
  const html = `
    <div class="deposit-instructions">
      <h3>Send USDT to Complete Deposit</h3>
      <div class="instruction-item">
        <label>Network:</label>
        <span>${instructions.network}</span>
      </div>
      <div class="instruction-item">
        <label>Token:</label>
        <span>${instructions.token}</span>
      </div>
      <div class="instruction-item">
        <label>Amount:</label>
        <span>${instructions.amount} USDT</span>
      </div>
      <div class="instruction-item">
        <label>Wallet Address:</label>
        <div class="address-container">
          <span class="address">${instructions.wallet_address}</span>
          <button onclick="copyAddress('${instructions.wallet_address}')">Copy</button>
        </div>
      </div>
      <div class="warning">
        ⚠️ Send exactly ${instructions.amount} USDT to this address within ${instructions.time_remaining_minutes} minutes
      </div>
      <div class="qr-code">
        <!-- Generate QR code for wallet address -->
      </div>
    </div>
  `;
  
  document.getElementById('deposit-container').innerHTML = html;
}
```

## Important Notes for Frontend

### 1. Wallet Assignment Expiry
- Each wallet assignment expires in **30 minutes**
- Always check `is_expired` field in status responses
- Show countdown timer to user
- Handle expired assignments gracefully

### 2. Amount Validation
- Always validate amounts on frontend before API calls
- Get current limits from `/api/transactions/limits`
- Show clear error messages for invalid amounts

### 3. Status Polling
- Poll `/api/transactions/deposit/status` every 30-60 seconds
- Stop polling when `has_active_deposit` becomes `false`
- Handle network errors gracefully

### 4. User Experience
- Show clear deposit instructions with QR code
- Display countdown timer for assignment expiry
- Provide copy-to-clipboard for wallet address
- Show deposit progress/status updates
- Refresh wallet balance after successful deposit

### 5. Error Handling
- Handle "already has active deposit" error by showing existing assignment
- Handle "no wallets available" error with retry option
- Show appropriate messages for network/server errors

### 6. Security Considerations
- Always use HTTPS for API calls
- Validate JWT token expiry
- Don't store sensitive data in localStorage
- Implement proper error logging

## Testing Scenarios

1. **Normal Flow**: Request deposit → Get assignment → Send crypto → Admin approval → Credit
2. **Existing Assignment**: Try to request when already have active assignment
3. **Expired Assignment**: Let assignment expire and check status
4. **Invalid Amount**: Test with amounts below/above limits
5. **No Wallets Available**: Test when wallet pool is exhausted
6. **Network Errors**: Test with poor connectivity

## Backend Processing Details

### Deposit Detection & Admin Approval
- Backend monitors assigned wallets every **60 seconds**
- Detects USDT TRC-20 transactions on TRON blockchain
- Validates transaction amount and timestamp
- Creates **PENDING** transaction record with blockchain hash
- **Admin approval required** before crediting user's wallet
- Admin approves via admin panel to complete deposit

### Wallet Pool System
- System maintains pool of pre-funded TRC-20 addresses
- Each assignment is exclusive (one user per wallet at a time)
- Assignments expire after 30 minutes if no deposit received
- Wallets return to pool after assignment completion/expiry

### Transaction States
1. **Assignment Created**: Wallet assigned, waiting for deposit
2. **Deposit Detected**: Blockchain transaction found, status = PENDING
3. **Admin Review**: Admin reviews and approves/rejects deposit
4. **Deposit Confirmed**: Transaction approved and user credited
5. **Assignment Expired**: No deposit received within time limit

## API Response Status Codes

### Success Codes
- `200 OK`: Request successful
- `201 Created`: Resource created successfully

### Error Codes
- `400 Bad Request`: Invalid request data or validation error
- `401 Unauthorized`: Invalid or expired JWT token
- `403 Forbidden`: User account inactive or insufficient permissions
- `404 Not Found`: Resource not found
- `503 Service Unavailable`: No wallets available in pool

## Complete Error Handling Examples

```javascript
async function handleDepositRequest(amount) {
  try {
    const response = await fetch('/api/transactions/deposit/request', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${getToken()}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ amount: parseFloat(amount) })
    });

    const data = await response.json();

    switch (response.status) {
      case 200:
        showDepositInstructions(data);
        startStatusPolling();
        break;

      case 400:
        if (data.existing_assignment) {
          showExistingAssignment(data.existing_assignment);
        } else {
          showError(data.error);
        }
        break;

      case 401:
        redirectToLogin();
        break;

      case 403:
        showError('Account is inactive. Please contact support.');
        break;

      case 503:
        showError('Service temporarily unavailable. Please try again in a few minutes.');
        setTimeout(() => handleDepositRequest(amount), 60000); // Retry after 1 minute
        break;

      default:
        showError('An unexpected error occurred. Please try again.');
    }
  } catch (error) {
    showError('Network error. Please check your connection.');
  }
}
```

## Real-time Updates Implementation

```javascript
class DepositManager {
  constructor() {
    this.pollInterval = null;
    this.isPolling = false;
  }

  startStatusPolling() {
    if (this.isPolling) return;

    this.isPolling = true;
    this.pollInterval = setInterval(async () => {
      await this.checkDepositStatus();
    }, 30000); // Poll every 30 seconds
  }

  stopStatusPolling() {
    if (this.pollInterval) {
      clearInterval(this.pollInterval);
      this.pollInterval = null;
    }
    this.isPolling = false;
  }

  async checkDepositStatus() {
    try {
      const response = await fetch('/api/transactions/deposit/status', {
        headers: { 'Authorization': `Bearer ${getToken()}` }
      });

      if (!response.ok) {
        if (response.status === 401) {
          this.stopStatusPolling();
          redirectToLogin();
          return;
        }
        throw new Error('Failed to check status');
      }

      const data = await response.json();

      if (!data.has_active_deposit) {
        this.stopStatusPolling();
        this.handleDepositComplete();
      } else {
        this.updateDepositStatus(data);
      }
    } catch (error) {
      console.error('Status polling error:', error);
      // Continue polling despite errors
    }
  }

  updateDepositStatus(data) {
    const { assignment, time_remaining_minutes, is_expired } = data;

    if (is_expired) {
      this.stopStatusPolling();
      this.handleDepositExpired();
      return;
    }

    // Update UI with remaining time
    this.updateCountdown(time_remaining_minutes);
  }

  async handleDepositComplete() {
    // Refresh wallet balance
    await this.refreshWalletBalance();

    // Show success message
    showSuccessMessage('Deposit completed successfully!');

    // Refresh transaction history
    await this.refreshTransactionHistory();
  }

  handleDepositExpired() {
    showWarningMessage('Deposit request expired. Please create a new deposit request.');
    // Clear deposit instructions
    clearDepositInstructions();
  }
}
```

## QR Code Generation

```javascript
function generateDepositQR(walletAddress, amount) {
  // Using qrcode.js library
  const qrData = `tron:${walletAddress}?amount=${amount}&token=USDT`;

  QRCode.toCanvas(document.getElementById('qr-canvas'), qrData, {
    width: 200,
    margin: 2,
    color: {
      dark: '#000000',
      light: '#FFFFFF'
    }
  });
}
```

## Wallet Balance Refresh

```javascript
async function refreshWalletBalance() {
  try {
    const response = await fetch('/api/dashboard/wallet-summary', {
      headers: { 'Authorization': `Bearer ${getToken()}` }
    });

    if (response.ok) {
      const data = await response.json();
      updateWalletUI(data.wallet_summary);
    }
  } catch (error) {
    console.error('Failed to refresh wallet balance:', error);
  }
}
```

## Mobile-Specific Considerations

### Deep Links for Wallet Apps
```javascript
function openInWalletApp(address, amount) {
  const deepLink = `tronlink://send?to=${address}&amount=${amount}&token=USDT`;

  // Try to open in TronLink
  window.location.href = deepLink;

  // Fallback to copy address after 2 seconds
  setTimeout(() => {
    copyToClipboard(address);
    showMessage('Address copied to clipboard. Please open your wallet app manually.');
  }, 2000);
}
```

### Responsive Design
- Ensure QR codes are scannable on mobile devices
- Make wallet addresses easily selectable/copyable
- Provide large, touch-friendly copy buttons
- Show clear visual feedback for copy actions

## Security Best Practices

1. **Token Management**
   - Store JWT tokens securely
   - Implement automatic token refresh
   - Clear tokens on logout

2. **Input Validation**
   - Validate all amounts on frontend
   - Sanitize user inputs
   - Implement rate limiting for API calls

3. **Error Information**
   - Don't expose sensitive error details to users
   - Log detailed errors for debugging
   - Show user-friendly error messages

4. **Network Security**
   - Always use HTTPS
   - Implement request timeouts
   - Handle network failures gracefully

This comprehensive documentation provides everything needed to implement a robust crypto deposit flow in the frontend application.
