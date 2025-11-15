# Backend Model Plan

## catalog app

### Country
- code (PK): CharField(3) - "US", "UK", "CA"
- name: CharField - "United States", "United Kingdom", "Canada"
- currency_code: CharField(3) - "USD", "GBP", "CAD"
- flag_url: URLField (optional)
- is_supported: BooleanField

### Bank (Financial Institution - Catalog Product)
- id: UUID (PK)
- name: CharField - "Chase", "Bank of America", "Wells Fargo", "CitiBank", "U.S Bank", "Credit Unions", etc.
- logo_url: URLField (optional)
- country: ForeignKey(Country) - which country this bank operates in
- is_active: BooleanField

### Account (Bank Account Product - Catalog Item)
- id: UUID (PK)
- sku: CharField (unique, auto-generated) - auto-generated from bank name + UUID (e.g., "CHASE-D4B98749")
- name: CharField - product name
- description: TextField 
- bank: ForeignKey(Bank) - which financial institution (country inherited from bank)
- balance_minor: BigIntegerField - account balance in minor units (e.g., 77300 for $773.00)
- price_minor: BigIntegerField - selling price in minor units
- image_url: URLField (optional)
- is_active: BooleanField
- metadata: JSONField (optional) - additional product data
- created_at, updated_at: DateTimeField
- **Properties:**
  - `country` (property) - returns `bank.country`
  - `currency_code` (property) - returns `bank.country.currency_code`

**Indexes:** (bank, is_active)
**SKU Generation:** Auto-generated via pre_save signal: `{BANK_NAME_CLEANED}-{UUID_FIRST_8_CHARS}`

---

## wallet app

### Wallet
- id: UUID (PK)
- user: ForeignKey(User, unique=True)
- currency_code: CharField(3) - "USD"
- balance_minor: BigIntegerField - current balance
- pending_minor: BigIntegerField - pending top-ups
- updated_at: DateTimeField

**Indexes:** (user, currency_code)

### TopUpIntent
- id: UUID (PK)
- user: ForeignKey(User)
- amount_minor: BigIntegerField
- currency_code: CharField(3)
- network: ForeignKey(CryptoNetwork) - cryptocurrency network
- deposit_address: ForeignKey(DepositAddress) - deposit address for crypto
- status: CharField - "pending", "awaiting_confirmations", "succeeded", "failed", "expired"
- provider_ref: CharField (optional) - external payment reference
- expires_at: DateTimeField
- created_at, updated_at: DateTimeField

**Indexes:** (user, status), (user, created_at)

### CryptoNetwork
- id: UUID (PK)
- key: CharField(unique) - "eth", "btc", "tron", "sol"
- name: CharField - "Ethereum", "Bitcoin", etc.
- chain_id: CharField (optional)
- explorer_url: URLField
- decimals: IntegerField - 18 for ETH, 8 for BTC
- native_symbol: CharField - "ETH", "BTC"
- is_active: BooleanField

### CryptoWallet
- id: UUID (PK)
- user: ForeignKey(User)
- network: ForeignKey(CryptoNetwork)
- external_wallet_address: CharField - user's wallet address
- address_label: CharField (optional) - user's label
- is_primary: BooleanField
- created_at: DateTimeField

**Unique constraint:** (user, network, is_primary=True) - only one primary per network

### DepositAddress
- id: UUID (PK)
- user: ForeignKey(User)
- network: ForeignKey(CryptoNetwork)
- address: CharField - deposit address
- memo_tag: CharField (optional) - for networks that need it
- is_active: BooleanField
- created_at: DateTimeField

**Indexes:** (user, network, is_active)

### OnChainTransaction
- id: UUID (PK)
- user: ForeignKey(User)
- network: ForeignKey(CryptoNetwork)
- tx_hash: CharField(unique) - blockchain transaction hash
- from_address: CharField
- to_address: CharField
- amount_atomic: BigIntegerField - amount in smallest unit (wei, satoshi)
- amount_minor: BigIntegerField - converted to minor units
- confirmations: IntegerField
- required_confirmations: IntegerField
- status: CharField - "pending", "confirmed", "failed"
- occurred_at: DateTimeField - when transaction occurred on-chain
- raw: JSONField - raw transaction data
- topup_intent: ForeignKey(TopUpIntent, null=True)
- created_at: DateTimeField

**Indexes:** (user, status), (tx_hash), (topup_intent)

---

## transactions app

### Transaction
- id: UUID (PK)
- user: ForeignKey(User)
- direction: CharField - "credit", "debit"
- category: CharField - "topup", "purchase", "transfer", "fee", "refund", "adjustment"
- amount_minor: BigIntegerField
- currency_code: CharField(3)
- description: CharField - "PlayStation Plus 10 Years Subscription"
- balance_after_minor: BigIntegerField - balance after this transaction
- related_order: ForeignKey(Order, null=True)
- related_topup_intent: ForeignKey(TopUpIntent, null=True)
- related_onchain_tx: ForeignKey(OnChainTransaction, null=True)
- idempotency_key: CharField(unique, null=True) - prevent duplicates
- created_at: DateTimeField

**Indexes:** (user, created_at), (user, category), (user, direction)

---

## orders app

### Cart
- id: UUID (PK)
- user: ForeignKey(User, unique=True) - one cart per user
- currency_code: CharField(3)
- created_at, updated_at: DateTimeField

### CartItem
- id: UUID (PK)
- cart: ForeignKey(Cart)
- account: ForeignKey(Account) - bank account product
- quantity: IntegerField
- unit_price_minor: BigIntegerField - price at time of adding (denormalized)
- total_price_minor: BigIntegerField - unit_price * quantity (denormalized)
- added_at: DateTimeField

**Unique constraint:** (cart, account) - prevent duplicates, update quantity instead

### Recipient
- id: UUID (PK)
- name: CharField
- email: EmailField (optional)
- phone: CharField (optional)
- country_code: CharField(3, optional)
- delivery_channel: CharField - "email", "sms", "code"

### Order
- id: UUID (PK)
- user: ForeignKey(User)
- order_number: CharField(unique) - "ORD-2024-001"
- status: CharField - "pending", "paid", "delivered", "canceled", "failed"
- subtotal_minor: BigIntegerField
- fees_minor: BigIntegerField
- total_minor: BigIntegerField
- currency_code: CharField(3)
- recipient: JSONField - recipient details (or FK to Recipient model)
- created_at, updated_at: DateTimeField

**Indexes:** (user, created_at), (user, status), (order_number)

### OrderItem
- id: UUID (PK)
- order: ForeignKey(Order)
- account: ForeignKey(Account) - bank account product
- quantity: IntegerField
- unit_price_minor: BigIntegerField - price at time of purchase
- total_price_minor: BigIntegerField
- metadata: JSONField (optional) - delivery codes, etc.
- created_at: DateTimeField

**Indexes:** (order)

### Fulfillment
- id: UUID (PK)
- order: ForeignKey(Order)
- status: CharField - "pending", "issued", "delivered", "failed"
- delivery_payload: JSONField - codes, pins, links, etc.
- delivered_at: DateTimeField (optional)
- failure_reason: TextField (optional)
- created_at, updated_at: DateTimeField

**Indexes:** (order, status)

---

## banking app
- **REMOVED** - Only cryptocurrency is used for payments (handled in wallet app)
- Bank and Account models are catalog products only

---

## notifications app

### Notification
- id: UUID (PK)
- user: ForeignKey(User)
- type: CharField - "transaction", "order", "system"
- title: CharField
- body: TextField
- data: JSONField (optional) - additional notification data
- is_read: BooleanField
- created_at: DateTimeField

**Indexes:** (user, is_read), (user, created_at)

---

## accounts app (Already Implemented)

### Profile
- ✅ Already implemented
- user, first_name, last_name, phone, avatar_url, country_code, time_zone, marketing_opt_in

---

## Additional Models Needed

### RewardPoints (Optional - for reward system)
- id: UUID (PK)
- user: ForeignKey(User, unique=True)
- points: IntegerField - current points balance
- credit_value_minor: BigIntegerField - $34 in credits = 3400 minor units
- updated_at: DateTimeField

---

## Model Relationships Summary

1. **User → Profile** (OneToOne) ✅
2. **User → Wallet** (OneToOne)
3. **User → Cart** (OneToOne)
4. **User → CryptoWallet** (OneToMany) - only payment method
5. **User → Transaction** (OneToMany)
6. **User → Order** (OneToMany)
7. **User → TopUpIntent** (OneToMany)
8. **User → Notification** (OneToMany)
9. **Country → Bank** (OneToMany)
10. **Country → Account** (OneToMany)
11. **Bank → Account** (OneToMany)
12. **Cart → CartItem** (OneToMany)
13. **CartItem → Account** (ManyToOne)
14. **Order → OrderItem** (OneToMany)
15. **OrderItem → Account** (ManyToOne)
18. **Order → Transaction** (OneToOne, optional)
19. **Order → Fulfillment** (OneToOne, optional)
20. **TopUpIntent → Transaction** (OneToOne, optional)
21. **TopUpIntent → OnChainTransaction** (OneToOne, optional)
22. **CryptoNetwork → CryptoWallet** (OneToMany)
23. **CryptoNetwork → DepositAddress** (OneToMany)
24. **CryptoNetwork → OnChainTransaction** (OneToMany)

---

## Next Steps

1. Implement catalog app models (Country, Bank, Account)
2. Implement wallet app models (Wallet, TopUpIntent, CryptoNetwork, CryptoWallet, DepositAddress, OnChainTransaction)
3. Implement transactions app model (Transaction)
4. Implement orders app models (Cart, CartItem, Order, OrderItem, Fulfillment)
5. Implement notifications app model (Notification)
6. Create serializers for all models
7. Create viewsets/views for all endpoints
8. Set up URL routing

**Note:** Banking app removed - only cryptocurrency payments via wallet app

