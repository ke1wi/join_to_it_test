from pydantic import BaseModel


class NotificationRequest(BaseModel):
    """Model for notification requests"""

    message: str


class BroadcastRequest(BaseModel):
    """Model for broadcast notification requests"""

    message: str


class PersonalMessageRequest(BaseModel):
    """Model for personal notification requests"""

    message: str
