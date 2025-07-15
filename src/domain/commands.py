from pydantic import EmailStr
from pydantic.dataclasses import dataclass
from typing import Dict, Optional, Any


@dataclass(frozen=True)
class Command:
    """Base class for all commands in the notification service."""
    ...


@dataclass(frozen=True)
class CreateNotificationPreferencesCommand(Command):
    """Command to create initial user notification preferences."""
    userid: str
    notification_email: EmailStr
    preferences: Dict[str, bool]


@dataclass(frozen=True)
class UpdateNotificationPreferencesCommand(Command):
    """Command to update existing user notification preferences."""
    userid: str
    notification_email: EmailStr
    preferences: Dict[str, bool]


@dataclass(frozen=True)
class SendNotificationCommand(Command):
    """Command to send a notification to a user."""
    userid: str
    notification_type: str
    recipient_email: EmailStr
    subject: str
    content: str
    template_vars: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class RetryFailedNotificationCommand(Command):
    """Command to retry a failed notification."""
    notification_id: str
