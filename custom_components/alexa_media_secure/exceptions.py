"""Alexa Media Exceptions"""


class EmptyDataException(Exception):
    """Empty data exception"""


class ForbiddenException(Exception):
    """Forbidden exception"""


class LoginForbiddenException(Exception):
    """Login forbidden exception"""


class LoginInvalidException(Exception):
    """Invalid login exception"""

    def __init__(self, attempts_remaining):
        self.attempts_remaining = attempts_remaining
        super().__init__(
            f"Invalid login credentials. {attempts_remaining} attempts remaining."
        )


class TimeoutException(Exception):
    """Timeout exception"""

    def __init__(self, message=""):
        super().__init__(f"Timeout exception: {message}")


class UnexpectedApiException(Exception):
    """Unexpected API exception"""
