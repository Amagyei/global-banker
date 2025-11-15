# Frontend Features & Data Requirements

## Dashboard
- **User Stats:**
  - My Balance (wallet balance)
  - Available Banks count (across all markets)
  - Recent Purchases count (this month)
  - Reward Points (with credit value)
- **Platform Stats:**
  - Total Sales
  - Active Banks
  - Customers
  - Growth percentage
- **Popular Categories:** Gaming, Retail, Entertainment, Food & Dining (with percentages)
- **Recent Activity:** List of recent transactions (action, time, amount)

## Navbar
- **Cart:** Items, quantity, subtotal
- **Wallet Balance:** Display current balance
- **Navigation:** Dashboard, US Banks, UK Banks, Canada Banks, Transactions
- **User Menu:** Profile, Orders, Top Up, Logout

## Transactions Page
- **Transaction Fields:**
  - id, date, brand, description, amount, status (completed/pending/failed)
- **Features:** View purchase history, filter by status

## Orders Page
- **Order Fields:**
  - id, orderNumber, date, brand, items, total, status (completed/processing/pending)
- **Features:** Track and manage bank purchases

## TopUp Page
- **Current Balance:** Display wallet balance
- **Quick Top Up:** Preset amounts (50, 100, 250, 500, 1000)
- **Custom Amount:** User-entered amount
- **Payment Methods:** Credit cards (card number, expiry, default flag)

## Profile Page
- **Personal Information:**
  - First Name, Last Name, Email, Phone, Address
- **Account Balance:** Current wallet balance
- **Features:** Update profile, view transaction history

## CountryCards Page (US/UK/Canada Banks)
- **Countries:** US, UK, Canada
- **Banks by Country:**
  - id, name, logo
- **Bank Accounts by Bank:**
  - id, balance, description, price
- **Features:** Select bank, view bank accounts, add to cart

## BankAccountTable Component
- **Fields:** id, balance, description, price
- **Features:** Display bank accounts, add to cart

## BankSelectionModal Component
- **Fields:** id, name, logo
- **Features:** Select bank from country-specific list

## Cart Context
- **Cart Items:**
  - id, description, price, quantity
- **Features:** Add to cart, remove from cart, clear cart, calculate subtotal

## Additional Features Noted
- **Reward Points System:** Points with credit conversion
- **Categories:** Gaming, Retail, Entertainment, Food & Dining
- **Brands:**  Chase Bank, Bank of America, Wells Fargo,CitiBank, U.S Bank, Credit Unions, Other
- **Payment Methods:** Credit cards with expiry and default flag
