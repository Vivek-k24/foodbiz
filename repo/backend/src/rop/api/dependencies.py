from __future__ import annotations

from collections.abc import Iterator

from fastapi import Depends
from sqlalchemy.orm import Session

from rop.application.catalog.service import CatalogService
from rop.application.commerce.service import CommerceService
from rop.application.inventory.service import InventoryService
from rop.application.kitchen.service import KitchenService
from rop.application.staff.service import StaffService
from rop.infrastructure.db.session import get_session_factory
from rop.infrastructure.messaging.redis_publisher import RedisEventPublisher


def get_db_session() -> Iterator[Session]:
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


def get_commerce_service(db: Session = Depends(get_db_session)) -> CommerceService:
    return CommerceService(db=db, publisher=RedisEventPublisher())


def get_catalog_service(db: Session = Depends(get_db_session)) -> CatalogService:
    return CatalogService(db=db)


def get_kitchen_service(db: Session = Depends(get_db_session)) -> KitchenService:
    return KitchenService(db=db, publisher=RedisEventPublisher())


def get_staff_service(
    commerce: CommerceService = Depends(get_commerce_service),
) -> StaffService:
    return StaffService(commerce=commerce)


def get_inventory_service() -> InventoryService:
    return InventoryService()
