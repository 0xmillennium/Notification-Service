from pydantic import EmailStr, Field
from pydantic.dataclasses import dataclass
from uuid import UUID, uuid4
from datetime import datetime, timezone
from src.core.correlation.context import get_correlation_id
from typing import Dict


@dataclass(kw_only=True)
class Event:
    source_service: str = "notification"
    event_id: UUID = Field(default_factory=uuid4)
    correlation_id: str = Field(default_factory=get_correlation_id)
    timestamp: float = Field(default_factory=lambda: datetime.now(tz=timezone.utc).timestamp())


@dataclass(kw_only=True)
class IncomingEvent(Event):
    """Events that the notification service receives from other services."""
    ...


@dataclass(kw_only=True)
class OutgoingEvent(Event):
    """Events that the notification service publishes to other services."""
    ...


# Incoming events that notification service subscribes to
@dataclass(kw_only=True)
class UserEmailVerificationRequested(IncomingEvent):
    """Event received when user service requests email verification."""
    userid: str
    username: str
    email: EmailStr
    verify_token: str
    event_type: str = "user.email_verification_requested"


@dataclass(kw_only=True)
class UserRegistered(IncomingEvent):
    """Event received when a new user registers."""
    userid: str
    username: str
    email: EmailStr
    event_type: str = "user.registered"


@dataclass(kw_only=True)
class PasswordResetRequested(IncomingEvent):
    """Event received when user requests password reset."""
    userid: str
    email: EmailStr
    reset_token: str
    event_type: str = "user.password_reset_requested"


# Outgoing events that notification service publishes
@dataclass(kw_only=True)
class NotificationPreferencesCreated(IncomingEvent):
    """Event published when notification preferences are created."""
    userid: str
    notification_email: EmailStr
    preferences: Dict[str, bool]
    event_type: str = "notification.preferences_created"


@dataclass(kw_only=True)
class NotificationPreferencesUpdated(IncomingEvent):
    """Event published when notification preferences are updated."""
    userid: str
    notification_email: EmailStr
    preferences: Dict[str, bool]
    event_type: str = "notification.preferences_updated"


@dataclass(kw_only=True)
class NotificationSent(OutgoingEvent):
    """Event published when a notification is successfully sent."""
    notification_id: str
    userid: str
    notification_type: str
    event_type: str = "notification.sent"


@dataclass(kw_only=True)
class NotificationFailed(OutgoingEvent):
    """Event published when a notification fails to send."""
    notification_id: str
    userid: str
    notification_type: str
    error_message: str
    retry_count: int
    event_type: str = "notification.failed"
