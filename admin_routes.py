from flask import Blueprint, jsonify, render_template, request, redirect, url_for, session, flash
from models import OrderItems, Payments, Sales, db, Admin, Products, Orders, Users, Suppliers,Returns
from hashpass import verify_password
import os
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = "static/uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

admin_bp = Blueprint("admin", __name__)

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@admin_bp.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        admin = Admin.query.filter_by(email=email).first()  # Find admin by email

        if admin and verify_password(admin.password, password):
            session["admin_id"] = admin.admin_id  # Store admin ID in session
            flash("Login successful!", "success")
            return redirect(url_for("admin.admin_dashboard"))
        else:
            flash("❌ Invalid email or password", "danger")  # Show error message

    return render_template("admin_login.html")

# Removed duplicate admin_dashboard route to avoid conflict

@admin_bp.route("/admin/logout")
def admin_logout():
    session.pop("admin_id", None)
    flash("✅ Logged out successfully", "success")
    return redirect(url_for("admin.admin_login"))


# Admin Dashboard
@admin_bp.route("/admin/dashboard")
def admin_dashboard():
    if "admin_id" not in session:
        flash("⚠️ Please log in as admin first", "warning")
        return redirect(url_for("admin.admin_login"))

    total_products = Products.query.count()
    total_orders = Orders.query.count()
    total_users = Users.query.count()

    return render_template("admin_dashboard.html", total_products=total_products, total_orders=total_orders, total_users=total_users)

# View All Products
@admin_bp.route("/admin/products")
def view_products():
    if "admin_id" not in session:
        flash("⚠️ Please log in as admin first", "warning")
        return redirect(url_for("admin.admin_login"))

    products = Products.query.all()
    return render_template("admin_products.html", products=products)

# View Orders (Fetching Order Status from Orders & Payment Status from Payments)
@admin_bp.route("/admin/orders")
def view_orders():
    if "admin_id" not in session:
        flash("⚠️ Please log in as admin first", "warning")
        return redirect(url_for("admin.admin_login"))

    # Fetch orders and payment status from payments table
    orders = db.session.query(
        Orders.order_id,
        Orders.user_id,
        Orders.status.label("order_status"),
        db.case(
            (Payments.status == "Success", "Success"),
            else_="Not Paid"
        ).label("payment_status")
    ).outerjoin(Payments, Orders.order_id == Payments.order_id).all()

    # ✅ Fetch return requests and store in a dictionary {order_id: request}
    return_requests = {req.order_id: req for req in Returns.query.all()}  # ✅ Use `Returns.query.all()`

    return render_template("admin_orders.html", orders=orders, return_requests=return_requests)


# View Users
@admin_bp.route("/admin/users")
def view_users():
    if "admin_id" not in session:
        flash("⚠️ Please log in as admin first", "warning")
        return redirect(url_for("admin.admin_login"))

    users = Users.query.all()
    return render_template("admin_users.html", users=users)

# 🟢 Add Product
@admin_bp.route("/admin/products/add", methods=["GET", "POST"])
def add_product():
    if "admin_id" not in session:
        flash("⚠️ Please log in as admin first", "warning")
        return redirect(url_for("admin.admin_login"))

    suppliers = Suppliers.query.all()

    if request.method == "POST":
        name = request.form["name"]
        price = request.form["price"]
        stock = request.form["stock"]
        supplier_id = request.form["supplier_id"]
        size = request.form["size"]

        image_file = request.files.get("image")
        image_filename = None

        if image_file and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            image_path = os.path.join(UPLOAD_FOLDER, filename)
            image_file.save(image_path)
            image_filename = filename

        # Save to DB
        new_product = Products(
            name=name,
            price=price,
            stock=stock,
            supplier_id=supplier_id,
            size=size,
            image=image_filename  # save the image filename
        )
        db.session.add(new_product)
        db.session.commit()

        flash("✅ Product added successfully!", "success")
        return redirect(url_for("admin.view_products"))

    return render_template("admin_add_product.html", suppliers=suppliers)

# 🟢 Edit Product
@admin_bp.route("/admin/products/edit/<int:product_id>", methods=["GET", "POST"])
def edit_product(product_id):
    if "admin_id" not in session:
        flash("⚠️ Please log in as admin first", "warning")
        return redirect(url_for("admin.admin_login"))

    product = Products.query.get_or_404(product_id)
    suppliers = Suppliers.query.all()  # Get all suppliers

    if request.method == "POST":
        product.name = request.form["name"]
        product.price = request.form["price"]
        product.stock = request.form["stock"]
        product.supplier_id = request.form["supplier_id"]
        product.size = request.form["size"]  # Adding the size field update
        db.session.commit()
        flash("✅ Product updated successfully!", "success")
        return redirect(url_for("admin.view_products"))

    return render_template("admin_edit_product.html", product=product, suppliers=suppliers)

# 🟢 Delete Product
@admin_bp.route("/admin/products/delete/<int:product_id>", methods=["POST"])
def delete_product(product_id):
    if "admin_id" not in session:
        flash("⚠️ Please log in as admin first", "warning")
        return redirect(url_for("admin.admin_login"))

    product = Products.query.get_or_404(product_id)

    # Check if product is linked to any order items
    from models import OrderItems  # adjust if your model is named differently
    linked_order_items = OrderItems.query.filter_by(product_id=product.product_id).first()

    if linked_order_items:
        flash("❌ Cannot delete product — it is linked to existing orders.", "danger")
        return redirect(url_for("admin.view_products"))

    db.session.delete(product)
    db.session.commit()
    flash("✅ Product deleted successfully!", "success")
    return redirect(url_for("admin.view_products"))

@admin_bp.route('/update_shipping/<int:order_id>', methods=['POST'])
def update_shipping(order_id):
    order = Orders.query.get(order_id)
    if order:
        new_status = request.form.get("shipping_status")  # Get status from form
        if new_status in ["Pending", "Shipped", "Delivered"]:
            order.status = new_status  # Update status
            db.session.commit()
            flash("Order status updated successfully!", "success")
        else:
            flash("Invalid status update!", "danger")
    return redirect(url_for("admin.view_orders"))  # Redirect back to admin panel

@admin_bp.route("/admin/process_return/<int:return_id>/<string:action>", methods=["POST"])
def process_return(return_id, action):
    if "admin_id" not in session:
        flash("⚠️ Please log in as admin first", "warning")
        return redirect(url_for("admin.admin_login"))

    return_request = Returns.query.get(return_id)
    if not return_request:
        flash("⚠️ Return request not found!", "danger")
        return redirect(url_for("admin.view_orders"))

    # ✅ Update only the return status, NOT the order status
    if action == "approve":
        return_request.status = "Approved"
        flash(f"✅ Return request for Order #{return_request.order_id} has been approved.", "success")
    elif action == "reject":
        return_request.status = "Rejected"
        flash(f"❌ Return request for Order #{return_request.order_id} has been rejected.", "danger")

    db.session.commit()
    return redirect(url_for("admin.view_orders"))

@admin_bp.route('/order_details/<int:order_id>', methods=['GET'])
def get_order_details(order_id):
    # Fetch the order and ensure it exists
    order = Orders.query.get(order_id)

    if not order:
        return jsonify({'error': 'Order not found'}), 404

    # Fetch order items
    order_items = (
        db.session.query(OrderItems, Products)
        .join(Products, OrderItems.product_id == Products.product_id)
        .filter(OrderItems.order_id == order_id)
        .all()
    )

    if not order_items:
        return jsonify({'error': 'No items found for this order'}), 404

    order_data = []
    for order_item, product in order_items:
        order_data.append({
            'product_name': product.name,
            'size': product.size,  # Add size from the Products table
            'quantity': order_item.quantity,
            'price': order_item.price,
            'total_price': order_item.quantity * order_item.price
        })

    # Convert address to string before returning JSON
    return jsonify({
        'order_items': order_data,
        'delivery_address': str(order.address)  # Convert to string
    })

@admin_bp.route('/admin/suppliers')
def manage_suppliers():
    suppliers = Suppliers.query.all()
    return render_template('manage_suppliers.html', suppliers=suppliers)

@admin_bp.route('/admin/suppliers/add', methods=['GET', 'POST'])
def add_supplier():
    if request.method == 'POST':
        name = request.form['name']
        contact_info = request.form['contact_info']
        address = request.form['address']  # Capture the address
        supplier = Suppliers(name=name, contact_info=contact_info, address=address)
        db.session.add(supplier)
        db.session.commit()
        flash('Supplier added successfully!', 'success')
        return redirect(url_for('admin.manage_suppliers'))
    return render_template('add_suppliers.html')


@admin_bp.route('/admin/suppliers/edit/<int:supplier_id>', methods=['GET', 'POST'])
def edit_supplier(supplier_id):
    supplier = Suppliers.query.get(supplier_id)
    if request.method == 'POST':
        supplier.name = request.form['name']
        supplier.contact_info = request.form['contact_info']
        supplier.address = request.form['address']  # Update the address
        db.session.commit()
        flash('Supplier updated successfully!', 'success')
        return redirect(url_for('admin.manage_suppliers'))
    return render_template('edit_suppliers.html', supplier=supplier)


@admin_bp.route('/admin/suppliers/delete/<int:supplier_id>', methods=['POST'])
def delete_supplier(supplier_id):
    supplier = Suppliers.query.get(supplier_id)
    db.session.delete(supplier)
    db.session.commit()
    flash('Supplier deleted successfully!', 'danger')
    return redirect(url_for('admin.manage_suppliers'))

@admin_bp.route('/admin/delete_order/<int:order_id>', methods=['POST'])
def delete_order(order_id):
    if 'admin_id' not in session:
        flash('Unauthorized access', 'error')
        return redirect(url_for('admin.admin_dashboard'))

    order = Orders.query.get(order_id)

    if order:
        # Delete related records first
        Returns.query.filter_by(order_id=order_id).delete()
        Sales.query.filter_by(order_id=order_id).delete()
        Payments.query.filter_by(order_id=order_id).delete()

        # Now delete the order
        db.session.delete(order)
        db.session.commit()
        
        flash(f'Order {order_id} deleted successfully.', 'success')
    else:
        flash('Order not found.', 'error')

    return redirect(url_for('admin.view_orders'))

# adminroutes.py or your relevant route file

@admin_bp.route("/order/<int:order_id>")
def order_details(order_id):
    # Fetch the order from the database
    order = Orders.query.get_or_404(order_id)
    
    # Fetch the order items (product details along with quantity)
    order_items = db.session.query(OrderItems, Products).join(Products).filter(OrderItems.order_id == order_id).all()
    
    # Get the payment details (assuming you have a 'Payments' table with a 'payment_status' field)
    payment = Payments.query.filter_by(order_id=order_id).first()
    
    # Calculate the total price by summing the price * quantity for all order items
    total_price = sum(item.quantity * product.price for item, product in order_items)
    
    # Get the delivery address and order creation date
    address = order.address
    created_at = order.created_at.strftime('%d-%m-%Y %H:%M:%S')  # Format the date as needed
    
    # Return the rendered template
    return render_template('order_details.html', 
                           order=order, 
                           order_items=order_items, 
                           payment=payment, 
                           address=address, 
                           total_price=total_price, 
                           created_at=created_at)
