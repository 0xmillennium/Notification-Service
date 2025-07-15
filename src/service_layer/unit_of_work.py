import abc
from sqlalchemy.orm.session import Session
from src.adapters.database import repository


class AbstractUnitOfWork(abc.ABC):
    """
    Abstract base class for a Unit of Work.

    Manages a business transaction, ensuring atomicity and providing a way
    to collect domain events from notification aggregates.
    """

    notification_preferences: repository.AbstractNotificationPreferencesRepository
    notification_requests: repository.AbstractNotificationRequestRepository

    def __enter__(self):
        """
        Enters the context for the Unit of Work.
        """
        return self

    def __exit__(self, *args):
        """
        Exits the context for the Unit of Work, ensuring rollback on exit.
        """
        self.rollback()

    def commit(self):
        """
        Commits changes made within the unit of work.
        """
        self._commit()

    def collect_new_events(self):
        """
        Collects new domain events from tracked notification aggregates.
        """
        for preferences in self.notification_preferences.seen:
            while preferences.events:
                yield preferences.events.pop(0)

        for request in self.notification_requests.seen:
            while request.events:
                yield request.events.pop(0)

    @abc.abstractmethod
    def _commit(self):
        """
        Abstract method to commit database changes.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def rollback(self):
        """
        Abstract method to roll back database changes.
        """
        raise NotImplementedError


class SqlAlchemyUnitOfWork(AbstractUnitOfWork):
    """
    SQLAlchemy implementation of the Unit of Work.

    Manages SQLAlchemy sessions and provides notification repositories.
    """

    def __init__(self, session_factory):
        """
        Initializes the SQLAlchemy Unit of Work.

        Args:
            session_factory (Callable[[], Session]): A callable that creates a new SQLAlchemy Session.
        """
        self.session_factory = session_factory

    def __enter__(self):
        """
        Enters the SQLAlchemy Unit of Work context, creating a session and notification repositories.
        """
        self.session = self.session_factory()  # type: Session
        self.notification_preferences = repository.SqlAlchemyNotificationPreferencesRepository(self.session)
        self.notification_requests = repository.SqlAlchemyNotificationRequestRepository(self.session)
        return super().__enter__()

    def __exit__(self, *args):
        """
        Exits the SQLAlchemy Unit of Work context, rolling back and closing the session.
        """
        super().__exit__(*args)
        self.session.close()

    def _commit(self):
        """
        Commits the current SQLAlchemy session.
        """
        self.session.commit()

    def rollback(self):
        """
        Rolls back the current SQLAlchemy session.
        """
        self.session.rollback()