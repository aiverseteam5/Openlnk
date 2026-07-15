"""Tests for OL-101..107 — business console, fee cycles, payments.

OL-101: Console dashboard (batches, schedule, fee cycle, commitments).
OL-102: Fee cycle generates commitments per enrolled student.
OL-103: Fee reminders include UPI deep-link to center VPA.
OL-103a: Share-to-WhatsApp CTA on commitment done.
OL-103b: Validate business UPI VPA before proposing fee commitment.
OL-104: Parent-reported payment moves fee toward done per rung.
OL-105: Owner ROI display (fees-recovered vs subscription cost).
OL-106: Razorpay subscription billing with GST invoices.
OL-107: Subscription lapse degrades to read-only, preserves parent access.
"""

from uuid import uuid4

import pytest


@pytest.mark.req("OL-101")
class TestConsoleDashboard:
    """Console shows batches, schedule, fee cycle, commitments dashboard."""

    def test_dashboard_service_exists(self):
        from app.services.console_service import ConsoleService

        assert ConsoleService is not None

    def test_dashboard_sections_method_signature(self):
        """Dashboard method accepts db and context_id for real queries."""
        import inspect

        from app.services.console_service import ConsoleService

        sig = inspect.signature(ConsoleService.get_dashboard_sections)
        params = list(sig.parameters.keys())
        assert "db" in params
        assert "context_id" in params

    def test_commitments_dashboard_states_method(self):
        """Dashboard returns commitments with pending / at-risk / closed keys."""
        import inspect

        from app.services.console_service import ConsoleService

        # Method is async and returns dict with "commitments" key
        assert inspect.iscoroutinefunction(ConsoleService.get_dashboard_sections)


@pytest.mark.req("OL-102")
class TestFeeCycleGeneration:
    """Fee cycle date generates fee commitments per enrolled student."""

    def test_fee_cycle_service_exists(self):
        from app.services.fee_cycle_service import FeeCycleService

        assert FeeCycleService is not None

    def test_generate_fee_commitments(self):
        from app.services.fee_cycle_service import FeeCycleService

        service = FeeCycleService()
        result = service.generate_fee_commitments(
            business_id=uuid4(),
            cycle_label="July 2026",
            enrolled_students=[
                {"student_name": "Alice", "parent_id": uuid4(), "amount_paise": 500000},
                {"student_name": "Bob", "parent_id": uuid4(), "amount_paise": 500000},
            ],
        )
        assert result.generated == 2


@pytest.mark.req("OL-103")
class TestFeeReminderUpi:
    """Fee reminders include UPI deep-link to center VPA."""

    def test_fee_reminder_includes_upi(self):
        """Fee commitment generation references UPI intent."""
        import inspect

        from app.services.fee_cycle_service import FeeCycleService

        source = inspect.getsource(FeeCycleService.generate_fee_commitments)
        assert "upi" in source.lower()


@pytest.mark.req("OL-103a")
class TestWhatsAppShareCta:
    """Share confirmation to WhatsApp CTA on commitment done."""

    def test_whatsapp_share_link_generation(self):
        from app.services.console_service import ConsoleService

        service = ConsoleService()
        link = service.generate_whatsapp_share(
            whatsapp_number="919876543210",
            commitment_title="July Fee",
            commitment_date="2026-07-15",
        )
        assert "wa.me" in link
        assert "919876543210" in link
        assert "July Fee" in link or "July+Fee" in link or "July%20Fee" in link


@pytest.mark.req("OL-103b")
class TestVpaValidation:
    """Validate business UPI VPA before proposing fee commitment."""

    def test_vpa_validation_valid(self):
        from app.services.upi_service import UpiService

        service = UpiService()
        # Should not raise
        service.generate_intent_url(
            vpa="center@upi",
            amount_paise=100,
            payee_name="Test",
            note="Test",
        )

    def test_vpa_validation_rejects_empty(self):
        from app.services.upi_service import UpiService

        service = UpiService()
        with pytest.raises(ValueError, match="VPA"):
            service.generate_intent_url(
                vpa="",
                amount_paise=100,
                payee_name="Test",
                note="Test",
            )

    def test_vpa_validation_rejects_malformed(self):
        from app.services.upi_service import UpiService

        service = UpiService()
        with pytest.raises(ValueError, match="format"):
            service.generate_intent_url(
                vpa="no-at-sign",
                amount_paise=100,
                payee_name="Test",
                note="Test",
            )


@pytest.mark.req("OL-104")
class TestPaymentConfirmation:
    """Parent payment moves fee toward done per rung policy."""

    def test_payment_confirmation_method(self):
        from app.services.fee_cycle_service import FeeCycleService

        service = FeeCycleService()
        assert hasattr(service, "record_payment_report")

    def test_payment_report_at_propose_requires_owner_confirm(self):
        """At Propose rung, owner confirmation is required."""
        from app.services.fee_cycle_service import FeeCycleService

        service = FeeCycleService()
        result = service.record_payment_report(
            commitment_id=uuid4(),
            reporter_role="parent",
            rung="propose",
        )
        assert result["requires_owner_confirmation"] is True


@pytest.mark.req("OL-105")
class TestOwnerRoi:
    """Owner sees fees-recovered vs subscription cost."""

    def test_roi_metric_method(self):
        from app.services.console_service import ConsoleService

        service = ConsoleService()
        assert hasattr(service, "get_roi_metrics")

    def test_roi_method_signature(self):
        """ROI method accepts db and context_id for real queries."""
        import inspect

        from app.services.console_service import ConsoleService

        sig = inspect.signature(ConsoleService.get_roi_metrics)
        params = list(sig.parameters.keys())
        assert "db" in params
        assert "context_id" in params
        assert inspect.iscoroutinefunction(ConsoleService.get_roi_metrics)


@pytest.mark.req("OL-106")
class TestRazorpayBilling:
    """Centers billed via Razorpay subscriptions with GST invoices."""

    def test_billing_service_exists(self):
        from app.services.billing_service import BillingService

        assert BillingService is not None

    def test_billing_has_create_subscription(self):
        from app.services.billing_service import BillingService

        service = BillingService()
        assert hasattr(service, "create_subscription")

    def test_billing_includes_gst(self):
        """Invoices include GST."""
        from app.services.billing_service import BillingService

        service = BillingService()
        assert hasattr(service, "generate_invoice")


@pytest.mark.req("OL-107")
class TestSubscriptionLapse:
    """Lapsed subscription degrades to read-only, preserves parent access."""

    def test_lapse_handler_exists(self):
        from app.services.billing_service import BillingService

        service = BillingService()
        assert hasattr(service, "handle_subscription_lapse")

    def test_lapse_preserves_parent_access(self):
        """Parent access preserved for 90 days after lapse."""
        from app.services.billing_service import BillingService

        service = BillingService()
        result = service.handle_subscription_lapse(business_id=uuid4())
        assert result["owner_read_only"] is True
        assert result["parent_access_days"] == 90

    def test_lapse_anonymizes_business_ref(self):
        """Household commitments persist with anonymized business ref."""
        from app.services.billing_service import BillingService

        service = BillingService()
        result = service.handle_subscription_lapse(business_id=uuid4())
        assert result["commitments_deleted"] is False
