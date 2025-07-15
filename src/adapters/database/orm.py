from sqlalchemy import Column, MetaData, String, Table, DateTime, Integer, JSON, Boolean
from sqlalchemy.orm import composite, registry
import datetime


metadata = MetaData()
mapper_registry = registry()

notification_preferences_table = Table(
    "notification_preferences",
    metadata,
    Column("user_id", String(32), key="db_userid", primary_key=True),
    Column("notification_email", String(255), key="db_notification_email", nullable=False),
    Column("email_verification_enabled", Boolean, key="db_email_verification_enabled", nullable=False, default=True),
    Column("password_reset_enabled", Boolean, key="db_password_reset_enabled", nullable=False, default=True),
    Column("welcome_enabled", Boolean, key="db_welcome_enabled", nullable=False, default=True),
    Column("security_alert_enabled", Boolean, key="db_security_alert_enabled", nullable=False, default=True),
    Column("created_at", DateTime, key="db_created_at", default=datetime.datetime.utcnow),
    Column("updated_at", DateTime, key="db_updated_at", default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow),
)

notification_request_table = Table(
    "notification_request",
    metadata,
    Column("id", String(32), key="db_notification_id", primary_key=True),
    Column("user_id", String(32), key="db_userid", nullable=False),
    Column("notification_type", String(50), key="db_notification_type", nullable=False),
    Column("recipient_email", String(255), key="db_recipient_email", nullable=False),
    Column("subject", String(500), key="db_subject", nullable=False),
    Column("content", String(10000), key="db_content", nullable=False),
    Column("template_vars", JSON, key="db_template_vars"),
    Column("status", String(20), key="db_status", nullable=False),
    Column("retry_count", Integer, key="db_retry_count", default=0),
    Column("created_at", DateTime, key="db_created_at", default=datetime.datetime.now),
    Column("updated_at", DateTime, key="db_updated_at", default=datetime.datetime.now, onupdate=datetime.datetime.now),
)


def init_orm_mappers():
    """
    Initializes SQLAlchemy ORM mappers for notification domain models.

    Maps notification domain models to database tables using composite types for value objects.
    """
    from src.domain.model import (
        UserID, NotificationPreferences, NotificationEmail, PreferenceSettings,
        NotificationRequest, NotificationID, NotificationType, NotificationStatus
    )

    # Notification Preferences mapping
    mapper_registry.map_imperatively(
        NotificationPreferences,
        notification_preferences_table,
        properties={
            "userid": composite(UserID, notification_preferences_table.c.db_userid),
            "notification_email": composite(NotificationEmail, notification_preferences_table.c.db_notification_email),
            "preferences": composite(
                PreferenceSettings,
                notification_preferences_table.c.db_email_verification_enabled,
                notification_preferences_table.c.db_password_reset_enabled,
                notification_preferences_table.c.db_welcome_enabled,
                notification_preferences_table.c.db_security_alert_enabled
            ),
        }
    )

    # Notification Request mapping
    mapper_registry.map_imperatively(
        NotificationRequest,
        notification_request_table,
        properties={
            "notification_id": composite(NotificationID, notification_request_table.c.db_notification_id),
            "userid": composite(UserID, notification_request_table.c.db_userid),
            "notification_type": notification_request_table.c.db_notification_type,
            "recipient_email": composite(NotificationEmail, notification_request_table.c.db_recipient_email),
            "subject": notification_request_table.c.db_subject,
            "content": notification_request_table.c.db_content,
            "template_vars": notification_request_table.c.db_template_vars,
            "status": notification_request_table.c.db_status,
            "retry_count": notification_request_table.c.db_retry_count,
            "created_at": notification_request_table.c.db_created_at,
            "updated_at": notification_request_table.c.db_updated_at,
        }
    )
