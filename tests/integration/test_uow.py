from uuid import uuid4
from src.domain.model import NotificationPreferences, NotificationRequest, NotificationType


class TestUnitOfWorkBehavior:
    """Integration tests for unit of work behavior"""

    def test_unit_of_work_can_save_preferences(self, fake_unit_of_work):
        """Test that unit of work can save notification preferences"""
        userid = uuid4().hex
        preferences = NotificationPreferences.create(
            userid=userid,
            notification_email="test@example.com",
            preferences={'email_verification': True}
        )

        fake_unit_of_work.notification_preferences.add(preferences)
        fake_unit_of_work.commit()

        retrieved = fake_unit_of_work.notification_preferences.get(userid)
        assert retrieved is not None
        assert retrieved.notification_email.value == "test@example.com"
        assert fake_unit_of_work.committed is True

    def test_unit_of_work_can_save_notification_requests(self, fake_unit_of_work):
        """Test that unit of work can save notification requests"""
        notification_id = uuid4().hex
        notification_request = NotificationRequest.create(
            notification_id=notification_id,
            userid=uuid4().hex,
            notification_type=NotificationType.EMAIL_VERIFICATION,
            recipient_email="test@example.com",
            subject="Test Subject",
            content="Test content"
        )

        fake_unit_of_work.notification_requests.add(notification_request)
        fake_unit_of_work.commit()

        retrieved = fake_unit_of_work.notification_requests.get(notification_id)
        assert retrieved is not None
        assert retrieved.subject == "Test Subject"
        assert fake_unit_of_work.committed is True

    def test_unit_of_work_rollback_behavior(self, fake_unit_of_work):
        """Test unit of work rollback mechanism"""
        userid = uuid4().hex
        preferences = NotificationPreferences.create(
            userid=userid,
            notification_email="test@example.com",
            preferences={'email_verification': True}
        )

        fake_unit_of_work.notification_preferences.add(preferences)
        # Rollback instead of commit
        fake_unit_of_work.rollback()

        # Should still be able to retrieve (in fake implementation)
        # but committed flag should be False
        assert fake_unit_of_work.committed is False

    def test_multiple_operations_in_single_transaction(self, fake_unit_of_work):
        """Test multiple operations in single unit of work transaction"""
        userid = uuid4().hex
        notification_id = uuid4().hex

        preferences = NotificationPreferences.create(
            userid=userid,
            notification_email="test@example.com",
            preferences={'email_verification': True}
        )

        notification_request = NotificationRequest.create(
            notification_id=notification_id,
            userid=userid,
            notification_type=NotificationType.SECURITY_ALERT,
            recipient_email="test@example.com",
            subject="Security Alert",
            content="Your account was accessed"
        )

        # Add both in same transaction
        fake_unit_of_work.notification_preferences.add(preferences)
        fake_unit_of_work.notification_requests.add(notification_request)
        fake_unit_of_work.commit()

        # Verify both were saved
        retrieved_prefs = fake_unit_of_work.notification_preferences.get(userid)
        retrieved_request = fake_unit_of_work.notification_requests.get(notification_id)

        assert retrieved_prefs is not None
        assert retrieved_request is not None
        assert retrieved_prefs.userid.value == userid
        assert retrieved_request.notification_id.value == notification_id
        assert fake_unit_of_work.committed is True


class TestUnitOfWorkWithDomainEvents:
    """Test unit of work behavior with domain events"""

    def test_preferences_creation_generates_events(self, fake_unit_of_work):
        """Test that creating preferences generates domain events"""
        userid = uuid4().hex
        preferences = NotificationPreferences.create(
            userid=userid,
            notification_email="test@example.com"
        )

        # Check that events were generated
        assert len(preferences.events) > 0

        fake_unit_of_work.notification_preferences.add(preferences)
        fake_unit_of_work.commit()

        # Events should still be present
        retrieved = fake_unit_of_work.notification_preferences.get(userid)
        assert retrieved is not None

    def test_notification_request_events(self, fake_unit_of_work):
        """Test that notification requests generate appropriate events"""
        notification_id = uuid4().hex
        notification_request = NotificationRequest.create(
            notification_id=notification_id,
            userid=uuid4().hex,
            notification_type=NotificationType.EMAIL_VERIFICATION,
            recipient_email="test@example.com",
            subject="Test",
            content="Test content"
        )

        # Check initial events
        initial_event_count = len(notification_request.events)
        assert initial_event_count > 0

        # Mark as sent should generate additional event
        notification_request.mark_as_sent()
        assert len(notification_request.events) > initial_event_count

        # Mark as failed should generate another event
        notification_request.mark_as_failed("Test failure")
        assert len(notification_request.events) > initial_event_count + 1
