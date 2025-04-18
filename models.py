from flask_sqlalchemy import SQLAlchemy
import datetime

db = SQLAlchemy()

def init_db(app):
    db.init_app(app)

# Admin Table
class Admin(db.Model):
    __tablename__ = 'admin'
    admin_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)  # Store hashed password
    email = db.Column(db.String(100), unique=True, nullable=False)

# Users Table
class Users(db.Model):
    __tablename__ = 'users'
    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)  # Store hashed password
    email = db.Column(db.String(100), unique=True, nullable=False)

# Suppliers Table
class Suppliers(db.Model):
    __tablename__ = 'suppliers'
    supplier_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    contact_info = db.Column(db.String(200), nullable=False)
    address = db.Column(db.String(300), nullable=True)  # New address field

    def __repr__(self):
        return f"<Supplier {self.name}>"

# Products Table
class Products(db.Model):
    __tablename__ = 'products'
    product_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.supplier_id'), nullable=False)
    image = db.Column(db.String(100))

    # Add Size Field
    size = db.Column(db.String(10), nullable=True)  # This will store product sizes like 'S', 'M', 'L'

# Cart Table
class Cart(db.Model):
    __tablename__ = 'cart'
    cart_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.product_id'), nullable=False)
    size = db.Column(db.String(10), nullable=True)  # Store selected size in the cart
    quantity = db.Column(db.Integer, nullable=False)

    product = db.relationship('Products', backref=db.backref('cart_items', lazy=True))

class Orders(db.Model):
    __tablename__ = 'orders'
    
    order_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), nullable=False, default="Pending")
    address = db.Column(db.Text, nullable=False)
    from datetime import datetime
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)


    return_request = db.relationship("Returns", backref="order", uselist=False)

# Order Items Table
class OrderItems(db.Model):
    __tablename__ = 'order_items'
    order_item_id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.order_id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.product_id'), nullable=False)
    size = db.Column(db.String(10), nullable=True)  # Store the size selected for the product in the order
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)

    product = db.relationship('Products', backref='order_items', lazy=True)

# Payments Table
class Payments(db.Model):
    __tablename__ = 'payments'

    payment_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.order_id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), nullable=False)  # Example: "Success" / "Failed" / "Pending"
    date = db.Column(db.DateTime, nullable=False, default=datetime.datetime.now) 

    order = db.relationship('Orders', backref=db.backref('payments', lazy=True))
    user = db.relationship('Users', backref=db.backref('payments', lazy=True))

    def __init__(self, order_id, user_id, amount, payment_method, status, date=None):
        self.order_id = order_id
        self.user_id = user_id
        self.amount = amount
        self.payment_method = payment_method
        self.status = status
        self.date = date if date else datetime.datetime.now()

# Returns Table
class Returns(db.Model):
    __tablename__ = 'returns'
    return_id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.order_id'), nullable=False)
    reason = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(50), nullable=False, default="Pending")

# Sales Table
class Sales(db.Model):
    __tablename__ = 'sales'

    sale_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.product_id'), nullable=False)
    quantity_sold = db.Column(db.Integer, nullable=False)
    total_revenue = db.Column(db.Float, nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.order_id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    size = db.Column(db.String(50), nullable=True)  # Add size column
    
    product = db.relationship('Products', backref=db.backref('sales', lazy=True))
    order = db.relationship('Orders', backref=db.backref('sales', lazy=True))
    user = db.relationship('Users', backref=db.backref('sales', lazy=True))

    def __init__(self, product_id, quantity_sold, total_revenue, order_id, user_id, size=None):
        self.product_id = product_id
        self.quantity_sold = quantity_sold
        self.total_revenue = total_revenue
        self.order_id = order_id
        self.user_id = user_id
        self.size = size  # ✅ Add this line
