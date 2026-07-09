from decimal import Decimal
from unittest.mock import patch
import smtplib

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Cart, Category, ContactMessage, Dispute, OrderItem, Product


class BuyNowTests(TestCase):
    def setUp(self):
        self.buyer = get_user_model().objects.create_user(
            username="buyer1",
            email="buyer1@example.com",
            password="secret123",
            role="buyer",
        )
        self.seller = get_user_model().objects.create_user(
            username="seller1",
            email="seller1@example.com",
            password="secret123",
            role="seller",
        )
        self.category = Category.objects.create(name="Electronics", slug="electronics")
        self.product = Product.objects.create(
            seller=self.seller,
            name="Phone",
            category=self.category,
            description="Great phone",
            price=Decimal("100.00"),
            quantity=5,
        )

    def test_buy_now_redirects_to_checkout_and_adds_item(self):
        self.client.login(username="buyer1", password="secret123")

        response = self.client.get(reverse("buy_now", args=[self.product.id]), {"quantity": 2})

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("checkout"))
        cart = Cart.objects.get(user=self.buyer)
        self.assertEqual(cart.items.get(product=self.product).quantity, 2)


class AdminPageTests(TestCase):
    def setUp(self):
        self.superuser = get_user_model().objects.create_superuser(
            username="adminpage",
            email="adminpage@example.com",
            password="secret123",
        )

    def test_admin_pages_render_for_superuser(self):
        self.client.login(username="adminpage", password="secret123")
        urls = [
            reverse("super_admin"),
            reverse("admin_listings"),
            reverse("admin_transactions"),
            reverse("admin_reports"),
            reverse("admin_disputes"),
            reverse("notifications"),
            reverse("add_category"),
        ]
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)


class ReplyMessageTests(TestCase):
    def setUp(self):
        self.superuser = get_user_model().objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="secret123",
        )
        self.contact = ContactMessage.objects.create(
            full_name="Buyer Name",
            email="buyer@example.com",
            user_type="buyer",
            subject="Order issue",
            message="I need help with my order.",
            message_type="support",
        )

    @patch("multi.views.EmailMultiAlternatives.send", side_effect=smtplib.SMTPException("Connection unexpectedly closed"))
    def test_reply_message_handles_smtp_failure(self, mock_send):
        self.client.login(username="admin", password="secret123")

        response = self.client.post(
            reverse("reply_message", args=[self.contact.id]),
            {
                "reply_to": "buyer@example.com",
                "subject": "Re: Order issue",
                "message": "Thanks for waiting.",
                "mark_as_resolved": "on",
            },
            follow=True,
        )

        self.assertContains(response, "Email failed to send")
        self.contact.refresh_from_db()
        self.assertEqual(self.contact.status, "unread")
        mock_send.assert_called_once()


class AdminDisputeWorkflowTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(
            username="disputeadmin",
            email="disputeadmin@example.com",
            password="secret123",
        )
        self.buyer = get_user_model().objects.create_user(
            username="buyer2",
            email="buyer2@example.com",
            password="secret123",
            role="buyer",
        )
        self.seller = get_user_model().objects.create_user(
            username="seller2",
            email="seller2@example.com",
            password="secret123",
            role="seller",
        )
        self.category = Category.objects.create(name="Electronics", slug="electronics")
        self.product = Product.objects.create(
            seller=self.seller,
            name="Laptop",
            category=self.category,
            description="Gaming laptop",
            price=Decimal("1000.00"),
            quantity=2,
        )
        self.order_item = OrderItem.objects.create(
            order=None,
            product=self.product,
            seller=self.seller,
            quantity=1,
            price=Decimal("1000.00"),
            status="Delivered",
        )
        self.dispute = Dispute.objects.create(
            order_item=self.order_item,
            buyer=self.buyer,
            seller=self.seller,
            complaint="The laptop arrived damaged.",
            evidence="photos-of-damage",
            seller_response="I shipped it safely.",
        )

    def test_admin_dispute_detail_shows_restructured_workflow(self):
        self.client.login(username="disputeadmin", password="secret123")

        response = self.client.get(reverse("dispute_detail", args=[self.dispute.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Buyer evidence")
        self.assertContains(response, "Seller evidence")
        self.assertContains(response, "Timeline")
        self.assertContains(response, "Escrow status")
        self.assertContains(response, "Partial refund")
        self.assertContains(response, "Return item required")

    def test_admin_can_change_dispute_action(self):
        self.client.login(username="disputeadmin", password="secret123")

        response = self.client.post(
            reverse("dispute_detail", args=[self.dispute.id]),
            {"action": "partial_refund"},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.dispute.refresh_from_db()
        self.assertEqual(self.dispute.status, "refunded")
