from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models import Orders,  db, Users,Products,OrderItems, Payments, Sales,Returns
from hashpass import hash_password, verify_password
from werkzeug.security import check_password_hash
import datetime

user_bp = Blueprint("user", __name__)

@user_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        # Check if username already exists
        if Users.query.filter_by(username=name).first():
            flash("❌ Username already taken. Please choose a different one.", "danger")
            return redirect(url_for("user.signup"))

        # Check if email already exists
        if Users.query.filter_by(email=email).first():
            flash("❌ Email already registered. Please log in.", "danger")
            return redirect(url_for("user.login"))

        # Hash password and create user
        hashed_password = hash_password(password)
        new_user = Users(username=name, email=email, password=hashed_password)
        db.session.add(new_user)

        try:
            db.session.commit()
            flash("✅ Signup successful! Please log in.", "success")
        except:
            db.session.rollback()
            flash("❌ Something went wrong. Please try again.", "danger")
            return redirect(url_for("user.signup"))

        return redirect(url_for("user.login"))

    return render_template("signup.html")


@user_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        user = Users.query.filter_by(email=email).first()

        if not user:
            flash("No account found with this email. Please sign up first.", "warning")
            return redirect(url_for('user.signup'))  # Redirect to signup page

        if check_password_hash(user.password, password):
            session['user_id'] = user.user_id  # Store user ID in session
            flash("Login successful!", "success")
            return redirect(url_for('user.dashboard'))  # Redirect to dashboard

        flash("Incorrect password. Please try again.", "danger")

    return render_template('login.html')

@user_bp.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        flash("⚠️ Please log in first!", "warning")
        return redirect(url_for("user.login"))

    user = Users.query.get(session["user_id"])

    return render_template("user_dashboard.html", user=user)

@user_bp.route('/my_orders')
def my_orders():
    if "user_id" not in session:
        flash("⚠️ Please log in first!", "warning")
        return redirect(url_for("user.login"))

    # Fetch only one row per order with related statuses
    orders = (
        db.session.query(
            Orders.order_id,
            Orders.total_amount,
            Orders.created_at,
            Orders.status.label("shipping_status"),
            db.func.coalesce(Payments.status, "Not Paid").label("payment_status"),
            db.func.coalesce(Returns.status, "No Return Requested").label("return_status")
        )
        .outerjoin(Payments, Orders.order_id == Payments.order_id)
        .outerjoin(Returns, Orders.order_id == Returns.order_id)
        .filter(Orders.user_id == session["user_id"])
        .order_by(Orders.created_at.desc())
        .all()
    )

    return render_template("user_orders.html", orders=orders)



@user_bp.route("/logout")
def logout():
    session.pop("user_id", None)
    flash("✅ Logged out successfully", "success")
    return redirect(url_for("user.login"))

@user_bp.route('/products')
def product_list():
    products = Products.query.all()
    return render_template('products.html', products=products)

@user_bp.route('/view_order/<int:order_id>')
def view_order(order_id):
    order = Orders.query.get(order_id)
    if not order:
        flash("Order not found", "danger")
        return redirect(url_for('user.dashboard'))

    # Fetch order items with product names and sizes
    order_items = db.session.query(
        OrderItems.quantity, 
        OrderItems.price, 
        Products.name,  # Fetch product name
        Products.size   # Fetch product size
    ).join(Products, OrderItems.product_id == Products.product_id).filter(OrderItems.order_id == order_id).all()

    # ✅ Fetch the latest payment status for this order
    payment = Payments.query.filter_by(order_id=order_id).order_by(Payments.date.desc()).first()

    return render_template('view_order.html', order=order, order_items=order_items, payment=payment)

@user_bp.route('/process_payment', methods=['POST'])
def process_payment():
    if 'user_id' not in session:
        flash("Please log in to continue.", "warning")
        return redirect(url_for('auth.login'))

    order_id = request.form.get('order_id')
    payment_method = request.form.get('payment_method')

    order = Orders.query.get(order_id)
    if not order:
        flash("Order not found!", "danger")
        return redirect(url_for('user.view_order'))

    user_id = session.get('user_id')  # ✅ Fetch user_id safely

    # ✅ Insert into Payments table
    new_payment = Payments(
        order_id=order_id,
        user_id=user_id,
        amount=order.total_amount,
        payment_method=payment_method,
        status="Success",
        date=datetime.datetime.now()
    )
    db.session.add(new_payment)

    # ✅ Insert into Sales table for each product in order_items
    order_items = OrderItems.query.filter_by(order_id=order_id).all()

    for item in order_items:
        # Get the size of the product from the order item
        product_size = item.size  # Ensure this is part of OrderItems

        # Now include the size in the Sales table
        new_sale = Sales(
            order_id=order_id,
            user_id=user_id,  # ✅ Use user_id correctly
            product_id=item.product_id,
            quantity_sold=item.quantity,
            total_revenue=item.price * item.quantity,
            size=product_size  # Track size sold
        )
        db.session.add(new_sale)

    db.session.commit()

    flash("Payment successful! Your order has been confirmed ✅", "success")
    return redirect(url_for('user.view_order', order_id=order_id))

@user_bp.route('/request_return/<int:order_id>', methods=['POST'])
def request_return(order_id):
    order = Orders.query.get(order_id)
    if not order:
        flash("Order not found!", "danger")
        return redirect(url_for('user_dashboard'))

    if order.status != "Delivered":
        flash("You can only return delivered orders!", "warning")
        return redirect(url_for('user_dashboard'))

    reason = request.form.get("reason")
    
    return_request = Returns(order_id=order_id, reason=reason)
    db.session.add(return_request)
    db.session.commit()

    flash("Return request submitted successfully!", "success")
    return redirect(url_for('user.dashboard'))

