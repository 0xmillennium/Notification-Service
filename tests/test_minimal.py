"""Minimal test to verify pytest works at all"""

def test_pytest_is_working():
    """Most basic test possible"""
    assert True

def test_simple_math():
    """Test basic operations"""
    assert 2 + 2 == 4
    assert 10 - 5 == 5

def test_string_operations():
    """Test string operations"""
    assert "hello" + " world" == "hello world"
    assert len("test") == 4
