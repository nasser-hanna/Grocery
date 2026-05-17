from flask import Flask, jsonify, request, render_template, session
import sqlite3, os, hashlib, secrets, random
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'freshtrack-secret-key-2026'
DB_PATH = os.path.join(os.path.dirname(__file__), 'grocery.db')

def hash_pw(pw): return hashlib.sha256(pw.encode()).hexdigest()

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

# ── INIT DB ──────────────────────────────────────────────────────────────────────

def init_db():
    conn = get_db(); c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS category (
            category_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        );
        CREATE TABLE IF NOT EXISTS product (
            product_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            unit_type TEXT NOT NULL,
            price_per_unit REAL NOT NULL,
            production_date TEXT,
            expire_date TEXT,
            stock_quantity INTEGER DEFAULT 0,
            low_stock_threshold INTEGER DEFAULT 10,
            category_id INTEGER,
            description TEXT DEFAULT '',
            image_emoji TEXT DEFAULT '🛒',
            FOREIGN KEY (category_id) REFERENCES category(category_id)
        );
        CREATE TABLE IF NOT EXISTS user (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            phone TEXT,
            address TEXT,
            password TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS "order" (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            order_date TEXT DEFAULT (datetime('now')),
            status TEXT DEFAULT 'pending',
            total_amount REAL DEFAULT 0,
            delivery_address TEXT,
            FOREIGN KEY (user_id) REFERENCES user(user_id)
        );
        CREATE TABLE IF NOT EXISTS order_item (
            item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            FOREIGN KEY (order_id) REFERENCES "order"(order_id),
            FOREIGN KEY (product_id) REFERENCES product(product_id)
        );
        CREATE TABLE IF NOT EXISTS alert (
            alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            alert_type TEXT NOT NULL,
            message TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (product_id) REFERENCES product(product_id)
        );
        CREATE TABLE IF NOT EXISTS admin (
            admin_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'admin',
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    conn.commit(); conn.close()

def seed_admins():
    conn = get_db(); c = conn.cursor()
    if c.execute("SELECT COUNT(*) FROM admin").fetchone()[0] > 0:
        conn.close(); return
    admins = [
        ("admin",     "admin@freshtrack.io",    hash_pw("admin123"),  "superadmin"),
        ("manager",   "manager@freshtrack.io",  hash_pw("manager123"),"admin"),
        ("inventory", "inventory@freshtrack.io",hash_pw("inv123"),    "admin"),
    ]
    for username, email, password, role in admins:
        c.execute("INSERT INTO admin(username,email,password,role) VALUES(?,?,?,?)",
                  (username, email, password, role))
    conn.commit(); conn.close()
    print("✅ Admin accounts seeded!")

def seed_db():
    conn = get_db(); c = conn.cursor()
    if c.execute("SELECT COUNT(*) FROM category").fetchone()[0] > 0:
        conn.close(); return

    cats = ["Fruits & Vegetables","Dairy & Eggs","Meat & Seafood","Bakery & Bread",
            "Beverages","Snacks & Sweets","Frozen Foods","Spices & Seasonings",
            "Oils & Sauces","Cleaning Supplies","Personal Care","Grains & Pasta"]
    for cat in cats:
        c.execute("INSERT INTO category (name) VALUES (?)", (cat,))
    conn.commit()

    today = datetime.now()
    # (name, unit, price, prod_offset, exp_offset, qty, threshold, cat_id, desc, emoji)
    products = [
        ("Organic Bananas","kg",1.99,-10,20,50,5,1,"Sweet organic bananas, perfectly ripe.","🍌"),
        ("Fresh Strawberries","punnet",3.49,-5,7,30,8,1,"Hand-picked, sun-ripened strawberries.","🍓"),
        ("Roma Tomatoes","kg",2.29,-7,10,45,10,1,"Firm & flavourful vine-ripened tomatoes.","🍅"),
        ("Baby Spinach","bag",2.79,-3,5,25,6,1,"Tender baby spinach leaves, triple-washed.","🥬"),
        ("Avocados","each",1.49,-10,4,40,8,1,"Creamy Hass avocados, ready to eat.","🥑"),
        ("Broccoli","head",1.89,-8,8,35,10,1,"Crisp green broccoli heads.","🥦"),
        ("Red Bell Peppers","each",1.29,-5,6,50,8,1,"Bright, sweet red peppers.","🫑"),
        ("Garlic Bulb","each",0.79,-30,60,80,15,1,"Full-flavour garlic bulbs.","🧄"),
        ("Whole Milk 2L","bottle",2.99,-7,14,60,15,2,"Fresh whole milk from local farms.","🥛"),
        ("Free Range Eggs 12pk","pack",4.29,-10,21,40,10,2,"Farm-fresh free range eggs.","🥚"),
        ("Cheddar Cheese 400g","pack",5.49,-20,60,35,8,2,"Aged mature cheddar, sharp & creamy.","🧀"),
        ("Greek Yogurt 500g","tub",3.79,-14,21,28,8,2,"Thick, protein-rich Greek yogurt.","🫙"),
        ("Unsalted Butter 250g","pack",3.29,-30,90,45,10,2,"Premium unsalted churned butter.","🧈"),
        ("Heavy Cream 300ml","bottle",2.49,-10,20,22,6,2,"Rich double cream for cooking.","🍶"),
        ("Chicken Breast 500g","pack",6.99,-3,5,30,8,3,"Skinless, boneless chicken breasts.","🍗"),
        ("Atlantic Salmon Fillet","kg",14.99,-2,4,20,5,3,"Fresh-caught Atlantic salmon fillets.","🐟"),
        ("Lean Ground Beef 500g","pack",7.49,-2,4,25,8,3,"Extra-lean minced beef.","🥩"),
        ("Pork Sausages 6pk","pack",5.29,-4,7,18,5,3,"Classic pork sausages, no fillers.","🌭"),
        ("Tiger Shrimp 400g","pack",9.99,-5,6,15,4,3,"Jumbo tiger shrimp, deveined.","🦐"),
        ("Sourdough Loaf","loaf",4.49,-2,5,20,6,4,"Slow-fermented artisan sourdough.","🍞"),
        ("Whole Wheat Bread","loaf",3.29,-3,6,30,8,4,"Nutritious whole wheat sandwich loaf.","🍞"),
        ("Croissants 4pk","pack",3.99,-1,3,18,5,4,"Buttery, flaky French croissants.","🥐"),
        ("Bagels 6pk","pack",3.49,-2,5,22,6,4,"New York-style plain bagels.","🥯"),
        ("Orange Juice 1L","carton",3.99,-30,90,55,12,5,"100% freshly squeezed orange juice.","🍊"),
        ("Sparkling Water 6pk","pack",4.49,-365,730,70,15,5,"Natural sparkling mineral water.","💧"),
        ("Green Tea 20 bags","box",3.79,-365,730,45,10,5,"Premium Japanese green tea bags.","🍵"),
        ("Cold Brew Coffee 500ml","bottle",5.49,-7,14,25,8,5,"Smooth cold-brew black coffee.","☕"),
        ("Coconut Water 330ml","can",1.99,-180,365,60,12,5,"Pure natural coconut water.","🥥"),
        ("Dark Chocolate 70%","bar",2.99,-180,365,50,12,6,"Rich single-origin 70% dark chocolate.","🍫"),
        ("Organic Trail Mix 300g","bag",5.99,-90,180,35,8,6,"Nuts, seeds & dried fruit blend.","🥜"),
        ("Rice Crackers 200g","bag",2.49,-90,180,40,10,6,"Light & crispy rice crackers.","🫘"),
        ("Hummus 200g","tub",2.79,-14,30,30,8,6,"Creamy chickpea hummus with olive oil.","🫙"),
        ("Frozen Peas 750g","bag",2.29,-90,365,40,10,7,"Sweet garden peas, flash frozen.","🫛"),
        ("Frozen Pizza Margherita","each",5.99,-60,180,25,6,7,"Stone-baked margherita pizza.","🍕"),
        ("Ice Cream Vanilla 1L","tub",4.99,-60,180,30,8,7,"Classic vanilla bean ice cream.","🍦"),
        ("Frozen Mixed Berries 500g","bag",4.49,-60,365,35,8,7,"Blueberries, raspberries & blackberries.","🫐"),
        ("Sea Salt 500g","jar",1.99,-365,1825,60,10,8,"Coarse Atlantic sea salt.","🧂"),
        ("Black Pepper Ground 100g","jar",2.49,-365,1095,55,10,8,"Freshly ground black pepper.","🫙"),
        ("Paprika Sweet 50g","jar",1.79,-365,1095,40,8,8,"Mild sweet Spanish paprika.","🌶️"),
        ("Cumin Ground 50g","jar",1.89,-365,1095,38,8,8,"Warm, earthy ground cumin.","🫙"),
        ("Oregano Dried 20g","jar",1.59,-365,730,35,8,8,"Mediterranean dried oregano.","🌿"),
        ("Extra Virgin Olive Oil 500ml","bottle",7.99,-365,730,40,8,9,"Cold-pressed extra virgin olive oil.","🫒"),
        ("Soy Sauce 150ml","bottle",2.29,-365,730,50,10,9,"Traditional brewed soy sauce.","🍶"),
        ("Tomato Passata 700g","jar",1.99,-365,730,55,12,9,"Smooth Italian tomato passata.","🍅"),
        ("Balsamic Vinegar 250ml","bottle",4.49,-365,730,30,8,9,"Aged Modena balsamic vinegar.","🍾"),
        ("Hot Sauce 150ml","bottle",3.29,-365,1095,35,8,9,"Fiery Louisiana-style hot sauce.","🌶️"),
        ("Basmati Rice 1kg","bag",3.49,-365,730,60,15,12,"Long-grain aged basmati rice.","🍚"),
        ("Penne Pasta 500g","pack",1.89,-365,730,70,15,12,"Bronze-die cut Italian penne.","🍝"),
        ("Rolled Oats 1kg","bag",2.99,-365,730,50,12,12,"Thick-cut whole grain rolled oats.","🥣"),
        ("Quinoa 500g","bag",4.99,-365,730,30,8,12,"White quinoa, pre-rinsed.","🌾"),
        ("Bread Flour 1.5kg","bag",2.79,-365,365,45,10,12,"Strong white bread flour.","🌾"),
    ]
    for name,unit,price,prod_off,exp_off,qty,thresh,cat_id,desc,emoji in products:
        pd = (today+timedelta(days=prod_off)).strftime('%Y-%m-%d')
        ed = (today+timedelta(days=exp_off)).strftime('%Y-%m-%d')
        c.execute("""INSERT INTO product(name,unit_type,price_per_unit,production_date,expire_date,
            stock_quantity,low_stock_threshold,category_id,description,image_emoji)
            VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (name,unit,price,pd,ed,qty,thresh,cat_id,desc,emoji))
    conn.commit()

    # Seed 10 users with hashed passwords (password = "pass" + index)
    users = [
        ("Alice Johnson","alice@email.com","+1-555-0101","123 Maple St, Springfield",hash_pw("pass1")),
        ("Bob Williams","bob@email.com","+1-555-0102","456 Oak Ave, Shelbyville",hash_pw("pass2")),
        ("Carol Davis","carol@email.com","+1-555-0103","789 Pine Rd, Capital City",hash_pw("pass3")),
        ("David Martinez","david@email.com","+1-555-0104","321 Elm Blvd, Ogdenville",hash_pw("pass4")),
        ("Emma Thompson","emma@email.com","+1-555-0105","654 Cedar Lane, North Haverbrook",hash_pw("pass5")),
        ("Frank Zhang","frank@email.com","+1-555-0106","88 River Walk, Shelbyville",hash_pw("pass6")),
        ("Grace Kim","grace@email.com","+1-555-0107","17 Sunflower Ave, Springfield",hash_pw("pass7")),
        ("Henry Brooks","henry@email.com","+1-555-0108","99 Birch Close, Capital City",hash_pw("pass8")),
        ("Isabella Rossi","isabella@email.com","+1-555-0109","5 Vineyard Rd, Ogdenville",hash_pw("pass9")),
        ("James Patel","james@email.com","+1-555-0110","42 Park Lane, Springfield",hash_pw("pass10")),
    ]
    for name,email,phone,address,password in users:
        c.execute("INSERT INTO user(name,email,phone,address,password) VALUES(?,?,?,?,?)",
                  (name,email,phone,address,password))
    conn.commit()

    # Seed orders
    all_products = c.execute("SELECT product_id,price_per_unit FROM product").fetchall()
    statuses = ['completed','completed','completed','pending','cancelled']
    order_ids = []
    for i in range(1,6):
        days_ago = random.randint(1,30)
        od = (today-timedelta(days=days_ago)).strftime('%Y-%m-%d %H:%M:%S')
        c.execute('INSERT INTO "order"(user_id,order_date,status) VALUES(?,?,?)',
                  (i, od, statuses[i-1]))
        order_ids.append(c.lastrowid)
    for _ in range(12):
        uid = random.randint(1,10)
        days_ago = random.randint(1,60)
        od = (today-timedelta(days=days_ago)).strftime('%Y-%m-%d %H:%M:%S')
        c.execute('INSERT INTO "order"(user_id,order_date,status) VALUES(?,?,?)',
                  (uid, od, random.choice(['completed','pending'])))
        order_ids.append(c.lastrowid)
    conn.commit()

    for oid in order_ids:
        selected = random.sample(list(all_products), random.randint(2,5))
        total = 0
        for prod in selected:
            qty = random.randint(1,4)
            price = prod['price_per_unit']
            c.execute("INSERT INTO order_item(order_id,product_id,quantity,unit_price) VALUES(?,?,?,?)",
                      (oid, prod['product_id'], qty, price))
            total += qty*price
        c.execute('UPDATE "order" SET total_amount=? WHERE order_id=?',(round(total,2),oid))
    conn.commit()

    # Alerts
    expiring = c.execute("""SELECT product_id,name,expire_date FROM product
        WHERE date(expire_date)<=date('now','+7 days') LIMIT 8""").fetchall()
    for p in expiring:
        c.execute("INSERT INTO alert(product_id,alert_type,message) VALUES(?,?,?)",
                  (p['product_id'],'expiry',f"⚠️ {p['name']} expires on {p['expire_date']}."))
    low = c.execute("""SELECT product_id,name,stock_quantity FROM product
        WHERE stock_quantity<=low_stock_threshold LIMIT 5""").fetchall()
    for p in low:
        c.execute("INSERT INTO alert(product_id,alert_type,message) VALUES(?,?,?)",
                  (p['product_id'],'low_stock',f"📦 {p['name']} is low on stock ({p['stock_quantity']} remaining)."))
    conn.commit(); conn.close()
    print("✅ DB seeded!")

# ── PAGES ────────────────────────────────────────────────────────────────────────

@app.route('/')
def user_portal():
    return render_template('user.html')

@app.route('/admin')
def admin_portal():
    if not session.get('admin_id'):
        return render_template('admin_login.html')
    return render_template('index.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_id', None)
    session.pop('admin_username', None)
    return render_template('admin_login.html')

# ── USER AUTH API ─────────────────────────────────────────────────────────────────

@app.route('/api/auth/register', methods=['POST'])
def register():
    d = request.json
    if not d.get('name') or not d.get('email') or not d.get('password'):
        return jsonify({'error': 'Name, email and password are required'}), 400
    conn = get_db(); c = conn.cursor()
    existing = c.execute("SELECT user_id FROM user WHERE email=?", (d['email'],)).fetchone()
    if existing:
        conn.close()
        return jsonify({'error': 'Email already registered'}), 409
    c.execute("INSERT INTO user(name,email,phone,address,password) VALUES(?,?,?,?,?)",
              (d['name'], d['email'], d.get('phone',''), d.get('address',''), hash_pw(d['password'])))
    conn.commit()
    uid = c.lastrowid
    user = dict(c.execute("SELECT user_id,name,email,phone,address,created_at FROM user WHERE user_id=?", (uid,)).fetchone())
    conn.close()
    session['user_id'] = uid
    return jsonify({'message': 'Account created!', 'user': user}), 201

@app.route('/api/auth/login', methods=['POST'])
def login():
    d = request.json
    conn = get_db()
    user = conn.execute("SELECT * FROM user WHERE email=? AND password=?",
                        (d['email'], hash_pw(d['password']))).fetchone()
    conn.close()
    if not user:
        return jsonify({'error': 'Invalid email or password'}), 401
    session['user_id'] = user['user_id']
    return jsonify({'message': 'Logged in', 'user': {
        'user_id': user['user_id'], 'name': user['name'], 'email': user['email'],
        'phone': user['phone'], 'address': user['address']
    }})

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Logged out'})

@app.route('/api/auth/me')
def me():
    uid = session.get('user_id')
    if not uid:
        return jsonify({'error': 'Not logged in'}), 401
    conn = get_db()
    user = conn.execute("""
        SELECT u.user_id,u.name,u.email,u.phone,u.address,u.created_at,
        COUNT(o.order_id) as order_count,
        COALESCE(SUM(o.total_amount),0) as total_spent
        FROM user u LEFT JOIN "order" o ON o.user_id=u.user_id
        WHERE u.user_id=? GROUP BY u.user_id""", (uid,)).fetchone()
    conn.close()
    if not user: return jsonify({'error': 'User not found'}), 404
    return jsonify(dict(user))

@app.route('/api/auth/profile', methods=['PUT'])
def update_profile():
    uid = session.get('user_id')
    if not uid: return jsonify({'error': 'Not logged in'}), 401
    d = request.json
    conn = get_db()
    if d.get('password'):
        conn.execute("UPDATE user SET name=?,phone=?,address=?,password=? WHERE user_id=?",
                     (d['name'], d.get('phone',''), d.get('address',''), hash_pw(d['password']), uid))
    else:
        conn.execute("UPDATE user SET name=?,phone=?,address=? WHERE user_id=?",
                     (d['name'], d.get('phone',''), d.get('address',''), uid))
    conn.commit()
    user = dict(conn.execute("SELECT user_id,name,email,phone,address FROM user WHERE user_id=?",(uid,)).fetchone())
    conn.close()
    return jsonify({'message': 'Profile updated', 'user': user})

# ── ADMIN AUTH API ───────────────────────────────────────────────────────────────

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    d = request.json
    conn = get_db()
    admin = conn.execute(
        "SELECT * FROM admin WHERE (username=? OR email=?) AND password=?",
        (d.get('username',''), d.get('username',''), hash_pw(d.get('password','')))
    ).fetchone()
    conn.close()
    if not admin:
        return jsonify({'error': 'Invalid username or password'}), 401
    session['admin_id'] = admin['admin_id']
    session['admin_username'] = admin['username']
    return jsonify({'message': 'Logged in', 'admin': {
        'admin_id': admin['admin_id'],
        'username': admin['username'],
        'email': admin['email'],
        'role': admin['role']
    }})

@app.route('/api/admin/logout', methods=['POST'])
def admin_api_logout():
    session.pop('admin_id', None)
    session.pop('admin_username', None)
    return jsonify({'message': 'Logged out'})

@app.route('/api/admin/me')
def admin_me():
    if not session.get('admin_id'):
        return jsonify({'error': 'Not authenticated'}), 401
    conn = get_db()
    admin = conn.execute("SELECT admin_id,username,email,role,created_at FROM admin WHERE admin_id=?",
                         (session['admin_id'],)).fetchone()
    conn.close()
    if not admin: return jsonify({'error': 'Not found'}), 404
    return jsonify(dict(admin))

# ── SHOP API ─────────────────────────────────────────────────────────────────────

@app.route('/api/shop/products')
def shop_products():
    search = request.args.get('search','')
    cat = request.args.get('category','')
    sort = request.args.get('sort','name')
    conn = get_db()
    q = """SELECT p.*,c.name as category_name FROM product p
           LEFT JOIN category c ON c.category_id=p.category_id
           WHERE p.stock_quantity>0 AND date(p.expire_date)>date('now')"""
    params=[]
    if search:
        q += " AND p.name LIKE ?"
        params.append(f'%{search}%')
    if cat:
        q += " AND p.category_id=?"
        params.append(cat)
    order_map = {'name':'p.name','price_asc':'p.price_per_unit ASC','price_desc':'p.price_per_unit DESC','newest':'p.product_id DESC'}
    q += f" ORDER BY {order_map.get(sort,'p.name')}"
    products = conn.execute(q, params).fetchall()
    conn.close()
    return jsonify([dict(p) for p in products])

@app.route('/api/shop/categories')
def shop_categories():
    conn = get_db()
    cats = conn.execute("""SELECT c.*,COUNT(p.product_id) as product_count
        FROM category c JOIN product p ON p.category_id=c.category_id
        WHERE p.stock_quantity>0 AND date(p.expire_date)>date('now')
        GROUP BY c.category_id HAVING product_count>0 ORDER BY c.name""").fetchall()
    conn.close()
    return jsonify([dict(c) for c in cats])

@app.route('/api/shop/product/<int:pid>')
def shop_product(pid):
    conn = get_db()
    p = conn.execute("""SELECT p.*,c.name as category_name FROM product p
        LEFT JOIN category c ON c.category_id=p.category_id WHERE p.product_id=?""",(pid,)).fetchone()
    conn.close()
    if not p: return jsonify({'error':'Not found'}),404
    return jsonify(dict(p))

# ── USER ORDERS ───────────────────────────────────────────────────────────────────

@app.route('/api/shop/orders', methods=['POST'])
def place_order():
    uid = session.get('user_id')
    if not uid: return jsonify({'error': 'Please log in to place an order'}), 401
    d = request.json
    items = d.get('items', [])
    if not items: return jsonify({'error': 'Cart is empty'}), 400

    conn = get_db(); c = conn.cursor()
    user = c.execute("SELECT address FROM user WHERE user_id=?",(uid,)).fetchone()
    delivery = d.get('delivery_address') or (user['address'] if user else '')

    c.execute('INSERT INTO "order"(user_id,status,delivery_address) VALUES(?,?,?)',
              (uid, 'pending', delivery))
    oid = c.lastrowid
    total = 0
    for item in items:
        prod = c.execute("SELECT price_per_unit,stock_quantity FROM product WHERE product_id=?",
                         (item['product_id'],)).fetchone()
        if not prod or prod['stock_quantity'] < item['quantity']:
            conn.rollback(); conn.close()
            return jsonify({'error': f"Insufficient stock for product #{item['product_id']}"}), 400
        c.execute("INSERT INTO order_item(order_id,product_id,quantity,unit_price) VALUES(?,?,?,?)",
                  (oid, item['product_id'], item['quantity'], prod['price_per_unit']))
        c.execute("UPDATE product SET stock_quantity=stock_quantity-? WHERE product_id=?",
                  (item['quantity'], item['product_id']))
        total += item['quantity'] * prod['price_per_unit']
    c.execute('UPDATE "order" SET total_amount=? WHERE order_id=?', (round(total,2), oid))
    conn.commit(); conn.close()
    return jsonify({'message': 'Order placed!', 'order_id': oid, 'total': round(total,2)}), 201

@app.route('/api/shop/my-orders')
def my_orders():
    uid = session.get('user_id')
    if not uid: return jsonify({'error': 'Not logged in'}), 401
    conn = get_db()
    orders = conn.execute("""
        SELECT o.*,COUNT(oi.item_id) as item_count FROM "order" o
        LEFT JOIN order_item oi ON oi.order_id=o.order_id
        WHERE o.user_id=? GROUP BY o.order_id ORDER BY o.order_date DESC""", (uid,)).fetchall()
    result = []
    for o in orders:
        od = dict(o)
        items = conn.execute("""SELECT oi.*,p.name as product_name,p.unit_type,p.image_emoji
            FROM order_item oi JOIN product p ON p.product_id=oi.product_id
            WHERE oi.order_id=?""", (o['order_id'],)).fetchall()
        od['items'] = [dict(i) for i in items]
        result.append(od)
    conn.close()
    return jsonify(result)

# ── ADMIN API (existing) ──────────────────────────────────────────────────────────

@app.route('/api/dashboard')
def dashboard():
    conn = get_db(); c = conn.cursor()
    total_products = c.execute("SELECT COUNT(*) FROM product").fetchone()[0]
    total_categories = c.execute("SELECT COUNT(*) FROM category").fetchone()[0]
    total_orders = c.execute('SELECT COUNT(*) FROM "order"').fetchone()[0]
    total_revenue = c.execute('SELECT COALESCE(SUM(total_amount),0) FROM "order" WHERE status="completed"').fetchone()[0]
    expiring_soon = c.execute("SELECT COUNT(*) FROM product WHERE date(expire_date)<=date('now','+7 days') AND date(expire_date)>=date('now')").fetchone()[0]
    low_stock_count = c.execute("SELECT COUNT(*) FROM product WHERE stock_quantity<=low_stock_threshold").fetchone()[0]
    unread_alerts = c.execute("SELECT COUNT(*) FROM alert WHERE is_read=0").fetchone()[0]
    rev_by_cat = c.execute("""SELECT cat.name,COALESCE(SUM(oi.quantity*oi.unit_price),0) as revenue
        FROM category cat LEFT JOIN product p ON p.category_id=cat.category_id
        LEFT JOIN order_item oi ON oi.product_id=p.product_id
        LEFT JOIN "order" o ON o.order_id=oi.order_id AND o.status='completed'
        GROUP BY cat.category_id ORDER BY revenue DESC LIMIT 6""").fetchall()
    recent_orders = c.execute("""SELECT o.order_id,u.name as user_name,o.order_date,o.status,o.total_amount
        FROM "order" o JOIN user u ON u.user_id=o.user_id ORDER BY o.order_date DESC LIMIT 5""").fetchall()
    conn.close()
    return jsonify({"stats":{"total_products":total_products,"total_categories":total_categories,
        "total_orders":total_orders,"total_revenue":round(total_revenue,2),
        "expiring_soon":expiring_soon,"low_stock":low_stock_count,"unread_alerts":unread_alerts},
        "revenue_by_category":[dict(r) for r in rev_by_cat],
        "recent_orders":[dict(r) for r in recent_orders]})

@app.route('/api/products')
def get_products():
    conn = get_db()
    search = request.args.get('search',''); category = request.args.get('category','')
    expiring = request.args.get('expiring',''); low_stock = request.args.get('low_stock','')
    q = """SELECT p.*,c.name as category_name,
        CASE WHEN date(p.expire_date)<=date('now','+3 days') THEN 1 ELSE 0 END as expiring_critical,
        CASE WHEN date(p.expire_date)<=date('now','+7 days') THEN 1 ELSE 0 END as expiring_soon,
        CASE WHEN p.stock_quantity<=p.low_stock_threshold THEN 1 ELSE 0 END as is_low_stock
        FROM product p LEFT JOIN category c ON c.category_id=p.category_id WHERE 1=1"""
    params=[]
    if search: q+=" AND p.name LIKE ?"; params.append(f'%{search}%')
    if category: q+=" AND p.category_id=?"; params.append(category)
    if expiring=='3': q+=" AND date(p.expire_date)<=date('now','+3 days')"
    elif expiring=='7': q+=" AND date(p.expire_date)<=date('now','+7 days')"
    if low_stock=='1': q+=" AND p.stock_quantity<=p.low_stock_threshold"
    q+=" ORDER BY p.expire_date ASC"
    products = conn.execute(q,params).fetchall()
    conn.close()
    return jsonify([dict(p) for p in products])

@app.route('/api/products/<int:pid>', methods=['GET'])
def get_product(pid):
    conn = get_db()
    p = conn.execute("SELECT p.*,c.name as category_name FROM product p LEFT JOIN category c ON c.category_id=p.category_id WHERE p.product_id=?",(pid,)).fetchone()
    conn.close()
    if not p: return jsonify({"error":"Not found"}),404
    return jsonify(dict(p))

@app.route('/api/products', methods=['POST'])
def create_product():
    d = request.json; conn = get_db(); c = conn.cursor()
    c.execute("""INSERT INTO product(name,unit_type,price_per_unit,production_date,expire_date,
        stock_quantity,low_stock_threshold,category_id,description,image_emoji) VALUES(?,?,?,?,?,?,?,?,?,?)""",
        (d['name'],d['unit_type'],d['price_per_unit'],d.get('production_date'),d.get('expire_date'),
         d.get('stock_quantity',0),d.get('low_stock_threshold',10),d.get('category_id'),
         d.get('description',''),d.get('image_emoji','🛒')))
    conn.commit(); nid=c.lastrowid; conn.close()
    return jsonify({"product_id":nid,"message":"Created"}),201

@app.route('/api/products/<int:pid>', methods=['PUT'])
def update_product(pid):
    d = request.json; conn = get_db()
    conn.execute("""UPDATE product SET name=?,unit_type=?,price_per_unit=?,production_date=?,
        expire_date=?,stock_quantity=?,low_stock_threshold=?,category_id=?,description=?,image_emoji=?
        WHERE product_id=?""",
        (d['name'],d['unit_type'],d['price_per_unit'],d.get('production_date'),d.get('expire_date'),
         d.get('stock_quantity',0),d.get('low_stock_threshold',10),d.get('category_id'),
         d.get('description',''),d.get('image_emoji','🛒'),pid))
    conn.commit(); conn.close()
    return jsonify({"message":"Updated"})

@app.route('/api/products/<int:pid>', methods=['DELETE'])
def delete_product(pid):
    conn = get_db()
    conn.execute("DELETE FROM product WHERE product_id=?",(pid,))
    conn.commit(); conn.close()
    return jsonify({"message":"Deleted"})

@app.route('/api/categories')
def get_categories():
    conn = get_db()
    cats = conn.execute("""SELECT c.*,COUNT(p.product_id) as product_count
        FROM category c LEFT JOIN product p ON p.category_id=c.category_id
        GROUP BY c.category_id ORDER BY c.name""").fetchall()
    conn.close()
    return jsonify([dict(c) for c in cats])

@app.route('/api/orders')
def get_orders():
    conn = get_db()
    orders = conn.execute("""SELECT o.*,u.name as user_name,u.email,COUNT(oi.item_id) as item_count
        FROM "order" o JOIN user u ON u.user_id=o.user_id
        LEFT JOIN order_item oi ON oi.order_id=o.order_id
        GROUP BY o.order_id ORDER BY o.order_date DESC""").fetchall()
    conn.close()
    return jsonify([dict(o) for o in orders])

@app.route('/api/orders/<int:oid>')
def get_order(oid):
    conn = get_db()
    order = conn.execute("""SELECT o.*,u.name as user_name,u.email,u.phone,u.address
        FROM "order" o JOIN user u ON u.user_id=o.user_id WHERE o.order_id=?""",(oid,)).fetchone()
    items = conn.execute("""SELECT oi.*,p.name as product_name,p.unit_type FROM order_item oi
        JOIN product p ON p.product_id=oi.product_id WHERE oi.order_id=?""",(oid,)).fetchall()
    conn.close()
    if not order: return jsonify({"error":"Not found"}),404
    return jsonify({"order":dict(order),"items":[dict(i) for i in items]})

@app.route('/api/orders/<int:oid>/status', methods=['PUT'])
def update_order_status(oid):
    d = request.json
    new_status = d.get('status')
    if new_status not in ('pending', 'confirmed', 'processing', 'completed', 'cancelled'):
        return jsonify({'error': 'Invalid status'}), 400
    conn = get_db()
    # If cancelling, restore stock
    if new_status == 'cancelled':
        old_order = conn.execute('SELECT status FROM "order" WHERE order_id=?', (oid,)).fetchone()
        if old_order and old_order['status'] not in ('cancelled', 'completed'):
            items = conn.execute('SELECT product_id, quantity FROM order_item WHERE order_id=?', (oid,)).fetchall()
            for item in items:
                conn.execute('UPDATE product SET stock_quantity=stock_quantity+? WHERE product_id=?',
                             (item['quantity'], item['product_id']))
    conn.execute('UPDATE "order" SET status=? WHERE order_id=?', (new_status, oid))
    conn.commit(); conn.close()
    return jsonify({'message': f'Order updated to {new_status}'})

@app.route('/api/alerts')
def get_alerts():
    conn = get_db()
    alerts = conn.execute("""SELECT a.*,p.name as product_name,p.expire_date,p.stock_quantity
        FROM alert a JOIN product p ON p.product_id=a.product_id
        ORDER BY a.is_read ASC, a.created_at DESC""").fetchall()
    conn.close()
    return jsonify([dict(a) for a in alerts])

@app.route('/api/alerts/<int:aid>/read', methods=['PUT'])
def mark_alert_read(aid):
    conn = get_db(); conn.execute("UPDATE alert SET is_read=1 WHERE alert_id=?",(aid,)); conn.commit(); conn.close()
    return jsonify({"message":"Marked as read"})

@app.route('/api/alerts/read-all', methods=['PUT'])
def mark_all_read():
    conn = get_db(); conn.execute("UPDATE alert SET is_read=1"); conn.commit(); conn.close()
    return jsonify({"message":"All read"})

@app.route('/api/expiring')
def get_expiring():
    days = int(request.args.get('days',7)); conn = get_db()
    products = conn.execute("""SELECT p.*,c.name as category_name,
        CAST(julianday(expire_date)-julianday('now') AS INTEGER) as days_until_expiry
        FROM product p LEFT JOIN category c ON c.category_id=p.category_id
        WHERE date(p.expire_date)<=date('now',?||' days') AND date(p.expire_date)>=date('now')
        ORDER BY p.expire_date ASC""",(str(days),)).fetchall()
    conn.close()
    return jsonify([dict(p) for p in products])

@app.route('/api/stock-value')
def stock_value():
    conn = get_db()
    data = conn.execute("""SELECT c.name as category,
        SUM(p.stock_quantity*p.price_per_unit) as total_value,
        SUM(p.stock_quantity) as total_units,COUNT(p.product_id) as product_count
        FROM category c LEFT JOIN product p ON p.category_id=c.category_id
        GROUP BY c.category_id ORDER BY total_value DESC""").fetchall()
    conn.close()
    return jsonify([dict(d) for d in data])

@app.route('/api/users')
def get_users():
    conn = get_db()
    users = conn.execute("""SELECT u.user_id,u.name,u.email,u.phone,u.address,u.created_at,
        COUNT(o.order_id) as order_count,COALESCE(SUM(o.total_amount),0) as total_spent
        FROM user u LEFT JOIN "order" o ON o.user_id=u.user_id
        GROUP BY u.user_id ORDER BY total_spent DESC""").fetchall()
    conn.close()
    return jsonify([dict(u) for u in users])

if __name__ == '__main__':
    init_db(); seed_db(); seed_admins()
    app.run(debug=True, port=5000)
