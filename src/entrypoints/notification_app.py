from fastapi import APIRouter, status, Depends, Request, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Dict, Optional, Any
from src.domain.commands import CreateNotificationPreferencesCommand, UpdateNotificationPreferencesCommand, SendNotificationCommand
from src.service_layer.messagebus import MessageBus
from src.service_layer.unit_of_work import AbstractUnitOfWork
from src.service_layer import views

router = APIRouter(
    prefix="/notifications",
    tags=["notifications"],
    responses={404: {"description": "Resource not found."}},
)

def get_messagebus(request: Request) -> MessageBus:
    return request.app.state.messagebus

def get_suow(request: Request) -> AbstractUnitOfWork:
    return request.app.state.suow

async def get_userid(request: Request) -> str:
    return request.app.state.user_id if hasattr(request.app.state, "user_id") else "a1b2c3d4e5f6789012345678901234ab"

class Preferences(BaseModel):
    email_verification: bool = True
    password_reset: bool = True
    welcome: bool = True
    security_alert: bool = True


# Request/Response models
class PreferencesBase(BaseModel):
    notification_email: EmailStr
    preferences: Preferences

class CreatePreferencesRequest(PreferencesBase):
    pass

class UpdatePreferencesRequest(PreferencesBase):
    pass


class SendNotificationRequest(BaseModel):
    notification_type: str
    recipient_email: EmailStr
    subject: str
    content: str
    template_vars: Optional[Dict[str, str]] = None


class PreferencesResponse(BaseModel):
    preferences: Preferences


class NotificationHistoryItem(BaseModel):
    notification_id: str
    notification_type: str
    recipient_email: EmailStr
    subject: str
    content: str
    template_vars: Optional[Dict[str, Any]] = None
    status: str
    retry_count: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class NotificationHistoryResponse(BaseModel):
    notifications: list[NotificationHistoryItem]


@router.post("/send", status_code=status.HTTP_202_ACCEPTED)
async def send_notification(
        request_data: SendNotificationRequest,
        userid: str = Depends(get_userid),
        messagebus: MessageBus = Depends(get_messagebus),
):
    """
    Send a notification (admin endpoint).
    """
    cmd = SendNotificationCommand(
        userid=userid,
        notification_type=request_data.notification_type,
        recipient_email=request_data.recipient_email,
        subject=request_data.subject,
        content=request_data.content,
        template_vars=request_data.template_vars
    )
    await messagebus.handle(cmd)
    return "OK"


@router.post("/preferences", status_code=status.HTTP_201_CREATED)
async def create_notification_preferences(
        request_data: CreatePreferencesRequest,
        userid: str = Depends(get_userid),
        messagebus: MessageBus = Depends(get_messagebus),
):
    """
    Create initial notification preferences for a user.
    """
    cmd = CreateNotificationPreferencesCommand(
        userid=userid,
        notification_email=request_data.notification_email,
        preferences=request_data.preferences.dict()
    )
    await messagebus.handle(cmd)
    return "OK"


@router.put("/preferences/{userid}", status_code=status.HTTP_200_OK)
async def update_notification_preferences(
        request_data: UpdatePreferencesRequest,
        userid: str = Depends(get_userid),
        messagebus: MessageBus = Depends(get_messagebus),
):
    """
    Update existing notification preferences for a user.
    """

    cmd = UpdateNotificationPreferencesCommand(
        userid=userid,
        notification_email=request_data.notification_email,
        preferences=request_data.preferences.dict()
    )
    await messagebus.handle(cmd)
    return "OK"


@router.get("/preferences/{userid}", response_model=PreferencesResponse)
async def get_notification_preferences(
        userid: str = Depends(get_userid),
        suow: AbstractUnitOfWork = Depends(get_suow)
):
    """
    Get notification preferences for a user.
    """
    # Access the standby UoW for read operations
    if not suow:
        raise HTTPException(status_code=500, detail="Database not available")

    preferences = await views.get_notification_preferences(userid, suow)
    if not preferences:
        raise HTTPException(status_code=404, detail="Preferences not found")

    print(preferences)

    return PreferencesResponse(preferences=Preferences(**preferences.to_dict()))


@router.get("/history/{userid}", response_model=NotificationHistoryResponse)
async def get_notification_history(
        limit: int = 50,
        userid: str = Depends(get_userid),
        suow: AbstractUnitOfWork = Depends(get_suow)
):
    """
    Get notification history for a user.

    Args:
        limit: Maximum number of notifications to return (default: 50)
        userid: User ID to get history for
        suow: Standby unit of work instance

    Returns:
        NotificationHistoryResponse containing list of notifications
    """
    if not suow:
        raise HTTPException(status_code=500, detail="Database not available")

    notifications = await views.get_notification_history(userid, limit, suow)
    return NotificationHistoryResponse(notifications=[
        NotificationHistoryItem(**notification) for notification in notifications
    ])
