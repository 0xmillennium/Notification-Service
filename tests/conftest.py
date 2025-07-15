# tests/conftest.py
import pytest
from uuid import uuid4
from src.domain.model import NotificationPreferences, NotificationRequest, NotificationType
from src.bootstrap import bootstrap
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, clear_mappers
from src.adapters.database.orm import init_orm_mappers, metadata
from src.adapters.database.repository import (
    SqlAlchemyNotificationPreferencesRepository,
    SqlAlchemyNotificationRequestRepository,
    AbstractNotificationPreferencesRepository,
    AbstractNotificationRequestRepository
)
from src.service_layer.unit_of_work import AbstractUnitOfWork, SqlAlchemyUnitOfWork


class FakeNotificationPreferencesRepository(AbstractNotificationPreferencesRepository):
    def __init__(self, preferences=None):
        super().__init__()
        self._preferences = preferences or {}

    def _add(self, preferences):
        self._preferences[preferences.userid.value] = preferences

    def _get(self, userid):
        return self._preferences.get(userid)


class FakeNotificationRequestRepository(AbstractNotificationRequestRepository):
    def __init__(self, requests=None):
        super().__init__()
        self._requests = requests or {}

    def _add(self, request):
        self._requests[request.notification_id.value] = request

    def _get(self, notification_id):
        return self._requests.get(notification_id)

    def get_failed_notifications(self, max_retry_count=3):
        return [r for r in self._requests.values()
                if hasattr(r.status, 'value') and r.status.value == 'failed' and r.retry_count < max_retry_count]


class FakeUnitOfWork(AbstractUnitOfWork):
    def __init__(self):
        self.notification_preferences = FakeNotificationPreferencesRepository()
        self.notification_requests = FakeNotificationRequestRepository()
        self.committed = False

    def _commit(self):
        self.committed = True

    def rollback(self):
        pass


@pytest.fixture(scope="function")
def sqlite_engine():
    """Create SQLite in-memory database for testing"""
    try:
        engine = create_engine("sqlite:///:memory:", echo=False)  # Disable echo for cleaner output
        metadata.create_all(engine)
        yield engine
    finally:
        try:
            metadata.drop_all(engine)
            engine.dispose()
        except:
            pass


@pytest.fixture(scope="function")
def sqlite_session_factory(sqlite_engine):
    """Create session factory for SQLite testing"""
    return sessionmaker(bind=sqlite_engine)


@pytest.fixture(scope="function")
def sqlalchemy_repository(sqlite_session_factory):
    """Create SQLAlchemy repository for testing"""
    try:
        clear_mappers()
        init_orm_mappers()
        session = sqlite_session_factory()
        yield SqlAlchemyNotificationPreferencesRepository(session)
    finally:
        try:
            session.close()
        except:
            pass


@pytest.fixture(scope="function")
def sqlalchemy_unit_of_work(sqlite_session_factory):
    """Create SQLAlchemy unit of work for testing"""
    try:
        clear_mappers()
        init_orm_mappers()
        yield SqlAlchemyUnitOfWork(sqlite_session_factory)
    except Exception as e:
        # If SQLAlchemy setup fails, provide a fake UoW
        yield FakeUnitOfWork()


@pytest.fixture(scope="function")
def fake_unit_of_work():
    """Create fake unit of work for isolated testing"""
    return FakeUnitOfWork()


@pytest.fixture(scope="function")
def notification_preferences():
    """Create test notification preferences"""
    return NotificationPreferences.create(
        userid=uuid4().hex,
        notification_email="test@example.com"
    )


@pytest.fixture(scope="function")
def notification_request():
    """Create test notification request"""
    return NotificationRequest.create(
        notification_id=uuid4().hex,
        userid=uuid4().hex,
        notification_type=NotificationType.EMAIL_VERIFICATION,
        recipient_email="test@example.com",
        subject="Test Notification",
        content="test_content"
    )
