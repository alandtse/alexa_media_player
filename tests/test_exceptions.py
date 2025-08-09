"""Test the exceptions module."""

import pytest

from custom_components.alexa_media.exceptions import (
    EmptyDataException,
    ForbiddenException,
    LoginForbiddenException,
    LoginInvalidException,
    TimeoutException,
    UnexpectedApiException,
)


def test_empty_data_exception():
    """Test EmptyDataException creation and inheritance."""
    exception = EmptyDataException("Test message")
    assert isinstance(exception, Exception)
    assert str(exception) == "Test message"


def test_forbidden_exception():
    """Test ForbiddenException creation and inheritance."""
    exception = ForbiddenException("Access denied")
    assert isinstance(exception, Exception)
    assert str(exception) == "Access denied"


def test_login_forbidden_exception():
    """Test LoginForbiddenException creation and inheritance."""
    exception = LoginForbiddenException("Login blocked")
    assert isinstance(exception, Exception)
    assert str(exception) == "Login blocked"


def test_login_invalid_exception():
    """Test LoginInvalidException with attempts remaining."""
    attempts = 3
    exception = LoginInvalidException(attempts)

    assert isinstance(exception, Exception)
    assert exception.attempts_remaining == attempts
    assert str(exception) == "Invalid login credentials. 3 attempts remaining."


def test_login_invalid_exception_zero_attempts():
    """Test LoginInvalidException with zero attempts remaining."""
    exception = LoginInvalidException(0)

    assert exception.attempts_remaining == 0
    assert str(exception) == "Invalid login credentials. 0 attempts remaining."


def test_timeout_exception_with_message():
    """Test TimeoutException with custom message."""
    message = "API call took too long"
    exception = TimeoutException(message)

    assert isinstance(exception, Exception)
    assert str(exception) == f"Timeour exception: {message}"


def test_timeout_exception_without_message():
    """Test TimeoutException with default empty message."""
    exception = TimeoutException()

    assert isinstance(exception, Exception)
    assert str(exception) == "Timeour exception: "


def test_unexpected_api_exception():
    """Test UnexpectedApiException creation and inheritance."""
    exception = UnexpectedApiException("Unexpected response")
    assert isinstance(exception, Exception)
    assert str(exception) == "Unexpected response"


def test_all_exceptions_are_raisable():
    """Test that all custom exceptions can be raised and caught."""
    exceptions_to_test = [
        (EmptyDataException, "empty"),
        (ForbiddenException, "forbidden"),
        (LoginForbiddenException, "login forbidden"),
        (LoginInvalidException, 2),
        (TimeoutException, "timeout"),
        (UnexpectedApiException, "unexpected"),
    ]

    for exception_class, arg in exceptions_to_test:
        with pytest.raises(exception_class):
            raise exception_class(arg)
