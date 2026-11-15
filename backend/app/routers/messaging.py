"""Messaging router — conversations & messages.

Powers concierge/help chat and parent<->therapist messaging. A conversation has
participants; messages are appended and marked read per participant.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from ..database import get_database
from ..utils.jwt_handler import get_current_user
from ..utils.mongo import serialize, paginate, oid, now
from .notifications import push_notification

router = APIRouter(prefix="/api/messaging", tags=["messaging"])


class StartConversation(BaseModel):
    participant_id: Optional[str] = None   # omit for concierge/support
    subject: Optional[str] = None
    type: str = "direct"                   # direct | concierge


class SendMessage(BaseModel):
    body: str = Field(min_length=1, max_length=4000)


@router.post("/conversations")
async def start_conversation(payload: StartConversation, current_user: dict = Depends(get_current_user)):
    """Start (or reuse) a conversation."""
    db = get_database()
    uid = str(current_user["_id"])
    participants = [uid]
    if payload.type == "concierge":
        participants.append("concierge")
    elif payload.participant_id:
        target = await db.users.find_one({"_id": oid(payload.participant_id)})
        if not target:
            raise HTTPException(status_code=404, detail="Participant not found")
        participants.append(payload.participant_id)
        existing = await db.conversations.find_one({"type": "direct", "participants": {"$all": participants, "$size": 2}})
        if existing:
            return serialize(existing)
    doc = {
        "participants": participants, "type": payload.type, "subject": payload.subject,
        "last_message": None, "last_message_at": now(), "created_at": now(),
    }
    result = await db.conversations.insert_one(doc)
    doc["_id"] = result.inserted_id
    return serialize(doc)


@router.get("/conversations")
async def list_conversations(current_user: dict = Depends(get_current_user)):
    """List the caller's conversations, newest activity first."""
    db = get_database()
    rows = await db.conversations.find({"participants": str(current_user["_id"])}).sort("last_message_at", -1).to_list(length=200)
    return {"conversations": serialize(rows)}


@router.get("/conversations/{conversation_id}/messages")
async def get_messages(conversation_id: str, page: int = 1, limit: int = 50, current_user: dict = Depends(get_current_user)):
    """Fetch messages in a conversation and mark them read for the caller."""
    db = get_database()
    conv = await db.conversations.find_one({"_id": oid(conversation_id)})
    if not conv or str(current_user["_id"]) not in conv["participants"]:
        raise HTTPException(status_code=403, detail="Access denied")
    await db.messages.update_many(
        {"conversation_id": conversation_id, "sender_id": {"$ne": str(current_user["_id"])}, "read": False},
        {"$set": {"read": True}},
    )
    return await paginate(db.messages, {"conversation_id": conversation_id}, page, limit, sort_field="created_at", sort_dir=1)


@router.post("/conversations/{conversation_id}/messages")
async def send_message(conversation_id: str, payload: SendMessage, current_user: dict = Depends(get_current_user)):
    """Post a message to a conversation."""
    db = get_database()
    uid = str(current_user["_id"])
    conv = await db.conversations.find_one({"_id": oid(conversation_id)})
    if not conv or uid not in conv["participants"]:
        raise HTTPException(status_code=403, detail="Access denied")
    msg = {
        "conversation_id": conversation_id, "sender_id": uid, "sender_name": current_user.get("full_name"),
        "body": payload.body, "read": False, "created_at": now(),
    }
    result = await db.messages.insert_one(msg)
    await db.conversations.update_one(
        {"_id": oid(conversation_id)}, {"$set": {"last_message": payload.body[:120], "last_message_at": now()}}
    )
    for pid in conv["participants"]:
        if pid not in (uid, "concierge"):
            await push_notification(pid, f"New message from {current_user.get('full_name')}", payload.body[:80], category="social", link="/messages")
    msg["_id"] = result.inserted_id
    return serialize(msg)


@router.get("/unread-count")
async def unread_messages(current_user: dict = Depends(get_current_user)):
    """Total unread messages across the caller's conversations."""
    db = get_database()
    uid = str(current_user["_id"])
    convs = await db.conversations.find({"participants": uid}, {"_id": 1}).to_list(length=500)
    ids = [str(c["_id"]) for c in convs]
    count = await db.messages.count_documents({"conversation_id": {"$in": ids}, "sender_id": {"$ne": uid}, "read": False})
    return {"unread": count}


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a conversation and its messages (participant only)."""
    db = get_database()
    conv = await db.conversations.find_one({"_id": oid(conversation_id)})
    if not conv or str(current_user["_id"]) not in conv["participants"]:
        raise HTTPException(status_code=403, detail="Access denied")
    await db.messages.delete_many({"conversation_id": conversation_id})
    await db.conversations.delete_one({"_id": oid(conversation_id)})
    return {"message": "Conversation deleted"}
