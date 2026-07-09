# ============================================================================
# IMPORTS
# ============================================================================

from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash, get_user_model
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.db.models import Avg, Count, Sum, Max, F, Q
from django.utils import timezone
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.core.paginator import Paginator
from decimal import Decimal
from collections import defaultdict
import random
import urllib.parse
import smtplib
from datetime import timedelta
# Add these to your existing imports
import os
import uuid
from django.core.mail import send_mail
from django.db import transaction
from django.conf import settings
from .forms import DisputeForm, DisputeResponseForm, BuyerReplyForm, AdminDecisionForm, ReturnTrackingForm

from .models import (
    Activity, Cart, Product, CartItem, Category, Review,
    Wishlist, Order, OrderItem, SellerProfile, BankDetails,
    ContactMessage, ShippingAddress, Dispute, Notification,DisputeEvidence,DisputeMessage
)
from .forms import ReviewForm
from .utils import create_activity, create_notification
from .utils import super_admin_required

User = get_user_model()


# ============================================================================
# HOME & PRODUCT VIEWS
# ============================================================================

def home(request):
    """Home page view with featured and new products"""
    now = timezone.now()
    rotation_key = int(now.timestamp() // 180)  # 3 minutes rotation
    if request.user.is_authenticated:
        wishlist_products = Wishlist.objects.filter(
            user=request.user
        ).values_list("product_id", flat=True)
    else:
        wishlist_products = []

    products = list(
        Product.objects.filter(quantity__gt=0)
        .select_related('seller')
        .prefetch_related('reviews')
    )

    if not products:
        return render(request, 'index.html', {
            'featured_products': [],
            'new_products': []
        })

    # Rotate ALL products every 3 mins
    random.seed(rotation_key)
    random.shuffle(products)

    featured_products = products[:8]  # Just first 8 after shuffle

    # New arrivals (latest first)
    new_products = sorted(
        products,
        key=lambda x: x.created_at,
        reverse=True
    )[:8]
    
    products = Product.objects.filter(quantity__gt=0).annotate(
        average_rating=Avg('reviews__rating'),
        rating_count=Count('reviews')
    )

    top_rated_products = products.filter(
        average_rating__gte=4,
        rating_count__gte=3
    )

    return render(request, 'index.html', {
        'featured_products': featured_products,
        'new_products': new_products,
        "wishlist_products": wishlist_products
    })


def product_detail(request, slug):
    """Product detail page with reviews and seller products"""

    product = get_object_or_404(
        Product.objects.select_related('seller')
        .prefetch_related('reviews__user'),
        slug=slug
    )

    # Handle Review Submission
    if request.method == "POST":
        if not request.user.is_authenticated:
            messages.error(request, "You must be logged in to write a review.")
            return redirect('login')

        if Review.objects.filter(product=product, user=request.user).exists():
            messages.error(request, "You have already reviewed this product.")
            return redirect('product_detail', slug=slug)

        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.product = product
            review.user = request.user
            review.save()
            messages.success(request, "Review submitted successfully!")
            return redirect('product_detail', slug=slug)
    else:
        form = ReviewForm()

    # SAFE wishlist (FIXED)
    wishlist_products = []
    if request.user.is_authenticated:
        wishlist_products = Wishlist.objects.filter(
            user=request.user
        ).values_list("product_id", flat=True)

    # New arrival
    now = timezone.now()
    new_arrival = (now - product.created_at).days <= 30

    # Ratings
    rating_data = product.reviews.aggregate(
        avg=Avg('rating'),
        count=Count('id')
    )

    average_rating = rating_data['avg'] or 0
    rating_count = rating_data['count'] or 0

    # Seller goods average: sum of each product's average rating divided by total seller products
    seller_products = Product.objects.filter(seller=product.seller).annotate(
        avg_rating=Avg('reviews__rating')
    )
    seller_product_count = seller_products.count()
    total_goods_rating = sum((sp.avg_rating or 0) for sp in seller_products)
    avg_seller_rating = total_goods_rating / seller_product_count if seller_product_count else 0
    seller_rating_count = Review.objects.filter(product__seller=product.seller).count()

    # Rating bars
    rating_bars = []
    for i in range(5, 0, -1):
        count = product.reviews.filter(rating=i).count()
        percent = round((count / rating_count) * 100) if rating_count > 0 else 0

        rating_bars.append({
            "star": i,
            "count": count,
            "percent": percent
        })

    # Top rated badge
    top_rated = average_rating >= 4 and rating_count >= 3

    # FINAL RETURN (THIS WAS MISSING)
    context = {
        "product": product,
        "form": form,
        "reviews": product.reviews.all().order_by('-created_at'),
        "wishlist_products": wishlist_products,
        "new_arrival": new_arrival,
        "average_rating": average_rating,
        "rating_count": rating_count,
        "avg_seller_rating": avg_seller_rating,
        "seller_rating_count": seller_rating_count,
        "rating_bars": rating_bars,
        "top_rated": top_rated,
    }

    return render(request, "product-details.html", context)   


def main_base(request):
    return render(request,'main_base.html')


def contact_view(request):
    if request.method == "POST":
        full_name = request.POST.get("full_name")
        email = request.POST.get("email")
        user_type = request.POST.get("user_type")
        subject = request.POST.get("subject")
        message = request.POST.get("message")

        # save message
        contact = ContactMessage.objects.create(
            full_name=full_name,
            email=email,
            user_type=user_type,
            subject=subject,
            message=message,
            message_type='contact', 
        )

        # CREATE ACTIVITY (THIS IS THE NOTIFICATION)
        create_activity(
            title="New Contact Message",
            description=f"{full_name} sent a message ({user_type})",
            activity_type="alert"
        )

        messages.success(request, "Message sent successfully!")
        return redirect("contact")

    return render(request, "contact_us.html")
    
@login_required
def delete_message(request, message_id):
    msg = get_object_or_404(ContactMessage, id=message_id)
    msg.delete()
    return redirect("admin_notifications")


def about(request):
    return render(request,"about_us.html")


def new_products(request):
    products = Product.objects.select_related('seller', 'category').all()

    # SEARCH (FIXED)
    search_query = request.GET.get('q')
    if search_query:
        products = products.filter(name__icontains=search_query)

    # CATEGORY
    category = request.GET.get('category')
    if category and category != "all":
        products = products.filter(category_id=category)

    # SORTING (FIXED)
    sort = request.GET.get('sort')
    if sort == "price-low":
        products = products.order_by('price')
    elif sort == "price-high":
        products = products.order_by('-price')
    else:
        products = products.order_by('-created_at')

    # PAGINATION
    paginator = Paginator(products, 8)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # animation delay
    for index, product in enumerate(page_obj):
        product.aos_delay = index * 50

    categories = Category.objects.all()

    if request.user.is_authenticated:
        wishlist_products = Wishlist.objects.filter(
            user=request.user
        ).values_list("product_id", flat=True)
    else:
        wishlist_products = []

    context = {
        'products': page_obj,
        'page_obj': page_obj,
        'categories': categories,
        "wishlist_products": wishlist_products
    }

    return render(request, 'products.html', context)


def search_suggestions(request):
    query = request.GET.get('q')

    products = Product.objects.filter(name__icontains=query)[:5]

    results = []
    for product in products:
        results.append({
            "id": product.id,
            "name": product.name,
            "image": product.front_image.url if product.front_image else "",
            "slug": product.slug,
        })

    return JsonResponse(results, safe=False)


# ============================================================================
# AUTHENTICATION VIEWS
# ============================================================================

def register(request):
    """User registration view"""
    if request.method == "POST":
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        username = request.POST.get("username")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")
        role = request.POST.get("role")

        # Validation
        if not all([first_name, last_name, username, email, password, confirm_password, role]):
            messages.error(request, "All fields are required.")
            return redirect("register")

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect("register")

        try:
            user = User.objects.create_user(
                first_name=first_name,
                last_name=last_name,
                username=username,
                email=email,
                password=password,
                role=role,
                phone=phone
            )

            # LOG ACTIVITY
            create_activity(
                title="New User Registered",
                description=f"{user.username} joined as {user.get_role_display()}",
                activity_type="user"
            )

            messages.success(request, "Account created! Please login.")
            return redirect("login")

        except IntegrityError:
            messages.error(request, "Username or Email already exists.")
            return redirect("register")

    return render(request, "register.html")


def login_view(request):
    """User login view"""
    if request.method == "POST":
        username_or_email = request.POST.get("username")
        password = request.POST.get("password")
        remember = request.POST.get("remember")

        if not username_or_email or not password:
            messages.error(request, "Please fill all fields.")
            return redirect("login")

        # Authenticate by email or username
        if "@" in username_or_email:
            try:
                user_obj = User.objects.get(email=username_or_email)
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                user = None
        else:
            user = authenticate(request, username=username_or_email, password=password)

        if user is not None:
            login(request, user)

            if not remember:
                request.session.set_expiry(0)

            # 🔥 Redirect based on role
            if user.role == "seller":
                return redirect("home")
            elif user.role == "buyer":
                return redirect("home")
            else:  # both buyer & seller
                return redirect("home")  # default dashboard for both

        else:
            messages.error(request, "Invalid email/username or password.")
            return redirect("login")

    return render(request, "login.html")


def logout_view(request):
    """User logout view"""
    logout(request)
    return redirect("home")


# ============================================================================
# DASHBOARD VIEWS
# ============================================================================

@login_required
def seller_dashboard(request):
    user = request.user

    orders = OrderItem.objects.filter(product__seller=user)

    # AUTO CHECK EXPIRED ORDERS
    for order in orders:
        order.check_expiry()

    total_sales = sum(item.subtotal() for item in orders if item.status == "Completed")
    total_orders = orders.count()
    pending_orders = orders.filter(status="Pending").count()
    p2p_orders = orders.filter(order__order_type="escrow").count()
    wallet_balance = getattr(user, "wallet_balance", 0)
    total_products = Product.objects.filter(seller=user).count()

    recent_orders = orders.select_related("product", "order").order_by("-id")[:5]

    return render(request, "seller/seller.html", {
        "total_sales": total_sales,
        "total_orders": total_orders,
        "pending_orders": pending_orders,
        "p2p_orders": p2p_orders,
        "wallet_balance": wallet_balance,
        "total_products": total_products,
        "recent_orders": recent_orders,
    })

@login_required
def buyer_dashboard(request):
    user = request.user

    if user.role not in ["buyer", "both"]:
        return redirect("seller_dashboard")

    orders = OrderItem.objects.filter(order__buyer=user).select_related("product", "order")

    # AUTO CHECK
    for order in orders:
        order.check_expiry()

    total_orders = orders.count()
    pending_orders = orders.filter(status="Pending").count()
    completed_orders = orders.filter(status="Completed").count()
    waiting_confirm = orders.filter(status="Delivered").count()

    recent_orders = orders.order_by("-id")[:3]

    return render(request, "buyer/buyer-dashboard.html", {
        "total_orders": total_orders,
        "pending_orders": pending_orders,
        "completed_orders": completed_orders,
        "waiting_confirm": waiting_confirm,
        "recent_orders": recent_orders,
    })

# ============================================================================
# PRODUCT MANAGEMENT VIEWS
# ============================================================================

@login_required
def add_product(request):
    """Add new product view"""
    if request.user.role not in ['seller', 'both']:
        return redirect('home')

    categories = Category.objects.all()

    if request.method == 'POST':
        name = request.POST.get('productName')
        category_slug = request.POST.get('category')
        category_obj = Category.objects.get(slug=category_slug) if category_slug else None

        sku = request.POST.get('sku')
        description = request.POST.get('description')
        price = request.POST.get('price')
        old_price = request.POST.get('oldPrice')
        quantity = request.POST.get('quantity')
        product_type = request.POST.get('productType', 'physical')

        specs = []
        for key in request.POST:
            if key.startswith('spec_name_'):
                index = key.split('_')[-1]
                spec_name = request.POST.get(f'spec_name_{index}')
                spec_value = request.POST.get(f'spec_value_{index}')
                if spec_name and spec_value:
                    specs.append({
                        'name': spec_name,
                        'value': spec_value
                    })

        Product.objects.create(
            seller=request.user,
            name=name,
            category=category_obj,
            sku=sku,
            description=description,
            price=price,
            old_price=old_price or None,
            quantity=quantity,
            product_type=product_type,
            specifications=specs,
            front_image=request.FILES.get('front_image'),
            back_image=request.FILES.get('back_image'),
            side_image=request.FILES.get('side_image'),
            extra_image=request.FILES.get('extra_image'),
        )

        return redirect('my_products')

    return render(request, 'seller/add-product.html', {
        'categories': categories
    })


@login_required
def my_products(request):
    """View seller's products"""
    if request.user.role not in ['seller', 'both']:
        return redirect('home')

    products = Product.objects.filter(seller=request.user)

    # SEARCH
    search = request.GET.get('search')
    if search:
        products = products.filter(name__icontains=search)

    # CATEGORY FILTER
    category_slug = request.GET.get('category')
    if category_slug:
        products = products.filter(category__slug=category_slug)

    #   STATUS FILTER
    status = request.GET.get('status')
    if status == "published":
        products = products.filter(quantity__gt=0)
    elif status == "outofstock":
        products = products.filter(quantity=0)

    products = products.order_by('-created_at')
    wishlist_products = Wishlist.objects.filter(user=request.user).values_list("product_id", flat=True)
    
    # AJAX response
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        html = render_to_string(
            'seller/partials/product-grid.html',
            {'products': products},
            request=request
        )
        return JsonResponse({'html': html})

    return render(request, 'seller/my-products.html', {
        'products': products,
        'categories': Category.objects.all(),
        "wishlist_products": wishlist_products
    })


@login_required
def edit_product(request, slug):
    """Edit product view"""
    product = get_object_or_404(Product, slug=slug, seller=request.user)

    if request.user.role not in ['seller', 'both']:
        return redirect('home')

    categories = Category.objects.all()

    if request.method == "POST":
        # Basic info
        product.name = request.POST.get('productName')
        product.sku = request.POST.get('sku')
        product.description = request.POST.get('description')
        product.price = request.POST.get('price')
        product.old_price = request.POST.get('oldPrice') or None
        product.quantity = request.POST.get('quantity')
        product.product_type = request.POST.get('productType', 'physical')

        # Category
        category_slug = request.POST.get('category')
        product.category = Category.objects.get(slug=category_slug) if category_slug else None

        # Specifications
        specs = []
        for key in request.POST:
            if key.startswith('spec_name_'):
                index = key.split('_')[-1]
                spec_name = request.POST.get(f'spec_name_{index}')
                spec_value = request.POST.get(f'spec_value_{index}')
                if spec_name and spec_value:
                    specs.append({'name': spec_name, 'value': spec_value})
        product.specifications = specs

        # Images (replace only if new files are uploaded)
        if request.FILES.get('front_image'):
            product.front_image = request.FILES.get('front_image')
        if request.FILES.get('back_image'):
            product.back_image = request.FILES.get('back_image')
        if request.FILES.get('side_image'):
            product.side_image = request.FILES.get('side_image')
        if request.FILES.get('extra_image'):
            product.extra_image = request.FILES.get('extra_image')

        product.save()
        return redirect('my_products')

    return render(request, 'seller/edit-product.html', {
        'product': product,
        'categories': categories
    })


@login_required
def delete_product(request, slug):
    """Delete product view"""
    product = get_object_or_404(Product, slug=slug, seller=request.user)
    product.delete()
    return redirect('my_products')


# ============================================================================
# CATEGORY MANAGEMENT
# ============================================================================

@super_admin_required
def add_category(request):
    """Add new category view"""
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        image = request.FILES.get('image')

        if name:
            category = Category(name=name, description=description, image=image)
            category.save()
            messages.success(request, f'Category "{name}" created successfully!')
            return redirect('add_category')
        else:
            messages.error(request, "Category name is required.")

    categories = Category.objects.all().order_by('name')
    return render(request, 'super_admin/add-category.html', {
        'categories': categories,
    })


@super_admin_required
def delete_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    category_name = category.name
    category.delete()
    messages.success(request, f'Category "{category_name}" deleted successfully!')
    return redirect('add_category')


# ============================================================================
# REVIEW VIEWS
# ============================================================================

@login_required
def write_review(request, slug):
    """Write review for product"""
    product = get_object_or_404(Product, slug=slug)

    if product.seller == request.user:
        messages.error(request, "You cannot review your own product.")
        return redirect('product_detail', slug=slug)

    if Review.objects.filter(product=product, user=request.user).exists():
        messages.error(request, "You have already reviewed this product.")
        return redirect('product_detail', slug=slug)

    if request.method == "POST":
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.product = product
            review.user = request.user
            review.save()
            messages.success(request, "Review submitted successfully!")
            return redirect('product_detail', slug=slug)
    else:
        form = ReviewForm()

    return render(request, 'write-review.html', {
        'form': form,
        'product': product
    })


# ============================================================================
# CART VIEWS
# ============================================================================

@login_required
def cart(request):
    """Shopping cart view"""
    cart, created = Cart.objects.get_or_create(user=request.user)
    items = cart.items.all()

    subtotal = sum(item.product.price * item.quantity for item in items)
    service_fee = subtotal * Decimal("0.025")
    total = subtotal + service_fee

    for item in items:
        item.subtotal = item.product.price * item.quantity

    context = {
        "cart": cart,
        "items": items,
        "subtotal": subtotal,
        "service_fee": service_fee,
        "total": total,
        "item_count": sum(item.quantity for item in items)
    }

    return render(request, "cart.html", context)


@login_required
def add_to_cart(request, product_id):
    # Handle AJAX request
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        if not request.user.is_authenticated:
            return JsonResponse({"success": False, "message": "Login required"}, status=401)

        product = get_object_or_404(Product, id=product_id)
        cart, _ = Cart.objects.get_or_create(user=request.user)

        try:
            data = json.loads(request.body or "{}")
            quantity = int(data.get("quantity", 1))
        except (json.JSONDecodeError, ValueError):
            quantity = 1

        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product
        )

        if quantity < 1:
            quantity = 1

        if product.quantity <= 0:
            return JsonResponse({
                "success": False,
                "message": "This product is currently out of stock."
            }, status=400)

        if not created:
            if cart_item.quantity + quantity > product.quantity:
                return JsonResponse({
                    "success": False,
                    "message": f"Only {product.quantity - cart_item.quantity} item{'s' if product.quantity - cart_item.quantity != 1 else ''} left in stock."
                }, status=400)
            cart_item.quantity += quantity
        else:
            if quantity > product.quantity:
                return JsonResponse({
                    "success": False,
                    "message": f"Only {product.quantity} item{'s' if product.quantity != 1 else ''} available." 
                }, status=400)
            cart_item.quantity = quantity

        cart_item.save()

        cart_count = sum(item.quantity for item in cart.items.all())

        return JsonResponse({
            "success": True,
            "cart_count": cart_count
        })

    # Handle normal form request
    product = get_object_or_404(Product, id=product_id)
    cart, _ = Cart.objects.get_or_create(user=request.user)

    if product.quantity <= 0:
        messages.error(request, "This product is currently out of stock.")
        return redirect('product_detail', slug=product.slug)

    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product
    )

    if not created:
        if cart_item.quantity < product.quantity:
            cart_item.quantity += 1
        else:
            messages.error(request, "You have reached the maximum available stock for this product.")
            return redirect('product_detail', slug=product.slug)
    else:
        cart_item.quantity = 1

    cart_item.save()

    return redirect("cart")

@login_required
def buy_now(request, product_id):
    """Add a product to the cart and go straight to checkout."""
    product = get_object_or_404(Product, id=product_id)
    quantity = int(request.GET.get("quantity", 1) or 1)

    if quantity < 1:
        quantity = 1

    if product.quantity <= 0:
        messages.error(request, "This product is currently out of stock.")
        return redirect("product_detail", slug=product.slug)

    if quantity > product.quantity:
        messages.error(request, f"Only {product.quantity} item{'s' if product.quantity != 1 else ''} available.")
        return redirect("product_detail", slug=product.slug)

    cart, _ = Cart.objects.get_or_create(user=request.user)
    cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)

    if not created:
        if cart_item.quantity + quantity > product.quantity:
            messages.error(request, f"Only {product.quantity - cart_item.quantity} item{'s' if product.quantity - cart_item.quantity != 1 else ''} left in stock.")
            return redirect("product_detail", slug=product.slug)
        cart_item.quantity += quantity
    else:
        cart_item.quantity = quantity

    cart_item.save()
    return redirect("checkout")


@login_required
def increase_quantity(request, item_id):
    """Increase cart item quantity"""
    item = get_object_or_404(CartItem, id=item_id)
    item.quantity += 1
    item.save()
    return redirect("cart")


@login_required
def decrease_quantity(request, item_id):
    """Decrease cart item quantity"""
    item = get_object_or_404(CartItem, id=item_id)
    if item.quantity > 1:
        item.quantity -= 1
        item.save()
    return redirect("cart")


@login_required
def remove_from_cart(request, item_id):
    """Remove item from cart"""
    item = get_object_or_404(CartItem, id=item_id)
    item.delete()
    return redirect("cart")


# ============================================================================
# CHECKOUT & PAYMENT VIEWS
# ============================================================================

@login_required
def checkout(request):
    cart = Cart.objects.get(user=request.user)
    items = cart.items.all()

    subtotal = sum(item.product.price * item.quantity for item in items)
    service_fee = subtotal * Decimal("0.025")
    total = subtotal + service_fee

    if request.method == "POST":
        # Store shipping information in the session so the secure payment flow can access it.
        request.session["shipping_info"] = {
            "fullname": request.POST.get("fullname", ""),
            "email": request.POST.get("email", ""),
            "phone": request.POST.get("phone", ""),
            "address": request.POST.get("address", ""),
            "city": request.POST.get("city", ""),
            "state": request.POST.get("state", ""),
            "country": request.POST.get("country", ""),
            "zip": request.POST.get("zip", ""),
            "instructions": request.POST.get("instructions", ""),
        }
        request.session.modified = True

        return redirect("payment_options")

    context = {
        "items": items,
        "subtotal": subtotal,
        "service_fee": service_fee,
        "total": total,
        "item_count": sum(item.quantity for item in items)
    }

    return render(request, "checkout.html", context)


@login_required
def payment_options(request):
    """Payment options view with WhatsApp integration"""
    cart = Cart.objects.get(user=request.user)
    items = cart.items.all()
    total = sum(item.product.price * item.quantity for item in items)

    seller_groups = defaultdict(list)
    for item in items:
        seller = item.product.seller
        seller_groups[seller].append(item)

    whatsapp_links = []
    for seller, seller_items in seller_groups.items():
        message = f"Hello {seller.username}, I want to order:\n\n"
        for item in seller_items:
            message += f"{item.product.name} x{item.quantity}\n"
        message += f"\nBuyer: {request.user.username}"
        encoded_message = urllib.parse.quote(message)
        whatsapp_url = f"https://wa.me/{seller.phone}?text={encoded_message}"
        whatsapp_links.append({"seller": seller, "link": whatsapp_url})

    context = {
        "items": items,
        "total": total,
        "buyer_name": request.user.username,
        "whatsapp_links": whatsapp_links
    }

    return render(request, "payment-options.html", context)


@login_required
def secure_payment(request):
    """Secure payment page"""
    cart = Cart.objects.get(user=request.user)
    items = cart.items.all()

    shipping_info = request.session.get("shipping_info")
    if not shipping_info:
        return redirect("checkout")

    subtotal = sum(item.product.price * item.quantity for item in items)
    fee_percentage = Decimal("0.025")
    fee = subtotal * fee_percentage
    total = subtotal + fee
    
    create_activity(
        title="Payment Initiated",
        description=f"{request.user.username} started a payment",
        activity_type="payment",
        amount=total
    )
    context = {
        "items": items,
        "subtotal": subtotal,
        "fee": fee,
        "total": total,
        "shipping_info": shipping_info,
    }

    return render(request, "secure-payment.html", context)


@login_required
def process_payment(request):
    if request.method == "POST":

        cart, created = Cart.objects.get_or_create(user=request.user)
        items = list(cart.items.all())  # ✅ CONVERT TO LIST before deleting

        if not items:
            return redirect("cart")

        shipping_info = request.session.get("shipping_info")
        if not shipping_info:
            shipping_info = {
                "fullname": request.POST.get("fullname", ""),
                "email": request.POST.get("email", ""),
                "phone": request.POST.get("phone", ""),
                "address": request.POST.get("address", ""),
                "city": request.POST.get("city", ""),
                "state": request.POST.get("state", ""),
                "country": request.POST.get("country", ""),
                "zip": request.POST.get("zip", ""),
                "instructions": request.POST.get("instructions", ""),
            }
            if not shipping_info["address"]:
                return redirect("checkout")

        subtotal = sum(item.product.price * item.quantity for item in items)
        fee = subtotal * Decimal("0.025")
        total = subtotal + fee

        shipping_address_text = ", ".join(filter(None, [
            shipping_info.get("address"),
            shipping_info.get("city"),
            shipping_info.get("state"),
            shipping_info.get("country"),
            shipping_info.get("zip"),
        ]))

        order = Order.objects.create(
            buyer=request.user,
            order_type="escrow",
            total_amount=total,
            shipping_address=shipping_address_text,
        )

        ShippingAddress.objects.create(
            order=order,
            full_name=shipping_info.get("fullname", ""),
            email=shipping_info.get("email", ""),
            phone=shipping_info.get("phone", ""),
            address=shipping_info.get("address", ""),
            city=shipping_info.get("city", ""),
            state=shipping_info.get("state", ""),
            country=shipping_info.get("country", ""),
            zip_code=shipping_info.get("zip", ""),
            instructions=shipping_info.get("instructions", ""),
        )

        for item in items:
            OrderItem.objects.create(
                order=order,
                seller=item.product.seller,
                product=item.product,
                quantity=item.quantity,
                price=item.product.price,
            )

        # NOTIFY SELLERS BEFORE DELETING CART
        for item in items:
            seller = item.product.seller
            create_notification(
                user=seller,
                title="New Order Received",
                description=f"You have a new order #{order.id} for {item.product.name} x{item.quantity}.",
                notification_type='order',
                priority='high',
                reference_id=f"ORD-{order.id}",
                reference_url=f"/seller/order/{order.id}/"
            )

        cart.items.all().delete()
        request.session.pop("shipping_info", None)

        return redirect("payment_success")

    return redirect("secure_payment")


def payment_success_view(request):
    """Payment success page"""
    return render(request, 'payment_success.html')


def payment_failure_view(request):
    """Payment failure page"""
    return render(request, 'payment_failure.html')


# ============================================================================
# ORDER MANAGEMENT VIEWS
# ============================================================================

@login_required
def seller_orders(request):
    """View seller orders"""
    filter_type = request.GET.get("filter", "all")
    items = OrderItem.objects.filter(product__seller=request.user).select_related("order", "product", "order__buyer")
    items = items.filter(seller_deleted=False)
    # FILTERING
    if filter_type == "pending":
        items = items.filter(status="Pending")
    elif filter_type == "processing":
        items = items.filter(status="Processing")
    elif filter_type == "shipped":
        items = items.filter(status="Shipped")
    elif filter_type == "completed":
        items = items.filter(status="Completed")
    elif filter_type == "escrow":
        items = items.filter(order__order_type="escrow")
    elif filter_type == "whatsapp":
        items = items.filter(order__order_type="whatsapp")

    # GROUPING
    grouped_orders = defaultdict(list)
    for item in items:
        grouped_orders[item.order].append(item)

    final_orders = []
    for order, order_items in grouped_orders.items():
        gallery = []
        for item in order_items[:3]:
            gallery.append({
                "image": item.product.front_image.url if item.product.front_image else "/static/default.png",
                "name": item.product.name
            })
        extra_count = len(order_items) - 3 if len(order_items) > 3 else 0

        final_orders.append({
            "order": order,
            "items": order_items,
            "status": order_items[0].status,
            "total": sum([i.subtotal() for i in order_items]),
            "gallery": gallery,
            "extra_count": extra_count,
            "main_title": order_items[0].product.name,
            "subtitle": ", ".join([i.product.name for i in order_items[1:3]]),
            "count": len(order_items)
        })

    counts = {
        "all": items.count(),
        "escrow": items.filter(order__order_type="escrow").count(),
        "whatsapp": items.filter(order__order_type="whatsapp").count(),
        "pending": items.filter(status="Pending").count(),
        "processing": items.filter(status="Processing").count(),
        "shipped": items.filter(status="Shipped").count(),
        "completed": items.filter(status="Completed").count(),
    }

    return render(request, "seller/seller-orders.html", {
        "grouped_orders": final_orders,
        "counts": counts,
        "active_filter": filter_type
    })


@login_required
def seller_order_detail(request, order_id):
    """View order details for seller"""
    order_item = get_object_or_404(OrderItem, id=order_id, seller=request.user)
    order = order_item.order
    order_items = OrderItem.objects.filter(order=order, seller=request.user).select_related("product")

    subtotal = sum([item.subtotal() for item in order_items])
    service_fee = subtotal * Decimal("0.025")
    total = subtotal + service_fee

    if request.method == "POST":
        new_status = request.POST.get("status")
        allowed_status = ["Pending", "Processing", "Shipped", "Delivered", "Cancelled"]

        if new_status in allowed_status:
            items = OrderItem.objects.filter(order=order, seller=request.user)
            for item in items:
                item.status = new_status
                if new_status == "Delivered":
                    item.delivered_at = timezone.now()  # ADD THIS LINE
                    item.start_delivery_timer()
                item.save()
                
                #  NOTIFY BUYER
                create_notification(
                    user=order.buyer,
                    title=f"Order Status Updated: {new_status}",
                    description=f"Your order #{order.id} for {item.product.name} is now {new_status}.",
                    notification_type='order',
                    priority='medium' if new_status in ['Processing', 'Shipped'] else 'high',
                    reference_id=f"ORD-{order.id}",
                    reference_url=f"/buyer/order/{order.id}/{request.user.id}/"
                )

        return redirect("seller_order_detail", order_id=order_item.id)

    shipping_address = order.shipping_address
    if not shipping_address:
        try:
            shipping = order.shipping
            shipping_address = f"{shipping.address}, {shipping.city}, {shipping.state}, {shipping.country}"
        except ShippingAddress.DoesNotExist:
            shipping_address = None

    return render(request, "seller-order-detail.html", {
        "order": order,
        "order_item": order_item,
        "order_items": order_items,
        "subtotal": subtotal,
        "service_fee": service_fee,
        "total": total,
        "shipping_address": shipping_address,
    })


@login_required
def seller_delete_order(request, item_id):
    item = get_object_or_404(OrderItem, id=item_id, seller=request.user)

    if request.method == "POST":
        if item.status in ["Cancelled", "Completed"]:
            item.seller_deleted = True
            item.save()

    return redirect("seller_order")

@login_required
def transactions(request):
    """View seller transactions with dispute status awareness."""

    orders = OrderItem.objects.filter(
        seller=request.user
    ).select_related("order", "product", "order__buyer").prefetch_related('disputes')

    # Check for disputes on each order item
    for item in orders:
        active_dispute = item.disputes.filter(
            status__in=['awaiting_seller', 'under_review', 'more_info', 
                       'awaiting_buyer', 'return_required', 'return_shipped', 
                       'return_received']
        ).first()
        item.active_dispute = active_dispute
        
        resolved_dispute = item.disputes.filter(
            status__in=['resolved_buyer', 'resolved_seller', 'resolved_mutual', 'cancelled']
        ).first()
        item.resolved_dispute = resolved_dispute

    # FILTERING
    ongoing_orders = orders.exclude(status__in=["Completed", "Cancelled"])
    completed_orders = orders.filter(status="Completed")
    cancelled_orders = orders.filter(status="Cancelled")
    pending_orders = orders.filter(status="Pending")
    disputed_orders = orders.filter(disputes__status__in=[
        'awaiting_seller', 'under_review', 'more_info', 'awaiting_buyer',
        'return_required', 'return_shipped', 'return_received'
    ]).distinct()

    #  CALCULATIONS
    total_sales = sum(o.subtotal() for o in completed_orders)
    ongoing_amount = sum(o.subtotal() for o in ongoing_orders)
    pending_amount = sum(o.subtotal() for o in pending_orders)
    cancelled_amount = sum(o.subtotal() for o in cancelled_orders)
    disputed_amount = sum(o.subtotal() for o in disputed_orders)

    context = {
        "orders": orders,
        "ongoing_count": ongoing_orders.count(),
        "ongoing_amount": ongoing_amount,
        "pending_amount": pending_amount,
        "total_sales": total_sales,
        "cancelled_amount": cancelled_amount,
        "disputed_count": disputed_orders.count(),
        "disputed_amount": disputed_amount,
    }

    return render(request, "seller/escrow.html", context)

@login_required
def buyer_order(request):
    """View buyer orders"""
    orders = Order.objects.filter(buyer=request.user).prefetch_related("items__product", "items__seller")
   
    grouped_orders = []

    for order in orders:
        seller_groups = defaultdict(list)

        for item in order.items.all():
            if item.seller_id:
                seller_groups[item.seller].append(item)

        for seller, items in seller_groups.items():
            if not items:
                continue

            gallery = [
                {
                    "image": item.product.front_image.url if item.product.front_image else "/static/default.png",
                    "name": item.product.name
                }
                for item in items[:3]
            ]

            extra_count = max(len(items) - 3, 0)

            if any(item.status == "Delivered" for item in items):
                display_status = "Delivered"
            elif all(item.status == "Completed" for item in items):
                display_status = "Completed"
            else:
                display_status = "Processing"

            # =========================
            # CHECK FOR ANY DISPUTE (active OR resolved)
            # =========================
            active_dispute = None
            resolved_dispute = None
            
            for item in items:
                # Check for active dispute
                dispute = Dispute.objects.filter(
                    order_item=item,
                    buyer=request.user
                ).exclude(
                    status__in=["resolved_buyer", "resolved_seller", "resolved_mutual", "cancelled"]
                ).first()
                if dispute:
                    active_dispute = dispute
                    break
            
            # If no active dispute, check for resolved one
            if not active_dispute:
                for item in items:
                    resolved = Dispute.objects.filter(
                        order_item=item,
                        buyer=request.user,
                        status__in=["resolved_buyer", "resolved_seller", "resolved_mutual"]
                    ).first()
                    if resolved:
                        resolved_dispute = resolved
                        break

            has_active_dispute = active_dispute is not None
            has_resolved_dispute = resolved_dispute is not None
            
            # Determine effective status for display
            if has_active_dispute:
                timer_state = "paused"      # Dispute in progress
                dispute_obj = active_dispute
            elif has_resolved_dispute:
                timer_state = "resolved"    # Admin decided
                dispute_obj = resolved_dispute
            else:
                timer_state = "running"     # Normal countdown
                dispute_obj = None

            grouped_orders.append({
                "order": order,
                "seller": seller,
                "items": items,
                "status": items[0].status,
                "display_status": display_status,
                "total_amount": sum(i.subtotal() for i in items),
                "gallery": gallery,
                "extra_count": extra_count,
                "main_title": items[0].product.name,
                "subtitle_titles": ", ".join([i.product.name for i in items[1:3]]),
                "item_count": len(items),
                # Dispute info
                "active_dispute": active_dispute,
                "resolved_dispute": resolved_dispute,
                "has_active_dispute": has_active_dispute,
                "has_resolved_dispute": has_resolved_dispute,
                "timer_state": timer_state,
                "dispute_obj": dispute_obj,
            })

    return render(request, "buyer/my-orders.html", {
        "grouped_orders": grouped_orders
    })

@login_required
def buyer_order_detail(request, order_id, seller_id):

    order = get_object_or_404(Order, id=order_id, buyer=request.user)

    order_items = OrderItem.objects.filter(
        order=order, seller_id=seller_id
    ).select_related("product", "seller")

    if not order_items.exists():
        return render(request, "buyer_order_detail.html", {"error": "Order not found"})

    # =========================
    # CHECK DISPUTES FOR EACH ITEM
    # =========================
    item_disputes = {}
    active_dispute = None
    has_active_dispute = False
    resolved_dispute = None
    has_resolved_dispute = False

    for item in order_items:
        # Get the MOST RECENT dispute for this item (not just first)
        dispute = Dispute.objects.filter(
            order_item=item,
            buyer=request.user
        ).order_by('-created_at').first()  # Get latest
        
        item_disputes[item.id] = dispute
        
        if dispute:
            if dispute.status in ['resolved_buyer', 'resolved_seller', 'resolved_mutual', 'cancelled']:
                # This is a RESOLVED dispute
                resolved_dispute = dispute
                has_resolved_dispute = True
            else:
                # This is an ACTIVE dispute
                active_dispute = dispute
                has_active_dispute = True

    # =========================
    # STATUS LOGIC
    # =========================
    if all(item.status == "Completed" for item in order_items):
        status = "Completed"
    elif any(item.status == "Cancelled" for item in order_items):
        status = "Cancelled"
    elif any(item.status == "Delivered" for item in order_items):
        status = "Delivered"
    elif any(item.status == "Shipped" for item in order_items):
        status = "Shipped"
    elif any(item.status == "Processing" for item in order_items):
        status = "Processing"
    else:
        status = "Pending"

    # =========================
    # CAN DISPUTE? 
    # Only if: Delivered + NO active dispute + NO resolved dispute
    # (One dispute per order item max)
    # =========================
    can_dispute = (
        status == "Delivered" 
        and not has_active_dispute 
        and not has_resolved_dispute
    )

    # =========================
    # CAN CONFIRM DELIVERY?
    # Only if Delivered + NO active dispute
    # =========================
    can_confirm = (status == "Delivered" and not has_active_dispute)

    # =========================
    # SHOW DISPUTE BANNER?
    # Only show if there's an ACTIVE dispute
    # Resolved disputes show a different banner
    # =========================
    show_dispute_banner = has_active_dispute
    show_resolution_banner = has_resolved_dispute

    # =========================
    # CALCULATIONS
    # =========================
    subtotal = sum(item.subtotal() for item in order_items)
    shipping = Decimal("0.00")
    tax = subtotal * Decimal("0.025")
    total = subtotal + shipping + tax

    buyer = order.buyer
    buyer_name = getattr(buyer, "username", "")
    buyer_email = getattr(buyer, "email", "")
    buyer_phone = getattr(buyer, "phone", "")

    address = None
    if hasattr(order, "shipping"):
        address = f"{order.shipping.address}, {order.shipping.city}, {order.shipping.state}, {order.shipping.country}"
    elif getattr(order, "shipping_address", None):
        address = order.shipping_address

    first_item = order_items.first()
    expires_at = first_item.expires_at if first_item else None

    return render(request, "buyer_order_detail.html", {
        "order": order,
        "order_items": order_items,
        "item_disputes": item_disputes,
        "active_dispute": active_dispute,
        "has_active_dispute": has_active_dispute,
        "resolved_dispute": resolved_dispute,
        "has_resolved_dispute": has_resolved_dispute,
        "show_dispute_banner": show_dispute_banner,
        "show_resolution_banner": show_resolution_banner,
        "can_dispute": can_dispute,
        "can_confirm": can_confirm,
        "subtotal": subtotal,
        "shipping": shipping,
        "tax": tax,
        "total": total,
        "status": status,
        "buyer_name": buyer_name,
        "buyer_email": buyer_email,
        "buyer_phone": buyer_phone,
        "shipping_address": address,
        "expires_at": expires_at,
        "seller_id": seller_id,
    })

def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, buyer=request.user)

    if request.method == "POST":
        OrderItem.objects.filter(order=order).update(status="Cancelled")

    return redirect("buyer_order")


@login_required
def confirm_delivery(request, order_id, seller_id):
    """Confirm delivery of order"""
    if request.method == "POST":
        items = OrderItem.objects.filter(
            order_id=order_id,
            product__seller_id=seller_id,
            order__buyer=request.user,
            status="Delivered"
        )
        updated_count = items.update(status="Completed")
        
        order = Order.objects.get(id=order_id, buyer=request.user)
        if not order.items.exclude(status="Completed").exists():
            order.status = "Completed"
            order.save()
        
        create_activity(
            title="Order Completed",
            description=f"Order #{order_id} completed by {request.user.username}",
            activity_type="order"
        )
        
        # NOTIFY SELLER
        create_notification(
            user=User.objects.get(id=seller_id),
            title="Order Completed",
            description=f"Order #{order_id} has been confirmed as delivered. Funds released to your wallet.",
            notification_type='payment',
            priority='high',
            reference_id=f"ORD-{order_id}",
            reference_url=f"/seller/order/{order_id}/"
        )
        
    return redirect("buyer_order")


# ============================================================================
# WISHLIST VIEWS
# ============================================================================

@login_required
def wishlist_view(request):
    """View wishlist"""
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related("product", "product__seller")
    return render(request, "buyer/wishlist.html", {"wishlist_items": wishlist_items})


@login_required
def add_to_wishlist(request, product_id):
    """Add product to wishlist"""
    product = get_object_or_404(Product, id=product_id)
    Wishlist.objects.get_or_create(user=request.user, product=product)
    return redirect(request.META.get("HTTP_REFERER", "wishlist"))


@login_required
def toggle_wishlist(request, product_id):
    """Toggle wishlist status for a product"""
    product = get_object_or_404(Product, id=product_id)
    wishlist_item, created = Wishlist.objects.get_or_create(user=request.user, product=product)

    if created:
        added = True
    else:
        wishlist_item.delete()
        added = False

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"success": True, "added": added})

    return redirect(request.META.get("HTTP_REFERER", "wishlist"))


@login_required
def remove_from_wishlist(request, product_id):
    """Remove product from wishlist"""
    Wishlist.objects.filter(user=request.user, product_id=product_id).delete()
    return redirect(request.META.get("HTTP_REFERER", "wishlist"))


# ============================================================================
# USER SETTINGS & PROFILE
# ============================================================================

@login_required
def user_settings(request):
    """User settings and profile management"""
    user = request.user
    seller_profile = None
    bank = None

    if user.role in ['seller', 'both']:
        seller_profile, created = SellerProfile.objects.get_or_create(
            user=user,
            defaults={'store_name': f"{user.username}'s Store"}
        )
        bank, created = BankDetails.objects.get_or_create(seller=seller_profile)

    if request.method == "POST":
        # UPDATE PROFILE
        if "save_profile" in request.POST:
            user.first_name = request.POST.get("first_name")
            user.last_name = request.POST.get("last_name")
            user.email = request.POST.get("email")
            user.phone = request.POST.get("full_phone")
            user.bio = request.POST.get("bio")
            if request.FILES.get("profile_image"):
                user.profile_image = request.FILES.get("profile_image")
            user.save()
            messages.success(request, "Profile updated.")
            return redirect("user_settings")

        # BECOME SELLER
        if "become_seller" in request.POST:
            if user.role == "buyer":
                user.role = "both"
            elif user.role == "seller":
                user.role = "seller"
            user.save()
            SellerProfile.objects.get_or_create(
                user=user,
                defaults={'store_name': request.POST.get("store_name", f"{user.username}'s Store")}
            )
            messages.success(request, "You are now a seller.")
            return redirect("user_settings")

        # UPDATE BANK
        if "update_bank" in request.POST and bank:
            bank.account_holder_name = request.POST.get("account_holder_name")
            bank.bank_name = request.POST.get("bank_name")
            bank.account_number = request.POST.get("account_number")
            bank.routing_number = request.POST.get("routing_number")
            bank.account_type = request.POST.get("account_type")
            bank.save()
            messages.success(request, "Bank details updated.")
            return redirect("user_settings")

        # BECOME BUYER
        if "become_buyer" in request.POST:
            if user.role == "seller":
                user.role = "both"
            user.save()
            messages.success(request, "You are now also a buyer.")
            return redirect("user_settings")

        # REMOVE BUYER ROLE
        if "remove_buyer" in request.POST:
            if user.role == "both":
                user.role = "seller"
                user.save()
                messages.success(request, "Buyer role removed.")
            return redirect("user_settings")

        # REMOVE SELLER ROLE
        if "remove_seller" in request.POST:
            if user.role == "both":
                user.role = "buyer"
                user.save()
                messages.success(request, "Seller role removed.")
            return redirect("user_settings")

    return render(request, "seller/seller-settings.html", {
        "seller_profile": seller_profile,
        "bank": bank,
    })


# ============================================================================
# SELLER CUSTOMERS VIEW
# ============================================================================

@login_required
def seller_customers(request):
    """View seller's customers"""
    seller = request.user
    search_query = request.GET.get("q", "").lower()

    items = OrderItem.objects.filter(product__seller=seller).select_related("order__buyer")
    customers_data = {}

    for item in items:
        buyer = item.order.buyer

        if search_query:
            if search_query not in buyer.username.lower() and search_query not in buyer.email.lower():
                continue

        if buyer not in customers_data:
            customers_data[buyer] = {
                "id": buyer.id,
                "username": buyer.username,
                "email": buyer.email,
                "image": buyer.profile_image.url if getattr(buyer, "profile_image", None) else "/static/images/default-user.png",
                "orders": set(),
                "total_spent": 0,
                "last_order": item.order.created_at
            }

        customers_data[buyer]["orders"].add(item.order.id)
        customers_data[buyer]["total_spent"] += item.subtotal()

        if item.order.created_at > customers_data[buyer]["last_order"]:
            customers_data[buyer]["last_order"] = item.order.created_at

    customers = []
    for data in customers_data.values():
       customers.append({
            "id": data["id"],
            "username": data["username"],
            "email": data["email"],
            "image": data["image"],
            "order_count": len(data["orders"]),
            "total_spent": float(data["total_spent"]),
            "last_order": data["last_order"].strftime("%b %d, %Y"),
        })

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"customers": customers})

    return render(request, "seller/customers.html", {"customers": customers})


# ============================================================================
# SUPER ADMIN VIEWS
# ============================================================================

@super_admin_required
def super_admin(request):
    total_users = User.objects.count()
    total_sellers = User.objects.filter(role__in=['seller', 'both']).count()
    total_buyers = User.objects.filter(role__in=['buyer', 'both']).count()
    total_products = Product.objects.count()

    total_escrow_orders = OrderItem.objects.filter(order__order_type='escrow').count()
    total_whatsapp_orders = OrderItem.objects.filter(order__order_type='whatsapp').count()
    total_completed = OrderItem.objects.filter(status='Completed').count()
    total_pending = OrderItem.objects.filter(status='Pending').count()

    total_disputes = Dispute.objects.count()
    total_reports = ContactMessage.objects.filter(message_type='report').count()
    total_messages = ContactMessage.objects.filter(message_type='contact').count()

    total_orders = Order.objects.count()
    completed_sales_total = OrderItem.objects.filter(status='Completed').aggregate(
        total=Sum(F('price') * F('quantity'))
    )['total'] or 0
    platform_revenue = completed_sales_total * Decimal('0.05')
    total_revenue = completed_sales_total

    recent_activities = Activity.objects.all().order_by('-created_at')[:6]

    sellers = User.objects.filter(role__in=['seller', 'both'])
    seller_data = []

    for seller in sellers:
        buyers_count = OrderItem.objects.filter(
            seller=seller
        ).values('order__buyer').distinct().count()
        orders_count = OrderItem.objects.filter(seller=seller).count()
        revenue = OrderItem.objects.filter(
            seller=seller,
            status='Completed'
        ).aggregate(total=Sum(F('price') * F('quantity')))['total'] or 0

        seller_data.append({
            'seller': seller,
            'buyers_count': buyers_count,
            'orders_count': orders_count,
            'revenue': revenue,
        })

    random.shuffle(seller_data)
    seller_data = seller_data[:4]

    context = {
        'total_users': total_users,
        'total_sellers': total_sellers,
        'total_buyers': total_buyers,
        'total_products': total_products,
        'total_escrow_orders': total_escrow_orders,
        'total_whatsapp_orders': total_whatsapp_orders,
        'total_completed': total_completed,
        'total_pending': total_pending,
        'total_disputes': total_disputes,
        'total_reports': total_reports,
        'total_messages': total_messages,
        'platform_revenue': platform_revenue,
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'recent_activities': recent_activities,
        'seller_data': seller_data,
    }
    return render(request, 'super_admin/dashboard.html', context)

@super_admin_required
def admin_base(request):
    """Admin base template"""
    return render(request, 'super_admin/admin_base.html')

@login_required
@super_admin_required
def admin_settings(request):
    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        old_password = request.POST.get("old_password")
        new_password = request.POST.get("new_password")

        user = request.user

        # Update name & email
        if name:
            user.username = name
        if email:
            user.email = email

        # `Change password
        if old_password and new_password:
            if user.check_password(old_password):
                user.set_password(new_password)
                update_session_auth_hash(request, user)  # keep logged in
                messages.success(request, "Password updated successfully")
            else:
                messages.error(request, "Old password is incorrect")
                return redirect('admin_settings')  # your url name

        user.save()
        messages.success(request, "Settings updated successfully")

        return redirect('admin_settings')

    return render(request, 'super_admin/admin_settings.html')



@super_admin_required
def market(request):
    #     get only sellers + both
    sellers = User.objects.filter(role__in=['seller', 'both'])

    seller_data = []

    for seller in sellers:
        # total buyers (people who bought from this seller)
        buyers_count = OrderItem.objects.filter(
            seller=seller
        ).values('order__buyer').distinct().count()

        # total orders
        orders_count = OrderItem.objects.filter(seller=seller).count()

        # total revenue
        revenue = OrderItem.objects.filter(
            seller=seller
        ).aggregate(total=Sum('price'))['total'] or 0

        seller_data.append({
            'seller': seller,
            'buyers_count': buyers_count,
            'orders_count': orders_count,
            'revenue': revenue,
        })

    return render(request, 'super_admin/markets.html', {
        'seller_data': seller_data
    })


@super_admin_required
def admin_listings(request):
    products = Product.objects.select_related('seller', 'category').order_by('-created_at')
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', 'all')
    category_id = request.GET.get('category', 'all')

    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(seller__username__icontains=search_query)
        )

    if status_filter == 'active':
        products = products.filter(quantity__gt=0)
    elif status_filter == 'out_of_stock':
        products = products.filter(quantity=0)

    if category_id != 'all':
        products = products.filter(category_id=category_id)

    categories = Category.objects.all().order_by('name')
    paginator = Paginator(products, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'super_admin/listings.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'category_id': category_id,
        'categories': categories,
    })


@super_admin_required
def admin_transactions(request):
    transactions = OrderItem.objects.select_related('order', 'product', 'seller', 'order__buyer').order_by('-id')
    search_query = request.GET.get('search', '')
    type_filter = request.GET.get('type', 'all')
    status_filter = request.GET.get('status', 'all')

    if search_query:
        transactions = transactions.filter(
            Q(product__name__icontains=search_query) |
            Q(seller__username__icontains=search_query) |
            Q(order__buyer__username__icontains=search_query) |
            Q(order__id__icontains=search_query)
        )

    if type_filter != 'all':
        transactions = transactions.filter(order__order_type=type_filter)

    if status_filter != 'all':
        transactions = transactions.filter(status=status_filter)

    paginator = Paginator(transactions, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'super_admin/transactions.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'type_filter': type_filter,
        'status_filter': status_filter,
    })


@super_admin_required
def admin_reports(request):
    reports = ContactMessage.objects.filter(message_type='report').order_by('-created_at')
    status_filter = request.GET.get('status', 'all')
    search_query = request.GET.get('search', '')

    if status_filter != 'all':
        reports = reports.filter(status=status_filter)

    if search_query:
        reports = reports.filter(
            Q(full_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(subject__icontains=search_query)
        )

    paginator = Paginator(reports, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'super_admin/reports.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
    })




@super_admin_required
def user_detail(request, user_id):
    user = get_object_or_404(User, id=user_id)
    product_count = Product.objects.filter(seller=user).count()
    order_count = OrderItem.objects.filter(Q(order__buyer=user) | Q(seller=user)).count()
    total_sales = OrderItem.objects.filter(seller=user, status='Completed').aggregate(total=Sum(F('price') * F('quantity')))['total'] or 0
    total_orders = OrderItem.objects.filter(seller=user).count() if user.role in ['seller', 'both'] else OrderItem.objects.filter(order__buyer=user).count()
    total_products = Product.objects.filter(seller=user).count()
    return render(request, 'super_admin/user_detail.html', {
        'user_obj': user,
        'product_count': product_count,
        'order_count': order_count,
        'total_sales': total_sales,
        'total_products': total_products,
        'total_orders': total_orders,
    })


@super_admin_required
def admin_product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    reviews = product.reviews.select_related('user').order_by('-created_at')
    return render(request, 'super_admin/product_detail.html', {
        'product': product,
        'reviews': reviews,
    })


@super_admin_required
def admin_delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.delete()
    messages.success(request, "Product deleted successfully.")
    return redirect('admin_listings')


@super_admin_required
def admin_transaction_detail(request, order_item_id):
    order_item = get_object_or_404(OrderItem, id=order_item_id)
    order = order_item.order
    timeline = ['Pending', 'Processing', 'Shipped', 'Delivered', 'Completed']
    return render(request, 'super_admin/transaction_detail.html', {
        'order_item': order_item,
        'order': order,
        'timeline': timeline,
    })


@super_admin_required
def report_detail(request, report_id):
    report = get_object_or_404(ContactMessage, id=report_id, message_type='report')
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'resolve':
            report.status = 'resolved'
            report.save()
        elif action == 'dismiss':
            report.status = 'read'
            report.save()
        return redirect('report_detail', report_id=report.id)
    return render(request, 'super_admin/report_detail.html', {
        'report': report,
    })





@super_admin_required
def toggle_user_status(request, user_id):
    user = get_object_or_404(User, id=user_id)

    # toggle active/inactive
    user.is_active = not user.is_active
    user.save()

    messages.success(request, f"{user.username} status updated.")
    return redirect('markets')  # your users page name

@super_admin_required
def delete_user(request, user_id):
    user = get_object_or_404(User, id=user_id)

    user.delete()

    messages.success(request, "User deleted successfully.")
    return redirect('markets')


@super_admin_required
def activity_log(request):
    activities = Activity.objects.all().order_by('-created_at')

    filter_type = request.GET.get('type')

    if filter_type and filter_type != 'all':
        activities = activities.filter(activity_type=filter_type)

    return render(request, 'super_admin/activity.html', {
        'activities': activities
    })

@login_required
@super_admin_required
def delete_activity(request, activity_id):
    if request.method == "POST":
        activity = get_object_or_404(Activity, id=activity_id)
        activity.delete()
    return redirect('activity')  # redirect back to activity page




@login_required
@super_admin_required
def admin_notifications(request):
    notifications_list = ContactMessage.objects.all().order_by('-created_at')

    paginator = Paginator(notifications_list, 5)  # 5 per page
    page_number = request.GET.get('page')
    notifications = paginator.get_page(page_number)

    return render(request, 'super_admin/notifications.html', {
        'notifications': notifications
    })
    
@login_required
@super_admin_required
def view_message(request, id):
    message = get_object_or_404(ContactMessage, id=id)

    # mark as read
    if message.status == "unread":
        message.status = "read"
        message.save()

    return render(request, "super_admin/view_notification.html", {
        "message": message
    })


from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
@super_admin_required
def reply_message(request, message_id):
    if request.method == "POST":
        reply_to = request.POST.get("reply_to")
        subject = request.POST.get("subject")
        message_content = request.POST.get("message")
        mark_resolved = request.POST.get("mark_as_resolved") == "on"

        contact = get_object_or_404(ContactMessage, id=message_id)

        html_content = render_to_string("emails/reply_notification.html", {
            "user_name": contact.full_name,
            "original_subject": contact.subject,
            "reply_message": message_content,
            "sender_email": settings.DEFAULT_FROM_EMAIL,
            "site_name": "Your AssetHub",
        })

        email = EmailMultiAlternatives(
            subject=subject,
            body=message_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[reply_to],
        )
        email.attach_alternative(html_content, "text/html")

        try:
            email.send(fail_silently=False)
        except smtplib.SMTPException as exc:
            contact.status = "unread"
            contact.save(update_fields=["status"])
            messages.error(request, f"Email failed to send: {exc}")
            return render(request, "super_admin/view_notification.html", {"message": contact})

        if mark_resolved:
            contact.status = 'resolved'
            contact.save(update_fields=["status"])

        messages.success(request, "Reply sent successfully!")
        return redirect("view_message", id=contact.id)

@login_required
@super_admin_required
def users(request):
    users = User.objects.all().order_by('-date_joined')

    # GET FILTER VALUES
    search_query = request.GET.get('search', '')
    role_filter = request.GET.get('role', 'all')
    status_filter = request.GET.get('status', 'all')

    # SEARCH (name, email, id)
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(id__icontains=search_query)
        )

    # ROLE FILTER
    if role_filter != 'all':
        users = users.filter(role=role_filter)

    # STATUS FILTER
    if status_filter == 'active':
        users = users.filter(is_active=True)
    elif status_filter == 'inactive':
        users = users.filter(is_active=False)

    # (You don't have suspended field yet, so ignore or add later)

    user_data = []

    for user in users:
        purchases_count = OrderItem.objects.filter(order__buyer=user).count()
        orders_count = user.order_set.count()

        if user.role in ['seller', 'both']:
            revenue = OrderItem.objects.filter(seller=user).aggregate(total=Sum('price'))['total'] or 0
        else:
            revenue = 0

        user_data.append({
            'user': user,
            'purchases_count': purchases_count,
            'orders_count': orders_count,
            'revenue': revenue,
        })

    # PAGINATION
    paginator = Paginator(user_data, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'super_admin/users.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'role_filter': role_filter,
        'status_filter': status_filter,
    })

from django.shortcuts import redirect, get_object_or_404
@super_admin_required
def toggle_user_status(request, user_id):
    user = get_object_or_404(User, id=user_id)

    user.is_active = not user.is_active
    user.save()

    return redirect(request.META.get('HTTP_REFERER', 'users'))
@super_admin_required
def delete_user(request, user_id):
    user = get_object_or_404(User, id=user_id)

    user.delete()

    return redirect(request.META.get('HTTP_REFERER', 'users'))

from django.template.loader import render_to_string
from django.http import JsonResponse
from django.db.models import Q, Sum

def ajax_search_users(request):
    search_query = request.GET.get('search', '')
    role_filter = request.GET.get('role', 'all')
    status_filter = request.GET.get('status', 'all')

    users = User.objects.all()

    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(id__icontains=search_query)
        )

    if role_filter != 'all':
        users = users.filter(role=role_filter)

    if status_filter == 'active':
        users = users.filter(is_active=True)
    elif status_filter == 'inactive':
        users = users.filter(is_active=False)

    user_data = []

    for user in users[:20]:  # limit for performance
        purchases_count = OrderItem.objects.filter(order__buyer=user).count()
        orders_count = user.order_set.count()

        if user.role in ['seller', 'both']:
            revenue = OrderItem.objects.filter(seller=user).aggregate(total=Sum('price'))['total'] or 0
        else:
            revenue = 0

        user_data.append({
            'user': user,
            'purchases_count': purchases_count,
            'orders_count': orders_count,
            'revenue': revenue,
        })

    html = render_to_string('super_admin/partials/user_rows.html', {
        'user_data': user_data
    })

    return JsonResponse({'html': html})

# ============================================================================
# MISCELLANEOUS VIEWS
# ============================================================================

def base(request):
    """Base template view"""
    user = request.user
    orders = OrderItem.objects.filter(product__seller=user)

    # AUTO CHECK EXPIRED ORDERS
    for order in orders:
        order.check_expiry()


    total_orders = orders.count()


    return render(request, "seller/basee.html", {
        "total_orders": total_orders,
    })


@login_required
def seller_settings(request):
    """Seller settings view"""
    return render(request, 'seller/seller-settings.html')





# ============================================================================
# NOTIFICATION VIEWS (BUYER / SELLER)
# ============================================================================

@login_required
def user_notifications(request):
    """View notifications for the logged-in buyer/seller"""
    notifications = Notification.objects.filter(user=request.user)

    # Filters
    filter_type = request.GET.get('type', 'all')
    filter_status = request.GET.get('status', 'all')
    search_query = request.GET.get('q', '')

    if filter_type != 'all':
        notifications = notifications.filter(notification_type=filter_type)
    
    if filter_status == 'unread':
        notifications = notifications.filter(is_read=False)
    elif filter_status == 'read':
        notifications = notifications.filter(is_read=True)

    if search_query:
        notifications = notifications.filter(
            Q(title__icontains=search_query) | 
            Q(description__icontains=search_query)
        )

    # Stats for summary cards
    total_notifications = Notification.objects.filter(user=request.user).count()
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    
    # Breakdown by type (for sidebar)
    type_counts = {
        'disputes': notifications.filter(notification_type='dispute', is_read=False).count(),
        'orders': notifications.filter(notification_type='order', is_read=False).count(),
        'payments': notifications.filter(notification_type='payment', is_read=False).count(),
        'shipping': notifications.filter(notification_type='shipping', is_read=False).count(),
        'security': notifications.filter(notification_type='security', is_read=False).count(),
        'escrow': notifications.filter(notification_type='escrow', is_read=False).count(),
    }

    # Pagination
    paginator = Paginator(notifications, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'notifications': page_obj,
        'page_obj': page_obj,
        'total_notifications': total_notifications,
        'unread_count': unread_count,
        'type_counts': type_counts,
        'filter_type': filter_type,
        'filter_status': filter_status,
        'search_query': search_query,
    }

    return render(request, 'notifications.html', context)


@login_required
def mark_notification_read(request, notification_id):
    """Mark a single notification as read"""
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.mark_as_read()
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'unread_count': request.user.notifications.filter(is_read=False).count()})
    
    return redirect('user_notifications')


@login_required
def mark_all_notifications_read(request):
    """Mark all notifications as read"""
    Notification.objects.filter(user=request.user, is_read=False).update(
        is_read=True, 
        read_at=timezone.now()
    )
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    
    return redirect('user_notifications')


@login_required
def delete_notification(request, notification_id):
    """Delete a notification"""
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.delete()
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    
    return redirect('user_notifications')


@login_required
def notification_count(request):
    """AJAX endpoint to get unread notification count (for navbar badge)"""
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({'count': count})



# ============================================================================
# DISPUTE VIEWS
# ============================================================================

def _send_dispute_email(subject, message, recipient_list, html_message=None):
    """Helper to send dispute-related emails"""
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_list,
            html_message=html_message,
            fail_silently=True
        )
    except Exception:
        pass  # Fail silently - notification system is primary


def _get_dispute_context(dispute):
    """Build common context for dispute templates"""
    from django.utils import timezone
    return {
        'dispute': dispute,
        'order_item': dispute.order_item,
        'order': dispute.order_item.order,
        'product': dispute.order_item.product,
        'buyer': dispute.buyer,
        'seller': dispute.seller,
        'escrow_amount': dispute.get_escrow_amount(),
        'evidences': dispute.evidences.all(),
        'messages': dispute.messages.all(),
    }


@login_required
def submit_dispute(request, order_item_id):
    """Buyer submits a new dispute claim"""
    order_item = get_object_or_404(
        OrderItem.objects.select_related('order', 'product', 'seller'),
        id=order_item_id,
        order__buyer=request.user
    )

    # Prevent duplicate active disputes
    existing = Dispute.objects.filter(
        order_item=order_item,
        buyer=request.user
    ).exclude(status__in=['resolved_buyer', 'resolved_seller', 'resolved_mutual', 'cancelled']).first()

    if existing:
        messages.error(request, f"You already have an active dispute for this order: #{existing.dispute_id}")
        return redirect('buyer_dispute_detail', dispute_id=existing.id)

    # Only allow disputes for delivered or shipped items
    if order_item.status not in ['Delivered', 'Shipped']:
        messages.error(request, "You can only dispute orders that have been shipped or delivered.")
        return redirect('buyer_order_detail', order_id=order_item.order.id, seller_id=order_item.seller.id)

    # Calculate days remaining (example: 7 days from delivery)
    if order_item.delivered_at:
        from datetime import datetime
        inspection_end = order_item.delivered_at + timedelta(days=7)
        days_remaining = max(0, (inspection_end - timezone.now()).days)
    else:
        days_remaining = 7  # default

    if request.method == 'POST':
        form = DisputeForm(request.POST, request.FILES)
        
        # Check declaration checkbox manually
        # declaration = request.POST.get('declaration')
        # if not declaration:
        #     messages.error(request, "You must confirm the declaration to proceed.")
        #     return render(request, 'buyer/submit-dispute.html', {
        #         'form': form,
        #         'order_item': order_item,
        #         'order': order_item.order,
        #         'product': order_item.product,
        #         'seller': order_item.seller,
        #         'escrow_amount': order_item.subtotal(),
        #         'days_remaining': days_remaining,
        #     })

        if form.is_valid():
            with transaction.atomic():
                dispute = form.save(commit=False)
                dispute.order_item = order_item
                dispute.buyer = request.user
                dispute.seller = order_item.seller
                dispute.status = 'awaiting_seller'
                dispute.buyer_declaration = True
                dispute.seller_deadline = timezone.now() + timedelta(days=5)
                dispute.save()

                # Handle file uploads
                files = request.FILES.getlist('evidence_files')
                for f in files[:10]:  # Max 10 files
                    file_ext = os.path.splitext(f.name)[1].lower()
                    file_type = 'other'
                    if file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                        file_type = 'image'
                    elif file_ext in ['.mp4', '.mov', '.avi', '.webm']:
                        file_type = 'video'
                    elif file_ext == '.pdf':
                        file_type = 'pdf'
                    elif file_ext in ['.doc', '.docx', '.txt']:
                        file_type = 'document'

                    DisputeEvidence.objects.create(
                        dispute=dispute,
                        file=f,
                        file_type=file_type,
                        uploaded_by='buyer',
                        file_name=f.name,
                        file_size=f.size
                    )

            #  EMAIL TO SELLER
            _send_dispute_email(
                subject=f"AssetHub - New Dispute Opened: #{dispute.dispute_id}",
                message=(
                    f"Hello {order_item.seller.username},\n\n"
                    f"A dispute has been opened for your order #{order_item.order.id}.\n"
                    f"Product: {order_item.product.name}\n"
                    f"Reason: {dispute.get_reason_display()}\n"
                    f"Please respond within 5 days.\n\n"
                    f"View dispute: /seller/dispute/{dispute.id}/respond/"
                ),
                recipient_list=[order_item.seller.email],
            )

            #  EMAIL TO ADMIN(S)
            from django.contrib.auth import get_user_model
            User = get_user_model()
            admin_emails = list(User.objects.filter(is_superuser=True).exclude(email='').values_list('email', flat=True))
            if admin_emails:
                _send_dispute_email(
                    subject=f"AssetHub - Admin Alert: New Dispute #{dispute.dispute_id}",
                    message=(
                        f"A new dispute has been opened.\n\n"
                        f"Dispute ID: {dispute.dispute_id}\n"
                        f"Buyer: {request.user.username}\n"
                        f"Seller: {order_item.seller.username}\n"
                        f"Product: {order_item.product.name}\n"
                        f"Reason: {dispute.get_reason_display()}\n\n"
                        f"Review at: /super/admin/dispute/{dispute.id}/"
                    ),
                    recipient_list=admin_emails,
                )

            #    NOTIFICATIONS
            create_notification(
                user=request.user,
                title="Dispute Submitted Successfully",
                description=f"Your dispute #{dispute.dispute_id} has been opened. The seller has 5 days to respond.",
                notification_type='dispute',
                priority='high',
                reference_id=dispute.dispute_id,
                reference_url=f"/buyer/dispute/{dispute.id}/"
            )

            create_notification(
                user=order_item.seller,
                title="New Dispute Opened",
                description=f"A dispute has been opened for Order #{order_item.order.id} - {order_item.product.name}. Please respond within 5 days.",
                notification_type='dispute',
                priority='high',
                reference_id=dispute.dispute_id,
                reference_url=f"/seller/dispute/{dispute.id}/respond/"
            )

            # Notify all admins
            admins = User.objects.filter(is_superuser=True)
            for admin in admins:
                create_notification(
                    user=admin,
                    title="New Dispute Requires Review",
                    description=f"Dispute #{dispute.dispute_id} opened by {request.user.username} against {order_item.seller.username}.",
                    notification_type='dispute',
                    priority='high',
                    reference_id=dispute.dispute_id,
                    reference_url=f"/super/admin/dispute/{dispute.id}/"
                )

            # Activity log
            create_activity(
                title="Dispute Opened",
                description=f"Buyer {request.user.username} opened dispute #{dispute.dispute_id} for order #{order_item.order.id}",
                activity_type='alert',
                amount=dispute.get_escrow_amount()
            )

            messages.success(request, f"Dispute #{dispute.dispute_id} submitted successfully!")
            return redirect('buyer_dispute_detail', dispute_id=dispute.id)

    else:
        form = DisputeForm()

    context = {
        'form': form,
        'order_item': order_item,
        'order': order_item.order,
        'product': order_item.product,
        'seller': order_item.seller,
        'escrow_amount': order_item.subtotal(),  # 🔥 ADDED
        'days_remaining': days_remaining,         # 🔥 ADDED
    }
    return render(request, 'buyer/submit-dispute.html', context)


@login_required
def buyer_disputes(request):
    """List all disputes for the buyer"""
    disputes = Dispute.objects.filter(buyer=request.user).select_related(
        'order_item__product', 'order_item__order', 'seller'
    ).order_by('-created_at')

    # Count stats
    active_statuses = ['awaiting_seller', 'under_review', 'more_info', 'awaiting_buyer', 'return_required', 'return_shipped', 'return_received']
    resolved_statuses = ['resolved_buyer', 'resolved_seller', 'resolved_mutual']
    
    active_count = disputes.filter(status__in=active_statuses).count()
    resolved_count = disputes.filter(status__in=resolved_statuses).count()
    
    # Total escrow amount in active disputes
    total_escrow = sum(
        d.get_escrow_amount() for d in disputes.filter(status__in=active_statuses)
    )

    return render(request, 'buyer/buyer_disputes.html', {
        'disputes': disputes,
        'active_count': active_count,
        'resolved_count': resolved_count,
        'total_escrow': total_escrow,
    })

@login_required
def buyer_dispute_detail(request, dispute_id):
    """Buyer views dispute details"""
    dispute = get_object_or_404(
        Dispute.objects.select_related('order_item__product', 'order_item__order', 'seller'),
        id=dispute_id,
        buyer=request.user
    )

    order_item = dispute.order_item
    order = order_item.order
    product = order_item.product

    reply_form = BuyerReplyForm()
    return_tracking_form = ReturnTrackingForm()

    context = {
        'dispute': dispute,
        'order_item': order_item,
        'order': order,
        'product': product,
        'seller': dispute.seller,
        'reply_form': reply_form,
        'return_tracking_form': return_tracking_form,
        'buyer_evidence': dispute.evidences.filter(uploaded_by='buyer'),
        'seller_evidence': dispute.evidences.filter(uploaded_by='seller'),
        'escrow_amount': dispute.get_escrow_amount(),
    }

    return render(request, 'buyer/dispute-detail.html', context)

@login_required
def buyer_dispute_reply(request, dispute_id):
    """Buyer replies to seller response"""
    dispute = get_object_or_404(
        Dispute,
        id=dispute_id,
        buyer=request.user,
        status__in=['awaiting_buyer', 'under_review', 'more_info']
    )

    if request.method == 'POST':
        form = BuyerReplyForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                DisputeMessage.objects.create(
                    dispute=dispute,
                    sender='buyer',
                    sender_user=request.user,
                    message=form.cleaned_data['message']
                )
                dispute.status = 'under_review'
                dispute.save()

            create_notification(
                user=dispute.seller,
                title="Buyer Replied to Dispute",
                description=f"The buyer has added a reply to dispute #{dispute.dispute_id}.",
                notification_type='dispute',
                priority='medium',
                reference_id=dispute.dispute_id,
                reference_url=f"/seller/dispute/{dispute.id}/"
            )

            messages.success(request, "Your reply has been submitted.")
            return redirect('buyer_dispute_detail', dispute_id=dispute.id)

    return redirect('buyer_dispute_detail', dispute_id=dispute.id)


@login_required
def submit_return_tracking(request, dispute_id):
    """Buyer submits return shipping information"""
    dispute = get_object_or_404(
        Dispute,
        id=dispute_id,
        buyer=request.user,
        status='return_required'
    )

    if request.method == 'POST':
        form = ReturnTrackingForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                dispute.return_courier = form.cleaned_data['return_courier']
                dispute.return_tracking = form.cleaned_data['return_tracking']
                dispute.return_shipped_at = timezone.now()
                dispute.status = 'return_shipped'
                dispute.save()

            create_notification(
                user=dispute.seller,
                title="Return Item Shipped",
                description=f"The buyer has shipped the return item for dispute #{dispute.dispute_id}. Courier: {dispute.return_courier}, Tracking: {dispute.return_tracking}",
                notification_type='dispute',
                priority='high',
                reference_id=dispute.dispute_id,
                reference_url=f"/seller/dispute/{dispute.id}/"
            )

            create_notification(
                user=request.user,
                title="Return Tracking Submitted",
                description=f"Your return tracking for dispute #{dispute.dispute_id} has been submitted. The seller will confirm receipt.",
                notification_type='dispute',
                priority='medium',
                reference_id=dispute.dispute_id,
                reference_url=f"/buyer/dispute/{dispute.id}/"
            )

            messages.success(request, "Return tracking information submitted.")
            return redirect('buyer_dispute_detail', dispute_id=dispute.id)

    return redirect('buyer_dispute_detail', dispute_id=dispute.id)


@login_required
def seller_disputes(request):
    """List all disputes for the seller"""
    disputes = Dispute.objects.filter(seller=request.user).select_related(
        'order_item__product', 'order_item__order', 'buyer'
    ).order_by('-created_at')

    # Count stats
    awaiting_statuses = ['awaiting_seller']
    review_statuses = ['under_review', 'more_info', 'awaiting_buyer', 'return_required', 'return_shipped', 'return_received']
    resolved_statuses = ['resolved_buyer', 'resolved_seller', 'resolved_mutual', 'cancelled']
    
    awaiting_response_count = disputes.filter(status__in=awaiting_statuses).count()
    under_review_count = disputes.filter(status__in=review_statuses).count()
    resolved_count = disputes.filter(status__in=resolved_statuses).count()
    
    # Total escrow at risk (active disputes only)
    active_statuses = awaiting_statuses + review_statuses
    total_escrow_at_risk = sum(
        d.get_escrow_amount() for d in disputes.filter(status__in=active_statuses)
    )

    return render(request, 'seller/seller-disputes.html', {
        'disputes': disputes,
        'awaiting_response_count': awaiting_response_count,
        'under_review_count': under_review_count,
        'resolved_count': resolved_count,
        'total_escrow_at_risk': total_escrow_at_risk,
    })


@login_required
def seller_respond_dispute(request, dispute_id):
    """Seller responds to a dispute"""
    dispute = get_object_or_404(
        Dispute.objects.select_related('order_item__product', 'order_item__order', 'buyer'),
        id=dispute_id,
        seller=request.user,
        status='awaiting_seller'
    )

    # Calculate days remaining
    days_remaining = dispute.days_until_seller_deadline() if hasattr(dispute, 'days_until_seller_deadline') else 5

    if request.method == 'POST':
        form = DisputeResponseForm(request.POST, request.FILES)
        if form.is_valid():
            with transaction.atomic():
                dispute.seller_response = form.cleaned_data['seller_response']
                dispute.seller_courier = form.cleaned_data.get('seller_courier') or ''
                dispute.seller_tracking = form.cleaned_data.get('seller_tracking') or ''
                dispute.seller_ship_date = form.cleaned_data.get('seller_ship_date')
                dispute.seller_delivery_confirm = form.cleaned_data.get('seller_delivery_confirm') or ''
                dispute.seller_declaration = True
                dispute.seller_responded_at = timezone.now()
                dispute.status = 'under_review'
                dispute.save()

                # Handle seller evidence uploads
                files = request.FILES.getlist('evidence_files')
                for f in files[:10]:
                    file_ext = os.path.splitext(f.name)[1].lower()
                    file_type = 'other'
                    if file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                        file_type = 'image'
                    elif file_ext in ['.mp4', '.mov', '.avi', '.webm']:
                        file_type = 'video'
                    elif file_ext == '.pdf':
                        file_type = 'pdf'
                    elif file_ext in ['.doc', '.docx', '.txt']:
                        file_type = 'document'

                    DisputeEvidence.objects.create(
                        dispute=dispute,
                        file=f,
                        file_type=file_type,
                        uploaded_by='seller',
                        file_name=f.name,
                        file_size=f.size
                    )

             # EMAIL TO BUYER
            _send_dispute_email(
                subject=f"AssetHub - Seller Responded: #{dispute.dispute_id}",
                message=(
                    f"Hello {dispute.buyer.username},\n\n"
                    f"The seller has responded to your dispute #{dispute.dispute_id}.\n"
                    f"Product: {dispute.order_item.product.name}\n"
                    f"You can now review their response on your dispute page.\n\n"
                    f"View dispute: /buyer/dispute/{dispute.id}/"
                ),
                recipient_list=[dispute.buyer.email],
            )

            # EMAIL TO ADMIN(S) — THIS WAS MISSING!
            from django.contrib.auth import get_user_model
            User = get_user_model()
            admin_emails = list(User.objects.filter(is_superuser=True).exclude(email='').values_list('email', flat=True))
            if admin_emails:
                _send_dispute_email(
                    subject=f"AssetHub - Admin Alert: Seller Responded to Dispute #{dispute.dispute_id}",
                    message=(
                        f"A seller has responded to a dispute.\n\n"
                        f"Dispute ID: {dispute.dispute_id}\n"
                        f"Buyer: {dispute.buyer.username}\n"
                        f"Seller: {request.user.username}\n"
                        f"Product: {dispute.order_item.product.name}\n"
                        f"Status: Under Review\n\n"
                        f"Review at: /super/admin/dispute/{dispute.id}/"
                    ),
                    recipient_list=admin_emails,
                )

            # NOTIFICATIONS (your existing code)
            create_notification(
                user=dispute.buyer,
                title="Seller Responded to Your Dispute",
                description=f"The seller has responded to dispute #{dispute.dispute_id}.",
                notification_type='dispute',
                priority='high',
                reference_id=dispute.dispute_id,
                reference_url=f"/buyer/dispute/{dispute.id}/"
            )

            create_notification(
                user=request.user,
                title="Response Submitted",
                description=f"Your response to dispute #{dispute.dispute_id} has been submitted.",
                notification_type='dispute',
                priority='medium',
                reference_id=dispute.dispute_id,
                reference_url=f"/seller/dispute/{dispute.id}/"
            )

            # Notify admins (in-app)
            admins = User.objects.filter(is_superuser=True)
            for admin in admins:
                create_notification(
                    user=admin,
                    title="Seller Responded - Review Needed",
                    description=f"Seller {request.user.username} responded to dispute #{dispute.dispute_id}.",
                    notification_type='dispute',
                    priority='high',
                    reference_id=dispute.dispute_id,
                    reference_url=f"/super/admin/dispute/{dispute.id}/"
                )

            messages.success(request, "Your response has been submitted successfully!")
            return redirect('seller_dispute_detail', dispute_id=dispute.id)

    else:
        form = DisputeResponseForm()

    context = {
        'dispute': dispute,
        'order_item': dispute.order_item,
        'order': dispute.order_item.order,
        'buyer': dispute.buyer,
        'form': form,
        'buyer_evidence': dispute.evidences.filter(uploaded_by='buyer'),
        'escrow_amount': dispute.get_escrow_amount(),
        'days_remaining': days_remaining,
    }

    return render(request, 'seller/respond-dispute.html', context)

@login_required
def seller_dispute_detail(request, dispute_id):
    """Seller views dispute details"""
    dispute = get_object_or_404(
        Dispute.objects.select_related('order_item__product', 'order_item__order', 'buyer'),
        id=dispute_id,
        seller=request.user
    )

    context = {
        'dispute': dispute,
        'order_item': dispute.order_item,
        'order': dispute.order_item.order,
        'product': dispute.order_item.product,
        'buyer': dispute.buyer,
        'buyer_evidence': dispute.evidences.filter(uploaded_by='buyer'),
        'seller_evidence': dispute.evidences.filter(uploaded_by='seller'),
        'escrow_amount': dispute.get_escrow_amount(),
    }

    return render(request, 'seller/dispute-detail.html', context)                                                                                                                                   

@login_required
def seller_confirm_return_received(request, dispute_id):
    """Seller confirms they received the returned item"""
    dispute = get_object_or_404(
        Dispute,
        id=dispute_id,
        seller=request.user,
        status='return_shipped'
    )
    # CRITICAL: Prevent if already decided
    if dispute.return_received_at or dispute.return_not_received_at:
        messages.error(request, "You have already responded to this return.")
        return redirect('seller_dispute_detail', dispute_id=dispute.id)
    
    if request.method == 'POST':
        with transaction.atomic():
            dispute.return_received_at = timezone.now()
            dispute.status = 'return_received'
            dispute.save()

        # Notify buyer
        create_notification(
            user=dispute.buyer,
            title="Return Item Confirmed Received",
            description=f"The seller has confirmed receipt of your returned item for dispute #{dispute.dispute_id}. Awaiting admin final decision.",
            notification_type='dispute',
            priority='high',
            reference_id=dispute.dispute_id,
            reference_url=f"/buyer/dispute/{dispute.id}/"
        )

        # Notify admins
        from django.contrib.auth import get_user_model
        User = get_user_model()
        admins = User.objects.filter(is_superuser=True)
        for admin in admins:
            create_notification(
                user=admin,
                title="Return Received — Final Review",
                description=f"Seller confirmed return receipt for dispute #{dispute.dispute_id}. Ready for final decision.",
                notification_type='dispute',
                priority='high',
                reference_id=dispute.dispute_id,
                reference_url=f"/super/admin/dispute/{dispute.id}/"
            )

        # Email admins
        admin_emails = list(User.objects.filter(is_superuser=True).exclude(email='').values_list('email', flat=True))
        if admin_emails:
            try:
                send_mail(
                    subject=f"AssetHub — Return Received for Dispute #{dispute.dispute_id}",
                    message=f"""Admin Alert,

                    The seller ({dispute.seller.username}) has confirmed they received the returned item for dispute #{dispute.dispute_id}.

                    BUYER: {dispute.buyer.username}
                    SELLER: {dispute.seller.username}
                    PRODUCT: {dispute.order_item.product.name}
                    TRACKING: {dispute.return_courier} — {dispute.return_tracking}
                    RECEIVED: {dispute.return_received_at.strftime('%B %d, %Y at %I:%M %p')}

                    STATUS: Ready for final admin decision.

                    AssetHub Dispute Resolution Team
                """,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=admin_emails,
                    fail_silently=True
                )
            except Exception:
                pass

        messages.success(request, "Return receipt confirmed. Admin will issue final decision.")
        return redirect('seller_dispute_detail', dispute_id=dispute.id)

    return redirect('seller_dispute_detail', dispute_id=dispute.id)

@login_required
def seller_confirm_return_not_received(request, dispute_id):
    """Seller confirms they have NOT received the returned item"""
    dispute = get_object_or_404(
        Dispute,
        id=dispute_id,
        seller=request.user,
        status='return_shipped'
    )
    # CRITICAL: Prevent if already decided
    if dispute.return_received_at or dispute.return_not_received_at:
        messages.error(request, "You have already responded to this return.")
        return redirect('seller_dispute_detail', dispute_id=dispute.id)
    
    if request.method == 'POST':
        with transaction.atomic():
            dispute.return_not_received_at = timezone.now()
            dispute.return_not_received_confirmed = True
            dispute.save()

        # Notify buyer that seller claims item not received
        create_notification(
            user=dispute.buyer,
            title="Seller Claims Return Not Received",
            description=f"The seller claims they have not received the return item for dispute #{dispute.dispute_id}. Admin will investigate.",
            notification_type='dispute',
            priority='high',
            reference_id=dispute.dispute_id,
            reference_url=f"/buyer/dispute/{dispute.id}/"
        )

        # Notify admins — URGENT, needs investigation
        from django.contrib.auth import get_user_model
        User = get_user_model()
        admins = User.objects.filter(is_superuser=True)
        for admin in admins:
            create_notification(
                user=admin,
                title="URGENT: Return Not Received — Investigation Needed",
                description=f"Seller {request.user.username} claims they did NOT receive the return for dispute #{dispute.dispute_id}. Tracking: {dispute.return_tracking}",
                notification_type='dispute',
                priority='high',
                reference_id=dispute.dispute_id,
                reference_url=f"/super/admin/dispute/{dispute.id}/"
            )

        # Email admins
        admin_emails = list(User.objects.filter(is_superuser=True).exclude(email='').values_list('email', flat=True))
        if admin_emails:
            try:
                send_mail(
                    subject=f"URGENT — AssetHub: Return Not Received for Dispute #{dispute.dispute_id}",
                    message=f"""Admin Alert,

                    The seller ({dispute.seller.username}) has confirmed they have NOT received the returned item for dispute #{dispute.dispute_id}.

                    BUYER: {dispute.buyer.username}
                    SELLER: {dispute.seller.username}
                    PRODUCT: {dispute.order_item.product.name}
                    TRACKING: {dispute.return_courier} — {dispute.return_tracking}
                    SHIPPED: {dispute.return_shipped_at.strftime('%B %d, %Y at %I:%M %p')}

                    SELLER CLAIMS: Item not received at return address.

                    ACTION REQUIRED: Please investigate this dispute immediately.

                    AssetHub Dispute Resolution Team
                    """,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=admin_emails,
                    fail_silently=True
                )
            except Exception:
                pass

        messages.warning(request, "Admin has been notified that you have not received the return. They will investigate and contact you shortly.")
        return redirect('seller_dispute_detail', dispute_id=dispute.id)

    return redirect('seller_dispute_detail', dispute_id=dispute.id)



@login_required
@super_admin_required
def admin_disputes_list(request):
    """Admin list view for all disputes with full filtering, search, and stats."""
    
    disputes = Dispute.objects.select_related(
        'order_item__product', 'order_item__order', 'buyer', 'seller'
    ).order_by('-created_at')
    
    # --- FILTERS ---
    status_filter = request.GET.get('status', 'all')
    priority_filter = request.GET.get('priority', 'all')
    search_query = request.GET.get('search', '').strip()
    
    if status_filter != 'all':
        disputes = disputes.filter(status=status_filter)
    
    # Note: Your Dispute model doesn't have a priority field yet.
    # When you add it, uncomment the line below.
    if priority_filter != 'all':
        # disputes = disputes.filter(priority=priority_filter)
        pass
    
    if search_query:
        disputes = disputes.filter(
            Q(dispute_id__icontains=search_query) |
            Q(order_item__order__id__icontains=search_query) |
            Q(buyer__username__icontains=search_query) |
            Q(buyer__email__icontains=search_query) |
            Q(seller__username__icontains=search_query) |
            Q(seller__email__icontains=search_query) |
            Q(order_item__product__name__icontains=search_query) |
            Q(reason__icontains=search_query)
        )
    
    # --- STATS (computed from ALL disputes, not filtered) ---
    all_disputes = Dispute.objects.all()
    
    total_disputes = all_disputes.count()
    
    open_statuses = ['awaiting_seller', 'awaiting_buyer', 'under_review', 'more_info']
    open_count = all_disputes.filter(status__in=open_statuses).count()
    
    waiting_seller_count = all_disputes.filter(status='awaiting_seller').count()
    waiting_admin_count = all_disputes.filter(status__in=['under_review', 'more_info', 'return_received']).count()
    
    resolved_buyer_count = all_disputes.filter(status='resolved_buyer').count()
    resolved_seller_count = all_disputes.filter(status='resolved_seller').count()
    
    partial_count = all_disputes.filter(status='resolved_mutual').count()
    
    closed_statuses = ['resolved_buyer', 'resolved_seller', 'resolved_mutual', 'cancelled']
    closed_count = all_disputes.filter(status__in=closed_statuses).count()
    
    # --- PAGINATION ---
    paginator = Paginator(disputes, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'super_admin/admin_disputes.html', {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'priority_filter': priority_filter,
        'search_query': search_query,
        # Stats
        'total_disputes': total_disputes,
        'open_count': open_count,
        'waiting_seller_count': waiting_seller_count,
        'waiting_admin_count': waiting_admin_count,
        'resolved_buyer_count': resolved_buyer_count,
        'resolved_seller_count': resolved_seller_count,
        'partial_count': partial_count,
        'closed_count': closed_count,
    })  

@login_required
@super_admin_required
def admin_dispute_detail(request, dispute_id):
    """Admin views full dispute details and makes decisions"""
    dispute = get_object_or_404(
        Dispute.objects.select_related(
            'order_item__product', 
            'order_item__order', 
            'order_item__order__buyer',
            'buyer', 
            'seller'
        ).prefetch_related('evidences', 'messages'),
        id=dispute_id
    )

    order_item = dispute.order_item
    order = order_item.order
    product = order_item.product
    buyer = dispute.buyer
    seller = dispute.seller

    # Buyer's order stats
    buyer_total_orders = OrderItem.objects.filter(order__buyer=buyer).count()
    buyer_prev_disputes = Dispute.objects.filter(buyer=buyer).exclude(id=dispute.id).count()
    # Simple buyer rating (average of their review ratings if they left any, or default)
    from django.db.models import Avg
    buyer_avg_rating = Review.objects.filter(user=buyer).aggregate(avg=Avg('rating'))['avg'] or 4.5

    # Seller's stats
    seller_total_orders = OrderItem.objects.filter(seller=seller, status='Completed').count()
    seller_prev_disputes = Dispute.objects.filter(seller=seller).exclude(id=dispute.id).count()
    seller_avg_rating = Review.objects.filter(product__seller=seller).aggregate(avg=Avg('rating'))['avg'] or 4.5

    # Evidence
    buyer_evidence = dispute.evidences.filter(uploaded_by='buyer')
    seller_evidence = dispute.evidences.filter(uploaded_by='seller')

    # Messages / timeline
    messages_list = dispute.messages.all().select_related('sender_user')

    # Days remaining calculation
    from datetime import timedelta
    if dispute.seller_deadline:
        days_remaining = max((dispute.seller_deadline - timezone.now()).days, 0)
    else:
        days_remaining = 0

    # Resolution deadline (example: 14 days from creation)
    resolution_deadline = dispute.created_at + timedelta(days=14)
    days_to_resolution = max((resolution_deadline - timezone.now()).days, 0)

    if request.method == 'POST':
        form = AdminDecisionForm(request.POST)
        if form.is_valid():
            decision = form.cleaned_data['decision']
            notes = form.cleaned_data['admin_notes']

            with transaction.atomic():
                dispute.admin_notes = notes
                dispute.admin_decision = f"Decision: {dict(AdminDecisionForm().fields['decision'].choices).get(decision)}. {notes}"
                dispute.admin_decided_at = timezone.now()
                dispute.decided_by = request.user

                if decision == 'more_info':
                    dispute.status = 'more_info'
                    dispute.save()

                    create_notification(
                        user=dispute.buyer,
                        title="More Information Requested",
                        description=f"Admin requests more information for dispute #{dispute.dispute_id}.",
                        notification_type='dispute',
                        priority='high',
                        reference_id=dispute.dispute_id,
                        reference_url=f"/buyer/dispute/{dispute.id}/"
                    )
                    create_notification(
                        user=dispute.seller,
                        title="More Information Requested",
                        description=f"Admin requests more information for dispute #{dispute.dispute_id}.",
                        notification_type='dispute',
                        priority='high',
                        reference_id=dispute.dispute_id,
                        reference_url=f"/seller/dispute/{dispute.id}/"
                    )
                    messages.info(request, "Both parties notified to provide more information.")

                elif decision == 'return_required':
                    dispute.status = 'return_required'
                    dispute.save()

                    create_notification(
                        user=dispute.buyer,
                        title="Return Required",
                        description=f"Please return the item for dispute #{dispute.dispute_id}.",
                        notification_type='dispute',
                        priority='high',
                        reference_id=dispute.dispute_id,
                        reference_url=f"/buyer/dispute/{dispute.id}/"
                    )
                    messages.success(request, "Buyer notified to return the item.")

                elif decision in ['resolved_buyer', 'resolved_seller', 'resolved_mutual']:
                    dispute.status = decision
                    dispute.resolved_at = timezone.now()
                    dispute.save()

                    amount = dispute.get_escrow_amount()

                    if decision == 'resolved_buyer':
                        if hasattr(buyer, 'wallet_balance'):
                            buyer.wallet_balance += amount
                            buyer.save()

                        create_notification(
                            user=buyer,
                            title="Dispute Resolved - You Won",
                            description=f"Dispute #{dispute.dispute_id} resolved in your favor. ${amount} refunded.",
                            notification_type='dispute',
                            priority='high',
                            reference_id=dispute.dispute_id
                        )
                        create_notification(
                            user=seller,
                            title="Dispute Resolved - Seller Lost",
                            description=f"Dispute #{dispute.dispute_id} resolved in buyer's favor.",
                            notification_type='dispute',
                            priority='high',
                            reference_id=dispute.dispute_id
                        )
                        _send_dispute_email(
                            subject=f"AssetHub - Dispute Resolved: #{dispute.dispute_id}",
                            message=f"Your dispute has been resolved in your favor. ${amount} refunded.",
                            recipient_list=[buyer.email],
                        )

                    elif decision == 'resolved_seller':
                        if hasattr(seller, 'wallet_balance'):
                            seller.wallet_balance += amount
                            seller.save()

                        order_item.status = 'Completed'
                        order_item.save()

                        create_notification(
                            user=seller,
                            title="Dispute Resolved - You Won",
                            description=f"Dispute #{dispute.dispute_id} resolved in your favor. ${amount} released.",
                            notification_type='dispute',
                            priority='high',
                            reference_id=dispute.dispute_id
                        )
                        create_notification(
                            user=buyer,
                            title="Dispute Resolved - Buyer Lost",
                            description=f"Dispute #{dispute.dispute_id} resolved in seller's favor.",
                            notification_type='dispute',
                            priority='high',
                            reference_id=dispute.dispute_id
                        )
                        _send_dispute_email(
                            subject=f"AssetHub - Dispute Resolved: #{dispute.dispute_id}",
                            message=f"The dispute has been resolved in your favor. Funds released.",
                            recipient_list=[seller.email],
                        )

                    elif decision == 'resolved_mutual':
                        create_notification(
                            user=buyer,
                            title="Dispute Resolved - Mutual Agreement",
                            description=f"Dispute #{dispute.dispute_id} resolved by mutual agreement.",
                            notification_type='dispute',
                            priority='high',
                            reference_id=dispute.dispute_id
                        )
                        create_notification(
                            user=seller,
                            title="Dispute Resolved - Mutual Agreement",
                            description=f"Dispute #{dispute.dispute_id} resolved by mutual agreement.",
                            notification_type='dispute',
                            priority='high',
                            reference_id=dispute.dispute_id
                        )

                    create_activity(
                        title=f"Dispute Resolved - {decision}",
                        description=f"Admin {request.user.username} resolved dispute #{dispute.dispute_id}",
                        activity_type='alert',
                        amount=amount
                    )
                    messages.success(request, f"Dispute #{dispute.dispute_id} resolved successfully!")

                dispute.save()
            return redirect('admin_dispute_detail', dispute_id=dispute.id)

    else:
        form = AdminDecisionForm()

    context = {
        'dispute': dispute,
        'order_item': order_item,
        'order': order,
        'product': product,
        'buyer': buyer,
        'seller': seller,
        'buyer_total_orders': buyer_total_orders,
        'buyer_prev_disputes': buyer_prev_disputes,
        'buyer_avg_rating': round(buyer_avg_rating, 1),
        'seller_total_orders': seller_total_orders,
        'seller_prev_disputes': seller_prev_disputes,
        'seller_avg_rating': round(seller_avg_rating, 1),
        'buyer_evidence': buyer_evidence,
        'seller_evidence': seller_evidence,
        'messages_list': messages_list,
        'escrow_amount': dispute.get_escrow_amount(),
        'days_remaining': days_remaining,
        'resolution_deadline': resolution_deadline,
        'days_to_resolution': days_to_resolution,
        'form': form,
    }

    return render(request, 'super_admin/dispute_detail.html', context)

@login_required
@super_admin_required
def admin_evidence_center(request, dispute_id):
    """Admin evidence center - view all evidence and request more."""
    dispute = get_object_or_404(
        Dispute.objects.select_related(
            'order_item__product', 'buyer', 'seller', 'decided_by'
        ).prefetch_related('evidences', 'messages'),
        id=dispute_id
    )
    
    buyer_evidence = dispute.evidences.filter(uploaded_by='buyer').order_by('-uploaded_at')
    seller_evidence = dispute.evidences.filter(uploaded_by='seller').order_by('-uploaded_at')
    system_messages = dispute.messages.filter(sender='admin').order_by('-created_at')
    
    context = {
        'dispute': dispute,
        'buyer': dispute.buyer,
        'seller': dispute.seller,
        'product': dispute.order_item.product,
        'buyer_evidence': buyer_evidence,
        'seller_evidence': seller_evidence,
        'system_messages': system_messages,
        'buyer_count': buyer_evidence.count(),
        'seller_count': seller_evidence.count(),
        'system_count': system_messages.count(),
        'total_evidence': buyer_evidence.count() + seller_evidence.count(),
    }
    return render(request, 'super_admin/evidence.html', context)


@login_required
@super_admin_required
def admin_request_evidence(request, dispute_id):
    """Admin requests additional evidence from a specific party — with email."""
    dispute = get_object_or_404(
        Dispute.objects.select_related('order_item__product', 'buyer', 'seller'),
        id=dispute_id
    )

    if request.method == 'POST':
        party = request.POST.get('party')
        message_text = request.POST.get('message', '').strip()
        evidence_type = request.POST.get('evidence_type', '')

        if party not in ['buyer', 'seller']:
            messages.error(request, "Invalid party specified.")
            return redirect('admin_evidence_center', dispute_id=dispute.id)

        with transaction.atomic():
            dispute.status = 'more_info'
            if party == 'buyer':
                dispute.buyer_deadline = timezone.now() + timedelta(days=3)
            else:
                dispute.seller_deadline = timezone.now() + timedelta(days=3)
            dispute.save()

            full_message = f"Additional evidence requested from {party}"
            if evidence_type:
                full_message += f" ({evidence_type})"
            full_message += f": {message_text}"

            DisputeMessage.objects.create(
                dispute=dispute,
                sender='admin',
                sender_user=request.user,
                message=full_message
            )

        target_user = dispute.buyer if party == 'buyer' else dispute.seller
        other_party = dispute.seller if party == 'buyer' else dispute.buyer
        party_label = 'Buyer' if party == 'buyer' else 'Seller'
        deadline = timezone.now() + timedelta(days=3)
        
        # === IN-APP NOTIFICATION ===
        create_notification(
            user=target_user,
            title="Additional Evidence Requested",
            description=f"Admin requests additional evidence for dispute #{dispute.dispute_id}. Deadline: 3 days.",
            notification_type='dispute',
            priority='high',
            reference_id=dispute.dispute_id,
            reference_url=f"/{'buyer' if party == 'buyer' else 'seller'}/dispute/{dispute.id}/"
        )
        
        # === EMAIL TO TARGET USER (Gmail) ===
        email_subject = f"AssetHub - Evidence Requested for Dispute #{dispute.dispute_id}"
        
        email_body_plain = f"""Hello {target_user.get_full_name() or target_user.username},

        The admin has requested additional evidence for your dispute.

        Dispute ID: {dispute.dispute_id}
        Product: {dispute.order_item.product.name}
        Order: #{dispute.order_item.order.id}

        Admin Message:
        {message_text}

        Deadline: You have 3 days to submit the requested evidence.
        Due by: {deadline.strftime('%B %d, %Y at %I:%M %p')}

        Please log in to your dashboard and upload the required evidence as soon as possible.

        ---
        AssetHub Dispute Resolution Team
        """
        
        email_body_html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; color: #333;">
            <div style="background: #1a1a2e; padding: 24px; text-align: center;">
                <h2 style="color: #fff; margin: 0;">AssetHub</h2>
                <p style="color: #aaa; margin: 8px 0 0 0; font-size: 14px;">Dispute Resolution</p>
            </div>
            <div style="padding: 32px 24px; background: #fff;">
                <h3 style="color: #1a1a2e; margin-top: 0;">Evidence Requested</h3>
                <p>Hello <strong>{target_user.get_full_name() or target_user.username}</strong>,</p>
                <p>The admin has requested additional evidence for your dispute.</p>
                
                <div style="background: #f8f9fa; border-radius: 8px; padding: 16px; margin: 20px 0;">
                    <div style="margin-bottom: 12px;">
                        <span style="color: #6b7280; font-size: 12px; text-transform: uppercase;">Dispute ID</span>
                        <div style="font-family: monospace; font-weight: 600; color: #1a1a2e;">#{dispute.dispute_id}</div>
                    </div>
                    <div style="margin-bottom: 12px;">
                        <span style="color: #6b7280; font-size: 12px; text-transform: uppercase;">Product</span>
                        <div style="font-weight: 500;">{dispute.order_item.product.name}</div>
                    </div>
                    <div>
                        <span style="color: #6b7280; font-size: 12px; text-transform: uppercase;">Order</span>
                        <div style="font-family: monospace;">#{dispute.order_item.order.id}</div>
                    </div>
                </div>
                
                <div style="background: #fffbeb; border-left: 4px solid #f59e0b; padding: 16px; margin: 20px 0;">
                    <div style="font-weight: 600; color: #92400e; margin-bottom: 8px;">Admin Message:</div>
                    <p style="margin: 0; color: #78350f;">{message_text}</p>
                </div>
                
                <div style="background: #fef2f2; border-radius: 8px; padding: 16px; text-align: center; margin: 20px 0;">
                    <div style="color: #dc2626; font-weight: 600; font-size: 14px;">
                        Deadline: 3 Days
                    </div>
                    <p style="margin: 8px 0 0 0; color: #991b1b; font-size: 13px;">
                        Please submit your evidence before {deadline.strftime('%B %d, %Y at %I:%M %p')}
                    </p>
                </div>
                
                <div style="text-align: center; margin: 28px 0;">
                    <a href="https://yourdomain.com/{'buyer' if party == 'buyer' else 'seller'}/dispute/{dispute.id}/" 
                       style="display: inline-block; background: #3b82f6; color: #fff; text-decoration: none; 
                              padding: 14px 32px; border-radius: 8px; font-weight: 600; font-size: 15px;">
                        Upload Evidence Now
                    </a>
                </div>
                
                <p style="color: #6b7280; font-size: 13px; margin-top: 24px;">
                    If you have any questions, please contact our support team.
                </p>
            </div>
            <div style="background: #f3f4f6; padding: 20px 24px; text-align: center; font-size: 12px; color: #9ca3af;">
                AssetHub Dispute Resolution Team<br>
                This is an automated message. Please do not reply directly to this email.
            </div>
        </div>
        """
        
        try:
            from django.core.mail import EmailMultiAlternatives
            email = EmailMultiAlternatives(
                subject=email_subject,
                body=email_body_plain,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[target_user.email],
            )
            email.attach_alternative(email_body_html, "text/html")
            email.send(fail_silently=False)
            email_sent = True
        except Exception as e:
            email_sent = False
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send evidence request email to {target_user.email}: {str(e)}")

        # === NOTIFY OTHER PARTY (transparency) ===
        create_notification(
            user=other_party,
            title=f"Evidence Requested from {party_label}",
            description=f"Admin requested additional evidence from the {party_label.lower()} for dispute #{dispute.dispute_id}.",
            notification_type='dispute',
            priority='medium',
            reference_id=dispute.dispute_id,
            reference_url=f"/super/admin/dispute/{dispute.id}/"
        )
        
        # === ACTIVITY LOG ===
        create_activity(
            title="Evidence Requested",
            description=f"Admin {request.user.username} requested evidence from {party_label} for dispute #{dispute.dispute_id}",
            activity_type='alert'
        )

        if email_sent:
            messages.success(request, f"Evidence request sent to {party_label} ({target_user.email}). Email delivered.")
        else:
            messages.warning(request, f"Evidence request saved, but email to {target_user.email} failed. In-app notification sent.")

        return redirect('admin_evidence_center', dispute_id=dispute.id)

    # GET request
    return render(request, 'super_admin/evidence.html', {
        'dispute': dispute,
        'buyer': dispute.buyer,
        'seller': dispute.seller,
    })

@login_required
def upload_dispute_evidence(request, dispute_id):
    """Upload additional evidence to an existing dispute — FIXED to correctly identify uploader."""
    dispute = get_object_or_404(
        Dispute.objects.select_related('order_item__product', 'buyer', 'seller'),
        id=dispute_id
    )

    # --- FIXED: Use ID comparison instead of object comparison ---
    # This avoids issues with stale/cached user objects vs fresh request.user
    if request.user.id == dispute.buyer_id:
        uploaded_by = 'buyer'
        uploader_role = 'Buyer'
    elif request.user.id == dispute.seller_id:
        uploaded_by = 'seller'
        uploader_role = 'Seller'
    else:
        messages.error(request, "You are not authorized to upload evidence for this dispute.")
        return redirect('home')

    if request.method == 'POST':
        files = request.FILES.getlist('evidence_files')
        if not files:
            messages.error(request, "Please select at least one file.")
            return redirect(request.META.get('HTTP_REFERER', 'home'))

        uploaded_count = 0
        for f in files:
            if dispute.evidences.count() >= 20:
                messages.warning(request, "Maximum file limit reached (20 files).")
                break

            file_ext = os.path.splitext(f.name)[1].lower()
            file_type = 'other'
            if file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                file_type = 'image'
            elif file_ext in ['.mp4', '.mov', '.avi', '.webm']:
                file_type = 'video'
            elif file_ext == '.pdf':
                file_type = 'pdf'
            elif file_ext in ['.doc', '.docx', '.txt']:
                file_type = 'document'

            DisputeEvidence.objects.create(
                dispute=dispute,
                file=f,
                file_type=file_type,
                uploaded_by=uploaded_by,
                file_name=f.name,
                file_size=f.size
            )
            uploaded_count += 1

        # --- FIXED: Notify the OTHER party (not the uploader) ---
        other_party = dispute.seller if uploaded_by == 'buyer' else dispute.buyer
        
        create_notification(
            user=other_party,
            title="New Evidence Uploaded",
            description=f"{uploader_role} uploaded {uploaded_count} new file(s) to dispute #{dispute.dispute_id}.",
            notification_type='dispute',
            priority='medium',
            reference_id=dispute.dispute_id,
            reference_url=f"/{'seller' if uploaded_by == 'buyer' else 'buyer'}/dispute/{dispute.id}/"
        )

        # --- Also notify admin ---
        from django.contrib.auth import get_user_model
        User = get_user_model()
        admins = User.objects.filter(is_superuser=True)
        for admin in admins:
            create_notification(
                user=admin,
                title=f"New Evidence - {uploader_role}",
                description=f"{uploader_role} {request.user.username} uploaded {uploaded_count} file(s) to dispute #{dispute.dispute_id}.",
                notification_type='dispute',
                priority='medium',
                reference_id=dispute.dispute_id,
                reference_url=f"/super/admin/dispute/{dispute.id}/evidence/"
            )

        messages.success(request, f"{uploaded_count} file(s) uploaded successfully as {uploader_role}.")

        # Redirect back to the correct dashboard
        if uploaded_by == 'buyer':
            return redirect('buyer_dispute_detail', dispute_id=dispute.id)
        else:
            return redirect('seller_dispute_detail', dispute_id=dispute.id)

    return redirect(request.META.get('HTTP_REFERER', 'home'))



@login_required
@super_admin_required
def admin_decision_center(request, dispute_id):
    """Admin decision center — review evidence, make final decision, handle escrow."""
    dispute = get_object_or_404(
        Dispute.objects.select_related(
            'order_item__product__category', 'order_item__order',
            'buyer', 'seller', 'decided_by'
        ).prefetch_related('evidences', 'messages'),
        id=dispute_id
    )
    
    # Prevent re-deciding on resolved disputes
    if dispute.is_resolved():
        messages.warning(request, f"Dispute #{dispute.dispute_id} is already resolved ({dispute.get_status_display()}).")
        return redirect('admin_dispute_detail', dispute_id=dispute.id)
    
    order_item = dispute.order_item
    order = order_item.order
    product = order_item.product
    buyer = dispute.buyer
    seller = dispute.seller
    escrow_amount = dispute.get_escrow_amount()
    
    # Evidence counts by type
    buyer_evidence = dispute.evidences.filter(uploaded_by='buyer')
    seller_evidence = dispute.evidences.filter(uploaded_by='seller')
    
    buyer_images = buyer_evidence.filter(file_type='image').count()
    buyer_videos = buyer_evidence.filter(file_type='video').count()
    buyer_docs = buyer_evidence.filter(file_type__in=['pdf', 'document']).count()
    buyer_receipts = buyer_evidence.filter(file_type='receipt').count()
    
    seller_images = seller_evidence.filter(file_type='image').count()
    seller_docs = seller_evidence.filter(file_type__in=['pdf', 'document']).count()
    
    evidence_summary = {
        'buyer': {
            'total': buyer_evidence.count(),
            'images': buyer_images,
            'videos': buyer_videos,
            'documents': buyer_docs,
            'receipts': buyer_receipts,
        },
        'seller': {
            'total': seller_evidence.count(),
            'images': seller_images,
            'courier': 1 if dispute.seller_courier else 0,
            'tracking': 1 if dispute.seller_tracking else 0,
            'documents': seller_docs,
        }
    }
    
    if request.method == 'POST':
        decision = request.POST.get('decision_type')
        refund_amount_str = request.POST.get('refund_amount', '0')
        return_required = request.POST.get('return_required', 'no')
        internal_notes = request.POST.get('internal_notes', '').strip()
        public_explanation = request.POST.get('public_explanation', '').strip()
        notify_buyer = request.POST.get('notify_buyer') == 'on'
        notify_seller = request.POST.get('notify_seller') == 'on'
        send_email = request.POST.get('send_email') == 'on'
        
        valid_decisions = ['resolved_buyer', 'resolved_seller', 'resolved_mutual', 'return_required']
        if decision not in valid_decisions:
            messages.error(request, "Invalid decision type selected.")
            return redirect('admin_decision_center', dispute_id=dispute.id)
        
        try:
            refund_amount = Decimal(refund_amount_str) if refund_amount_str else Decimal('0')
        except:
            refund_amount = Decimal('0')
        
        if refund_amount > escrow_amount:
            refund_amount = escrow_amount
        
        with transaction.atomic():
            dispute.status = decision
            dispute.admin_notes = internal_notes
            dispute.admin_decision = public_explanation
            dispute.admin_decided_at = timezone.now()
            dispute.decided_by = request.user
            
            if decision in ['resolved_buyer', 'resolved_seller', 'resolved_mutual']:
                dispute.resolved_at = timezone.now()
            
            dispute.save()
            
            # ============================================================================
            # ORDER COMPLETION LOGIC — Close the order when dispute is resolved
            # ============================================================================
            
            if decision == 'resolved_buyer':
                # Buyer wins — refund them
                if hasattr(buyer, 'wallet_balance'):
                    buyer.wallet_balance += refund_amount
                    buyer.save()
                
                # If return is required, keep order open for return flow
                if return_required == 'yes':
                    dispute.status = 'return_required'
                    dispute.buyer_deadline = timezone.now() + timedelta(days=7)
                    dispute.save()
                    # Order stays "Delivered" until return is complete
                else:
                    # No return needed — CLOSE THE ORDER IMMEDIATELY
                    order_item.status = 'Completed'
                    order_item.save()
                    
                    # Check if all items in order are completed
                    if not order.items.exclude(status='Completed').exists():
                        order.status = 'Completed'
                        order.save()
                
            elif decision == 'resolved_seller':
                # Seller wins — release funds and CLOSE ORDER
                if hasattr(seller, 'wallet_balance'):
                    seller.wallet_balance += escrow_amount
                    seller.save()
                
                # CLOSE ORDER ITEM
                order_item.status = 'Completed'
                order_item.save()
                
                # CLOSE PARENT ORDER if all items done
                if not order.items.exclude(status='Completed').exists():
                    order.status = 'Completed'
                    order.save()
                
            elif decision == 'resolved_mutual':
                # Mutual agreement — split and CLOSE ORDER
                half = escrow_amount / 2
                if hasattr(buyer, 'wallet_balance'):
                    buyer.wallet_balance += half
                    buyer.save()
                if hasattr(seller, 'wallet_balance'):
                    seller.wallet_balance += half
                    seller.save()
                
                # CLOSE ORDER ITEM
                order_item.status = 'Completed'
                order_item.save()
                
                # CLOSE PARENT ORDER if all items done
                if not order.items.exclude(status='Completed').exists():
                    order.status = 'Completed'
                    order.save()
                    
            elif decision == 'return_required':
                # Buyer needs to return item — keep order open
                dispute.buyer_deadline = timezone.now() + timedelta(days=7)
                dispute.save()
                # Order stays "Delivered" until return flow completes
        
        # === IN-APP NOTIFICATIONS ===
        if notify_buyer:
            if decision == 'resolved_buyer':
                if return_required == 'yes':
                    title = "Dispute Resolved — Return Required"
                    desc = f"You won dispute #{dispute.dispute_id}. Please return the item to receive your ${refund_amount} refund."
                else:
                    title = "Dispute Resolved — You Won"
                    desc = f"Dispute #{dispute.dispute_id} resolved in your favor. ${refund_amount} refunded to your wallet. Order closed."
            elif decision == 'resolved_seller':
                title = "Dispute Resolved — Seller Won"
                desc = f"Dispute #{dispute.dispute_id} was resolved in the seller's favor. Order closed."
            elif decision == 'resolved_mutual':
                title = "Dispute Resolved — Mutual Agreement"
                desc = f"Dispute #{dispute.dispute_id} resolved by mutual agreement. Order closed."
            elif decision == 'return_required':
                title = "Return Required"
                desc = f"Admin requires you to return the item for dispute #{dispute.dispute_id}. You have 7 days."
            else:
                title = "Dispute Updated"
                desc = f"Dispute #{dispute.dispute_id} status updated."
            
            create_notification(
                user=buyer, title=title, description=desc,
                notification_type='dispute', priority='high',
                reference_id=dispute.dispute_id,
                reference_url=f"/buyer/dispute/{dispute.id}/"
            )
        
        if notify_seller:
            if decision == 'resolved_buyer':
                title = "Dispute Resolved — Seller Lost"
                desc = f"Dispute #{dispute.dispute_id} was resolved in the buyer's favor. ${refund_amount} refunded from escrow."
                if return_required != 'yes':
                    desc += " Order closed."
            elif decision == 'resolved_seller':
                title = "Dispute Resolved — You Won"
                desc = f"Dispute #{dispute.dispute_id} resolved in your favor. ${escrow_amount} released to your wallet. Order closed."
            elif decision == 'resolved_mutual':
                title = "Dispute Resolved — Mutual Agreement"
                desc = f"Dispute #{dispute.dispute_id} resolved by mutual agreement. Order closed."
            elif decision == 'return_required':
                title = "Return Required from Buyer"
                desc = f"Admin requires the buyer to return the item for dispute #{dispute.dispute_id}."
            else:
                title = "Dispute Updated"
                desc = f"Dispute #{dispute.dispute_id} status updated."
            
            create_notification(
                user=seller, title=title, description=desc,
                notification_type='dispute', priority='high',
                reference_id=dispute.dispute_id,
                reference_url=f"/seller/dispute/{dispute.id}/"
            )
        
        # === EMAIL NOTIFICATIONS ===
        if send_email:
            _send_decision_email(dispute, buyer, seller, decision, refund_amount, 
                                 escrow_amount, public_explanation, return_required)
        
        # === ACTIVITY LOG ===
        create_activity(
            title=f"Dispute Resolved — {decision}",
            description=f"Admin {request.user.username} resolved dispute #{dispute.dispute_id}",
            activity_type='alert',
            amount=refund_amount if decision == 'resolved_buyer' else escrow_amount
        )
        
        messages.success(request, f"Decision submitted for dispute #{dispute.dispute_id}. Both parties notified.")
        return redirect('admin_dispute_detail', dispute_id=dispute.id)
    
    context = {
        'dispute': dispute,
        'order_item': order_item,
        'order': order,
        'product': product,
        'buyer': buyer,
        'seller': seller,
        'escrow_amount': escrow_amount,
        'evidence_summary': evidence_summary,
        'buyer_evidence': buyer_evidence,
        'seller_evidence': seller_evidence,
        'resolution_deadline': dispute.created_at + timedelta(days=14),
        'days_to_resolution': max((dispute.created_at + timedelta(days=14) - timezone.now()).days, 0),
    }
    return render(request, 'super_admin/decision_center.html', context)




@login_required
def buyer_wallet(request):
    """Buyer wallet view — shows balance, transactions, and refund history"""
    user = request.user
    
    # Get wallet balance
    wallet_balance = getattr(user, 'wallet_balance', Decimal('0.00'))
    
    # Get all disputes where buyer won (refunds)
    refunds = Dispute.objects.filter(
        buyer=user,
        status='resolved_buyer'
    ).select_related(
        'order_item__product', 'seller'
    ).order_by('-resolved_at')
    
    # Calculate total refunded
    total_refunded = sum(
        d.get_escrow_amount() for d in refunds
    )
    
    # Get completed orders (money spent)
    completed_orders = OrderItem.objects.filter(
        order__buyer=user,
        status='Completed'
    ).select_related('product', 'seller').order_by('-order__created_at')
    
    total_spent = sum(item.subtotal() for item in completed_orders)
    
    # Recent transactions (last 20)
    recent_transactions = []
    
    # Add refunds as credit transactions
    for refund in refunds[:10]:
        recent_transactions.append({
            'type': 'credit',
            'title': f'Refund — {refund.order_item.product.name}',
            'description': f'Dispute #{refund.dispute_id} resolved in your favor',
            'amount': refund.get_escrow_amount(),
            'date': refund.resolved_at,
            'status': 'completed',
            'icon': 'fa-undo',
            'color': '#059669',  # green
        })
    
    # Add order payments as debit transactions
    for order_item in completed_orders[:10]:
        recent_transactions.append({
            'type': 'debit',
            'title': f'Payment — {order_item.product.name}',
            'description': f'Order #{order_item.order.id}',
            'amount': order_item.subtotal(),
            'date': order_item.order.created_at,
            'status': 'completed',
            'icon': 'fa-shopping-bag',
            'color': '#dc2626',  # red
        })
    
    # Sort by date descending
    recent_transactions.sort(key=lambda x: x['date'], reverse=True)
    
    # Stats
    stats = {
        'total_refunded': total_refunded,
        'total_spent': total_spent,
        'net_balance': wallet_balance,
        'pending_refunds': Dispute.objects.filter(
            buyer=user,
            status__in=['return_shipped', 'return_received', 'under_review']
        ).count(),
    }
    
    return render(request, 'buyer/wallet.html', {
        'wallet_balance': wallet_balance,
        'refunds': refunds,
        'total_refunded': total_refunded,
        'total_spent': total_spent,
        'recent_transactions': recent_transactions,
        'stats': stats,
    })

def _send_decision_email(dispute, buyer, seller, decision, refund_amount, escrow_amount, explanation, return_required):
    """Helper to send decision emails to both parties."""
    
    decision_labels = {
        'resolved_buyer': 'Buyer Won — Full Refund',
        'resolved_seller': 'Seller Won — Funds Released',
        'resolved_mutual': 'Mutual Agreement',
        'return_required': 'Return Required',
    }
    
    for user in [buyer, seller]:
        subject = f"AssetHub — Dispute #{dispute.dispute_id} Decision: {decision_labels.get(decision, 'Updated')}"
        
        plain = f"""Hello {user.get_full_name() or user.username},

        A decision has been made on your dispute.

        Dispute ID: {dispute.dispute_id}
        Product: {dispute.order_item.product.name}
        Decision: {decision_labels.get(decision, decision)}

        {explanation}

        ---
        AssetHub Dispute Resolution Team
        """
                
        try:
            send_mail(
                subject=subject,
                message=plain,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True
            )
        except Exception:
            pass



@login_required
def buyer_return_tracking(request, dispute_id):
    """Buyer submits return shipping information for a dispute."""
    dispute = get_object_or_404(
        Dispute.objects.select_related(
            'order_item__product', 'order_item__order', 'seller'
        ),
        id=dispute_id,
        buyer=request.user,
        status='return_required'
    )
    
    if request.method == 'POST':
        form = ReturnTrackingForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                dispute.return_courier = form.cleaned_data['return_courier']
                dispute.return_tracking = form.cleaned_data['return_tracking']
                dispute.return_shipped_at = timezone.now()
                dispute.status = 'return_shipped'
                dispute.save()
            
            # Notify seller
            create_notification(
                user=dispute.seller,
                title="Return Item Shipped",
                description=f"Buyer shipped return for dispute #{dispute.dispute_id}. Courier: {dispute.return_courier}, Tracking: {dispute.return_tracking}",
                notification_type='dispute',
                priority='high',
                reference_id=dispute.dispute_id,
                reference_url=f"/seller/dispute/{dispute.id}/"
            )
            
            # Notify admins
            admins = User.objects.filter(is_superuser=True)
            for admin in admins:
                create_notification(
                    user=admin,
                    title="Return Shipped — Awaiting Receipt",
                    description=f"Buyer shipped return for dispute #{dispute.dispute_id}. Tracking: {dispute.return_tracking}",
                    notification_type='dispute',
                    priority='high',
                    reference_id=dispute.dispute_id,
                    reference_url=f"/super/admin/dispute/{dispute.id}/"
                )
            
            # Email seller
            try:
                send_mail(
                    subject=f"AssetHub — Return Shipped for Dispute #{dispute.dispute_id}",
                    message=f"""Hello {dispute.seller.get_full_name() or dispute.seller.username},

                    The buyer has shipped the return item for dispute #{dispute.dispute_id}.

                    Courier: {dispute.return_courier}
                    Tracking Number: {dispute.return_tracking}
                    Shipped Date: {dispute.return_shipped_at.strftime('%B %d, %Y')}

                    Please confirm receipt once the item arrives.

                    AssetHub Dispute Resolution Team
                    """,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[dispute.seller.email],
                    fail_silently=True
                )
            except Exception:
                pass
            
            messages.success(request, "Return tracking submitted successfully! Seller has been notified.")
            return redirect('buyer_dispute_detail', dispute_id=dispute.id)
    else:
        form = ReturnTrackingForm()
    
    return render(request, 'buyer/return_tracking.html', {
        'dispute': dispute,
        'product': dispute.order_item.product,
        'seller': dispute.seller,
        'form': form,
        'deadline': dispute.buyer_deadline,
        'days_remaining': max((dispute.buyer_deadline - timezone.now()).days, 0) if dispute.buyer_deadline else 7,
    })
    
    
@login_required
def buyer_decisions_list(request):
    """Buyer views all disputes with admin decisions and actions needed."""
    disputes = Dispute.objects.filter(
        buyer=request.user
    ).select_related(
        'order_item__product', 'seller', 'decided_by'
    ).order_by('-created_at')
    
    # Categorize by status
    active_disputes = disputes.filter(
        status__in=['awaiting_seller', 'under_review', 'more_info', 'return_required', 'return_shipped']
    )
    
    resolved_disputes = disputes.filter(
        status__in=['resolved_buyer', 'resolved_seller', 'resolved_mutual', 'cancelled', 'return_received']
    )
    
    # Counts for stats cards
    awaiting_action = disputes.filter(status='return_required').count()
    under_review = disputes.filter(status__in=['under_review', 'more_info']).count()
    resolved_buyer_count = disputes.filter(status='resolved_buyer').count()
    resolved_seller_count = disputes.filter(status='resolved_seller').count()
    
    return render(request, 'buyer/decisions_list.html', {
        'disputes': disputes,
        'active_disputes': active_disputes,
        'resolved_disputes': resolved_disputes,
        'awaiting_action': awaiting_action,
        'under_review': under_review,
        'resolved_buyer_count': resolved_buyer_count,
        'resolved_seller_count': resolved_seller_count,
        'total_disputes': disputes.count(),
    })



@login_required
def seller_submit_return_address(request, dispute_id):
    """Seller submits their return shipping address when buyer wins dispute."""
    dispute = get_object_or_404(
        Dispute.objects.select_related(
            'order_item__product', 'order_item__order', 'buyer'
        ),
        id=dispute_id,
        seller=request.user,
        status='return_required'
    )
    
    # Check if deadline passed
    if dispute.seller_address_deadline and timezone.now() > dispute.seller_address_deadline:
        messages.error(request, "The deadline to submit your return address has passed. The dispute has been auto-resolved in favor of the buyer.")
        return redirect('seller_dispute_detail', dispute_id=dispute.id)
    
    if request.method == 'POST':
        address = request.POST.get('seller_return_address', '').strip()
        if not address or len(address) < 10:
            messages.error(request, "Please enter a complete return address (at least 10 characters).")
            return redirect('seller_submit_return_address', dispute_id=dispute.id)
        
        with transaction.atomic():
            dispute.seller_return_address = address
            dispute.seller_return_address_submitted_at = timezone.now()
            dispute.save()
        
        # Notify buyer that they can now ship
        create_notification(
            user=dispute.buyer,
            title="Return Address Received — Ship Item Now",
            description=f"Seller has provided their return address for dispute #{dispute.dispute_id}. You can now ship the item back.",
            notification_type='dispute',
            priority='high',
            reference_id=dispute.dispute_id,
            reference_url=f"/buyer/dispute/{dispute.id}/return/"
        )
        
        # Notify admins
        admins = User.objects.filter(is_superuser=True)
        for admin in admins:
            create_notification(
                user=admin,
                title="Seller Provided Return Address",
                description=f"Seller submitted return address for dispute #{dispute.dispute_id}. Buyer can now ship.",
                notification_type='dispute',
                priority='medium',
                reference_id=dispute.dispute_id,
                reference_url=f"/super/admin/dispute/{dispute.id}/"
            )
        
        # Email buyer
        try:
            send_mail(
                subject=f"Ship Your Return — Dispute #{dispute.dispute_id}",
                message=f"""Hello {dispute.buyer.get_full_name() or dispute.buyer.username},

                The seller has provided their return shipping address for dispute #{dispute.dispute_id}.

                PRODUCT: {dispute.order_item.product.name}

                RETURN ADDRESS:
                {address}

                Please ship the item to this address and submit your tracking information on your dispute page.

                AssetHub Dispute Resolution Team
                """,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[dispute.buyer.email],
                fail_silently=True
            )
        except Exception:
            pass
        
        messages.success(request, "Return address submitted successfully! The buyer has been notified and can now ship the item.")
        return redirect('seller_dispute_detail', dispute_id=dispute.id)
    
    # Calculate days remaining
    days_remaining = 0
    if dispute.seller_address_deadline:
        days_remaining = max((dispute.seller_address_deadline - timezone.now()).days, 0)
    
    return render(request, 'seller/submit_return_address.html', {
        'dispute': dispute,
        'product': dispute.order_item.product,
        'buyer': dispute.buyer,
        'days_remaining': days_remaining,
        'deadline': dispute.seller_address_deadline,
    })
    
    


@login_required
@super_admin_required
def admin_force_decision(request, dispute_id):
    """Admin forces a decision when seller disputes return receipt."""
    dispute = get_object_or_404(
        Dispute.objects.select_related(
            'order_item__product', 'order_item__order',
            'buyer', 'seller'
        ),
        id=dispute_id
    )
    
    if request.method != 'POST':
        return redirect('admin_dispute_detail', dispute_id=dispute.id)
    
    decision = request.POST.get('decision')
    reason = request.POST.get('reason', '')
    
    if decision not in ['resolved_buyer', 'resolved_seller']:
        messages.error(request, "Invalid decision.")
        return redirect('admin_dispute_detail', dispute_id=dispute.id)
    
    escrow_amount = dispute.get_escrow_amount()
    
    with transaction.atomic():
        dispute.status = decision
        dispute.admin_decision = f"Forced Decision: {reason}"
        dispute.admin_decided_at = timezone.now()
        dispute.decided_by = request.user
        dispute.resolved_at = timezone.now()
        dispute.save()
        
        if decision == 'resolved_buyer':
            # Buyer wins — refund them
            if hasattr(dispute.buyer, 'wallet_balance'):
                dispute.buyer.wallet_balance += escrow_amount
                dispute.buyer.save()
            
            # FIXED: Use correct related_name and get_or_create
            seller_profile, _ = SellerProfile.objects.get_or_create(user=dispute.seller)
            seller_profile.warning_count = getattr(seller_profile, 'warning_count', 0) + 1
            seller_profile.save()
            
            # Notify buyer
            create_notification(
                user=dispute.buyer,
                title="Dispute Resolved — You Won",
                description=f"Admin verified tracking and ruled in your favor. ${escrow_amount} refunded.",
                notification_type='dispute',
                priority='high',
                reference_id=dispute.dispute_id
            )
            
            # Notify seller (with warning)
            create_notification(
                user=dispute.seller,
                title="Dispute Resolved — Seller Lost",
                description=f"Admin rejected your claim. Tracking proved delivery. ${escrow_amount} refunded to buyer. Warning #{seller_profile.warning_count} issued.",
                notification_type='dispute',
                priority='high',
                reference_id=dispute.dispute_id
            )
            
            # Email both
            _send_dispute_email(
                subject=f"AssetHub — Dispute Resolved: #{dispute.dispute_id}",
                message=f"Admin decision: Buyer wins. Tracking confirmed delivery. ${escrow_amount} refunded.",
                recipient_list=[dispute.buyer.email, dispute.seller.email]
            )
            
            messages.success(request, f"Buyer refunded. Seller flagged with warning #{seller_profile.warning_count}.")
            
        elif decision == 'resolved_seller':
            # Seller wins — release funds
            if hasattr(dispute.seller, 'wallet_balance'):
                dispute.seller.wallet_balance += escrow_amount
                dispute.seller.save()
            
            order_item = dispute.order_item
            order_item.status = 'Completed'
            order_item.save()
            
            # Notify both
            create_notification(
                user=dispute.seller,
                title="Dispute Resolved — You Won",
                description=f"Admin ruled in your favor. ${escrow_amount} released.",
                notification_type='dispute',
                priority='high',
                reference_id=dispute.dispute_id
            )
            create_notification(
                user=dispute.buyer,
                title="Dispute Resolved — Buyer Lost",
                description=f"Admin ruled tracking insufficient. ${escrow_amount} released to seller.",
                notification_type='dispute',
                priority='high',
                reference_id=dispute.dispute_id
            )
            
            messages.success(request, f"Seller wins. Funds released.")
    
    create_activity(
        title=f"Forced Dispute Decision — {decision}",
        description=f"Admin {request.user.username} forced decision on dispute #{dispute.dispute_id}. Reason: {reason}",
        activity_type='alert',
        amount=escrow_amount
    )
    
    return redirect('admin_dispute_detail', dispute_id=dispute.id)