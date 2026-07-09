from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings

class User(AbstractUser):
    ROLE_CHOICES = (
        ('buyer', 'Buyer'),
        ('seller', 'Seller'),
        ('both', 'Buyer & Seller'),
    )

    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default='buyer'
    )

    profile_image = models.ImageField(upload_to='profiles/', blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True)
    bio = models.TextField(blank=True)
    
    def __str__(self):
        return self.username


# ================= NOTIFICATIONS =================
class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('order', 'Order'),
        ('payment', 'Payment'),
        ('dispute', 'Dispute'),
        ('shipping', 'Shipping'),
        ('security', 'Security'),
        ('escrow', 'Escrow'),
        ('system', 'System'),
        ('review', 'Review'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    notification_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPES,
        default='system'
    )
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='low'
    )
    reference_id = models.CharField(max_length=50, blank=True, null=True)
    reference_url = models.CharField(max_length=255, blank=True, null=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.title}"

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])
    
# ================= SELLER PROFILE =================
class SellerProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='seller_profile'
    )
    store_name = models.CharField(max_length=255)
    verified = models.BooleanField(default=False)
    warning_count = models.PositiveIntegerField(default=0)  # ← ADD THIS

    def __str__(self):
        return f"{self.user.username} Seller"


# ================= BANK DETAILS =================
class BankDetails(models.Model):
    seller = models.OneToOneField(
        SellerProfile,
        on_delete=models.CASCADE,
        related_name='bank_details'
    )

    account_holder_name = models.CharField(max_length=255)
    bank_name = models.CharField(max_length=255)
    account_number = models.CharField(max_length=50)
    routing_number = models.CharField(max_length=50)

    ACCOUNT_TYPES = (
        ('checking', 'Checking'),
        ('savings', 'Savings'),
    )
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES)

    def __str__(self):
        return f"{self.seller.user.username} Bank"    


# app_name/models.py
from django.db import models
from django.utils.text import slugify

class Category(models.Model):
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='category_images/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # automatically generate slug from name if not provided
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    
    
from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.db.models import Avg

class Product(models.Model):
    PRODUCT_TYPE_CHOICES = [
        ('physical', 'Physical'),
        ('digital', 'Digital'),
    ]

    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='products'
    )

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    sku = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=12, decimal_places=2)
    old_price = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    quantity = models.PositiveIntegerField()
    product_type = models.CharField(max_length=10, choices=PRODUCT_TYPE_CHOICES, default='physical')
    specifications = models.JSONField(default=list, blank=True)

    #  FIXED IMAGE FIELDS
    front_image = models.ImageField(upload_to='products/', blank=True, null=True)
    back_image = models.ImageField(upload_to='products/', blank=True, null=True)
    side_image = models.ImageField(upload_to='products/', blank=True, null=True)
    extra_image = models.ImageField(upload_to='products/', blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    
    def average_rating(self):
        return self.reviews.aggregate(avg=Avg('rating'))['avg'] or 0

    def rating_count(self):
        return self.reviews.count()

    @property
    def discount_amount(self):
        if self.old_price and self.old_price > self.price:
            return round(self.old_price - self.price, 2)
        return 0

    @property
    def discount_percent(self):
        if self.old_price and self.old_price > self.price:
            return int(((self.old_price - self.price) / self.old_price) * 100)
        return 0
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Product.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    
    
    
class Review(models.Model):
    product = models.ForeignKey(Product, related_name="reviews", on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField()  # 1 to 5
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    
    
class Cart(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} Cart"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def subtotal(self):
        return self.product.price * self.quantity

    def __str__(self):
        return f"{self.product.name} ({self.quantity})"
    
    
class ShippingAddress(models.Model):
    order = models.OneToOneField("Order", on_delete=models.CASCADE, related_name="shipping")

    full_name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20)

    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=20)

    instructions = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.full_name} - {self.city}"


from django.conf import settings
from django.db import models


class Order(models.Model):

    ORDER_TYPE = [
        ('escrow', 'Escrow'),
        ('whatsapp', 'WhatsApp'),
    ]

    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    shipping_address = models.TextField(blank=True, null=True)

    # ❗ KEEP this only for global reference (optional)
    order_type = models.CharField(max_length=20, choices=ORDER_TYPE)

    total_amount = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"Order #{self.id}"


from django.utils import timezone
from datetime import timedelta
from django.utils import timezone
from datetime import timedelta

class OrderItem(models.Model):

    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Processing', 'Processing'),
        ('Shipped', 'Shipped'),
        ('Delivered', 'Delivered'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    ]

    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    order = models.ForeignKey("Order", on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("Product", on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    seller_deleted = models.BooleanField(default=False)
    price = models.DecimalField(max_digits=12, decimal_places=2)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Pending")

    #  TIMER FIELD
    delivered_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(blank=True, null=True)

    def start_delivery_timer(self):
        """Start countdown ONLY when delivered"""
        if not self.expires_at:
            # change to minutes for testing
            self.expires_at = timezone.now() + timedelta(hours=48)
            self.save()

    def check_expiry(self):
        """Auto-complete the order and release escrow funds to the seller
        if the buyer takes no action within the 48-hour inspection window."""
        if not self.expires_at:
            return
        if self.status == "Delivered" and timezone.now() > self.expires_at:
            self.status = "Completed"
            self.save()

            seller = self.seller
            if hasattr(seller, "wallet_balance"):
                seller.wallet_balance += self.subtotal()
                seller.save()

            from .utils import create_notification
            create_notification(
                user=self.order.buyer,
                title="Order Auto-Completed",
                description=f"Order #{self.order.id} was automatically marked as completed after the 48-hour inspection period. Funds have been released to the seller.",
                notification_type='escrow',
                priority='medium',
                reference_id=f"ORD-{self.order.id}"
            )

            create_notification(
                user=seller,
                title="Payment Released — Order Auto-Completed",
                description=f"Order #{self.order.id} was automatically completed after the 48-hour inspection period. ${self.subtotal()} has been released to your wallet.",
                notification_type='escrow',
                priority='high',
                reference_id=f"ORD-{self.order.id}"
            )
            
            self.save()

    def subtotal(self):
        return self.quantity * self.price
# models.py

from django.db import models
from django.conf import settings

class Wishlist(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,  
        on_delete=models.CASCADE,
        related_name="wishlists"
    )
    product = models.ForeignKey(
        "Product",
        on_delete=models.CASCADE,
        related_name="wishlisted"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "product")

    def __str__(self):
        return f"{self.user} - {self.product}"



class Activity(models.Model):
    ACTIVITY_TYPES = [
        ('user', 'User'),
        ('order', 'Order'),
        ('payment', 'Payment'),
        ('alert', 'Alert'),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField()
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
    
class ContactMessage(models.Model):
    USER_TYPE_CHOICES = [
        ('buyer', 'Buyer'),
        ('seller', 'Seller'),
        ('partner', 'Partner'),
        ('other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('unread', 'Unread'),
        ('read', 'Read'),
        ('resolved', 'Resolved'),
    ]

    TYPE_CHOICES = [
        ('contact', 'Contact'),
        ('support', 'Support'),
        ('report', 'Report'),
    ]

    full_name = models.CharField(max_length=255)
    email = models.EmailField()
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES)

    subject = models.CharField(max_length=255, blank=True, null=True)
    message = models.TextField()

   
    message_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='contact')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='unread')

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} - {self.email}"

    # OPTIONAL: for preview in table
    def short_message(self):
        return self.message[:50] + "..." if len(self.message) > 50 else self.message


# ================= DISPUTE EVIDENCE =================
class DisputeEvidence(models.Model):
    EVIDENCE_TYPES = [
        ('image', 'Image'),
        ('video', 'Video'),
        ('pdf', 'PDF'),
        ('document', 'Document'),
        ('receipt', 'Receipt'),
        ('other', 'Other'),
    ]

    UPLOADER_CHOICES = [
        ('buyer', 'Buyer'),
        ('seller', 'Seller'),
    ]

    dispute = models.ForeignKey(
        'Dispute',
        on_delete=models.CASCADE,
        related_name='evidences'
    )
    file = models.FileField(upload_to='dispute_evidence/%Y/%m/%d/')
    file_type = models.CharField(max_length=20, choices=EVIDENCE_TYPES, default='other')
    uploaded_by = models.CharField(max_length=10, choices=UPLOADER_CHOICES)
    file_name = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(help_text='Size in bytes')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']
        verbose_name_plural = 'Dispute Evidences'

    def __str__(self):
        return f"{self.get_uploaded_by_display()} Evidence - {self.file_name}"


# ================= DISPUTE MESSAGE =================
class DisputeMessage(models.Model):
    SENDER_CHOICES = [
        ('buyer', 'Buyer'),
        ('seller', 'Seller'),
        ('admin', 'Admin'),
    ]

    dispute = models.ForeignKey(
        'Dispute',
        on_delete=models.CASCADE,
        related_name='messages'
    )
    sender = models.CharField(max_length=10, choices=SENDER_CHOICES)
    sender_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.get_sender_display()} message on Dispute #{self.dispute.id}"


# ================= EXPANDED DISPUTE MODEL =================
# NOTE: Replace your existing Dispute model with this expanded version
# Run: python manage.py makemigrations && python manage.py migrate

class Dispute(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('awaiting_seller', 'Awaiting Seller Response'),
        ('awaiting_buyer', 'Awaiting Buyer Reply'),
        ('under_review', 'Under Admin Review'),
        ('more_info', 'More Information Requested'),
        ('return_required', 'Return Required'),
        ('return_shipped', 'Return Shipped'),
        ('return_received', 'Return Received'),
        ('resolved_buyer', 'Resolved - Buyer Won'),
        ('resolved_seller', 'Resolved - Seller Won'),
        ('resolved_mutual', 'Resolved - Mutual Agreement'),
        ('cancelled', 'Cancelled'),
    ]

    REASON_CHOICES = [
        ('wrong_item', 'Wrong Item Received'),
        ('damaged', 'Damaged Product'),
        ('counterfeit', 'Counterfeit Product'),
        ('missing_accessories', 'Missing Accessories'),
        ('not_as_described', 'Product Not As Described'),
        ('not_delivered', 'Item Not Delivered'),
        ('other', 'Other'),
    ]

    RESOLUTION_CHOICES = [
        ('full_refund', 'Full Refund'),
        ('partial_refund', 'Partial Refund'),
        ('replacement', 'Replacement'),
        ('other', 'Other'),
    ]

    # Core references
    order_item = models.ForeignKey(
        'OrderItem',
        on_delete=models.CASCADE,
        related_name='disputes'
    )
    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='buyer_disputes'
    )
    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='seller_disputes'
    )

    # Dispute details
    dispute_id = models.CharField(max_length=20, unique=True, blank=True)
    reason = models.CharField(max_length=30, choices=REASON_CHOICES)
    complaint = models.TextField()
    requested_resolution = models.CharField(max_length=20, choices=RESOLUTION_CHOICES)

    # Seller response
    seller_response = models.TextField(blank=True, null=True)
    seller_courier = models.CharField(max_length=100, blank=True, null=True)
    seller_tracking = models.CharField(max_length=100, blank=True, null=True)
    seller_ship_date = models.DateField(blank=True, null=True)
    seller_delivery_confirm = models.CharField(max_length=50, blank=True, null=True)
    seller_responded_at = models.DateTimeField(blank=True, null=True)
    seller_return_address = models.TextField(
    blank=True, 
    null=True,
    help_text='Address where buyer should return the item'
    )
    seller_return_address_submitted_at = models.DateTimeField(
        blank=True, 
        null=True
    )
    seller_address_deadline = models.DateTimeField(
        blank=True, 
        null=True,
        help_text='Deadline for seller to provide return address (6 days from admin decision)'
    )
    return_not_received_at = models.DateTimeField(null=True, blank=True)
    return_not_received_confirmed = models.BooleanField(default=False)
    # Admin review
    admin_notes = models.TextField(blank=True, null=True)
    admin_decision = models.TextField(blank=True, null=True)
    admin_decided_at = models.DateTimeField(blank=True, null=True)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='dispute_decisions'
    )

    # Return tracking (when buyer must return item)
    return_courier = models.CharField(max_length=100, blank=True, null=True)
    return_tracking = models.CharField(max_length=100, blank=True, null=True)
    return_shipped_at = models.DateTimeField(blank=True, null=True)
    return_received_at = models.DateTimeField(blank=True, null=True)

    # Status & deadlines
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending')
    seller_deadline = models.DateTimeField(blank=True, null=True)
    buyer_deadline = models.DateTimeField(blank=True, null=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(blank=True, null=True)

    # Declaration check
    buyer_declaration = models.BooleanField(default=False)
    seller_declaration = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Dispute #{self.dispute_id} - {self.get_status_display()}"

    def save(self, *args, **kwargs):
        if not self.dispute_id:
            # Generate unique dispute ID: DSP-XXXXX
            import random
            import string
            while True:
                new_id = 'DSP-' + ''.join(random.choices(string.digits, k=5))
                if not Dispute.objects.filter(dispute_id=new_id).exists():
                    self.dispute_id = new_id
                    break
        super().save(*args, **kwargs)

    def is_resolved(self):
        return self.status in ['resolved_buyer', 'resolved_seller', 'resolved_mutual', 'cancelled']

    def get_escrow_amount(self):
        return self.order_item.subtotal()

    def days_until_seller_deadline(self):
        from django.utils import timezone
        if not self.seller_deadline:
            return None
        delta = self.seller_deadline - timezone.now()
        return max(delta.days, 0)