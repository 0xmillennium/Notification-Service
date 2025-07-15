from abc import ABC, abstractmethod
from typing import Set, Union, Any
from sqlalchemy.orm import Session
from src.domain.model import UserID, NotificationPreferences, NotificationRequest, NotificationID


class AbstractNotificationPreferencesRepository(ABC):
    """Abstract repository for notification preferences."""

    def __init__(self):
        self.seen = set()  # type: Set[NotificationPreferences]

    def add(self, preferences: NotificationPreferences):
        """
        Adds notification preferences to the repository and marks it as seen.
        """
        self._add(preferences)
        self.seen.add(preferences)

    def get(self, userid: Union[UserID, str]) -> NotificationPreferences | None:
        """
        Retrieves notification preferences by user ID and marks it as seen if found.
        """
        preferences = self._get(userid)
        if preferences:
            self.seen.add(preferences)
        return preferences

    @abstractmethod
    def _add(self, preferences: NotificationPreferences):
        """
        Abstract method to add notification preferences to the persistence layer.
        """
        raise NotImplementedError

    @abstractmethod
    def _get(self, userid: Union[UserID, str]) -> NotificationPreferences | None:
        """
        Abstract method to retrieve notification preferences by user ID from the persistence layer.
        """
        raise NotImplementedError


class AbstractNotificationRequestRepository(ABC):
    """Abstract repository for notification requests."""

    def __init__(self):
        self.seen = set()  # type: Set[NotificationRequest]

    def add(self, request: NotificationRequest):
        """
        Adds a notification request to the repository and marks it as seen.
        """
        self._add(request)
        self.seen.add(request)

    def get(self, notification_id: Union[NotificationID, str]) -> NotificationRequest | None:
        """
        Retrieves a notification request by its ID and marks it as seen if found.
        """
        request = self._get(notification_id)
        if request:
            self.seen.add(request)
        return request

    @abstractmethod
    def _add(self, request: NotificationRequest):
        """
        Abstract method to add a notification request to the persistence layer.
        """
        raise NotImplementedError

    @abstractmethod
    def _get(self, notification_id: Union[NotificationID, str]) -> NotificationRequest | None:
        """
        Abstract method to retrieve a notification request by ID from the persistence layer.
        """
        raise NotImplementedError

    @abstractmethod
    def get_failed_notifications(self, max_retry_count: int = 3) -> list[NotificationRequest]:
        """Get failed notifications that can be retried."""
        pass


class SqlAlchemyNotificationPreferencesRepository(AbstractNotificationPreferencesRepository):
    """SQLAlchemy implementation for notification preferences."""

    def __init__(self, session: Session):
        """
        Initializes the SQLAlchemy notification preferences repository with a database session.
        """
        super().__init__()
        self.session = session

    def _add(self, preferences: NotificationPreferences):
        """
        Adds notification preferences to the SQLAlchemy session.
        """
        self.session.add(preferences)

    def _get(self, userid: Union[UserID, str]) -> NotificationPreferences | None:
        """
        Retrieves notification preferences by user ID from the database using SQLAlchemy.
        """
        userid = userid if isinstance(userid, UserID) else UserID(userid)
        return (self.session.query(NotificationPreferences)
                .filter(NotificationPreferences.userid == userid)
                .first())


class SqlAlchemyNotificationRequestRepository(AbstractNotificationRequestRepository):
    """SQLAlchemy implementation for notification requests."""

    def __init__(self, session: Session):
        """
        Initializes the SQLAlchemy notification request repository with a database session.
        """
        super().__init__()
        self.session = session

    def _add(self, request: NotificationRequest):
        """
        Adds a notification request to the SQLAlchemy session.
        """
        self.session.add(request)

    def _get(self, notification_id: Union[NotificationID, str]) -> NotificationRequest | None:
        """
        Retrieves a notification request by ID from the database using SQLAlchemy.
        """
        notification_id = notification_id if isinstance(notification_id, NotificationID) else NotificationID(notification_id)
        return self.session.query(NotificationRequest).filter(
            NotificationRequest.notification_id == notification_id
        ).first()

    def get_failed_notifications(self, max_retry_count: int = 3) -> list[NotificationRequest]:
        """Get failed notifications that can be retried."""
        from src.domain.model import NotificationStatus
        return (
            self.session.query(NotificationRequest)
            .filter(
                NotificationRequest.status == NotificationStatus.FAILED,
                NotificationRequest.retry_count < max_retry_count
            )
            .all()
        )

    def get_notification_history(self, userid: Union[UserID, str], limit: int) -> list[NotificationRequest]:
        """
        Get notification history for a user, ordered by creation date descending.

        Args:
            userid: The user ID to get history for
            limit: Maximum number of notifications to return

        Returns:
            List of NotificationRequest objects
        """
        userid = userid if isinstance(userid, UserID) else UserID(userid)
        return (
            self.session.query(NotificationRequest)
            .filter(NotificationRequest.userid == userid)
            .order_by(NotificationRequest.created_at.desc())
            .limit(limit)
            .all()
        )
