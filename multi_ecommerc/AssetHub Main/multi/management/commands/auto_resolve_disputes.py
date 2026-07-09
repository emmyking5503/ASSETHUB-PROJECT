# management/commands/auto_resolve_disputes.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from yourapp.models import Dispute

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        # Auto-resolve if seller hasn't responded in 7 days after return shipped
        cutoff = timezone.now() - timedelta(days=7)
        disputes = Dispute.objects.filter(
            status='return_shipped',
            return_shipped_at__lt=cutoff,
            return_received_at__isnull=True,
            return_not_received_at__isnull=True
        )
        
        for dispute in disputes:
            # Auto-refund buyer
            dispute.status = 'resolved_buyer'
            dispute.admin_decision = "Auto-resolved: Seller did not respond within 7 days."
            dispute.resolved_at = timezone.now()
            dispute.save()
            
            if hasattr(dispute.buyer, 'wallet_balance'):
                dispute.buyer.wallet_balance += dispute.get_escrow_amount()
                dispute.buyer.save()
            
            # Notify both parties...
        
        self.stdout.write(f"Auto-resolved {disputes.count()} disputes.")