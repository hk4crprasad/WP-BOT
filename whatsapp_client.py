import asyncio
import httpx
from config import settings

_BASE_URL = f"https://graph.facebook.com/v25.0/{settings.WHATSAPP_PHONE_NUMBER_ID}"
_HEADERS = {
    "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
    "Content-Type": "application/json",
}


async def send_text_message(to: str, body: str) -> dict:
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "text",
        "text": {"preview_url": False, "body": body},
    }
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            f"{_BASE_URL}/messages", headers=_HEADERS, json=payload
        )
        response.raise_for_status()
        return response.json()


async def mark_as_read(message_id: str) -> None:
    payload = {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": message_id,
    }
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(f"{_BASE_URL}/messages", headers=_HEADERS, json=payload)


async def broadcast_messages(phones: list[str], body: str) -> dict:
    results = {"sent": 0, "failed": 0, "errors": []}
    for phone in phones:
        try:
            await send_text_message(phone, body)
            results["sent"] += 1
        except Exception as exc:
            results["failed"] += 1
            results["errors"].append({"phone": phone, "error": str(exc)})
        await asyncio.sleep(0.3)  # stay within WhatsApp rate limits
    return results
