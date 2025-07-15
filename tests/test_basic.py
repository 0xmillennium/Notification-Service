# tests/test_basic.py
"""Basic test to verify test infrastructure works"""

def test_basic_functionality():
    """Simple test to verify pytest is working"""
    assert 1 + 1 == 2

def test_imports():
    """Test that we can import our modules"""
    from src.domain.model import NotificationPreferences, NotificationType
    assert NotificationPreferences is not None
    assert NotificationType is not None
