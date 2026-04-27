import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.core.models.base import Base, PrimaryKeyMixin, SoftDeleteMixin, TimestampMixin


class Tenant(Base, PrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "tenants"

    slug: Mapped[str] = mapped_column(String(63), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    plan: Mapped[str] = mapped_column(String(50), nullable=False, default="starter")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    settings: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    max_users: Mapped[int] = mapped_column(Integer, nullable=False, default=25)

    users: Mapped[list["User"]] = relationship("User", back_populates="tenant", lazy="noload")  # type: ignore[name-defined]  # noqa: F821


class TenantSettings(Base, PrimaryKeyMixin, TimestampMixin):
    __tablename__ = "tenant_settings"

    tenant_id: Mapped[uuid.UUID] = mapped_column(nullable=False, unique=True, index=True)
    feature_flags: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    branding: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
