from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from . import models
from .config import get_settings
from .vpn import get_vpn_provider


def aware(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def upsert_user(db: Session, tg: dict) -> models.User:
    user = db.query(models.User).filter_by(telegram_id=int(tg["id"])).first()
    if not user:
        user = models.User(telegram_id=int(tg["id"]))
        db.add(user)
    user.username = tg.get("username")
    user.first_name = tg.get("first_name", "")[:128]
    user.last_seen_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)
    return user


def active_subscription(db: Session, user_id: int) -> models.Subscription | None:
    now = datetime.now(timezone.utc)
    sub = db.query(models.Subscription).filter(
        models.Subscription.user_id == user_id,
        models.Subscription.status == "active",
        models.Subscription.expires_at > now,
    ).order_by(models.Subscription.expires_at.desc()).first()
    return sub


async def activate_order(db: Session, order: models.Order) -> models.Subscription:
    existing = db.query(models.Subscription).filter_by(order_id=order.id).first()
    if existing:
        return existing
    if order.status == "paid":
        paid_subscription = db.query(models.Subscription).filter_by(
            user_id=order.user_id, status="active"
        ).order_by(models.Subscription.expires_at.desc()).first()
        if paid_subscription:
            return paid_subscription
    now = datetime.now(timezone.utc)
    active = db.query(models.Subscription).filter(
        models.Subscription.user_id == order.user_id,
        models.Subscription.status == "active",
    ).order_by(models.Subscription.expires_at.desc()).first()
    base = max(now, aware(active.expires_at)) if active else now
    expires = base + timedelta(days=order.plan.days)
    username = active.external_username if active else f"tg_{order.user.telegram_id}"
    vpn = await get_vpn_provider().create_or_extend(username, expires, order.plan.traffic_gb, order.plan.devices)
    if active:
        subscription = active
        subscription.access_url = vpn.access_url
        subscription.expires_at = expires
        subscription.traffic_gb = order.plan.traffic_gb
        subscription.devices = order.plan.devices
        subscription.status = "active"
    else:
        subscription = models.Subscription(
            user_id=order.user_id,
            order_id=order.id,
            external_username=vpn.username,
            access_url=vpn.access_url,
            traffic_gb=order.plan.traffic_gb,
            devices=order.plan.devices,
            starts_at=now,
            expires_at=expires,
        )
    order.status = "paid"
    order.paid_at = now
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription


async def activate_trial(db: Session, user: models.User, days: int, traffic_gb: int) -> models.Subscription:
    if user.trial_used:
        raise ValueError("Trial already used")
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=days)
    vpn = await get_vpn_provider().create_or_extend(f"tg_{user.telegram_id}", expires, traffic_gb, settings.default_subscription_devices)
    subscription = models.Subscription(
        user_id=user.id,
        external_username=vpn.username,
        access_url=vpn.access_url,
        traffic_gb=traffic_gb,
        devices=settings.default_subscription_devices,
        starts_at=now,
        expires_at=expires,
    )
    user.trial_used = True
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription


async def provision_default_subscription(db: Session, user: models.User) -> models.Subscription:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    subscription = active_subscription(db, user.id)
    if subscription:
        username = subscription.external_username or f"tg_{user.telegram_id}"
        vpn = await get_vpn_provider().create_or_extend(
            username,
            aware(subscription.expires_at),
            subscription.traffic_gb,
            settings.default_subscription_devices,
        )
        subscription.external_username = vpn.username
        subscription.access_url = vpn.access_url
        subscription.devices = settings.default_subscription_devices
        db.add(subscription)
        db.commit()
        db.refresh(subscription)
        return subscription
    expires = now + timedelta(days=settings.default_subscription_days)
    vpn = await get_vpn_provider().create_or_extend(
        f"tg_{user.telegram_id}",
        expires,
        settings.default_subscription_traffic_gb,
        settings.default_subscription_devices,
    )
    subscription = models.Subscription(
        user_id=user.id,
        external_username=vpn.username,
        access_url=vpn.access_url,
        traffic_gb=settings.default_subscription_traffic_gb,
        devices=settings.default_subscription_devices,
        starts_at=now,
        expires_at=expires,
        status="active",
    )
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription


async def reprovision_active_subscription(db: Session, user: models.User) -> models.Subscription:
    subscription = active_subscription(db, user.id)
    if not subscription:
        raise ValueError("No active subscription")
    username = subscription.external_username or f"tg_{user.telegram_id}"
    vpn = await get_vpn_provider().create_or_extend(username, aware(subscription.expires_at), subscription.traffic_gb, subscription.devices)
    subscription.external_username = vpn.username
    subscription.access_url = vpn.access_url
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription
