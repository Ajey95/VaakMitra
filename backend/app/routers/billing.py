"""Billing router — subscription plans, subscriptions and invoices.

A professional SaaS-style billing surface (no real payment gateway wired; this
records subscriptions and generates invoice records). Admins manage plans.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from datetime import timedelta
from ..database import get_database
from ..utils.jwt_handler import get_current_user, require_admin
from ..utils.mongo import serialize, paginate, oid, audit, now

router = APIRouter(prefix="/api/billing", tags=["billing"])

DEFAULT_PLANS = [
    {"slug": "free", "name": "Free", "price": 0, "interval": "month", "features": ["5 lessons", "Basic analytics"]},
    {"slug": "plus", "name": "Plus", "price": 299, "interval": "month", "features": ["All lessons", "Full analytics", "Games & rewards"]},
    {"slug": "pro", "name": "Pro", "price": 799, "interval": "month", "features": ["Everything in Plus", "Therapist access", "Priority support"]},
]


class SubscribeRequest(BaseModel):
    plan_slug: str


class PlanCreate(BaseModel):
    slug: str
    name: str
    price: float
    interval: str = "month"
    features: list = []


@router.get("/plans")
async def list_plans(current_user: dict = Depends(get_current_user)):
    """List available plans (seeds defaults on first call)."""
    db = get_database()
    if await db.plans.count_documents({}) == 0:
        await db.plans.insert_many([{**p, "active": True, "created_at": now()} for p in DEFAULT_PLANS])
    plans = await db.plans.find({"active": True}).sort("price", 1).to_list(length=50)
    return {"plans": serialize(plans)}


@router.get("/subscription")
async def my_subscription(current_user: dict = Depends(get_current_user)):
    """Return the caller's active subscription (or the implicit free plan)."""
    db = get_database()
    sub = await db.subscriptions.find_one({"user_id": str(current_user["_id"]), "status": "active"})
    if not sub:
        return {"plan_slug": "free", "status": "active", "implicit": True}
    return serialize(sub)


@router.post("/subscribe")
async def subscribe(payload: SubscribeRequest, current_user: dict = Depends(get_current_user)):
    """Subscribe to a plan (records subscription + an invoice)."""
    db = get_database()
    uid = str(current_user["_id"])
    plan = await db.plans.find_one({"slug": payload.plan_slug, "active": True})
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    # Deactivate any current subscription.
    await db.subscriptions.update_many({"user_id": uid, "status": "active"}, {"$set": {"status": "cancelled", "cancelled_at": now()}})
    sub = {
        "user_id": uid, "plan_slug": plan["slug"], "plan_name": plan["name"], "price": plan["price"],
        "status": "active", "started_at": now(), "renews_at": now() + timedelta(days=30), "created_at": now(),
    }
    result = await db.subscriptions.insert_one(sub)
    if plan["price"] > 0:
        await db.invoices.insert_one({
            "user_id": uid, "subscription_id": str(result.inserted_id), "plan_name": plan["name"],
            "amount": plan["price"], "currency": "INR", "status": "paid", "created_at": now(),
        })
    await audit("billing.subscribe", current_user, meta={"plan": plan["slug"]})
    sub["_id"] = result.inserted_id
    return serialize(sub)


@router.post("/cancel")
async def cancel_subscription(current_user: dict = Depends(get_current_user)):
    """Cancel the active subscription."""
    db = get_database()
    result = await db.subscriptions.update_many(
        {"user_id": str(current_user["_id"]), "status": "active"}, {"$set": {"status": "cancelled", "cancelled_at": now()}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="No active subscription")
    return {"message": "Subscription cancelled"}


@router.get("/invoices")
async def list_invoices(page: int = 1, limit: int = 20, current_user: dict = Depends(get_current_user)):
    """Paginated invoice history."""
    db = get_database()
    return await paginate(db.invoices, {"user_id": str(current_user["_id"])}, page, limit)


@router.get("/invoices/{invoice_id}")
async def get_invoice(invoice_id: str, current_user: dict = Depends(get_current_user)):
    """Fetch a single invoice."""
    db = get_database()
    inv = await db.invoices.find_one({"_id": oid(invoice_id)})
    if not inv or (inv["user_id"] != str(current_user["_id"]) and current_user.get("role") != "admin"):
        raise HTTPException(status_code=404, detail="Invoice not found")
    return serialize(inv)


# ---- Admin --------------------------------------------------------------------

@router.post("/plans/admin")
async def create_plan(payload: PlanCreate, current_admin: dict = Depends(require_admin)):
    """Admin: create a plan."""
    db = get_database()
    if await db.plans.find_one({"slug": payload.slug}):
        raise HTTPException(status_code=409, detail="Slug exists")
    doc = {**payload.model_dump(), "active": True, "created_at": now()}
    result = await db.plans.insert_one(doc)
    doc["_id"] = result.inserted_id
    return serialize(doc)


@router.get("/admin/revenue")
async def revenue(current_admin: dict = Depends(require_admin)):
    """Admin: total revenue, active subscriptions and MRR."""
    db = get_database()
    invoices = await db.invoices.find({"status": "paid"}).to_list(length=100000)
    total = sum(i.get("amount", 0) for i in invoices)
    active = await db.subscriptions.count_documents({"status": "active"})
    active_subs = await db.subscriptions.find({"status": "active"}).to_list(length=100000)
    mrr = sum(s.get("price", 0) for s in active_subs)
    return {"total_revenue": total, "active_subscriptions": active, "mrr": mrr, "invoice_count": len(invoices)}
