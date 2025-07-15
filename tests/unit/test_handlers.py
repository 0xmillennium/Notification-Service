import pytest
from uuid import uuid4
from unittest.mock import Mock, patch
from src.domain.model import NotificationPreferences, NotificationRequest, NotificationType
from src.domain.commands import (
    UpdateNotificationPreferencesCommand,
    SendNotificationCommand,
    RetryFailedNotificationCommand
)


class TestNotificationDomainModel:
    """Unit tests for notification domain models"""

    def test_notification_preferences_creation(self):
        """Test creating notification preferences"""
        userid = uuid4().hex
        email = "test@example.com"

        preferences = NotificationPreferences.create(
            userid=userid,
            notification_email=email
        )

        assert preferences.userid.value == userid
        assert preferences.notification_email.value == email
        assert len(preferences.events) > 0  # Should generate creation event

    def test_notification_preferences_with_custom_settings(self):
        """Test creating preferences with custom notification settings"""
        userid = uuid4().hex
        custom_prefs = {
            'email_verification': True,
            'security_alert': False,
            'marketing': True,
            'password_reset': True
        }

        preferences = NotificationPreferences.create(
            userid=userid,
            notification_email="custom@example.com",
            preferences=custom_prefs
        )

        # Test specific notification type checks
        assert preferences.is_notification_enabled(NotificationType.EMAIL_VERIFICATION) is True
        assert preferences.is_notification_enabled(NotificationType.SECURITY_ALERT) is False
        assert preferences.is_notification_enabled(NotificationType.PASSWORD_RESET) is True

    def test_notification_preferences_email_update(self):
        """Test updating notification email"""
        preferences = NotificationPreferences.create(
            userid=uuid4().hex,
            notification_email="old@example.com"
        )

        new_email = "new@example.com"
        preferences.update_email(new_email)

        assert preferences.notification_email.value == new_email

    def test_notification_preferences_settings_update(self):
        """Test updating notification preferences"""
        preferences = NotificationPreferences.create(
            userid=uuid4().hex,
            notification_email="test@example.com"
        )

        new_preferences = {
            'email_verification': False,
            'security_alert': True,
            'marketing': False
        }

        initial_event_count = len(preferences.events)
        preferences.update_preferences(new_preferences)

        # Should generate update event
        assert len(preferences.events) > initial_event_count
        assert preferences.is_notification_enabled(NotificationType.EMAIL_VERIFICATION) is False
        assert preferences.is_notification_enabled(NotificationType.SECURITY_ALERT) is True


class TestNotificationRequest:
    """Unit tests for notification request model"""

    def test_notification_request_creation(self):
        """Test creating notification request"""
        notification_id = uuid4().hex
        userid = uuid4().hex

        request = NotificationRequest.create(
            notification_id=notification_id,
            userid=userid,
            notification_type=NotificationType.EMAIL_VERIFICATION,
            recipient_email="test@example.com",
            subject="Test Subject",
            content="Test content"
        )

        assert request.notification_id.value == notification_id
        assert request.userid.value == userid
        assert request.status.value == 'pending'
        assert request.retry_count == 0
        assert len(request.events) > 0

    def test_notification_request_status_transitions(self):
        """Test notification status transitions"""
        request = NotificationRequest.create(
            notification_id=uuid4().hex,
            userid=uuid4().hex,
            notification_type=NotificationType.PASSWORD_RESET,
            recipient_email="test@example.com",
            subject="Password Reset",
            content="Reset your password"
        )

        # Test marking as sent
        initial_events = len(request.events)
        request.mark_as_sent()

        assert request.status.value == 'sent'
        assert len(request.events) > initial_events

    def test_notification_request_failure_handling(self):
        """Test notification failure handling"""
        request = NotificationRequest.create(
            notification_id=uuid4().hex,
            userid=uuid4().hex,
            notification_type=NotificationType.SECURITY_ALERT,
            recipient_email="test@example.com",
            subject="Security Alert",
            content="Alert content"
        )

        # Test marking as failed
        error_message = "SMTP server unavailable"
        initial_events = len(request.events)
        request.mark_as_failed(error_message)

        assert request.status.value == 'failed'
        assert len(request.events) > initial_events
        assert request.retry_count == 0  # Failure doesn't increment retry count

    def test_notification_request_retry_logic(self):
        """Test notification retry logic"""
        request = NotificationRequest.create(
            notification_id=uuid4().hex,
            userid=uuid4().hex,
            notification_type=NotificationType.EMAIL_VERIFICATION,  # Fixed: use existing type
            recipient_email="test@example.com",
            subject="Email Verification",
            content="Please verify your email"
        )

        # Mark as failed first
        request.mark_as_failed("Temporary failure")

        # Test can retry logic when in FAILED status
        assert request.can_retry(max_retries=3) is True
        assert request.retry_count == 0
        assert request.status.value == 'failed'

        # Test retry increment
        request.increment_retry()
        assert request.retry_count == 1
        assert request.status.value == 'retrying'

        # After increment_retry, status is RETRYING, so can_retry should be False
        # This matches the domain logic: you can only retry FAILED notifications
        assert request.can_retry(max_retries=3) is False

        # Mark as failed again to test multiple retries
        request.mark_as_failed("Another failure")
        assert request.can_retry(max_retries=3) is True  # Should be able to retry again

        # Test approaching retry limit
        request.increment_retry()  # retry_count = 2
        request.mark_as_failed("Third failure")
        assert request.retry_count == 2
        assert request.can_retry(max_retries=3) is True  # Still can retry

        request.increment_retry()  # retry_count = 3 (at max retries)
        assert request.retry_count == 3
        request.mark_as_failed("Final failure")

        # Now at max retries, should not be able to retry
        assert request.can_retry(max_retries=3) is False

    def test_notification_request_with_template_vars(self):
        """Test notification request with template variables"""
        template_vars = {
            'user_name': 'John Doe',
            'reset_link': 'https://example.com/reset/123'
        }

        request = NotificationRequest.create(
            notification_id=uuid4().hex,
            userid=uuid4().hex,
            notification_type=NotificationType.PASSWORD_RESET,
            recipient_email="john@example.com",
            subject="Password Reset for {user_name}",
            content="Click here to reset: {reset_link}",
            template_vars=template_vars
        )

        assert request.template_vars == template_vars


class TestNotificationCommands:
    """Unit tests for notification commands"""

    def test_update_notification_preferences_command(self):
        """Test UpdateNotificationPreferencesCommand"""
        command = UpdateNotificationPreferencesCommand(
            userid=uuid4().hex,
            notification_email="test@example.com",
            preferences={
                'email_verification': True,
                'marketing': False
            }
        )

        assert command.userid is not None
        assert command.notification_email == "test@example.com"
        assert command.preferences['email_verification'] is True
        assert command.preferences['marketing'] is False

    def test_send_notification_command(self):
        """Test SendNotificationCommand"""
        command = SendNotificationCommand(
            notification_id=uuid4().hex,
            userid=uuid4().hex,
            notification_type="email_verification",
            recipient_email="test@example.com",
            subject="Verify Email",
            content="Please verify your email"
        )

        assert command.notification_id is not None
        assert command.userid is not None
        assert command.notification_type == "email_verification"
        assert command.subject == "Verify Email"

    def test_retry_failed_notification_command(self):
        """Test RetryFailedNotificationCommand"""
        notification_id = uuid4().hex
        command = RetryFailedNotificationCommand(notification_id=notification_id)

        assert command.notification_id == notification_id


class TestNotificationBusinessLogic:
    """Unit tests for notification business logic"""

    def test_notification_eligibility_based_on_preferences(self):
        """Test notification eligibility based on user preferences"""
        userid = uuid4().hex

        # Create preferences with mixed settings
        preferences = NotificationPreferences.create(
            userid=userid,
            notification_email="user@example.com",
            preferences={
                'email_verification': True,
                'security_alert': True,
                'marketing': False,
                'password_reset': True
            }
        )

        # Test eligibility for different notification types
        test_cases = [
            (NotificationType.EMAIL_VERIFICATION, True),
            (NotificationType.SECURITY_ALERT, True),
            (NotificationType.PASSWORD_RESET, True),
            (NotificationType.WELCOME, True),  # Default to True if not specified
        ]

        for notification_type, expected_enabled in test_cases:
            actual_enabled = preferences.is_notification_enabled(notification_type)
            assert actual_enabled == expected_enabled, \
                f"Notification type {notification_type} should be {expected_enabled}, got {actual_enabled}"

    def test_notification_event_generation(self):
        """Test that domain events are properly generated"""
        # Test preference creation events
        preferences = NotificationPreferences.create(
            userid=uuid4().hex,
            notification_email="test@example.com"
        )
        assert len(preferences.events) > 0

        # Test preference update events
        initial_event_count = len(preferences.events)
        preferences.update_preferences({'marketing': False})
        assert len(preferences.events) > initial_event_count

        # Test notification request events
        request = NotificationRequest.create(
            notification_id=uuid4().hex,
            userid=uuid4().hex,
            notification_type=NotificationType.EMAIL_VERIFICATION,
            recipient_email="test@example.com",
            subject="Test",
            content="Test"
        )
        request_initial_events = len(request.events)

        # Status change should generate events
        request.mark_as_sent()
        assert len(request.events) > request_initial_events

        request.mark_as_failed("Test failure")
        assert len(request.events) > request_initial_events + 1
