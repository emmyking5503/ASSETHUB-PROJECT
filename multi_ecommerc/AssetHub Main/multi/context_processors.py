from django.urls import reverse
from .models import OrderItem, Activity, ContactMessage


def seller_context(request):
    notifications = []
    notification_count = 0

    if request.user.is_authenticated:
        orders = OrderItem.objects.filter(product__seller=request.user)
        for order in orders:
            order.check_expiry()

        if request.user.is_superuser:
            messages = ContactMessage.objects.filter(status='unread').order_by('-created_at')[:5]
            notification_count = messages.count()
            for msg in messages:
                notifications.append({
                    'title': msg.subject or f'New message from {msg.full_name}',
                    'description': msg.message[:90],
                    'url': reverse('view_message', args=[msg.id]),
                    'icon': 'fa-envelope',
                })
        else:
            activities = Activity.objects.all().order_by('-created_at')[:5]
            notification_count = activities.count()
            for activity in activities:
                notifications.append({
                    'title': activity.title,
                    'description': activity.description[:90],
                    'url': '#',
                    'icon': 'fa-bell',
                })

        return {
            'pending_orders': orders.filter(status='Pending').count(),
            'dashboard_notifications': notifications,
            'dashboard_notifications_count': notification_count,
        }

    return {
        'pending_orders': 0,
        'dashboard_notifications': [],
        'dashboard_notifications_count': 0,
    }