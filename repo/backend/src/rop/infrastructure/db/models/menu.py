from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class RestaurantModel(Base):
    __tablename__ = "restaurants"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    menus: Mapped[list["MenuModel"]] = relationship(back_populates="restaurant")


class MenuModel(Base):
    __tablename__ = "menus"
    __table_args__ = (
        UniqueConstraint("restaurant_id", "version", name="uq_menus_restaurant_version"),
    )

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    restaurant_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("restaurants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    restaurant: Mapped[RestaurantModel] = relationship(back_populates="menus")
    items: Mapped[list["MenuItemModel"]] = relationship(
        back_populates="menu",
        cascade="all, delete-orphan",
        order_by="MenuItemModel.id",
    )


class MenuItemModel(Base):
    __tablename__ = "menu_items"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    menu_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("menus.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    menu: Mapped[MenuModel] = relationship(back_populates="items")
