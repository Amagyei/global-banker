## App structure reference

### accounts ✅ (Implemented)
- Models: Profile ✅
- Views: Auth (register/login/refresh) ✅, Profile (GET/PATCH /api/profile/me) ✅
- Serializers: RegisterSerializer ✅, LoginSerializer ✅, ProfileSerializer ✅
- Auth: Email + password with JWT tokens
- Endpoints: `/api/auth/register`, `/api/auth/login`, `/api/auth/refresh`, `/api/profile/me`
- Security TODOs:
  - OTP verification (email/SMS on registration/login)
  - Rate limiting for auth endpoints
  - Account lockout after failed attempts
  - Password reset flow
  - 2FA/MFA support
  - Device/session management
  - Email verification before activation
  - Security logging
  - HTTPS-only cookies in production
  - Proof-of-Work (client puzzle) verification on register/login
  - Small crypto deposit verification as alternative KYC-lite

### catalog
- Models: Country, Bank, Account
- Views: Countries list, Banks list, Accounts list (filtered by country/bank)
- Serializers: CountrySerializer, BankSerializer, AccountSerializer
- **Note:** Bank and Account are catalog products (items being sold)

### banking
- **REMOVED** - Only cryptocurrency payments (handled in wallet app)

### wallet (includes crypto)
- Models: Wallet, CryptoNetwork, CryptoWallet, DepositAddress, TopUpIntent, OnChainTransaction
- Views: Wallet balances, Top-ups, Crypto networks/addresses/tx, Webhook
- Serializers: WalletSerializer, TopUpIntentSerializer, CryptoNetworkSerializer, DepositAddressSerializer, OnChainTxSerializer

### transactions
- Models: Transaction
- Views: Transactions list with filters
- Serializers: TransactionSerializer

### orders
- Models: Cart, CartItem, Order, OrderItem, Fulfillment, Recipient (JSON or model)
- Views: Cart CRUD, Create order, Orders list/detail, Cancel, Fulfill (internal)
- Serializers: CartSerializer, CartItemSerializer, OrderSerializer, OrderItemSerializer, FulfillmentSerializer

### notifications
- Models: Notification
- Views: Notifications list, Mark read
- Serializers: NotificationSerializer

### core (optional helpers)
- Utilities: pagination defaults, money helpers, permissions, idempotency, enums/constants

### Cross-app relations
- Profile.user → auth.User
- Account.country → Country
- Account.bank → Bank
- Bank.country → Country
- Wallet.user → auth.User
- TopUpIntent.user → auth.User; TopUpIntent.network → CryptoNetwork?; TopUpIntent.deposit_address → DepositAddress?
- OnChainTransaction.user → auth.User; OnChainTransaction.network → CryptoNetwork; OnChainTransaction.topup_intent → TopUpIntent?
- Transaction.user → auth.User; related_topup_intent → TopUpIntent?; related_onchain_tx → OnChainTransaction?; related_order → Order?
- Cart.user → auth.User (one cart per user)
- CartItem.cart → Cart; CartItem.account → Account
- Order.user → auth.User
- OrderItem.order → Order; OrderItem.account → Account
- Fulfillment.order → Order
- Notification.user → auth.User

### Conventions
- Money in minor units; on-chain stores atomic and derived minor using network decimals
- Indexes: (user, created_at) on Transaction and Order; unique primary wallet per (user, network); unique (cart, gift_item)

