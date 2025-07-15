import logging

from src.adapters.message_broker import publisher
from src.domain import commands
from src.service_layer import unit_of_work
from src.adapters.email_provider import AbstractEmailProvider
from src.domain.model import NotificationPreferences, NotificationRequest, NotificationType, NotificationStatus
from src.core.events import events
from uuid import uuid4

logger = logging.getLogger(__name__)


async def create_notification_preferences_handler(
    cmd: commands.CreateNotificationPreferencesCommand,
    puow: unit_of_work.AbstractUnitOfWork
):
    """
    Handles creating new notification preferences.
    """
    with puow:
        preferences = NotificationPreferences.create(
            userid=cmd.userid,
            notification_email=cmd.notification_email,
            preferences=cmd.preferences
        )
        puow.notification_preferences.add(preferences)
        puow.commit()
        logger.info(f"Created notification preferences for user: {cmd.userid}")


async def update_notification_preferences_handler(
    cmd: commands.UpdateNotificationPreferencesCommand,
    puow: unit_of_work.AbstractUnitOfWork
):
    """
    Handles updating existing notification preferences.
    """
    with puow:
        existing_preferences = puow.notification_preferences.get(cmd.userid)
        if not existing_preferences:
            logger.error(f"Cannot update non-existent preferences for user: {cmd.userid}")
            raise ValueError(f"Notification preferences not found for user: {cmd.userid}")

        existing_preferences.update_preferences(cmd.preferences)
        puow.commit()
        logger.info(f"Updated notification preferences for user: {cmd.userid}")


async def send_notification_handler(
        cmd: commands.SendNotificationCommand,
        puow: unit_of_work.AbstractUnitOfWork,
        ntfy: AbstractEmailProvider
):
    """
    Handles sending notifications via email.

    Checks user preferences, creates notification request, and attempts to send email.
    """
    with puow:
        # Check if user has notification preferences and if this type is enabled
        preferences = puow.notification_preferences.get(cmd.userid)
        if preferences:
            notification_type = NotificationType(cmd.notification_type)
            if not preferences.is_notification_enabled(notification_type):
                logger.info(f"Notification {cmd.notification_type} disabled for user {cmd.userid}")
                return

        # Create notification request
        request = NotificationRequest.create(
            notification_id=uuid4().hex,
            userid=cmd.userid,
            notification_type=NotificationType(cmd.notification_type),
            recipient_email=cmd.recipient_email,
            subject=cmd.subject,
            content=cmd.content,
            template_vars=cmd.template_vars
        )

        puow.notification_requests.add(request)

        while request.can_retry():
            # Attempt to send email
            success = await ntfy.send_email(
                to_email=str(cmd.recipient_email),
                subject=cmd.subject,
                content=cmd.content,
                template_vars=cmd.template_vars
            )

            if success:
                request.mark_as_sent()
                logger.info(f"Notification {request.notification_id} sent successfully")
                break
            else:
                request.mark_as_failed("Failed to send email")
                logger.error(f"Failed to send notification {request.notification_id}")
                request.increment_retry()

        puow.commit()


async def retry_failed_notification_handler(
        cmd: commands.RetryFailedNotificationCommand,
        puow: unit_of_work.AbstractUnitOfWork,
        ntfy: AbstractEmailProvider
):
    """
    Handles retrying failed notifications with exponential backoff.
    """
    with puow:
        request = puow.notification_requests.get(cmd.notification_id)
        if not request or request.status != NotificationStatus.FAILED:
            logger.warning(f"Notification {cmd.notification_id} not found or not in failed state")
            return

        cmd = commands.SendNotificationCommand(
            userid=request.userid.value,
            notification_type=request.notification_type.value,
            recipient_email=request.recipient_email.value,
            subject=request.subject,
            content=request.content,
            template_vars=request.template_vars
        )

        await send_notification_handler(cmd, puow, ntfy)


async def user_email_verification_requested_handler(
        event: events.UserEmailVerificationRequested,
        puow: unit_of_work.AbstractUnitOfWork,
        ntfy: AbstractEmailProvider
):
    """
    Handles UserEmailVerificationRequested events from user service.

    Creates and sends email verification notification.
    """
    # Create send notification command
    cmd = commands.SendNotificationCommand(
        userid=event.userid,
        notification_type=NotificationType.EMAIL_VERIFICATION.value,
        recipient_email=event.email,
        subject="Please verify your email address",
        content="email_verification",  # Template name
        template_vars={
            "username": event.username,
            "verification_link": f"https://yourapp.com/verify/{event.verify_token}",
            "service_name": "Chadland Customer Service"
        }
    )

    await send_notification_handler(cmd, puow, ntfy)


async def user_registered_handler(
        event: events.UserRegistered,
        puow: unit_of_work.AbstractUnitOfWork
):
    """
    Handles UserRegistered events to create default notification preferences.
    """
    # Create default notification preferences for new user
    cmd = commands.CreateNotificationPreferencesCommand(
        userid=event.userid,
        notification_email=event.email,
        preferences={nt.value: True for nt in NotificationType}  # Enable all by default
    )

    await create_notification_preferences_handler(cmd, puow)


async def password_reset_requested_handler(
        event: events.PasswordResetRequested,
        puow: unit_of_work.AbstractUnitOfWork,
        ntfy: AbstractEmailProvider
):
    """
    Handles password reset requests.
    """
    cmd = commands.SendNotificationCommand(
        userid=event.userid,
        notification_type=NotificationType.PASSWORD_RESET.value,
        recipient_email=event.email,
        subject="Password Reset Request",
        content="password_reset",  # Template name
        template_vars={
            "reset_link": f"https://yourapp.com/reset/{event.reset_token}",
            "service_name": "Chadland Customer Service"
        }
    )

    await send_notification_handler(cmd, puow, ntfy)


async def notification_preferences_created_handler(
    event: events.NotificationPreferencesCreated,
    puow: unit_of_work.AbstractUnitOfWork,
    ntfy: AbstractEmailProvider
):
    """
    Handles NotificationPreferencesCreated events.
    Sends a welcome email to the user with their notification settings.

    Args:
        event: The NotificationPreferencesCreated event
        puow: Primary unit of work instance
        ntfy: Email provider instance
    """
    logger.info(
        f"New notification preferences created for user {event.userid} "
        f"with email {event.notification_email}"
    )

    # Send welcome email with notification settings
    cmd = commands.SendNotificationCommand(
        userid=event.userid,
        notification_type=NotificationType.WELCOME.value,
        recipient_email=event.notification_email,
        subject="Welcome to Notifications Service",
        content="welcome",  # Template name
        template_vars={
            "service_name": "YourApp"
        }
    )
    await send_notification_handler(cmd, puow, ntfy)


async def notification_preferences_updated_handler(
    event: events.NotificationPreferencesUpdated,
    puow: unit_of_work.AbstractUnitOfWork,
    ntfy: AbstractEmailProvider
):
    """
    Handles NotificationPreferencesUpdated events.
    Sends an email notifying the user about their preference changes.

    Args:
        event: The NotificationPreferencesUpdated event
        puow: Primary unit of work instance
        ntfy: Email provider instance
    """
    logger.info(
        f"Notification preferences updated for user {event.userid} "
        f"with email {event.notification_email}"
    )

    # Send notification about preference changes
    cmd = commands.SendNotificationCommand(
        userid=event.userid,
        notification_type=NotificationType.SECURITY_ALERT.value,
        recipient_email=event.notification_email,
        subject="Your Notification Preferences Have Been Updated",
        content="security_alert",  # Template name
        template_vars={
            "alert_message": "Your notification preferences have been successfully updated.",
            "service_name": "Chadland Customer Service"
        }
    )
    await send_notification_handler(cmd, puow, ntfy)


# External Event Handlers - Generalized for DRY principle
async def publish_event_to_external_services(event: events.OutgoingEvent, pub: publisher.AbstractEventPublisher):
    """
    Generalized event publisher for external services.

    This single handler can publish any event type to external services,
    following DRY principle by eliminating repetitive publishing code.

    Args:
        event: Any domain event to be published
        pub: Event publisher instance
    """
    event_type = type(event).__name__
    logger.info(f"Publishing {event_type} event.")
    await pub.publish_event(event)

"""
These dictionaries map commands and events to their respective handler functions.
This setup allows the message bus to dispatch incoming commands and events to the correct processing logic.
"""

COMMAND_HANDLERS = {
    commands.CreateNotificationPreferencesCommand: create_notification_preferences_handler,
    commands.UpdateNotificationPreferencesCommand: update_notification_preferences_handler,
    commands.SendNotificationCommand: send_notification_handler,
    commands.RetryFailedNotificationCommand: retry_failed_notification_handler,
}

EVENT_HANDLERS = {
    events.UserEmailVerificationRequested: [user_email_verification_requested_handler],
    events.UserRegistered: [user_registered_handler],
    events.PasswordResetRequested: [password_reset_requested_handler],
    events.NotificationFailed: [publish_event_to_external_services],
    events.NotificationPreferencesCreated: [notification_preferences_created_handler],
    events.NotificationPreferencesUpdated: [notification_preferences_updated_handler],
    events.NotificationSent: [publish_event_to_external_services],
}
