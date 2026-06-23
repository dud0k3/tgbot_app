from collections.abc import Generator
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from .config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
if settings.database_url.startswith("sqlite"):
    Path("data").mkdir(exist_ok=True)
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(engine, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from . import models
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if db.query(models.Plan).count() == 0:
            db.add_all([
                models.Plan(name="СТАРТ", days=30, price_stars=149, traffic_gb=100, devices=2, position=1),
                models.Plan(name="СВОБОДА", days=90, price_stars=379, traffic_gb=300, devices=4, position=2, badge="ВЫГОДНО"),
                models.Plan(name="БЕСКОНЕЧНОСТЬ", days=365, price_stars=1190, traffic_gb=0, devices=8, position=3, badge="МАКСИМУМ"),
            ])
            db.commit()

