import uuid
from sqlalchemy.orm import reconstructor
from typing import Annotated, Dict, Optional
from pydantic.dataclasses import dataclass
from pydantic import EmailStr, Field
from src.core.events import events
from enum import Enum


@dataclass(frozen=True)
class BaseValueObject:
    # def __composite_values__(self) -> tuple[Any, ...]:
    #     return tuple(getattr(self, field.name) for field in fields(self))
    #
    # def __eq__(self, other):
    #     return isinstance(other, type(self)) and all(getattr(self, field.name) == getattr(other, field.name) for field in fields(self))
    #
    # def __ne__(self, other):
    #     return not self.__eq__(other)
    ...


@dataclass(frozen=True)
class UserID(BaseValueObject):
    """Value object representing a user ID from external user service."""
    value: Annotated[
        str,
        Field(pattern=r"^[0-9a-f]{32}$")
    ]


@dataclass(frozen=True)
class NotificationEmail(BaseValueObject):
    """Value object for notification email addresses."""
    value: EmailStr


@dataclass(frozen=True)
class NotificationID(BaseValueObject):
    """Value object for notification request identifiers."""
    value: Annotated[
        str,
        Field(pattern=r"^[0-9a-f]{32}$")
    ]


@dataclass(frozen=True)
class PreferenceSettings(BaseValueObject):
    """Value object for notification preference settings."""
    email_verification: bool = True
    password_reset: bool = True
    welcome: bool = True
    security_alert: bool = True

    def to_dict(self):
        """Convert PreferenceSettings to dictionary for external use."""
        return {
            "email_verification": self.email_verification,
            "password_reset": self.password_reset,
            "welcome": self.welcome,
            "security_alert": self.security_alert
        }


class NotificationType(str, Enum):
    """Enumeration of available notification types."""
    EMAIL_VERIFICATION = "email_verification"
    PASSWORD_RESET = "password_reset"
    WELCOME = "welcome"
    SECURITY_ALERT = "security_alert"


class NotificationStatus(str, Enum):
    """Enumeration of notification request statuses."""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    RETRYING = "retrying"


class NotificationPreferences:
    """
    Aggregate root for managing user notification preferences.

    This aggregate manages a user's notification settings including
    their preferred notification email and which types of notifications
    they want to receive.
    """

    def __init__(self,
                 userid: UserID,
                 notification_email: NotificationEmail,
                 preferences: PreferenceSettings):
        self.userid = userid
        self.notification_email = notification_email
        self.preferences = preferences
        self.events = []

    @reconstructor
    def init_on_load(self):
        self.events = []

    @classmethod
    def create(cls,
               userid: str,
               notification_email: EmailStr,
               preferences: Dict[str, bool] = None):
        """
        Factory method to create new NotificationPreferences.

        Args:
            userid: User identifier from external user service
            notification_email: Email address for notifications
            preferences: Dict of notification types and their enabled status
        """
        if preferences is None:
            preferences = {nt.value: True for nt in NotificationType}

        settings = PreferenceSettings(
            email_verification=preferences.get(NotificationType.EMAIL_VERIFICATION.value, True),
            password_reset=preferences.get(NotificationType.PASSWORD_RESET.value, True),
            welcome=preferences.get(NotificationType.WELCOME.value, True),
            security_alert=preferences.get(NotificationType.SECURITY_ALERT.value, True)
        )

        prefs = cls(
            UserID(userid),
            NotificationEmail(notification_email),
            settings
        )

        prefs.events.append(
            events.NotificationPreferencesCreated(
                userid=userid,
                notification_email=notification_email,
                preferences=cls._preferences_to_dict(settings)
            )
        )
        return prefs

    def update_preferences(self, new_preferences: Dict[str, bool]):
        """
        Update notification preferences and raise an event.

        Args:
            new_preferences: Dictionary of notification types and their enabled status
        """
        settings = PreferenceSettings(
            email_verification=new_preferences.get(NotificationType.EMAIL_VERIFICATION.value, True),
            password_reset=new_preferences.get(NotificationType.PASSWORD_RESET.value, True),
            welcome=new_preferences.get(NotificationType.WELCOME.value, True),
            security_alert=new_preferences.get(NotificationType.SECURITY_ALERT.value, True)
        )
        self.preferences = settings
        self.events.append(
            events.NotificationPreferencesUpdated(
                userid=self.userid.value,
                notification_email=self.notification_email.value,
                preferences=self._preferences_to_dict(settings)
            )
        )

    def update_email(self, new_email: EmailStr):
        """Update notification email address."""
        self.notification_email = NotificationEmail(new_email)

    def is_notification_enabled(self, notification_type: NotificationType) -> bool:
        """Check if a specific notification type is enabled for this user."""
        return getattr(self.preferences, notification_type.value, True)

    @staticmethod
    def _preferences_to_dict(preferences: PreferenceSettings) -> Dict[str, bool]:
        """Convert PreferenceSettings to dictionary for external use."""
        return {
            NotificationType.EMAIL_VERIFICATION.value: preferences.email_verification,
            NotificationType.PASSWORD_RESET.value: preferences.password_reset,
            NotificationType.WELCOME.value: preferences.welcome,
            NotificationType.SECURITY_ALERT.value: preferences.security_alert
        }


class NotificationRequest:
    """
    Entity representing a notification request.

    Tracks the lifecycle of a notification from creation through
    delivery attempts, including retry logic and status tracking.
    """

    def __init__(self,
                 notification_id: NotificationID,
                 userid: UserID,
                 notification_type: NotificationType,
                 recipient_email: NotificationEmail,
                 subject: str,
                 content: str,
                 template_vars: Dict = None,
                 status: NotificationStatus = NotificationStatus.PENDING,
                 retry_count: int = 0):
        self.notification_id = notification_id
        self.userid = userid
        self.notification_type = notification_type
        self.recipient_email = recipient_email
        self.subject = subject
        self.content = content
        self.template_vars = template_vars or {}
        self.status = status
        self.retry_count = retry_count
        self.events = []

    @reconstructor
    def init_on_load(self):
        self.events = []

    @classmethod
    def create(cls,
               notification_id: str,
               userid: str,
               notification_type: NotificationType,
               recipient_email: EmailStr,
               subject: str,
               content: str,
               template_vars: Dict = None):
        """Factory method to create a new NotificationRequest."""
        request = cls(
            NotificationID(notification_id),
            UserID(userid),
            notification_type,
            NotificationEmail(recipient_email),
            subject,
            content,
            template_vars
        )
        return request

    def mark_as_sent(self):
        """Mark notification as successfully sent."""
        self.status = NotificationStatus.SENT
        self.events.append(
            events.NotificationSent(
                notification_id=self.notification_id.value,
                userid=self.userid.value,
                notification_type=self.notification_type.value
            )
        )

    def mark_as_failed(self, error_message: str):
        """Mark notification as failed and emit domain event."""
        self.status = NotificationStatus.FAILED
        self.events.append(
            events.NotificationFailed(
                notification_id=self.notification_id.value,
                userid=self.userid.value,
                notification_type=self.notification_type,
                error_message=error_message,
                retry_count=self.retry_count
            )
        )

    def increment_retry(self):
        """Increment retry count and mark as retrying."""
        self.retry_count += 1
        self.status = NotificationStatus.RETRYING

    def can_retry(self, max_retries: int = 3) -> bool:
        """Check if notification can be retried based on retry count."""
        return self.retry_count < max_retries
