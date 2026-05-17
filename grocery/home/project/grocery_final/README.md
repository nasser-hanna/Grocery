# 🥦 FreshTrack — Smart Grocery Inventory System

A full-stack web application for tracking grocery inventory, expiry dates, and shopping orders.

## Tech Stack
- **Backend**: Python + Flask (REST API)
- **Database**: SQLite (auto-seeded with sample data)
- **Frontend**: Vanilla HTML/CSS/JS (no build tools needed)

## Quick Start

```bash
# 1. Install dependencies
pip install Flask

# 2. Run the app
python app.py

# 3. Open in browser
http://localhost:5000
```

## Features

| Feature | Description |
|---|---|
| 📊 Dashboard | Live stats: products, revenue, alerts, low stock |
| 🧺 Products | Full CRUD — add, edit, delete, filter products |
| ⏳ Expiry Report | Query "items expiring in next 3/7/14/30 days" |
| 📦 Stock Value | "Total stock value by category" query |
| 🛒 Orders | Order history with full item breakdown |
| 👥 Customers | User profiles and spending history |
| 🔔 Alerts | Automatic expiry + low-stock alerts |

## Database Schema

- **category** — Product categories (12 seeded)
- **product** — Items with price, stock, expiry dates (51 seeded)
- **user** — Customer accounts (5 seeded)
- **order** — Purchase orders with status (15 seeded)
- **order_item** — Line items per order
- **alert** — Auto-generated expiry and low-stock alerts (8 seeded)

## API Endpoints

```
GET  /api/dashboard          — Stats + recent orders + revenue chart
GET  /api/products           — List products (filter: search, category, expiry, low_stock)
POST /api/products           — Create product
PUT  /api/products/:id       — Update product
DEL  /api/products/:id       — Delete product
GET  /api/categories         — All categories with product counts
GET  /api/orders             — All orders
GET  /api/orders/:id         — Order detail with items
GET  /api/alerts             — All alerts (sorted unread first)
PUT  /api/alerts/:id/read    — Mark alert as read
PUT  /api/alerts/read-all    — Mark all alerts read
GET  /api/expiring?days=N    — Products expiring in N days
GET  /api/stock-value        — Total stock value by category
GET  /api/users              — Customers with order stats
```

## User Portal (NEW)

Visit `http://localhost:5000` for the **user-facing store**.
Visit `http://localhost:5000/admin` for the **admin dashboard**.

### Pre-loaded User Accounts
| Name | Email | Password |
|---|---|---|
| Alice Johnson | alice@email.com | pass1 |
| Bob Williams | bob@email.com | pass2 |
| Carol Davis | carol@email.com | pass3 |
| David Martinez | david@email.com | pass4 |
| Emma Thompson | emma@email.com | pass5 |
| Frank Zhang | frank@email.com | pass6 |
| Grace Kim | grace@email.com | pass7 |
| Henry Brooks | henry@email.com | pass8 |
| Isabella Rossi | isabella@email.com | pass9 |
| James Patel | james@email.com | pass10 |

### User Portal Features
- Register new account (saved to database)
- Login / Logout with session
- Browse 51 products across categories
- Filter by category, sort by price/name
- Search products in real-time
- Add to cart (persists in localStorage)
- Checkout & place real orders
- View order history with full item breakdown
- Edit profile (name, phone, address, password)
