from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from . import models
from .auth import telegram_user
from .config import get_settings
from .db import get_db
from .services import activate_order, activate_trial, active_subscription, aware, provision_default_subscription, reprovision_active_subscription, upsert_user


router = APIRouter(prefix="/api")
settings = get_settings()


def current_user(tg: dict = Depends(telegram_user), db: Session = Depends(get_db)) -> models.User:
    user = upsert_user(db, tg)
    if user.is_blocked:
        raise HTTPException(403, "Account is blocked")
    return user


def admin_user(tg: dict = Depends(telegram_user), db: Session = Depends(get_db)) -> models.User:
    user = upsert_user(db, tg)
    if user.telegram_id not in settings.admins:
        raise HTTPException(403, "Admin access required")
    return user


def iso(value):
    return aware(value).isoformat() if value else None


def plan_json(plan: models.Plan) -> dict:
    return {
        "id": plan.id,
        "name": plan.name,
        "days": plan.days,
        "traffic_gb": plan.traffic_gb,
        "devices": plan.devices,
        "badge": plan.badge,
        "active": plan.active,
        "position": plan.position,
    }


def subscription_json(sub: models.Subscription | None) -> dict | None:
    if not sub:
        return None
    now = datetime.now(timezone.utc)
    active = sub.status == "active" and aware(sub.expires_at) > now
    return {
        "id": sub.id,
        "status": "active" if active else "expired",
        "access_url": sub.access_url,
        "starts_at": iso(sub.starts_at),
        "expires_at": iso(sub.expires_at),
        "traffic_gb": sub.traffic_gb,
        "devices": sub.devices,
        "days_left": max(0, (aware(sub.expires_at) - now).days),
    }


def protocol_list() -> list[dict]:
    result = []
    for item in settings.protocols:
        raw = item.strip()
        lower = raw.lower()
        kind = "TLS" if "tls" in lower and "reality" not in lower else "Reality" if "reality" in lower else "VPN"
        result.append({"name": raw, "kind": kind})
    return result


@router.get("/bootstrap")
def bootstrap(user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    plans = db.query(models.Plan).filter_by(active=True).order_by(models.Plan.position, models.Plan.id).all()
    sub = active_subscription(db, user.id)
    return {
        "brand": "JOOT VPN",
        "user": {"telegram_id": user.telegram_id, "first_name": user.first_name, "username": user.username},
        "is_admin": user.telegram_id in settings.admins,
        "trial_available": False,
        "trial_days": settings.trial_days,
        "plans": [plan_json(p) for p in plans],
        "subscription": subscription_json(sub),
        "support_username": settings.support_username,
        "vpn_provider": settings.vpn_provider,
        "default_devices": settings.default_subscription_devices,
        "default_days": settings.default_subscription_days,
        "default_traffic_gb": settings.default_subscription_traffic_gb,
        "protocols": protocol_list(),
    }


@router.post("/connect")
async def connect(user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    try:
        sub = await provision_default_subscription(db, user)
    except Exception as error:
        detail = str(error).strip() or type(error).__name__
        raise HTTPException(502, f"VPN provisioning failed: {detail}")
    return subscription_json(sub)


@router.post("/trial")
async def trial(user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    if not settings.trial_enabled:
        raise HTTPException(404, "Trial is disabled")
    try:
        sub = await activate_trial(db, user, settings.trial_days, settings.trial_traffic_gb)
    except ValueError as error:
        raise HTTPException(409, str(error))
    except Exception as error:
        detail = str(error).strip() or type(error).__name__
        raise HTTPException(502, f"VPN provisioning failed: {detail}")
    return subscription_json(sub)


@router.post("/subscription/reprovision")
async def reprovision_subscription(user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    try:
        sub = await reprovision_active_subscription(db, user)
    except ValueError as error:
        raise HTTPException(404, str(error))
    except Exception as error:
        detail = str(error).strip() or type(error).__name__
        raise HTTPException(502, f"VPN provisioning failed: {detail}")
    return subscription_json(sub)


class PlanInput(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    days: int = Field(ge=1, le=3650)
    price_stars: int = Field(default=0, ge=0, le=1_000_000)
    traffic_gb: int = Field(ge=0, le=1_000_000)
    devices: int = Field(ge=1, le=100)
    badge: str | None = Field(default=None, max_length=40)
    active: bool = True
    position: int = 0


@router.get("/admin/dashboard")
def admin_dashboard(admin: models.User = Depends(admin_user), db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    users = db.query(func.count(models.User.id)).scalar() or 0
    paid = db.query(func.count(models.Order.id)).filter(models.Order.status == "paid").scalar() or 0
    revenue = db.query(func.coalesce(func.sum(models.Order.amount_stars), 0)).filter(models.Order.status == "paid").scalar() or 0
    active = db.query(func.count(models.Subscription.id)).filter(
        models.Subscription.status == "active", models.Subscription.expires_at > now
    ).scalar() or 0
    recent_orders = db.query(models.Order).options(joinedload(models.Order.user), joinedload(models.Order.plan)).order_by(models.Order.id.desc()).limit(50).all()
    recent_users = db.query(models.User).order_by(models.User.id.desc()).limit(100).all()
    return {
        "stats": {"users": users, "paid_orders": paid, "revenue_stars": int(revenue), "active_subscriptions": active},
        "plans": [plan_json(p) for p in db.query(models.Plan).order_by(models.Plan.position, models.Plan.id).all()],
        "orders": [{
            "id": o.id,
            "telegram_id": o.user.telegram_id,
            "user": o.user.first_name or o.user.username or str(o.user.telegram_id),
            "plan": o.plan.name,
            "amount_stars": o.amount_stars,
            "status": o.status,
            "created_at": iso(o.created_at),
        } for o in recent_orders],
        "users": [{
            "telegram_id": u.telegram_id,
            "name": u.first_name,
            "username": u.username,
            "blocked": u.is_blocked,
            "trial_used": u.trial_used,
            "created_at": iso(u.created_at),
        } for u in recent_users],
    }


@router.post("/admin/plans")
def create_plan(body: PlanInput, admin: models.User = Depends(admin_user), db: Session = Depends(get_db)):
    plan = models.Plan(**body.model_dump())
    db.add(plan)
    db.add(models.AuditLog(actor_telegram_id=admin.telegram_id, action="plan.create", details=body.model_dump_json()))
    db.commit()
    db.refresh(plan)
    return plan_json(plan)


@router.put("/admin/plans/{plan_id}")
def update_plan(plan_id: int, body: PlanInput, admin: models.User = Depends(admin_user), db: Session = Depends(get_db)):
    plan = db.get(models.Plan, plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")
    for key, value in body.model_dump().items():
        setattr(plan, key, value)
    db.add(models.AuditLog(actor_telegram_id=admin.telegram_id, action="plan.update", details=f"plan={plan_id}"))
    db.commit()
    return plan_json(plan)


class BlockInput(BaseModel):
    blocked: bool


@router.put("/admin/users/{telegram_id}/block")
def block_user(telegram_id: int, body: BlockInput, admin: models.User = Depends(admin_user), db: Session = Depends(get_db)):
    user = db.query(models.User).filter_by(telegram_id=telegram_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    if telegram_id in settings.admins:
        raise HTTPException(400, "Admin cannot be blocked")
    user.is_blocked = body.blocked
    db.add(models.AuditLog(actor_telegram_id=admin.telegram_id, action="user.block", details=f"user={telegram_id};blocked={body.blocked}"))
    db.commit()
    return {"ok": True}


@router.post("/admin/orders/{order_id}/retry")
async def retry_order(order_id: int, admin: models.User = Depends(admin_user), db: Session = Depends(get_db)):
    order = db.query(models.Order).options(joinedload(models.Order.user), joinedload(models.Order.plan)).filter_by(id=order_id).first()
    if not order or order.status not in {"provision_error", "paid"}:
        raise HTTPException(400, "Order cannot be retried")
    try:
        sub = await activate_order(db, order)
    except Exception as error:
        detail = str(error).strip() or type(error).__name__
        raise HTTPException(502, f"Provisioning failed: {detail}")
    db.add(models.AuditLog(actor_telegram_id=admin.telegram_id, action="order.retry", details=f"order={order_id}"))
    db.commit()
    return subscription_json(sub)
