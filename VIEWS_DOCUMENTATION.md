# API Views Documentation

Complete list of all views organized by app with their purpose and endpoints.

---

## 📁 **accounts** App

### `RegisterView` (APIView)
**Purpose**: User registration  
**Endpoint**: `POST /api/auth/register/`  
**Permissions**: Public (AllowAny)  
**Functionality**:
- Creates new user account
- Creates user profile
- Returns JWT access and refresh tokens
- TODO: Add Proof-of-Work validation
- TODO: Support crypto deposit verification

---

### `LoginView` (APIView)
**Purpose**: User authentication  
**Endpoint**: `POST /api/auth/login/`  
**Permissions**: Public (AllowAny)  
**Functionality**:
- Validates email and password
- Returns JWT access and refresh tokens
- Returns user information
- TODO: Add Proof-of-Work validation for anti-abuse

---

### `MeView` (APIView)
**Purpose**: Get/update current user profile  
**Endpoints**: 
- `GET /api/profile/me/` - Get profile
- `PATCH /api/profile/me/` - Update profile
**Permissions**: Authenticated only  
**Functionality**:
- Returns current user's profile data
- Allows partial updates to profile fields

---

## 📁 **catalog** App

### `CountryViewSet` (ReadOnlyModelViewSet)
**Purpose**: List available countries  
**Endpoint**: `GET /api/catalog/countries/`  
**Permissions**: Public (AllowAny)  
**Functionality**:
- Lists all countries
- Filter by `is_supported`
- Search by name or code
- Read-only (no create/update/delete)

---

### `BankViewSet` (ReadOnlyModelViewSet)
**Purpose**: List banks by country  
**Endpoint**: `GET /api/catalog/banks/`  
**Permissions**: Public (AllowAny)  
**Functionality**:
- Lists all banks
- Filter by `country` (country code) and `is_active`
- Search by bank name
- Returns banks with country information

---

### `AccountViewSet` (ReadOnlyModelViewSet)
**Purpose**: List bank account products  
**Endpoint**: `GET /api/catalog/accounts/`  
**Permissions**: Public (AllowAny)  
**Functionality**:
- Lists active bank accounts for sale
- Filters by `bank` and `is_active`
- Filters by `country` (through bank relationship)
- **Excludes accounts user has already purchased** (if authenticated)
- Search by name, description, SKU
- Ordering by price, balance, created date

---

### `FullzViewSet` (ReadOnlyModelViewSet)
**Purpose**: List individual fullz products  
**Endpoint**: `GET /api/catalog/fullzs/`  
**Permissions**: Public (AllowAny)  
**Functionality**:
- Lists active fullz items
- Filters by `bank` and `is_active`
- Filters by `country` (through bank relationship)
- Search by name, description, email, SSN
- Ordering by created date

---

### `FullzPackageViewSet` (ReadOnlyModelViewSet)
**Purpose**: List fullz packages (bundles)  
**Endpoint**: `GET /api/catalog/fullz-packages/`  
**Permissions**: Public (AllowAny)  
**Functionality**:
- Lists active fullz packages
- Filters by `bank` and `is_active`
- Filters by `country` (through bank relationship)
- Search by name, description
- Ordering by price, quantity, created date

---

## 📁 **wallet** App (v1 - Non-custodial)

### `WalletViewSet` (ReadOnlyModelViewSet)
**Purpose**: Get user wallet balance  
**Endpoint**: `GET /api/wallet/wallet/`  
**Permissions**: Authenticated only  
**Functionality**:
- Returns user's wallet (creates if doesn't exist)
- Returns balance in minor units (cents)
- Returns currency code (USD)
- Returns as list format for consistency

---

### `CryptoNetworkViewSet` (ReadOnlyModelViewSet)
**Purpose**: List supported cryptocurrency networks  
**Endpoint**: `GET /api/wallet/networks/`  
**Permissions**: Authenticated only  
**Functionality**:
- Lists active cryptocurrency networks
- Returns network details (name, symbol, decimals, explorer URLs)
- Used for top-up network selection

---

### `DepositAddressViewSet` (ReadOnlyModelViewSet)
**Purpose**: List user's deposit addresses  
**Endpoint**: `GET /api/wallet/deposit-addresses/`  
**Permissions**: Authenticated only  
**Functionality**:
- Lists user's active deposit addresses
- Shows derived addresses for each network
- Used for displaying deposit addresses to users

---

### `TopUpIntentViewSet` (ModelViewSet)
**Purpose**: Create and manage top-up intents (non-custodial)  
**Endpoints**:
- `GET /api/wallet/topups/` - List user's top-ups
- `POST /api/wallet/topups/` - Create new top-up
- `GET /api/wallet/topups/{id}/` - Get top-up details
- `POST /api/wallet/topups/{id}/check_status/` - Manually check payment status
**Permissions**: Authenticated only  
**Functionality**:
- Creates top-up intent with derived deposit address
- Uses xpub to derive unique addresses per user
- Tracks top-up status (pending, succeeded, failed)
- Manual status check triggers blockchain monitoring
- Handles xpub configuration errors gracefully

---

### `OnChainTransactionViewSet` (ReadOnlyModelViewSet)
**Purpose**: List on-chain transactions  
**Endpoint**: `GET /api/wallet/transactions/`  
**Permissions**: Authenticated only  
**Functionality**:
- Lists user's on-chain transactions
- Shows transaction details (hash, amount, confirmations)
- Linked to top-up intents
- Ordered by occurrence date (newest first)

---

## 📁 **wallet** App (v2 - OXA Pay Integration)

### `WalletV2ViewSet` (ReadOnlyModelViewSet)
**Purpose**: Get user wallet balance (v2)  
**Endpoint**: `GET /api/v2/wallet/wallet/`  
**Permissions**: Authenticated only  
**Functionality**: Same as v1 WalletViewSet

---

### `CryptoNetworkV2ViewSet` (ReadOnlyModelViewSet)
**Purpose**: List supported cryptocurrency networks (v2)  
**Endpoint**: `GET /api/v2/wallet/networks/`  
**Permissions**: Authenticated only  
**Functionality**: Same as v1 CryptoNetworkViewSet

---

### `TopUpIntentV2ViewSet` (ModelViewSet)
**Purpose**: Create top-up intents using OXA Pay  
**Endpoints**:
- `GET /api/v2/wallet/topups/` - List user's top-ups
- `POST /api/v2/wallet/topups/` - Create new top-up via OXA Pay
- `GET /api/v2/wallet/topups/{id}/` - Get top-up details
**Permissions**: Authenticated only  
**Functionality**:
- Creates top-up intent
- Generates OXA Pay payment address
- Returns payment details (address, QR code, track ID)
- Supports static address reuse
- Returns both topup and payment data

---

### `OxaPayPaymentViewSet` (ReadOnlyModelViewSet)
**Purpose**: List OXA Pay payments  
**Endpoints**:
- `GET /api/v2/wallet/payments/` - List user's payments
- `GET /api/v2/wallet/payments/accepted_currencies/` - Get accepted currencies
**Permissions**: Authenticated only  
**Functionality**:
- Lists user's OXA Pay payment history
- Shows payment status (pending, paid, failed, expired)
- Returns payment details (amount, address, track ID)
- Filtered by current user

---

### `OxaPayStaticAddressViewSet` (ModelViewSet)
**Purpose**: Manage reusable static addresses  
**Endpoints**:
- `GET /api/v2/wallet/static-addresses/` - List static addresses
- `POST /api/v2/wallet/static-addresses/` - Create static address
- `DELETE /api/v2/wallet/static-addresses/{id}/` - Delete static address
**Permissions**: Authenticated only  
**Functionality**:
- Creates reusable payment addresses via OXA Pay
- Prevents duplicate addresses per network
- Returns address and QR code
- Can be reused for multiple payments

---

### `OxaPayInvoiceViewSet` (ViewSet)
**Purpose**: Generate payment invoices  
**Endpoint**: `POST /api/v2/wallet/invoices/`  
**Permissions**: Authenticated only  
**Functionality**:
- Generates OXA Pay invoices for orders
- Creates payment links
- Supports custom descriptions, return URLs, callback URLs
- Used for checkout flow

---

### `oxapay_webhook` (Function View)
**Purpose**: Handle OXA Pay payment callbacks  
**Endpoint**: `POST /api/v2/wallet/webhook/`  
**Permissions**: Public (CSRF exempt)  
**Functionality**:
- Receives payment status updates from OXA Pay
- Verifies HMAC-SHA512 signature
- Updates payment status (paying, paid, failed, expired)
- Credits user wallet on successful payment
- Creates transaction records
- Links payments to orders
- Sends email notifications
- Returns "OK" to prevent retries

---

### `webhook_status` (API View)
**Purpose**: Monitor webhook health and activity  
**Endpoint**: `GET /api/v2/wallet/webhook/status/`  
**Permissions**: Admin only  
**Functionality**:
- Shows webhook endpoint status
- Lists recent pending payments
- Lists recent paid payments
- Shows payment statistics (last 24 hours)
- Identifies expired but pending payments

---

### `webhook_payment_detail` (API View)
**Purpose**: Get detailed payment information  
**Endpoint**: `GET /api/v2/wallet/webhook/payment/{track_id}/`  
**Permissions**: Admin only  
**Functionality**:
- Returns detailed information for a specific payment
- Shows payment status, amounts, addresses
- Shows payment timestamps and expiration
- Returns raw webhook response data

---

### `test_webhook` (API View)
**Purpose**: Manually test webhook processing  
**Endpoint**: `POST /api/v2/wallet/webhook/test/`  
**Permissions**: Admin only  
**Functionality**:
- Manually triggers webhook processing for a payment
- Allows testing different payment statuses
- Useful for debugging webhook logic
- Returns test results and updated payment status

---

## 📁 **transactions** App

### `TransactionViewSet` (ReadOnlyModelViewSet)
**Purpose**: List user transactions  
**Endpoint**: `GET /api/transactions/`  
**Permissions**: Authenticated only  
**Functionality**:
- Lists all transactions for current user
- Filters by:
  - `direction` (credit/debit)
  - `category` (topup/purchase/transfer/fee/refund/adjustment)
  - `status` (pending/completed/failed)
  - `currency_code`
  - `date_from` / `date_to`
  - `min_amount` / `max_amount`
- Search by description
- Ordering by created date or amount
- Shows transaction history with balances

---

## 📁 **orders** App

### `CartViewSet` (ModelViewSet)
**Purpose**: Manage shopping cart  
**Endpoints**:
- `GET /api/cart/` - Get user's cart
- `POST /api/cart/items/` - Add item to cart
**Permissions**: Authenticated only  
**Functionality**:
- Creates cart if doesn't exist
- Adds accounts to cart
- Prevents adding already-purchased accounts
- Updates quantity if item already in cart

---

### `CartItemViewSet` (ModelViewSet)
**Purpose**: Manage cart items  
**Endpoints**:
- `GET /api/cart/items/` - List cart items
- `PATCH /api/cart/items/{id}/` - Update item quantity
- `DELETE /api/cart/items/{id}/` - Remove item from cart
**Permissions**: Authenticated only  
**Functionality**:
- Lists items in user's cart
- Updates item quantities
- Removes items from cart
- Shows item details (account, price, quantity)

---

### `OrderViewSet` (ModelViewSet)
**Purpose**: Create and manage orders  
**Endpoints**:
- `GET /api/orders/` - List user's orders
- `POST /api/orders/` - Create new order
- `GET /api/orders/{id}/` - Get order details
**Permissions**: Authenticated only  
**Functionality**:
- Creates order from cart
- Supports two payment methods:
  - **Wallet**: Deducts balance immediately, marks order as 'paid'
  - **Crypto (OXA Pay)**: Creates order as 'pending', waits for webhook confirmation
- Validates wallet balance for wallet payments
- Creates order items from cart
- Creates transaction records
- Clears cart after successful wallet payment
- Returns order with items and status

---

## 📁 **notifications** App

### (No views currently implemented)
**Purpose**: Future notification system  
**Status**: App exists but no views defined yet

---

## Summary by Endpoint

### Authentication
- `POST /api/auth/register/` - Register new user
- `POST /api/auth/login/` - Login user
- `POST /api/auth/refresh/` - Refresh JWT token (DRF SimpleJWT)

### Profile
- `GET /api/profile/me/` - Get profile
- `PATCH /api/profile/me/` - Update profile

### Catalog
- `GET /api/catalog/countries/` - List countries
- `GET /api/catalog/banks/` - List banks
- `GET /api/catalog/accounts/` - List accounts
- `GET /api/catalog/fullzs/` - List fullz
- `GET /api/catalog/fullz-packages/` - List fullz packages

### Wallet (v1 - Non-custodial)
- `GET /api/wallet/wallet/` - Get wallet
- `GET /api/wallet/networks/` - List networks
- `GET /api/wallet/deposit-addresses/` - List addresses
- `GET /api/wallet/topups/` - List top-ups
- `POST /api/wallet/topups/` - Create top-up
- `POST /api/wallet/topups/{id}/check_status/` - Check status
- `GET /api/wallet/transactions/` - List on-chain transactions

### Wallet (v2 - OXA Pay)
- `GET /api/v2/wallet/wallet/` - Get wallet
- `GET /api/v2/wallet/networks/` - List networks
- `GET /api/v2/wallet/topups/` - List top-ups
- `POST /api/v2/wallet/topups/` - Create top-up (OXA Pay)
- `GET /api/v2/wallet/payments/` - List payments
- `GET /api/v2/wallet/payments/accepted_currencies/` - Get currencies
- `GET /api/v2/wallet/static-addresses/` - List static addresses
- `POST /api/v2/wallet/static-addresses/` - Create static address
- `POST /api/v2/wallet/invoices/` - Generate invoice
- `POST /api/v2/wallet/webhook/` - OXA Pay webhook
- `GET /api/v2/wallet/webhook/status/` - Webhook status (admin)
- `GET /api/v2/wallet/webhook/payment/{track_id}/` - Payment detail (admin)
- `POST /api/v2/wallet/webhook/test/` - Test webhook (admin)

### Transactions
- `GET /api/transactions/` - List transactions

### Orders
- `GET /api/cart/` - Get cart
- `POST /api/cart/items/` - Add to cart
- `GET /api/cart/items/` - List cart items
- `PATCH /api/cart/items/{id}/` - Update item
- `DELETE /api/cart/items/{id}/` - Remove item
- `GET /api/orders/` - List orders
- `POST /api/orders/` - Create order

---

## Permission Summary

- **Public (AllowAny)**: Registration, login, catalog browsing
- **Authenticated**: All wallet, transaction, order, and profile endpoints
- **Admin Only**: Webhook monitoring and testing endpoints

---

## Notes

1. **Two Wallet Systems**: 
   - v1 (`/api/wallet/`) - Non-custodial, xpub-derived addresses
   - v2 (`/api/v2/wallet/`) - OXA Pay integration, custodial

2. **Payment Methods**:
   - Wallet balance (immediate deduction)
   - Crypto via OXA Pay (webhook confirmation)

3. **Security**:
   - JWT authentication for all protected endpoints
   - HMAC signature verification for webhooks
   - User-scoped queries (users only see their own data)

4. **Future Enhancements** (TODOs):
   - Proof-of-Work validation for registration/login
   - Crypto deposit verification alternative
   - Notification system

