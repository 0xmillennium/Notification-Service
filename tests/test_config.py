# tests/test_config.py
"""Test configuration and utilities for notification service tests"""

import pytest
from unittest.mock import Mock, patch


class TestEmailProvider:
    """Mock email provider for testing"""

    def __init__(self):
        self.sent_emails = []
        self.should_fail = False
        self.failure_message = "Email sending failed"

    def send_email(self, to: str, subject: str, content: str, **kwargs) -> bool:
        if self.should_fail:
            raise Exception(self.failure_message)

        self.sent_emails.append({
            'to': to,
            'subject': subject,
            'content': content,
            'kwargs': kwargs
        })
        return True

    def get_sent_emails(self):
        return self.sent_emails.copy()

    def clear_sent_emails(self):
        self.sent_emails.clear()

    def set_failure_mode(self, should_fail: bool, message: str = "Email sending failed"):
        self.should_fail = should_fail
        self.failure_message = message


@pytest.fixture
def mock_email_provider():
    """Provide a mock email provider for testing"""
    return TestEmailProvider()


# Test data factories
class TestDataFactory:
    """Factory for creating test data"""

    @staticmethod
    def create_test_preferences(userid: str = None, **kwargs):
        """Create test notification preferences"""
        from uuid import uuid4
        from src.domain.model import NotificationPreferences

        defaults = {
            'userid': userid or uuid4().hex,
            'notification_email': 'test@example.com',
            'email_enabled': True,
            'marketing_enabled': False,
            'security_enabled': True
        }
        defaults.update(kwargs)

        return NotificationPreferences.create(**defaults)

    @staticmethod
    def create_test_notification_request(notification_id: str = None,
                                       userid: str = None, **kwargs):
        """Create test notification request"""
        from uuid import uuid4
        from src.domain.model import NotificationRequest, NotificationType

        defaults = {
            'notification_id': notification_id or uuid4().hex,
            'userid': userid or uuid4().hex,
            'notification_type': NotificationType.EMAIL_VERIFICATION,
            'recipient_email': 'test@example.com',
            'subject': 'Test Subject',
            'content': 'Test content'
        }
        defaults.update(kwargs)

        return NotificationRequest.create(**defaults)


@pytest.fixture
def test_data_factory():
    """Provide test data factory"""
    return TestDataFactory()


# Async test utilities
def async_test(coro):
    """Decorator to run async tests"""
    def wrapper(*args, **kwargs):
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro(*args, **kwargs))
        finally:
            loop.close()
    return wrapper


# Pytest markers for different test categories
pytest_plugins = []

def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "e2e: marks tests as end-to-end tests"
    )
    config.addinivalue_line(
        "markers", "performance: marks tests as performance tests"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow running"
    )
    config.addinivalue_line(
        "markers", "requires_broker: marks tests that require message broker"
    )
    config.addinivalue_line(
        "markers", "requires_database: marks tests that require database"
    )
