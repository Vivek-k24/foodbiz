from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import delete, inspect
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from rop.infrastructure.db.models.menu import MenuItemModel, MenuModel, RestaurantModel
from rop.infrastructure.db.models.table import TableModel
from rop.infrastructure.db.session import get_engine


def _modifier(
    code: str,
    label: str,
    kind: str,
    options: list[str] | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "code": code,
        "label": label,
        "kind": kind,
    }
    if options:
        payload["options"] = options
    return payload


SEED_ITEMS: list[dict[str, object]] = [
    {
        "id": "itm_001",
        "menu_id": "men_001",
        "name": "Margherita Pizza",
        "description": "San Marzano tomato, mozzarella, basil.",
        "price_cents": 1450,
        "currency": "USD",
        "is_available": True,
        "allowed_modifiers_json": [
            _modifier("extra_mozzarella", "Extra Mozzarella", "toggle"),
            _modifier("no_basil", "No Basil", "toggle"),
            _modifier("crust", "Crust", "choice", ["regular", "thin", "gluten_free"]),
        ],
    },
    {
        "id": "itm_002",
        "menu_id": "men_001",
        "name": "Pizza Diavola",
        "description": "Spicy salami, tomato, mozzarella, chili.",
        "price_cents": 1650,
        "currency": "USD",
        "is_available": True,
        "allowed_modifiers_json": [
            _modifier("spice_level", "Spice Level", "choice", ["mild", "medium", "hot"]),
            _modifier("extra_spicy_salami", "Extra Spicy Salami", "toggle"),
            _modifier("no_chili_flakes", "No Chili Flakes", "toggle"),
        ],
    },
    {
        "id": "itm_003",
        "menu_id": "men_001",
        "name": "Spaghetti Carbonara",
        "description": "Guanciale, pecorino, egg, black pepper.",
        "price_cents": 1790,
        "currency": "USD",
        "is_available": True,
        "allowed_modifiers_json": [
            _modifier("add_guanciale", "Add Guanciale", "toggle"),
            _modifier("no_egg", "No Egg", "toggle"),
            _modifier("pasta", "Pasta", "choice", ["spaghetti", "rigatoni"]),
        ],
    },
    {
        "id": "itm_004",
        "menu_id": "men_001",
        "name": "Fettuccine Alfredo",
        "description": "Creamy parmesan sauce over fresh pasta.",
        "price_cents": 1690,
        "currency": "USD",
        "is_available": True,
        "allowed_modifiers_json": [
            _modifier("add_chicken", "Add Chicken", "toggle"),
            _modifier("extra_parmesan", "Extra Parmesan", "toggle"),
            _modifier("sauce", "Sauce", "choice", ["light", "normal", "extra"]),
        ],
    },
    {
        "id": "itm_005",
        "menu_id": "men_001",
        "name": "Lasagna Classica",
        "description": "Layered pasta with bolognese and bechamel.",
        "price_cents": 1890,
        "currency": "USD",
        "is_available": True,
        "allowed_modifiers_json": [
            _modifier("extra_bolognese", "Extra Bolognese", "toggle"),
            _modifier("no_bechamel", "No Bechamel", "toggle"),
            _modifier("add_chili_oil", "Add Chili Oil", "toggle"),
        ],
    },
    {
        "id": "itm_006",
        "menu_id": "men_001",
        "name": "Chicken Parmigiana",
        "description": "Breaded chicken, marinara, mozzarella.",
        "price_cents": 1950,
        "currency": "USD",
        "is_available": True,
        "allowed_modifiers_json": [
            _modifier("extra_marinara", "Extra Marinara", "toggle"),
            _modifier("extra_mozzarella", "Extra Mozzarella", "toggle"),
            _modifier("side", "Side", "choice", ["spaghetti", "salad"]),
        ],
    },
    {
        "id": "itm_007",
        "menu_id": "men_001",
        "name": "Risotto ai Funghi",
        "description": "Creamy risotto with roasted mushrooms.",
        "price_cents": 1850,
        "currency": "USD",
        "is_available": True,
        "allowed_modifiers_json": [
            _modifier("extra_mushrooms", "Extra Mushrooms", "toggle"),
            _modifier("add_truffle_oil", "Add Truffle Oil", "toggle"),
            _modifier("no_garlic", "No Garlic", "toggle"),
        ],
    },
    {
        "id": "itm_008",
        "menu_id": "men_001",
        "name": "Bruschetta al Pomodoro",
        "description": "Grilled bread, tomato, basil, olive oil.",
        "price_cents": 950,
        "currency": "USD",
        "is_available": True,
        "allowed_modifiers_json": [
            _modifier("no_garlic", "No Garlic", "toggle"),
            _modifier("extra_basil", "Extra Basil", "toggle"),
            _modifier("add_burrata", "Add Burrata", "toggle"),
        ],
    },
    {
        "id": "itm_009",
        "menu_id": "men_001",
        "name": "Caesar Salad",
        "description": "Romaine, parmesan, croutons, Caesar dressing.",
        "price_cents": 990,
        "currency": "USD",
        "is_available": True,
        "allowed_modifiers_json": [
            _modifier("add_chicken", "Add Chicken", "toggle"),
            _modifier("no_croutons", "No Croutons", "toggle"),
            _modifier("dressing", "Dressing", "choice", ["light", "normal", "extra"]),
        ],
    },
    {
        "id": "itm_010",
        "menu_id": "men_001",
        "name": "Tiramisu",
        "description": "Mascarpone, cocoa, espresso-soaked ladyfingers.",
        "price_cents": 850,
        "currency": "USD",
        "is_available": False,
        "allowed_modifiers_json": [
            _modifier("extra_cocoa", "Extra Cocoa", "toggle"),
            _modifier("no_coffee", "No Coffee", "toggle"),
            _modifier("add_espresso_shot", "Add Espresso Shot", "toggle"),
        ],
    },
    {
        "id": "drink_001",
        "menu_id": "men_001",
        "name": "Espresso",
        "description": "Rich Italian espresso.",
        "price_cents": 350,
        "currency": "USD",
        "is_available": True,
        "allowed_modifiers_json": [
            _modifier("size", "Size", "choice", ["single", "double"]),
            _modifier("add_sugar", "Add Sugar", "toggle"),
        ],
    },
    {
        "id": "drink_002",
        "menu_id": "men_001",
        "name": "Cappuccino",
        "description": "Espresso with steamed milk and foam.",
        "price_cents": 450,
        "currency": "USD",
        "is_available": True,
        "allowed_modifiers_json": [
            _modifier("milk", "Milk", "choice", ["whole", "oat", "almond"]),
            _modifier("extra_foam", "Extra Foam", "toggle"),
        ],
    },
    {
        "id": "drink_003",
        "menu_id": "men_001",
        "name": "Latte",
        "description": "Espresso, steamed milk, silky finish.",
        "price_cents": 490,
        "currency": "USD",
        "is_available": True,
        "allowed_modifiers_json": [
            _modifier("milk", "Milk", "choice", ["whole", "oat", "almond"]),
            _modifier("extra_shot", "Extra Shot", "toggle"),
            _modifier("syrup", "Syrup", "choice", ["vanilla", "caramel", "none"]),
        ],
    },
    {
        "id": "drink_004",
        "menu_id": "men_001",
        "name": "Iced Tea",
        "description": "Fresh brewed tea over ice.",
        "price_cents": 390,
        "currency": "USD",
        "is_available": True,
        "allowed_modifiers_json": [
            _modifier("sweetener", "Sweetener", "choice", ["unsweet", "sweet", "half"]),
            _modifier("lemon", "Lemon", "toggle"),
        ],
    },
    {
        "id": "drink_005",
        "menu_id": "men_001",
        "name": "Lemonade",
        "description": "House lemonade with fresh citrus.",
        "price_cents": 420,
        "currency": "USD",
        "is_available": True,
        "allowed_modifiers_json": [
            _modifier("sparkling", "Sparkling", "toggle"),
            _modifier("less_sugar", "Less Sugar", "toggle"),
        ],
    },
    {
        "id": "drink_006",
        "menu_id": "men_001",
        "name": "Sparkling Water",
        "description": "Chilled mineral water.",
        "price_cents": 350,
        "currency": "USD",
        "is_available": True,
        "allowed_modifiers_json": [
            _modifier("lime", "Lime", "toggle"),
        ],
    },
    {
        "id": "drink_007",
        "menu_id": "men_001",
        "name": "Still Water",
        "description": "Still bottled water.",
        "price_cents": 250,
        "currency": "USD",
        "is_available": True,
        "allowed_modifiers_json": None,
    },
    {
        "id": "drink_008",
        "menu_id": "men_001",
        "name": "Coke",
        "description": "Classic cola.",
        "price_cents": 300,
        "currency": "USD",
        "is_available": True,
        "allowed_modifiers_json": [
            _modifier("ice", "Ice", "choice", ["no_ice", "regular_ice", "extra_ice"]),
        ],
    },
    {
        "id": "drink_009",
        "menu_id": "men_001",
        "name": "Diet Coke",
        "description": "Zero sugar cola.",
        "price_cents": 300,
        "currency": "USD",
        "is_available": True,
        "allowed_modifiers_json": [
            _modifier("ice", "Ice", "choice", ["no_ice", "regular_ice", "extra_ice"]),
        ],
    },
    {
        "id": "drink_010",
        "menu_id": "men_001",
        "name": "Sprite",
        "description": "Lemon-lime soda.",
        "price_cents": 300,
        "currency": "USD",
        "is_available": True,
        "allowed_modifiers_json": [
            _modifier("ice", "Ice", "choice", ["no_ice", "regular_ice", "extra_ice"]),
        ],
    },
    {
        "id": "drink_011",
        "menu_id": "men_001",
        "name": "Orange Juice",
        "description": "Fresh orange juice.",
        "price_cents": 450,
        "currency": "USD",
        "is_available": True,
        "allowed_modifiers_json": [
            _modifier("pulp", "Pulp", "choice", ["no_pulp", "some_pulp", "lots_pulp"]),
        ],
    },
    {
        "id": "drink_012",
        "menu_id": "men_001",
        "name": "Apple Juice",
        "description": "Pressed apple juice.",
        "price_cents": 450,
        "currency": "USD",
        "is_available": True,
        "allowed_modifiers_json": None,
    },
    {
        "id": "drink_013",
        "menu_id": "men_001",
        "name": "House Red (glass)",
        "description": "House red by the glass.",
        "price_cents": 900,
        "currency": "USD",
        "is_available": True,
        "allowed_modifiers_json": None,
    },
    {
        "id": "drink_014",
        "menu_id": "men_001",
        "name": "House White (glass)",
        "description": "House white by the glass.",
        "price_cents": 900,
        "currency": "USD",
        "is_available": True,
        "allowed_modifiers_json": None,
    },
    {
        "id": "drink_015",
        "menu_id": "men_001",
        "name": "Italian Soda",
        "description": "Italian soda with citrus sparkle.",
        "price_cents": 550,
        "currency": "USD",
        "is_available": True,
        "allowed_modifiers_json": [
            _modifier("flavor", "Flavor", "choice", ["blood_orange", "lemon", "berry"]),
            _modifier("sparkling", "Sparkling", "toggle"),
        ],
    },
]


def main() -> None:
    engine = get_engine(timeout_seconds=2.0)
    inspector = inspect(engine)
    required_tables = {"restaurants", "menus", "menu_items", "tables"}
    if not required_tables.issubset(set(inspector.get_table_names(schema="public"))):
        print("no schema yet")
        return

    now = datetime.now(timezone.utc)
    target_item_ids = [str(item["id"]) for item in SEED_ITEMS]

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
            .values(id="men_001", restaurant_id="rst_001", version=1, updated_at=now)
            .on_conflict_do_update(
                index_elements=[MenuModel.id],
                set_={"restaurant_id": "rst_001", "version": 1, "updated_at": now},
            )
        )

        session.execute(
            delete(MenuItemModel).where(
                MenuItemModel.menu_id == "men_001",
                MenuItemModel.id.not_in(target_item_ids),
            )
        )

        for item in SEED_ITEMS:
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
                        "allowed_modifiers_json": item["allowed_modifiers_json"],
                    },
                )
            )

        session.execute(
            insert(TableModel)
            .values(
                id="tbl_001",
                restaurant_id="rst_001",
                status="OPEN",
                opened_at=now,
                closed_at=None,
            )
            .on_conflict_do_update(
                index_elements=[TableModel.id],
                set_={
                    "restaurant_id": "rst_001",
                    "status": "OPEN",
                    "opened_at": now,
                    "closed_at": None,
                },
            )
        )

        session.commit()
        print("seed complete")


if __name__ == "__main__":
    main()
