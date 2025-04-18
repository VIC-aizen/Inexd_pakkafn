from flask import Blueprint, request, session, redirect, url_for, flash, render_template
from models import Users, db, Cart, Products, Orders, OrderItems

cart_bp = Blueprint("cart", __name__)

@cart_bp.route("/cart")
def view_cart():
    user_id = session.get('user_id')
    if not user_id:
        return "Please log in to view your cart.", 403

    cart_items = Cart.query.filter_by(user_id=user_id).all()

    # Fetch all products in one query and use a dictionary to map product_id to product
    products = {product.product_id: product for product in Products.query.all()}

    products_in_cart = [
        {
            'cart_id': cart_item.cart_id,
            'product_name': products.get(cart_item.product_id).name,  # Access from the products dictionary
            'product_price': products.get(cart_item.product_id).price,
            'quantity': cart_item.quantity,
            'size': products.get(cart_item.product_id).size  # Fetch size directly from Products
        }
        for cart_item in cart_items
        if products.get(cart_item.product_id)  # Ensure the product exists
    ]

    return render_template('cart.html', cart_items=products_in_cart)

@cart_bp.route('/cart/add', methods=['POST'])
def add_to_cart():
    user_id = session.get('user_id')
    if not user_id:
        return "Please log in to add items to the cart.", 403

    product_id = request.form.get('product_id')
    quantity = int(request.form.get('quantity'))

    # Check if product is already in the cart
    existing_item = Cart.query.filter_by(user_id=user_id, product_id=product_id).first()
    if existing_item:
        existing_item.quantity += quantity
    else:
        new_item = Cart(user_id=user_id, product_id=product_id, quantity=quantity)
        db.session.add(new_item)

    db.session.commit()

    # ✅ Fetch product to show name in flash message
    product = Products.query.get(product_id)
    flash(f" Added {product.name} to your cart!", "success")

    return redirect(url_for('product.view_products'))


# 🟢 Update Cart Quantity
@cart_bp.route("/cart/update/<int:cart_id>", methods=["POST"])
def update_cart(cart_id):
    if "user_id" not in session:
        flash("⚠️ Please log in first", "warning")
        return redirect(url_for("auth.login"))

    new_quantity = int(request.form["quantity"])
    cart_item = Cart.query.get_or_404(cart_id)
    cart_item.quantity = new_quantity
    db.session.commit()
    flash("✅ Cart updated!", "success")
    return redirect(url_for("cart.view_cart"))

# 🟢 Remove from Cart
@cart_bp.route("/cart/remove/<int:cart_id>", methods=["POST"])
def remove_from_cart(cart_id):
    if "user_id" not in session:
        flash("⚠️ Please log in first", "warning")
        return redirect(url_for("auth.login"))

    cart_item = Cart.query.get_or_404(cart_id)
    db.session.delete(cart_item)
    db.session.commit()
    flash("🗑️ Item removed from cart!", "success")
    return redirect(url_for("cart.view_cart"))

@cart_bp.route('/checkout', methods=['GET', 'POST'])
def checkout():
    user_id = session.get('user_id')

    if not user_id:
        flash("Please log in first!", "error")
        return redirect(url_for('auth.login'))

    cart_items = Cart.query.filter_by(user_id=user_id).all()

    if not cart_items:
        flash("Your cart is empty!", "error")
        return redirect(url_for('cart.view_cart'))

    # Calculate total amount
    total_amount = sum(Products.query.get(item.product_id).price * item.quantity for item in cart_items)

    # Fetch last used address from previous orders
    last_order = Orders.query.filter_by(user_id=user_id).order_by(Orders.order_id.desc()).first()
    saved_address = last_order.address if last_order else ""

    if request.method == 'POST':
        address = request.form.get('address', '').strip()

        if not address:
            flash("Please enter a delivery address!", "error")
            return redirect(url_for('cart.checkout'))

        # Create a new order with total_amount and address
        new_order = Orders(user_id=user_id, total_amount=total_amount, status="Pending", address=address)
        db.session.add(new_order)
        db.session.commit()

        # Add items to order
        for item in cart_items:
            product = Products.query.get(item.product_id)
            if product:
                order_item = OrderItems(
                    order_id=new_order.order_id,
                    product_id=item.product_id,
                    quantity=item.quantity,
                    price=product.price * item.quantity,
                    size=item.size
                )
                db.session.add(order_item)

                # Reduce stock
                if product.stock >= item.quantity:
                    product.stock -= item.quantity
                else:
                    flash(f"Not enough stock for {product.name}!", "error")
                    return redirect(url_for('cart.view_cart'))

        # Clear cart after successful order placement
        Cart.query.filter_by(user_id=user_id).delete()
        db.session.commit()

        flash("Checkout successful! Your order has been placed.", "success")
        return redirect(url_for('user.view_order', order_id=new_order.order_id))

    return render_template('checkout.html', cart_items=cart_items, total_amount=total_amount, address=saved_address)

