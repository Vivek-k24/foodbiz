from __future__ import annotations

from sqlalchemy import inspect
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from rop.infrastructure.db.models.menu import MenuItemModel, MenuModel, RestaurantModel
from rop.infrastructure.db.session import get_engine


def main() -> None:
    engine = get_engine(timeout_seconds=2.0)
    inspector = inspect(engine)
    required_tables = {"restaurants", "menus", "menu_items"}
    if not required_tables.issubset(set(inspector.get_table_names(schema="public"))):
        print("no schema yet")
        return

    with Session(engine) as session:
        session.execute(
            insert(RestaurantModel)
            .values(id="rst_001", name="Downtown Test Kitchen")
            .on_conflict_do_update(
                index_elements=[RestaurantModel.id],
                set_={"name": "Downtown Test Kitchen"},
            )
        )

        session.execute(
            insert(MenuModel)
            .values(id="men_001", restaurant_id="rst_001", version=1)
            .on_conflict_do_update(
                index_elements=[MenuModel.id],
                set_={"restaurant_id": "rst_001", "version": 1},
            )
        )

        items = [
            {
                "id": "itm_001",
                "menu_id": "men_001",
                "name": "Margherita Pizza",
                "description": "Tomato, mozzarella, basil",
                "price_cents": 1450,
                "currency": "USD",
                "is_available": True,
            },
            {
                "id": "itm_002",
                "menu_id": "men_001",
                "name": "Chicken Alfredo",
                "description": "Fettuccine, creamy parmesan sauce",
                "price_cents": 1690,
                "currency": "USD",
                "is_available": True,
            },
            {
                "id": "itm_003",
                "menu_id": "men_001",
                "name": "Caesar Salad",
                "description": "Romaine, croutons, parmesan",
                "price_cents": 990,
                "currency": "USD",
                "is_available": True,
            },
            {
                "id": "itm_004",
                "menu_id": "men_001",
                "name": "Tiramisu",
                "description": "Espresso-soaked ladyfingers",
                "price_cents": 850,
                "currency": "USD",
                "is_available": False,
            },
        ]

        for item in items:
            session.execute(
                insert(MenuItemModel)
                .values(**item)
                .on_conflict_do_update(
                    index_elements=[MenuItemModel.id],
                    set_={
                        "menu_id": item["menu_id"],
                        "name": item["name"],
                        "description": item["description"],
                        "price_cents": item["price_cents"],
                        "currency": item["currency"],
                        "is_available": item["is_available"],
                    },
                )
            )

        session.commit()
        print("seed complete")


if __name__ == "__main__":
    main()
