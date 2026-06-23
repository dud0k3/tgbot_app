from datetime import datetime, timezone
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64))
    first_name: Mapped[str] = mapped_column(String(128), default="")
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    trial_used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Plan(Base):
    __tablename__ = "plans"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    days: Mapped[int] = mapped_column(Integer)
    price_stars: Mapped[int] = mapped_column(Integer)
    traffic_gb: Mapped[int] = mapped_column(Integer, default=0)
    devices: Mapped[int] = mapped_column(Integer, default=1)
    badge: Mapped[str | None] = mapped_column(String(40))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    position: Mapped[int] = mapped_column(Integer, default=0)


class Order(Base):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"))
    amount_stars: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(24), default="pending", index=True)
    invoice_payload: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    telegram_payment_charge_id: Mapped[str | None] = mapped_column(String(128), unique=True)
    provider_payment_charge_id: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    user: Mapped[User] = relationship()
    plan: Mapped[Plan] = relationship()


class Subscription(Base):
    __tablename__ = "subscriptions"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"), unique=True)
    external_username: Mapped[str] = mapped_column(String(128), unique=True)
    access_url: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(24), default="active")
    traffic_gb: Mapped[int] = mapped_column(Integer, default=0)
    devices: Mapped[int] = mapped_column(Integer, default=1)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    user: Mapped[User] = relationship()
    order: Mapped[Order | None] = relationship()


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    action: Mapped[str] = mapped_column(String(80))
    details: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

