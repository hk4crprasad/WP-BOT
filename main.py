import logging
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query
from fastapi.responses import PlainTextResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ai_handler import get_ai_response
from config import settings
from database import (
    add_or_update_subscriber,
    close_db,
    get_all_active_subscribers,
    get_all_subscribers,
    init_db,
    opt_out_subscriber,
)
from models import BroadcastRequest, WhatsAppWebhook
from whatsapp_client import broadcast_messages, mark_as_read, send_text_message

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_OPT_OUT_KEYWORDS = {"stop", "unsubscribe", "optout", "opt out", "opt-out"}

security = HTTPBearer()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    logger.info("MongoDB connected")
    yield
    await close_db()
    logger.info("MongoDB disconnected")


app = FastAPI(title="ABC Coaching WhatsApp Bot", lifespan=lifespan)


def _verify_owner(auth: HTTPAuthorizationCredentials = Depends(security)):
    if auth.credentials != settings.OWNER_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/webhook")
async def verify_webhook(
    hub_mode: str | None = Query(None, alias="hub.mode"),
    hub_verify_token: str | None = Query(None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(None, alias="hub.challenge"),
):
    if hub_mode == "subscribe" and hub_verify_token == settings.WHATSAPP_VERIFY_TOKEN:
        logger.info("Webhook verified by Meta")
        return PlainTextResponse(hub_challenge)
    raise HTTPException(status_code=403, detail="Verification failed")


async def _process_message(phone: str, name: str, message_id: str, text: str):
    await add_or_update_subscriber(phone, name)
    await mark_as_read(message_id)

    if text.strip().lower() in _OPT_OUT_KEYWORDS:
        await opt_out_subscriber(phone)
        await send_text_message(
            phone,
            "You have been unsubscribed from ABC Coaching Centre broadcasts. "
            "Reply with any message to re-subscribe.",
        )
        return

    try:
        reply = await get_ai_response(phone, text)
        await send_text_message(phone, reply)
    except Exception as exc:
        logger.error("AI/send error for %s: %s", phone, exc)
        await send_text_message(
            phone,
            "Sorry, I'm having trouble right now. Please try again shortly or "
            "contact us directly.",
        )


@app.post("/webhook")
async def receive_webhook(payload: WhatsAppWebhook, background: BackgroundTasks):
    for entry in payload.entry:
        for change in entry.changes:
            value = change.value
            if not value.messages:
                continue

            msg = value.messages[0]
            if msg.type != "text" or not msg.text:
                continue

            phone = msg.from_
            text = msg.text.body
            name = (
                value.contacts[0].profile.name
                if value.contacts
                else phone
            )

            background.add_task(_process_message, phone, name, msg.id, text)

    # Meta requires a 200 response immediately
    return {"status": "ok"}


@app.post("/broadcast")
async def broadcast(
    body: BroadcastRequest,
    _: None = Depends(_verify_owner),
):
    if body.phone_numbers:
        phones = body.phone_numbers
    else:
        phones = await get_all_active_subscribers()

    if not phones:
        return {"status": "no_subscribers", "sent_count": 0}

    results = await broadcast_messages(phones, body.message)
    return {
        "status": "done",
        "sent_count": results["sent"],
        "failed_count": results["failed"],
        "errors": results["errors"],
    }


@app.get("/subscribers")
async def list_subscribers(_: None = Depends(_verify_owner)):
    subscribers = await get_all_subscribers()
    return {"count": len(subscribers), "subscribers": subscribers}
