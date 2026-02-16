from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from rop.infrastructure.db.models.menu import Base


class TableModel(Base):
    __tablename__ = "tables"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    restaurant_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("restaurants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
