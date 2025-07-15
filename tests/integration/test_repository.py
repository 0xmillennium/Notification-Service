from uuid import uuid4
from src.domain.model import NotificationPreferences, NotificationRequest, NotificationType


class TestNotificationPreferencesRepository:
    """Integration tests for notification preferences repository"""

    def test_notification_preferences_repository_add_and_get(self, fake_unit_of_work):
        """Test adding and retrieving notification preferences using fake repository."""
        userid = uuid4().hex
        preferences = NotificationPreferences.create(
            userid=userid,
            notification_email="test@example.com"
        )

        fake_unit_of_work.notification_preferences.add(preferences)
        retrieved = fake_unit_of_work.notification_preferences.get(userid)

        assert retrieved is not None
        assert retrieved.userid.value == userid
        assert retrieved.notification_email.value == "test@example.com"

    def test_notification_preferences_repository_get_nonexistent(self, fake_unit_of_work):
        """Test retrieving non-existent notification preferences returns None."""
        result = fake_unit_of_work.notification_preferences.get(uuid4().hex)
        assert result is None

    def test_notification_preferences_with_custom_settings(self, fake_unit_of_work):
        """Test creating preferences with custom notification settings"""
        userid = uuid4().hex
        preferences = NotificationPreferences.create(
            userid=userid,
            notification_email="custom@example.com",
            preferences={
                'email_verification': True,
                'security_alert': False,
                'marketing': True
            }
        )

        fake_unit_of_work.notification_preferences.add(preferences)
        retrieved = fake_unit_of_work.notification_preferences.get(userid)

        assert retrieved is not None
        assert retrieved.preferences.value['email_verification'] is True
        assert retrieved.preferences.value['security_alert'] is False
        assert retrieved.preferences.value['marketing'] is True


class TestNotificationRequestRepository:
    """Integration tests for notification request repository"""

    def test_notification_request_add_and_get(self, fake_unit_of_work):
        """Test adding and retrieving notification requests"""
        notification_id = uuid4().hex
        userid = uuid4().hex

        notification_request = NotificationRequest.create(
            notification_id=notification_id,
            userid=userid,
            notification_type=NotificationType.EMAIL_VERIFICATION,
            recipient_email="test@example.com",
            subject="Test Subject",
            content="Test content"
        )

        fake_unit_of_work.notification_requests.add(notification_request)
        retrieved = fake_unit_of_work.notification_requests.get(notification_id)

        assert retrieved is not None
        assert retrieved.notification_id.value == notification_id
        assert retrieved.subject == "Test Subject"
        assert retrieved.content == "Test content"

    def test_notification_status_transitions(self, fake_unit_of_work):
        """Test notification status transitions"""
        notification_id = uuid4().hex

        notification_request = NotificationRequest.create(
            notification_id=notification_id,
            userid=uuid4().hex,
            notification_type=NotificationType.PASSWORD_RESET,
            recipient_email="test@example.com",
            subject="Password Reset",
            content="Reset your password"
        )

        # Initially pending
        assert notification_request.status.value == 'pending'

        fake_unit_of_work.notification_requests.add(notification_request)

        # Mark as sent
        notification_request.mark_as_sent()
        assert notification_request.status.value == 'sent'

        # Verify it's still accessible
        retrieved = fake_unit_of_work.notification_requests.get(notification_id)
        assert retrieved.status.value == 'sent'

    def test_notification_failure_and_retry(self, fake_unit_of_work):
        """Test notification failure and retry mechanism"""
        notification_id = uuid4().hex

        notification_request = NotificationRequest.create(
            notification_id=notification_id,
            userid=uuid4().hex,
            notification_type=NotificationType.EMAIL_VERIFICATION,
            recipient_email="test@example.com",
            subject="Email Verification",
            content="Verify content"
        )

        fake_unit_of_work.notification_requests.add(notification_request)

        # Mark as failed
        notification_request.mark_as_failed("SMTP server unavailable")
        assert notification_request.status.value == 'failed'
        assert notification_request.retry_count == 0

        # Check if can retry when in FAILED status
        assert notification_request.can_retry(max_retries=3) is True

        # Increment retry count
        notification_request.increment_retry()
        assert notification_request.retry_count == 1
        assert notification_request.status.value == 'retrying'

        # After increment_retry, status is RETRYING, so can_retry should be False
        # This matches the domain logic: you can only retry FAILED notifications
        assert notification_request.can_retry(max_retries=3) is False

    def test_failed_notifications_query(self, fake_unit_of_work):
        """Test querying failed notifications for retry"""
        # Create multiple notification requests with different statuses
        failed_notifications = []

        for i in range(5):
            notification_request = NotificationRequest.create(
                notification_id=uuid4().hex,
                userid=uuid4().hex,
                notification_type=NotificationType.SECURITY_ALERT,
                recipient_email=f"user{i}@example.com",
                subject=f"Alert {i}",
                content="Security alert content"
            )

            if i < 3:  # Mark first 3 as failed
                notification_request.mark_as_failed("Email delivery failed")
                failed_notifications.append(notification_request)
            else:  # Mark last 2 as sent
                notification_request.mark_as_sent()

            fake_unit_of_work.notification_requests.add(notification_request)

        # Query failed notifications
        retrieved_failed = fake_unit_of_work.notification_requests.get_failed_notifications()

        assert len(retrieved_failed) == 3
        for notification in retrieved_failed:
            assert notification.status.value == 'failed'
            assert notification.retry_count < 3


class TestRepositoryTransactions:
    """Test repository transaction behavior using fake implementations"""

    def test_unit_of_work_commit_behavior(self, fake_unit_of_work):
        """Test unit of work commit behavior"""
        userid = uuid4().hex

        preferences = NotificationPreferences.create(
            userid=userid,
            notification_email="test@example.com",
            preferences={'email_verification': True}
        )

        # Before commit
        assert fake_unit_of_work.committed is False

        fake_unit_of_work.notification_preferences.add(preferences)
        fake_unit_of_work.commit()

        # After commit
        assert fake_unit_of_work.committed is True

        # Verify data is accessible
        retrieved = fake_unit_of_work.notification_preferences.get(userid)
        assert retrieved is not None

    def test_rollback_behavior(self, fake_unit_of_work):
        """Test rollback behavior"""
        userid = uuid4().hex

        preferences = NotificationPreferences.create(
            userid=userid,
            notification_email="test@example.com"
        )

        fake_unit_of_work.notification_preferences.add(preferences)
        fake_unit_of_work.rollback()

        # After rollback, committed should still be False
        assert fake_unit_of_work.committed is False
