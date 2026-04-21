from pydantic import BaseModel, Field
from typing import Optional


class WhatsAppText(BaseModel):
    body: str


class WhatsAppMessage(BaseModel):
    id: str
    from_: str = Field(alias="from")
    type: str
    timestamp: str
    text: Optional[WhatsAppText] = None

    model_config = {"populate_by_name": True}


class WhatsAppProfile(BaseModel):
    name: str


class WhatsAppContact(BaseModel):
    profile: WhatsAppProfile
    wa_id: str


class WhatsAppValue(BaseModel):
    messaging_product: str
    messages: Optional[list[WhatsAppMessage]] = None
    contacts: Optional[list[WhatsAppContact]] = None


class WhatsAppChange(BaseModel):
    value: WhatsAppValue
    field: str


class WhatsAppEntry(BaseModel):
    id: str
    changes: list[WhatsAppChange]


class WhatsAppWebhook(BaseModel):
    object: str
    entry: list[WhatsAppEntry]


class BroadcastRequest(BaseModel):
    message: str
    phone_numbers: Optional[list[str]] = None
