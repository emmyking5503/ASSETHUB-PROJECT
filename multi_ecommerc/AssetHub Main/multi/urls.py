from django.contrib import admin
from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static
from .views import logout_view

urlpatterns = [
   
    # path('', views.home, name='home'),
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path("base/", views.base, name="base"),
    path("login/", views.login_view, name="login"),
    path("seller/dashboard/", views.seller_dashboard, name="seller_dashboard"),
    path("buyer/dashboard/", views.buyer_dashboard, name="buyer_dashboard"),
    path('add-product/', views.add_product, name='add_product'),
    path('my-products/', views.my_products, name='my_products'),
    path('seller/order/', views.seller_orders, name='seller_order'),
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),
    path('add-category/', views.add_category, name='add_category'),
    path('delete-category/<int:category_id>/', views.delete_category, name='delete_category'),
    path('edit-product/<slug:slug>/', views.edit_product, name='edit_product'),
    path('delete-product/<slug:slug>/', views.delete_product, name='delete_product'),
    path('settings/', views.user_settings, name='user_settings'),
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),
    path('product/<slug:slug>/review/', views.write_review, name='write_review'),
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('buy-now/<int:product_id>/', views.buy_now, name='buy_now'),
    path('products/new/', views.new_products, name='new_products'),
    path("search-suggestions/", views.search_suggestions, name="search_suggestions"),
    path("cart/", views.cart, name="cart"),
    path("add-to-cart/<int:product_id>/", views.add_to_cart, name="add_to_cart"),
    path("cart/remove/<int:item_id>/", views.remove_from_cart, name="remove_from_cart"),
    path("cart/increase/<int:item_id>/", views.increase_quantity, name="increase_quantity"),
    path("cart/decrease/<int:item_id>/", views.decrease_quantity, name="decrease_quantity"),
    # path('products/', views.all_products, name='all_products'),
    path('checkout/', views.checkout, name="checkout"),
    path("payment-options/", views.payment_options, name="payment_options"),
    path("secure-payment/", views.secure_payment, name="secure_payment"),
    path("process-payment/", views.process_payment, name="process_payment"),
    
    path('payment-success/', views.payment_success_view, name='payment_success'),
    path('payment-failure/', views.payment_failure_view, name='payment_failure'),
    
    path('escrow/', views.transactions, name='escrow'),
    
    path('markets/', views.market, name='markets'),
    path('activity/', views.activity_log, name='activity'),
    path('delete-activity/<int:activity_id>/', views.delete_activity, name='delete_activity'),
# ============================================================================
# USER NOTIFICATIONS (BUYER / SELLER)
# ============================================================================
path('notifications/', views.user_notifications, name='user_notifications'),
path('notifications/mark-read/<int:notification_id>/', views.mark_notification_read, name='mark_notification_read'),
path('notifications/mark-all-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
path('notifications/delete/<int:notification_id>/', views.delete_notification, name='delete_notification'),
path('notifications/count/', views.notification_count, name='notification_count'),

# ============================================================================
# ADMIN NOTIFICATIONS (keep these separate)
# ============================================================================
path('super/notifications/', views.admin_notifications, name='admin_notifications'),
path('admin/messages/delete/<int:message_id>/', views.delete_message, name='delete_message'),
path('message/<int:id>/', views.view_message, name='view_message'),
path("message/reply/<int:message_id>/", views.reply_message, name="reply_message"),    
    path('users/', views.users, name='users'),
    path('admin_base/', views.admin_base, name='admin_base'),
    path('super/admin/dashboard/', views.super_admin, name='super_admin'),
    path('super/admin/listings/', views.admin_listings, name='admin_listings'),
    path('super/admin/transactions/', views.admin_transactions, name='admin_transactions'),
    path('super/admin/reports/', views.admin_reports, name='admin_reports'),

    path('super/admin/user/<int:user_id>/', views.user_detail, name='user_detail'),
    path('super/admin/product/<int:product_id>/', views.admin_product_detail, name='admin_product_detail'),
    path('super/admin/product/<int:product_id>/delete/', views.admin_delete_product, name='admin_delete_product'),
    path('super/admin/transaction/<int:order_item_id>/', views.admin_transaction_detail, name='admin_transaction_detail'),
    path('super/admin/report/<int:report_id>/', views.report_detail, name='report_detail'),

    path('seller/order/<int:order_id>/', views.seller_order_detail, name='seller_order_detail'),
    path('contact/', views.contact_view, name='contact'),
    path('admin/messages/delete/<int:message_id>/', views.delete_message, name='delete_message'),
    path('message/<int:id>/', views.view_message, name='view_message'),
    path('about/', views.about, name='about'),
    path('main_base/', views.main_base, name='main_base'),
    # urls.py
path("message/reply/<int:message_id>/", views.reply_message, name="reply_message"),
    # buyer
    path('buyer/orders/', views.buyer_order, name='buyer_order'),
    path('super/settings', views.admin_settings, name='admin_settings'),
    path(
    'confirm-delivery/<int:order_id>/<int:seller_id>/',
    views.confirm_delivery,
    name='confirm_delivery'
),
    path('seller/customers/', views.seller_customers, name='seller_customers'),
    path('ajax/search-users/', views.ajax_search_users, name='ajax_search_users'),
    path('toggle-user/<int:user_id>/', views.toggle_user_status, name='toggle_user_status'),
    path('delete-user/<int:user_id>/', views.delete_user, name='delete_user'),
    # urls.py
    path('toggle-user/<int:user_id>/', views.toggle_user_status, name='toggle_user_status'),
    path('delete-user/<int:user_id>/', views.delete_user, name='delete_user'),
    path("wishlist/", views.wishlist_view, name="wishlist"),
    path("wishlist/add/<int:product_id>/", views.add_to_wishlist, name="add_to_wishlist"),
    path("wishlist/remove/<int:product_id>/", views.remove_from_wishlist, name="remove_from_wishlist"),
    path("toggle-wishlist/<int:product_id>/", views.toggle_wishlist, name="toggle_wishlist"),
    path("buyer/order/<int:order_id>/<int:seller_id>/", views.buyer_order_detail, name="buyer_order_detail"),
    path('cancel-order/<int:order_id>/', views.cancel_order, name='cancel_order'),
    path('seller-delete-order/<int:item_id>/', views.seller_delete_order, name='seller_delete_order'),
    path("logout/", logout_view, name="logout"),
    
    
    
        # ============================================================================
    # DISPUTE URLS
    # ============================================================================
    
    # Buyer dispute URLs
    path('buyer/disputes/', views.buyer_disputes, name='buyer_disputes'),
    path('buyer/dispute/<int:dispute_id>/', views.buyer_dispute_detail, name='buyer_dispute_detail'),
    path('buyer/dispute/<int:dispute_id>/reply/', views.buyer_dispute_reply, name='buyer_dispute_reply'),
    path('buyer/dispute/<int:dispute_id>/return-tracking/', views.submit_return_tracking, name='submit_return_tracking'),
    path('buyer/order/<int:order_item_id>/dispute/', views.submit_dispute, name='submit_dispute'),
    
    # Seller dispute URLs
    path('seller/disputes/', views.seller_disputes, name='seller_disputes'),
    path('seller/dispute/<int:dispute_id>/', views.seller_dispute_detail, name='seller_dispute_detail'),
    path('seller/dispute/<int:dispute_id>/respond/', views.seller_respond_dispute, name='seller_respond_dispute'),
    path('seller/dispute/<int:dispute_id>/confirm-return/', views.seller_confirm_return_received, name='seller_confirm_return_received'),
    
    # Admin dispute URLs (enhanced)
    path('super/admin/disputes/', views.admin_disputes_list, name='admin_disputes_list'),
    # path('super/admin/disputes/', views.admin_disputes, name='admin_disputes'),
    path('super/admin/dispute/<int:dispute_id>/', views.admin_dispute_detail, name='admin_dispute_detail'),
    path('super/admin/dispute/<int:dispute_id>/request-evidence/', views.admin_request_evidence, name='admin_request_evidence'),
    # Evidence Center
    path('super/admin/dispute/<int:dispute_id>/evidence/', views.admin_evidence_center, name='admin_evidence_center'),
    path('super/admin/dispute/<int:dispute_id>/request-evidence/', views.admin_request_evidence, name='admin_request_evidence'),
    path('super/admin/dispute/<int:dispute_id>/decision/', views.admin_decision_center, name='admin_decision_center'),
    # Buyer return tracking
    path('buyer/dispute/<int:dispute_id>/return/', views.buyer_return_tracking, name='buyer_return_tracking'),

    # Buyer decisions list (admin decisions on their disputes)
    path('buyer/decisions/', views.buyer_decisions_list, name='buyer_decisions_list'),
    # Shared evidence upload
    path('dispute/<int:dispute_id>/upload-evidence/', views.upload_dispute_evidence, name='upload_dispute_evidence'),
    
    # Seller submit return address
    path('seller/dispute/<int:dispute_id>/return-address/', views.seller_submit_return_address, name='seller_submit_return_address'),
    path('seller/dispute/<int:dispute_id>/confirm-return/', views.seller_confirm_return_received, name='seller_confirm_return_received'),
    path('seller/dispute/<int:dispute_id>/return-not-received/', views.seller_confirm_return_not_received, name='seller_confirm_return_not_received'),
    path('super/admin/dispute/<int:dispute_id>/force-decision/', views.admin_force_decision, name='admin_force_decision'),
    path('buyer/wallet/', views.buyer_wallet, name='buyer_wallet'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
