from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from rop.infrastructure.db.models.menu import Base


class OrderModel(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    restaurant_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("restaurants.id", ondelete="CASCADE"),
        nullable=False,
    )
    table_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("tables.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    total_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)

    lines: Mapped[list["OrderLineModel"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="OrderLineModel.id",
    )

    __table_args__ = (
        Index("ix_orders_restaurant_created_at_desc", "restaurant_id", "created_at"),
        Index("ix_orders_table_created_at_desc", "table_id", "created_at"),
    )


class OrderLineModel(Base):
    __tablename__ = "order_lines"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    order_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    item_id: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    line_total_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    order: Mapped[OrderModel] = relationship(back_populates="lines")
