from pydantic import BaseModel


class NotificationRequest(BaseModel):
    """Model for notification requests"""

    message: str
    broadcast: bool = True
