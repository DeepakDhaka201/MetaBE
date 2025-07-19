# Crypto Withdrawal Flow - Frontend Integration Guide

## Overview
This document provides complete details for implementing the crypto withdrawal functionality in the frontend. The system uses a manual admin approval process where users request withdrawals, admins approve them, and then manually send crypto to user addresses.

## Complete Withdrawal Flow

### 1. User Initiates Withdrawal Request

**Endpoint:** `POST /api/transactions/withdraw`

**Headers:**
```
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "amount": 100.50,
  "wallet_address": "TRx1234567890abcdef...",
  "wallet_type": "available_fund",
  "description": "Withdrawal to personal wallet"
}
```

**Success Response (201):**
```json
{
  "message": "Withdrawal request submitted successfully",
  "transaction": {
    "transaction_id": "TXN_WD_ABC123",
    "transaction_type": "withdrawal",
    "wallet_type": "available_fund",
    "amount": 100.50,
    "fee": 5.0,
    "status": "pending",
    "to_address": "TRx1234567890abcdef...",
    "description": "Withdrawal to TRx1234567890abcdef...",
    "created_at": "2024-01-15T10:30:00Z",
    "estimated_processing_time": "24-48 hours"
  },
  "status": "pending_admin_approval",
  "estimated_processing_time": "24-48 hours"
}
```

**Error Responses:**
```json
// Insufficient balance
{
  "error": "Insufficient balance",
  "available_balance": 95.25,
  "required_amount": 105.50,
  "withdrawal_fee": 5.0
}

// Invalid wallet type
{
  "error": "Withdrawals only allowed from Available Fund wallet",
  "message": "Contact admin to move funds to Available Fund for withdrawal"
}

// Amount validation errors
{
  "error": "Minimum withdrawal amount is 20 USDT"
}

{
  "error": "Maximum withdrawal amount is 5000 USDT"
}

// Invalid address
{
  "error": "Invalid TRON wallet address format"
}

// User not verified
{
  "error": "Account verification required for withdrawals"
}
```

### 2. Get Transaction History (Including Withdrawals)

**Endpoint:** `GET /api/transactions/history`

**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Query Parameters:**
- `type=withdrawal` - Filter for withdrawal transactions only
- `status` (optional): Filter by status (`pending`, `completed`, `failed`, `cancelled`)
- `limit` (optional): Number of records (max 100, default 50)
- `offset` (optional): Pagination offset (default 0)

**Success Response (200):**
```json
{
  "transactions": [
    {
      "transaction_id": "TXN_WD_ABC123",
      "transaction_type": "withdrawal",
      "wallet_type": "available_fund",
      "amount": 100.50,
      "fee": 5.0,
      "status": "pending",
      "to_address": "TRx1234567890abcdef...",
      "description": "Withdrawal to personal wallet",
      "created_at": "2024-01-15T10:30:00Z",
      "processed_at": null,
      "confirmed_at": null,
      "admin_notes": null,
      "blockchain_txn_id": null
    },
    {
      "transaction_id": "TXN_WD_XYZ789",
      "transaction_type": "withdrawal",
      "wallet_type": "available_fund",
      "amount": 50.0,
      "fee": 5.0,
      "status": "completed",
      "to_address": "TRx9876543210fedcba...",
      "description": "Withdrawal to external wallet",
      "created_at": "2024-01-14T15:20:00Z",
      "processed_at": "2024-01-15T09:15:00Z",
      "confirmed_at": "2024-01-15T09:15:00Z",
      "admin_notes": "Approved and processed manually",
      "blockchain_txn_id": "0xabcdef1234567890..."
    }
  ],
  "pagination": {
    "total_count": 15,
    "limit": 50,
    "offset": 0,
    "has_more": false
  }
}
```

### 3. Cancel Pending Withdrawal

**Endpoint:** `POST /api/transactions/cancel/{transaction_id}`

**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Success Response (200):**
```json
{
  "message": "Transaction cancelled successfully",
  "transaction": {
    "transaction_id": "TXN_WD_ABC123",
    "transaction_type": "withdrawal",
    "status": "cancelled",
    "amount": 100.50,
    "fee": 5.0,
    "error_message": "Cancelled by user",
    "processed_at": "2024-01-15T11:00:00Z"
  }
}
```

**Error Responses:**
```json
// Transaction not found or cannot be cancelled
{
  "error": "Transaction not found or cannot be cancelled"
}

// Only withdrawals can be cancelled
{
  "error": "Only withdrawal transactions can be cancelled"
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
  "daily_withdrawal_limit": 10000.0,
  "monthly_withdrawal_limit": 50000.0
}
```

### 5. Get Specific Transaction Details

**Endpoint:** `GET /api/transactions/{transaction_id}`

**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Success Response (200):**
```json
{
  "transaction": {
    "transaction_id": "TXN_WD_ABC123",
    "transaction_type": "withdrawal",
    "wallet_type": "available_fund",
    "amount": 100.50,
    "fee": 5.0,
    "status": "pending",
    "to_address": "TRx1234567890abcdef...",
    "description": "Withdrawal to personal wallet",
    "created_at": "2024-01-15T10:30:00Z",
    "processed_at": null,
    "confirmed_at": null,
    "admin_notes": null,
    "blockchain_txn_id": null,
    "estimated_processing_time": "24-48 hours"
  }
}
```

### 6. Get Available Withdrawal Balance

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
  "withdrawal_info": {
    "withdrawable_amount": 1250.75,
    "withdrawable_wallets": ["available_fund"],
    "locked_amount": 0.0
  },
  "last_updated": "2024-01-15T10:45:00Z"
}
```

## Frontend Implementation Guide

### Step 1: Withdrawal Request Flow
```javascript
// 1. Validate inputs on frontend
async function initiateWithdrawal(amount, address, description = '') {
  // Validate amount
  if (amount < limits.min_withdrawal || amount > limits.max_withdrawal) {
    showError(`Amount must be between ${limits.min_withdrawal} and ${limits.max_withdrawal} USDT`);
    return;
  }

  // Validate TRON address format
  if (!isValidTronAddress(address)) {
    showError('Please enter a valid TRON wallet address');
    return;
  }

  // Check available balance
  const totalRequired = amount + limits.withdrawal_fee;
  if (totalRequired > availableBalance) {
    showError(`Insufficient balance. Required: ${totalRequired} USDT (including ${limits.withdrawal_fee} USDT fee)`);
    return;
  }

  // Submit withdrawal request
  try {
    const response = await fetch('/api/transactions/withdraw', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        amount: parseFloat(amount),
        wallet_address: address.trim(),
        wallet_type: 'available_fund',
        description: description.trim()
      })
    });

    const data = await response.json();

    if (response.ok) {
      showWithdrawalSuccess(data);
      refreshTransactionHistory();
      refreshWalletBalance();
    } else {
      showError(data.error);
    }
  } catch (error) {
    showError('Network error. Please try again.');
  }
}

// 2. TRON address validation
function isValidTronAddress(address) {
  // TRON addresses start with 'T' and are 34 characters long
  const tronRegex = /^T[A-Za-z0-9]{33}$/;
  return tronRegex.test(address);
}
```

### Step 2: Transaction Status Tracking
```javascript
// Track withdrawal status
function showWithdrawalSuccess(data) {
  const html = `
    <div class="withdrawal-success">
      <h3>Withdrawal Request Submitted</h3>
      <div class="transaction-details">
        <div class="detail-item">
          <label>Transaction ID:</label>
          <span>${data.transaction.transaction_id}</span>
        </div>
        <div class="detail-item">
          <label>Amount:</label>
          <span>${data.transaction.amount} USDT</span>
        </div>
        <div class="detail-item">
          <label>Fee:</label>
          <span>${data.transaction.fee} USDT</span>
        </div>
        <div class="detail-item">
          <label>To Address:</label>
          <span class="address">${data.transaction.to_address}</span>
        </div>
        <div class="detail-item">
          <label>Status:</label>
          <span class="status pending">Pending Admin Approval</span>
        </div>
        <div class="detail-item">
          <label>Processing Time:</label>
          <span>${data.estimated_processing_time}</span>
        </div>
      </div>
      <div class="actions">
        <button onclick="cancelWithdrawal('${data.transaction.transaction_id}')" class="btn-cancel">
          Cancel Request
        </button>
        <button onclick="viewTransactionHistory()" class="btn-secondary">
          View History
        </button>
      </div>
    </div>
  `;
  
  document.getElementById('withdrawal-result').innerHTML = html;
}
```

### Step 3: Cancel Withdrawal
```javascript
async function cancelWithdrawal(transactionId) {
  if (!confirm('Are you sure you want to cancel this withdrawal request?')) {
    return;
  }

  try {
    const response = await fetch(`/api/transactions/cancel/${transactionId}`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });

    const data = await response.json();

    if (response.ok) {
      showSuccess('Withdrawal cancelled successfully. Funds have been unlocked.');
      refreshTransactionHistory();
      refreshWalletBalance();
    } else {
      showError(data.error);
    }
  } catch (error) {
    showError('Failed to cancel withdrawal. Please try again.');
  }
}
```

### Step 4: Transaction History Display
```javascript
async function loadWithdrawalHistory() {
  try {
    const response = await fetch('/api/transactions/history?type=withdrawal&limit=20', {
      headers: { 'Authorization': `Bearer ${token}` }
    });

    const data = await response.json();

    if (response.ok) {
      displayWithdrawalHistory(data.transactions);
    }
  } catch (error) {
    console.error('Failed to load withdrawal history:', error);
  }
}

function displayWithdrawalHistory(transactions) {
  const html = transactions.map(tx => `
    <div class="transaction-item ${tx.status}">
      <div class="tx-header">
        <span class="tx-id">${tx.transaction_id}</span>
        <span class="tx-status status-${tx.status}">${getStatusDisplay(tx.status)}</span>
      </div>
      <div class="tx-details">
        <div class="amount">-${tx.amount} USDT</div>
        <div class="fee">Fee: ${tx.fee} USDT</div>
        <div class="address">${tx.to_address}</div>
        <div class="date">${formatDate(tx.created_at)}</div>
      </div>
      ${tx.status === 'pending' ? `
        <div class="tx-actions">
          <button onclick="cancelWithdrawal('${tx.transaction_id}')" class="btn-cancel-small">
            Cancel
          </button>
        </div>
      ` : ''}
      ${tx.blockchain_txn_id ? `
        <div class="blockchain-link">
          <a href="https://tronscan.org/#/transaction/${tx.blockchain_txn_id}" target="_blank">
            View on Blockchain
          </a>
        </div>
      ` : ''}
    </div>
  `).join('');

  document.getElementById('withdrawal-history').innerHTML = html;
}

function getStatusDisplay(status) {
  const statusMap = {
    'pending': 'Pending Approval',
    'processing': 'Processing',
    'completed': 'Completed',
    'failed': 'Failed',
    'cancelled': 'Cancelled',
    'rejected': 'Rejected'
  };
  return statusMap[status] || status;
}
```

## Withdrawal Process Explanation

### User Experience Flow
1. **Request**: User enters amount and TRON address
2. **Validation**: System validates amount, address, and balance
3. **Lock Funds**: Funds are immediately locked to prevent double spending
4. **Admin Review**: Admin reviews withdrawal request (24-48 hours)
5. **Manual Processing**: Admin manually sends crypto to user's address
6. **Completion**: Transaction marked as completed in system

### Security Features
- **Immediate Fund Locking**: Prevents double spending
- **Admin Approval Required**: Manual review of all withdrawals
- **User Cancellation**: Users can cancel pending requests
- **Audit Trail**: Complete transaction history
- **Address Validation**: TRON address format validation
- **Balance Verification**: Ensures sufficient funds including fees

### Status Meanings
- **Pending**: Waiting for admin approval
- **Processing**: Admin is manually sending crypto
- **Completed**: Crypto sent and transaction confirmed
- **Cancelled**: User cancelled the request
- **Rejected**: Admin rejected the request
- **Failed**: Technical error occurred

## Important Notes for Frontend

### 1. Fund Locking
- Funds are locked immediately when withdrawal is requested
- Locked funds are not available for other transactions
- Cancelling withdrawal unlocks the funds immediately

### 2. Manual Processing
- All withdrawals require manual admin approval
- Processing time is typically 24-48 hours
- Users should be informed about the manual process

### 3. Address Validation
- Always validate TRON address format on frontend
- TRON addresses start with 'T' and are 34 characters long
- Show clear error messages for invalid addresses

### 4. Fee Handling
- Withdrawal fee is added to the requested amount
- Always show total amount (amount + fee) to user
- Check balance against total required amount

### 5. Error Handling
- Handle insufficient balance gracefully
- Show clear messages for validation errors
- Provide retry options for network errors

### 6. User Communication
- Clearly explain the manual approval process
- Set proper expectations for processing time
- Provide transaction tracking capabilities

## Admin Workflow (For Reference)

### Admin Approval Process
1. **Review Request**: Admin sees withdrawal request in admin panel
2. **Verify Details**: Check amount, address, user verification status
3. **Approve/Reject**: Admin approves or rejects the request
4. **Manual Crypto Send**: Admin manually sends USDT to user's address
5. **Update Transaction**: Admin can add blockchain transaction hash
6. **Mark Complete**: Transaction status updated to completed

### Admin Endpoints (For Admin Panel)
```
GET /api/admin/transactions?status=pending&type=withdrawal
POST /api/admin/transactions/{id}/approve
POST /api/admin/transactions/{id}/reject
```

## Advanced Frontend Features

### Real-time Status Updates
```javascript
class WithdrawalManager {
  constructor() {
    this.statusCheckInterval = null;
  }

  startStatusMonitoring(transactionId) {
    // Check status every 5 minutes for pending withdrawals
    this.statusCheckInterval = setInterval(async () => {
      await this.checkWithdrawalStatus(transactionId);
    }, 300000); // 5 minutes
  }

  async checkWithdrawalStatus(transactionId) {
    try {
      const response = await fetch(`/api/transactions/${transactionId}`, {
        headers: { 'Authorization': `Bearer ${getToken()}` }
      });

      if (response.ok) {
        const data = await response.json();
        this.updateTransactionStatus(data.transaction);

        // Stop monitoring if transaction is no longer pending
        if (data.transaction.status !== 'pending') {
          this.stopStatusMonitoring();
          this.handleStatusChange(data.transaction);
        }
      }
    } catch (error) {
      console.error('Status check failed:', error);
    }
  }

  stopStatusMonitoring() {
    if (this.statusCheckInterval) {
      clearInterval(this.statusCheckInterval);
      this.statusCheckInterval = null;
    }
  }

  handleStatusChange(transaction) {
    switch (transaction.status) {
      case 'completed':
        showNotification('Withdrawal completed successfully!', 'success');
        refreshWalletBalance();
        break;
      case 'rejected':
        showNotification('Withdrawal was rejected by admin', 'error');
        refreshWalletBalance(); // Funds should be unlocked
        break;
      case 'failed':
        showNotification('Withdrawal failed. Funds have been returned.', 'warning');
        refreshWalletBalance();
        break;
    }
  }
}
```

### Withdrawal Calculator
```javascript
function createWithdrawalCalculator() {
  return {
    calculateTotal: (amount, fee) => {
      return parseFloat(amount) + parseFloat(fee);
    },

    calculateReceived: (amount, fee) => {
      return parseFloat(amount); // User receives the amount, fee is separate
    },

    validateAmount: (amount, limits, availableBalance) => {
      const numAmount = parseFloat(amount);
      const total = numAmount + limits.withdrawal_fee;

      if (numAmount < limits.min_withdrawal) {
        return { valid: false, error: `Minimum withdrawal is ${limits.min_withdrawal} USDT` };
      }

      if (numAmount > limits.max_withdrawal) {
        return { valid: false, error: `Maximum withdrawal is ${limits.max_withdrawal} USDT` };
      }

      if (total > availableBalance) {
        return { valid: false, error: `Insufficient balance. Need ${total} USDT (including ${limits.withdrawal_fee} USDT fee)` };
      }

      return { valid: true };
    },

    formatDisplay: (amount, fee) => {
      return {
        amount: parseFloat(amount).toFixed(2),
        fee: parseFloat(fee).toFixed(2),
        total: (parseFloat(amount) + parseFloat(fee)).toFixed(2)
      };
    }
  };
}

// Usage in withdrawal form
const calculator = createWithdrawalCalculator();

function updateWithdrawalPreview(amount) {
  const validation = calculator.validateAmount(amount, limits, availableBalance);
  const display = calculator.formatDisplay(amount, limits.withdrawal_fee);

  if (validation.valid) {
    document.getElementById('withdrawal-preview').innerHTML = `
      <div class="preview-item">
        <label>You will receive:</label>
        <span class="amount">${display.amount} USDT</span>
      </div>
      <div class="preview-item">
        <label>Network fee:</label>
        <span class="fee">${display.fee} USDT</span>
      </div>
      <div class="preview-item total">
        <label>Total deducted:</label>
        <span class="total">${display.total} USDT</span>
      </div>
    `;
    enableWithdrawButton();
  } else {
    document.getElementById('withdrawal-preview').innerHTML = `
      <div class="error">${validation.error}</div>
    `;
    disableWithdrawButton();
  }
}
```

### Address Book Feature
```javascript
class AddressBook {
  constructor() {
    this.addresses = this.loadAddresses();
  }

  loadAddresses() {
    const stored = localStorage.getItem('withdrawal_addresses');
    return stored ? JSON.parse(stored) : [];
  }

  saveAddresses() {
    localStorage.setItem('withdrawal_addresses', JSON.stringify(this.addresses));
  }

  addAddress(address, label) {
    if (!this.isValidTronAddress(address)) {
      throw new Error('Invalid TRON address');
    }

    const existing = this.addresses.find(addr => addr.address === address);
    if (existing) {
      throw new Error('Address already exists');
    }

    this.addresses.push({
      id: Date.now().toString(),
      address: address,
      label: label,
      created_at: new Date().toISOString(),
      used_count: 0
    });

    this.saveAddresses();
  }

  removeAddress(id) {
    this.addresses = this.addresses.filter(addr => addr.id !== id);
    this.saveAddresses();
  }

  incrementUsage(address) {
    const addr = this.addresses.find(a => a.address === address);
    if (addr) {
      addr.used_count++;
      addr.last_used = new Date().toISOString();
      this.saveAddresses();
    }
  }

  getAddresses() {
    return this.addresses.sort((a, b) => b.used_count - a.used_count);
  }

  isValidTronAddress(address) {
    return /^T[A-Za-z0-9]{33}$/.test(address);
  }
}
```

### Mobile Optimizations
```javascript
// Mobile-specific withdrawal features
function initMobileWithdrawal() {
  // Add camera QR code scanning for addresses
  if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
    addQRScanButton();
  }

  // Add haptic feedback for important actions
  function vibrate(pattern = [100]) {
    if (navigator.vibrate) {
      navigator.vibrate(pattern);
    }
  }

  // Optimize input for mobile
  function setupMobileInputs() {
    const amountInput = document.getElementById('withdrawal-amount');
    amountInput.setAttribute('inputmode', 'decimal');
    amountInput.setAttribute('pattern', '[0-9]*\\.?[0-9]*');
  }

  setupMobileInputs();
}

function addQRScanButton() {
  const scanButton = document.createElement('button');
  scanButton.innerHTML = '📷 Scan QR Code';
  scanButton.onclick = startQRScan;
  document.getElementById('address-input-container').appendChild(scanButton);
}

async function startQRScan() {
  try {
    // Implementation would use a QR code scanning library
    // like qr-scanner or jsQR
    const result = await scanQRCode();
    if (result && isValidTronAddress(result)) {
      document.getElementById('withdrawal-address').value = result;
      updateWithdrawalPreview();
    }
  } catch (error) {
    showError('QR code scanning failed');
  }
}
```

## Security Best Practices

### Frontend Security
1. **Input Validation**: Always validate amounts and addresses on frontend
2. **Secure Storage**: Don't store sensitive data in localStorage
3. **Token Management**: Handle JWT token expiry gracefully
4. **Rate Limiting**: Implement client-side rate limiting for requests

### User Education
1. **Address Verification**: Encourage users to double-check addresses
2. **Processing Time**: Set clear expectations about manual processing
3. **Fee Transparency**: Always show fees clearly before confirmation
4. **Security Tips**: Educate users about withdrawal security

### Error Prevention
1. **Confirmation Dialogs**: Use confirmation for all withdrawal actions
2. **Address Validation**: Validate TRON address format strictly
3. **Amount Limits**: Enforce min/max limits on frontend
4. **Balance Checks**: Always verify sufficient balance including fees

## Testing Scenarios

### Functional Testing
1. **Valid Withdrawal**: Test with valid amount and address
2. **Invalid Address**: Test with malformed TRON addresses
3. **Insufficient Balance**: Test with amount exceeding balance
4. **Amount Limits**: Test below minimum and above maximum
5. **Cancellation**: Test cancelling pending withdrawals
6. **Network Errors**: Test with poor connectivity

### Edge Cases
1. **Exact Balance**: Withdrawal that uses entire available balance
2. **Concurrent Requests**: Multiple withdrawal requests
3. **Session Expiry**: Token expiry during withdrawal process
4. **Address Reuse**: Using same address multiple times

### User Experience Testing
1. **Mobile Responsiveness**: Test on various mobile devices
2. **Loading States**: Test with slow network connections
3. **Error Recovery**: Test error handling and recovery flows
4. **Accessibility**: Test with screen readers and keyboard navigation

This comprehensive documentation provides everything needed to implement a robust withdrawal system that works seamlessly with the manual admin approval process.
