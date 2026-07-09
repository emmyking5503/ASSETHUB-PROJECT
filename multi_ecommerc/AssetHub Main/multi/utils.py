from .models import Activity

def create_activity(title, description, activity_type, amount=None):
    Activity.objects.create(
        title=title,
        description=description,
        activity_type=activity_type,
        amount=amount
    )
    
from django.shortcuts import redirect
from functools import wraps

def super_admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_superuser:
            return redirect('home')  # or login page
        return view_func(request, *args, **kwargs)
    return _wrapped_view



from django.utils import timezone
from .models import Notification

def create_notification(user, title, description, notification_type='system', 
                        priority='low', reference_id=None, reference_url=None):
    """
    Create a notification for a specific user.
    
    Args:
        user: The User to notify
        title: Short title of the notification
        description: Detailed message
        notification_type: 'order', 'payment', 'dispute', 'shipping', 'security', 'escrow', 'system', 'review'
        priority: 'low', 'medium', 'high'
        reference_id: Optional reference number (e.g., order ID, dispute ID)
        reference_url: Optional URL to redirect when clicked
    """
    return Notification.objects.create(
        user=user,
        title=title,
        description=description,
        notification_type=notification_type,
        priority=priority,
        reference_id=reference_id,
        reference_url=reference_url
    )