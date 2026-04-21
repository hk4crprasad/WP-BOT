from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from config import settings

_client: AsyncIOMotorClient | None = None


def get_db():
    return _client[settings.MONGODB_DB]


async def init_db():
    global _client
    _client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = get_db()
    await db.subscribers.create_index("phone", unique=True)
    await db.conversations.create_index("phone", unique=True)


async def close_db():
    global _client
    if _client:
        _client.close()
        _client = None


async def add_or_update_subscriber(phone: str, name: str) -> None:
    db = get_db()
    now = datetime.now(timezone.utc)
    await db.subscribers.update_one(
        {"phone": phone},
        {
            "$set": {"name": name, "last_seen": now},
            "$setOnInsert": {"opted_in": True, "created_at": now},
        },
        upsert=True,
    )


async def get_all_active_subscribers() -> list[str]:
    db = get_db()
    cursor = db.subscribers.find({"opted_in": True}, {"phone": 1})
    return [doc["phone"] async for doc in cursor]


async def get_all_subscribers() -> list[dict]:
    db = get_db()
    cursor = db.subscribers.find({}, {"_id": 0})
    return [doc async for doc in cursor]


async def opt_out_subscriber(phone: str) -> None:
    db = get_db()
    await db.subscribers.update_one({"phone": phone}, {"$set": {"opted_in": False}})


async def get_conversation_history(phone: str, limit: int = 10) -> list[dict]:
    db = get_db()
    doc = await db.conversations.find_one({"phone": phone})
    if not doc or "messages" not in doc:
        return []
    messages = doc["messages"]
    # return last `limit` messages, only role+content
    return [{"role": m["role"], "content": m["content"]} for m in messages[-limit:]]


async def append_messages(phone: str, user_msg: str, assistant_msg: str) -> None:
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    await db.conversations.update_one(
        {"phone": phone},
        {
            "$push": {
                "messages": {
                    "$each": [
                        {"role": "user", "content": user_msg, "ts": now},
                        {"role": "assistant", "content": assistant_msg, "ts": now},
                    ],
                    "$slice": -40,  # keep last 40 entries (20 exchanges)
                }
            }
        },
        upsert=True,
    )
