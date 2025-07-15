# tests/integration/test_notification_flow.py
import pytest
from uuid import uuid4
from src.domain.model import NotificationPreferences, NotificationRequest, NotificationType


class TestNotificationDomainFlow:
    """Integration tests for notification domain logic flow"""

    def test_complete_notification_preferences_flow(self, fake_unit_of_work):
        """Test complete flow: create preferences -> retrieve -> modify"""
        userid = uuid4().hex
        email = "test@example.com"

        # 1. Create notification preferences
        preferences = NotificationPreferences.create(
            userid=userid,
            notification_email=email,
            preferences={
                'email_verification': True,
                'security_alert': True,
                'marketing': False
            }
        )

        fake_unit_of_work.notification_preferences.add(preferences)
        fake_unit_of_work.commit()

        # 2. Verify preferences were saved
        retrieved = fake_unit_of_work.notification_preferences.get(userid)
        assert retrieved is not None
        assert retrieved.notification_email.value == email
        assert retrieved.preferences.value['email_verification'] is True
        assert retrieved.preferences.value['marketing'] is False

        # 3. Check if notification is enabled for specific types
        assert retrieved.is_notification_enabled(NotificationType.EMAIL_VERIFICATION) is True
        assert retrieved.is_notification_enabled(NotificationType.SECURITY_ALERT) is True

    def test_notification_request_lifecycle(self, fake_unit_of_work):
        """Test notification request from creation to completion"""
        notification_id = uuid4().hex
        userid = uuid4().hex

        # 1. Create notification request
        notification_request = NotificationRequest.create(
            notification_id=notification_id,
            userid=userid,
            notification_type=NotificationType.PASSWORD_RESET,
            recipient_email="user@example.com",
            subject="Password Reset Request",
            content="Click here to reset your password"
        )

        # Initially should be pending
        assert notification_request.status.value == 'pending'
        assert len(notification_request.events) > 0  # Should have creation event

        fake_unit_of_work.notification_requests.add(notification_request)
        fake_unit_of_work.commit()

        # 2. Mark as sent and verify
        notification_request.mark_as_sent()
        assert notification_request.status.value == 'sent'

        # 3. Verify it's retrievable with new status
        retrieved = fake_unit_of_work.notification_requests.get(notification_id)
        assert retrieved.status.value == 'sent'

    def test_notification_failure_and_retry_flow(self, fake_unit_of_work):
        """Test notification failure and retry workflow"""
        notification_id = uuid4().hex

        # 1. Create and save notification request
        notification_request = NotificationRequest.create(
            notification_id=notification_id,
            userid=uuid4().hex,
            notification_type=NotificationType.EMAIL_VERIFICATION,
            recipient_email="test@example.com",
            subject="Email Verification",
            content="Please verify your email"
        )

        fake_unit_of_work.notification_requests.add(notification_request)
        fake_unit_of_work.commit()

        # 2. Simulate failure
        notification_request.mark_as_failed("SMTP connection timeout")
        assert notification_request.status.value == 'failed'
        assert notification_request.retry_count == 0

        # 3. Check if can retry when in FAILED status
        assert notification_request.can_retry(max_retries=3) is True

        # 4. Attempt retry
        notification_request.increment_retry()
        assert notification_request.retry_count == 1
        assert notification_request.status.value == 'retrying'

        # 5. After increment_retry, status is RETRYING, so can_retry should be False
        # This matches the domain logic: you can only retry FAILED notifications
        assert notification_request.can_retry(max_retries=3) is False

    def test_preferences_and_notification_interaction(self, fake_unit_of_work):
        """Test interaction between preferences and notifications"""
        userid = uuid4().hex
        email = "user@example.com"

        # 1. Set up user preferences
        preferences = NotificationPreferences.create(
            userid=userid,
            notification_email=email,
            preferences={
                'email_verification': True,
                'security_alert': False,
                'marketing': True,
                'password_reset': True
            }
        )

        fake_unit_of_work.notification_preferences.add(preferences)
        fake_unit_of_work.commit()

        # 2. Test different notification types against preferences
        test_cases = [
            (NotificationType.EMAIL_VERIFICATION, True),
            (NotificationType.SECURITY_ALERT, False),
            (NotificationType.PASSWORD_RESET, True),
        ]

        for notification_type, should_be_enabled in test_cases:
            enabled = preferences.is_notification_enabled(notification_type)
            assert enabled == should_be_enabled, f"{notification_type} should be {should_be_enabled}"

            # Create notification request
            notification_request = NotificationRequest.create(
                notification_id=uuid4().hex,
                userid=userid,
                notification_type=notification_type,
                recipient_email=email,
                subject=f"Test {notification_type.value}",
                content="Test content"
            )

            fake_unit_of_work.notification_requests.add(notification_request)

        fake_unit_of_work.commit()


class TestNotificationBulkOperations:
    """Test bulk operations and queries"""

    def test_bulk_notification_creation(self, fake_unit_of_work):
        """Test creating multiple notifications efficiently"""
        userid = uuid4().hex
        notification_requests = []

        # Create multiple notifications
        for i in range(10):
            notification_request = NotificationRequest.create(
                notification_id=uuid4().hex,
                userid=userid,
                notification_type=NotificationType.WELCOME,  # Fixed: use existing type
                recipient_email=f"user{i}@example.com",
                subject=f"Welcome Email {i}",
                content=f"Welcome content for user {i}"
            )
            notification_requests.append(notification_request)
            fake_unit_of_work.notification_requests.add(notification_request)

        fake_unit_of_work.commit()

        # Verify all were created
        for notification_request in notification_requests:
            retrieved = fake_unit_of_work.notification_requests.get(
                notification_request.notification_id.value
            )
            assert retrieved is not None
            assert retrieved.notification_type == NotificationType.WELCOME

    def test_failed_notifications_bulk_query(self, fake_unit_of_work):
        """Test querying multiple failed notifications"""
        failed_count = 0
        total_count = 15

        # Create mix of successful and failed notifications
        for i in range(total_count):
            notification_request = NotificationRequest.create(
                notification_id=uuid4().hex,
                userid=uuid4().hex,
                notification_type=NotificationType.SECURITY_ALERT,
                recipient_email=f"user{i}@example.com",
                subject=f"Alert {i}",
                content="Security alert"
            )

            # Mark some as failed
            if i % 3 == 0:  # Every 3rd notification fails
                notification_request.mark_as_failed("Delivery failed")
                failed_count += 1
            else:
                notification_request.mark_as_sent()

            fake_unit_of_work.notification_requests.add(notification_request)

        fake_unit_of_work.commit()

        # Query failed notifications
        failed_notifications = fake_unit_of_work.notification_requests.get_failed_notifications()

        assert len(failed_notifications) == failed_count
        for notification in failed_notifications:
            assert notification.status.value == 'failed'
            assert notification.retry_count < 3
