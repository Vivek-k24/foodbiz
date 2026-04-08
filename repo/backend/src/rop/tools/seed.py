from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import delete, inspect, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from rop.infrastructure.db.models.location import LocationModel
from rop.infrastructure.db.models.menu import (
    MenuCategoryModel,
    MenuItemModel,
    MenuModel,
    RestaurantModel,
)
from rop.infrastructure.db.models.role import RoleModel
from rop.infrastructure.db.models.session_record import SessionModel
from rop.infrastructure.db.models.table import TableModel
from rop.infrastructure.db.session import get_engine


def _modifier(
    code: str,
    label: str,
    kind: str,
    options: list[str] | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {"code": code, "label": label, "kind": kind}
    if options:
        payload["options"] = options
    return payload


ROLE_ROWS: list[dict[str, str]] = [
    {
        "id": "rol_ceo",
        "code": "CEO",
        "display_name": "Chief Executive Officer",
        "role_group": "CORPORATE",
    },
    {
        "id": "rol_president",
        "code": "PRESIDENT",
        "display_name": "President",
        "role_group": "CORPORATE",
    },
    {
        "id": "rol_coo",
        "code": "COO",
        "display_name": "Chief Operating Officer",
        "role_group": "CORPORATE",
    },
    {
        "id": "rol_cmo",
        "code": "CMO",
        "display_name": "Chief Marketing Officer",
        "role_group": "CORPORATE",
    },
    {
        "id": "rol_clo",
        "code": "CLO",
        "display_name": "Chief Legal Officer",
        "role_group": "CORPORATE",
    },
    {
        "id": "rol_cfo",
        "code": "CFO",
        "display_name": "Chief Financial Officer",
        "role_group": "CORPORATE",
    },
    {
        "id": "rol_chro",
        "code": "CHRO",
        "display_name": "Chief Human Resources Officer",
        "role_group": "CORPORATE",
    },
    {
        "id": "rol_vp",
        "code": "VP",
        "display_name": "Vice President",
        "role_group": "CORPORATE_SUPPORT",
    },
    {
        "id": "rol_director",
        "code": "DIRECTOR",
        "display_name": "Director",
        "role_group": "CORPORATE_SUPPORT",
    },
    {
        "id": "rol_hq_staff",
        "code": "HQ_STAFF",
        "display_name": "HQ Staff",
        "role_group": "CORPORATE_SUPPORT",
    },
    {
        "id": "rol_area_director",
        "code": "AREA_DIRECTOR",
        "display_name": "Area Director",
        "role_group": "REGIONAL",
    },
    {
        "id": "rol_franchise_consultant",
        "code": "FRANCHISE_CONSULTANT",
        "display_name": "Franchise Consultant",
        "role_group": "REGIONAL",
    },
    {
        "id": "rol_gm",
        "code": "GM",
        "display_name": "General Manager",
        "role_group": "LOCATION_MANAGEMENT",
    },
    {
        "id": "rol_agm",
        "code": "AGM",
        "display_name": "Assistant General Manager",
        "role_group": "LOCATION_MANAGEMENT",
    },
    {
        "id": "rol_foh_manager",
        "code": "FOH_MANAGER",
        "display_name": "Front of House Manager",
        "role_group": "LOCATION_MANAGEMENT",
    },
    {
        "id": "rol_boh_manager",
        "code": "BOH_MANAGER",
        "display_name": "Back of House Manager",
        "role_group": "LOCATION_MANAGEMENT",
    },
    {
        "id": "rol_bar_manager",
        "code": "BAR_MANAGER",
        "display_name": "Bar Manager",
        "role_group": "LOCATION_MANAGEMENT",
    },
    {
        "id": "rol_exec_chef",
        "code": "EXEC_CHEF",
        "display_name": "Executive Chef",
        "role_group": "KITCHEN",
    },
    {
        "id": "rol_sous_chef",
        "code": "SOUS_CHEF",
        "display_name": "Sous Chef",
        "role_group": "KITCHEN",
    },
    {
        "id": "rol_line_cook",
        "code": "LINE_COOK",
        "display_name": "Line Cook",
        "role_group": "KITCHEN",
    },
    {"id": "rol_prep", "code": "PREP", "display_name": "Prep Cook", "role_group": "KITCHEN"},
    {
        "id": "rol_dishwasher",
        "code": "DISHWASHER",
        "display_name": "Dishwasher",
        "role_group": "KITCHEN",
    },
    {
        "id": "rol_server",
        "code": "SERVER",
        "display_name": "Server",
        "role_group": "FRONT_OF_HOUSE",
    },
    {
        "id": "rol_bartender",
        "code": "BARTENDER",
        "display_name": "Bartender",
        "role_group": "FRONT_OF_HOUSE",
    },
    {"id": "rol_host", "code": "HOST", "display_name": "Host", "role_group": "FRONT_OF_HOUSE"},
    {
        "id": "rol_busser",
        "code": "BUSSER",
        "display_name": "Busser",
        "role_group": "FRONT_OF_HOUSE",
    },
    {
        "id": "rol_bar_back",
        "code": "BAR_BACK",
        "display_name": "Bar Back",
        "role_group": "FRONT_OF_HOUSE",
    },
]

CATEGORY_ROWS: list[dict[str, str]] = [
    {
        "id": "cat_western",
        "name": "Western",
        "category_kind": "FOOD",
        "cuisine_or_family": "WESTERN",
    },
    {
        "id": "cat_mexican",
        "name": "Mexican",
        "category_kind": "FOOD",
        "cuisine_or_family": "MEXICAN",
    },
    {"id": "cat_french", "name": "French", "category_kind": "FOOD", "cuisine_or_family": "FRENCH"},
    {
        "id": "cat_italian",
        "name": "Italian",
        "category_kind": "FOOD",
        "cuisine_or_family": "ITALIAN",
    },
    {"id": "cat_greek", "name": "Greek", "category_kind": "FOOD", "cuisine_or_family": "GREEK"},
    {"id": "cat_beer", "name": "Beer", "category_kind": "DRINK", "cuisine_or_family": "BEER"},
    {"id": "cat_wine", "name": "Wine", "category_kind": "DRINK", "cuisine_or_family": "WINE"},
    {
        "id": "cat_spirits",
        "name": "Spirits",
        "category_kind": "DRINK",
        "cuisine_or_family": "SPIRITS",
    },
    {
        "id": "cat_cocktail",
        "name": "Cocktails",
        "category_kind": "DRINK",
        "cuisine_or_family": "COCKTAIL",
    },
    {
        "id": "cat_non_alcoholic",
        "name": "Non-Alcoholic",
        "category_kind": "DRINK",
        "cuisine_or_family": "NON_ALCOHOLIC",
    },
]

MENU_ITEMS: list[dict[str, object]] = [
    {
        "id": "itm_001",
        "category_id": "cat_western",
        "name": "Grilled New York Strip",
        "description": "12 oz strip steak with herb butter and roasted potatoes.",
        "price_cents": 2890,
        "currency": "USD",
        "is_available": True,
        "allowed_modifiers_json": [
            _modifier(
                "temperature",
                "Temperature",
                "choice",
                ["rare", "medium_rare", "medium", "well_done"],
            ),
            _modifier("add_peppercorn_sauce", "Add Peppercorn Sauce", "toggle"),
        ],
    },
    {
        "id": "itm_002",
        "category_id": "cat_western",
        "name": "Buttermilk Chicken Sandwich",
        "description": "Crispy chicken, house pickles, and aioli on brioche.",
        "price_cents": 1590,
        "currency": "USD",
        "is_available": True,
        "allowed_modifiers_json": [
            _modifier("side", "Side", "choice", ["fries", "salad"]),
            _modifier("extra_pickles", "Extra Pickles", "toggle"),
        ],
    },
    {
        "id": "itm_003",
        "category_id": "cat_western",
        "name": "Classic Cheeseburger",
        "description": "Double patty burger with cheddar, onion, lettuce, and burger sauce.",
        "price_cents": 1490,
        "currency": "USD",
        "is_available": True,
        "allowed_modifiers_json": [
            _modifier("cheese", "Cheese", "choice", ["cheddar", "swiss", "none"]),
            _modifier("add_bacon", "Add Bacon", "toggle"),
        ],
    },
    {
        "id": "itm_004",
        "category_id": "cat_mexican",
        "name": "Chicken Tinga Tacos",
        "description": "Three corn tortillas with smoky shredded chicken and crema.",
        "price_cents": 1390,
        "currency": "USD",
        "is_available": True,
        "allowed_modifiers_json": [
            _modifier("salsa", "Salsa", "choice", ["verde", "roja", "both"]),
            _modifier("no_onion", "No Onion", "toggle"),
        ],
    },
    {
        "id": "itm_005",
        "category_id": "cat_mexican",
        "name": "Carne Asada Burrito",
        "description": "Grilled steak, rice, beans, pico, and jack cheese.",
        "price_cents": 1690,
        "currency": "USD",
        "is_available": True,
        "allowed_modifiers_json": [
            _modifier("beans", "Beans", "choice", ["black", "pinto", "none"]),
            _modifier("extra_guac", "Extra Guac", "toggle"),
        ],
    },
    {
        "id": "itm_006",
        "category_id": "cat_mexican",
        "name": "Chilaquiles Verdes",
        "description": "Crispy tortillas, salsa verde, queso fresco, and eggs.",
        "price_cents": 1490,
        "currency": "USD",
        "is_available": True,
        "allowed_modifiers_json": [
            _modifier("eggs", "Eggs", "choice", ["sunny_side", "scrambled"]),
            _modifier("add_chorizo", "Add Chorizo", "toggle"),
        ],
    },
    {
        "id": "itm_007",
        "category_id": "cat_french",
        "name": "Steak Frites",
        "description": "Bistro steak with pommes frites and maître d'hôtel butter.",
        "price_cents": 2650,
        "currency": "USD",
        "is_available": True,
        "allowed_modifiers_json": [
            _modifier(
                "temperature",
                "Temperature",
                "choice",
                ["rare", "medium_rare", "medium", "well_done"],
            ),
            _modifier("extra_aioli", "Extra Aioli", "toggle"),
        ],
    },
    {
        "id": "itm_008",
        "category_id": "cat_french",
        "name": "Croque Monsieur",
        "description": "Ham, Gruyère, béchamel, and toasted pain de mie.",
        "price_cents": 1450,
        "currency": "USD",
        "is_available": True,
        "allowed_modifiers_json": [
            _modifier("add_egg", "Add Egg", "toggle"),
            _modifier("side", "Side", "choice", ["fries", "greens"]),
        ],
    },
    {
        "id": "itm_009",
        "category_id": "cat_french",
        "name": "Moules Marinières",
        "description": "Mussels steamed with white wine, shallots, and parsley.",
        "price_cents": 1790,
        "currency": "USD",
        "is_available": True,
        "allowed_modifiers_json": [
            _modifier("broth", "Broth", "choice", ["classic", "cream"]),
            _modifier("extra_bread", "Extra Bread", "toggle"),
        ],
    },
    {
        "id": "itm_010",
        "category_id": "cat_italian",
        "name": "Margherita Pizza",
        "description": "San Marzano tomato, mozzarella, basil.",
        "price_cents": 1450,
        "currency": "USD",
        "is_available": True,
        "allowed_modifiers_json": [
            _modifier("extra_mozzarella", "Extra Mozzarella", "toggle"),
            _modifier("crust", "Crust", "choice", ["regular", "thin", "gluten_free"]),
        ],
    },
    {
        "id": "itm_011",
        "category_id": "cat_italian",
        "name": "Spaghetti Carbonara",
        "description": "Guanciale, pecorino, egg, black pepper.",
        "price_cents": 1790,
        "currency": "USD",
        "is_available": True,
        "allowed_modifiers_json": [
            _modifier("pasta", "Pasta", "choice", ["spaghetti", "rigatoni"]),
            _modifier("add_guanciale", "Add Guanciale", "toggle"),
        ],
    },
    {
        "id": "itm_012",
        "category_id": "cat_italian",
        "name": "Chicken Parmigiana",
        "description": "Breaded chicken, marinara, mozzarella, and herbs.",
        "price_cents": 1950,
        "currency": "USD",
        "is_available": True,
        "allowed_modifiers_json": [
            _modifier("side", "Side", "choice", ["spaghetti", "salad"]),
            _modifier("extra_marinara", "Extra Marinara", "toggle"),
        ],
    },
    {
        "id": "itm_013",
        "category_id": "cat_greek",
        "name": "Chicken Souvlaki Plate",
        "description": "Grilled chicken skewers with rice pilaf and tzatziki.",
        "price_cents": 1725,
        "currency": "USD",
        "is_available": True,
        "allowed_modifiers_json": [
            _modifier("side", "Side", "choice", ["rice", "greek_potatoes", "salad"]),
            _modifier("extra_tzatziki", "Extra Tzatziki", "toggle"),
        ],
    },
    {
        "id": "itm_014",
        "category_id": "cat_greek",
        "name": "Lamb Gyro",
        "description": "Warm pita with shaved lamb, onion, tomato, and yogurt sauce.",
        "price_cents": 1490,
        "currency": "USD",
        "is_available": True,
        "allowed_modifiers_json": [
            _modifier("no_onion", "No Onion", "toggle"),
            _modifier("extra_feta", "Extra Feta", "toggle"),
        ],
    },
    {
        "id": "itm_015",
        "category_id": "cat_greek",
        "name": "Spanakopita",
        "description": "Flaky phyllo pastry with spinach and feta.",
        "price_cents": 1090,
        "currency": "USD",
        "is_available": True,
        "allowed_modifiers_json": [_modifier("add_salad", "Add Side Salad", "toggle")],
    },
    {
        "id": "itm_016",
        "category_id": "cat_beer",
        "name": "Pilsner Draft",
        "description": "Crisp German-style pilsner.",
        "price_cents": 700,
        "currency": "USD",
        "is_available": True,
        "allowed_modifiers_json": [_modifier("size", "Size", "choice", ["12oz", "16oz"])],
    },
    {
        "id": "itm_017",
        "category_id": "cat_beer",
        "name": "Hazy IPA Draft",
        "description": "Juicy tropical IPA.",
        "price_cents": 800,
        "currency": "USD",
        "is_available": True,
        "allowed_modifiers_json": [_modifier("size", "Size", "choice", ["12oz", "16oz"])],
    },
    {
        "id": "itm_018",
        "category_id": "cat_wine",
        "name": "House Red Glass",
        "description": "Medium-bodied red blend.",
        "price_cents": 900,
        "currency": "USD",
        "is_available": True,
        "allowed_modifiers_json": None,
    },
    {
        "id": "itm_019",
        "category_id": "cat_wine",
        "name": "House White Glass",
        "description": "Bright citrus-forward white wine.",
        "price_cents": 900,
        "currency": "USD",
        "is_available": True,
        "allowed_modifiers_json": None,
    },
    {
        "id": "itm_020",
        "category_id": "cat_spirits",
        "name": "Single Malt Pour",
        "description": "2 oz neat or rocks pour.",
        "price_cents": 1400,
        "currency": "USD",
        "is_available": True,
        "allowed_modifiers_json": [_modifier("serve", "Serve", "choice", ["neat", "rocks"])],
    },
    {
        "id": "itm_021",
        "category_id": "cat_spirits",
        "name": "Reposado Tequila Pour",
        "description": "2 oz premium tequila.",
        "price_cents": 1250,
        "currency": "USD",
        "is_available": True,
        "allowed_modifiers_json": [_modifier("serve", "Serve", "choice", ["neat", "rocks"])],
    },
    {
        "id": "itm_022",
        "category_id": "cat_cocktail",
        "name": "Negroni",
        "description": "Gin, Campari, sweet vermouth.",
        "price_cents": 1350,
        "currency": "USD",
        "is_available": True,
        "allowed_modifiers_json": [
            _modifier("style", "Style", "choice", ["classic", "boulevardier"]),
            _modifier("orange_twist", "Orange Twist", "toggle"),
        ],
    },
    {
        "id": "itm_023",
        "category_id": "cat_cocktail",
        "name": "Margarita",
        "description": "Tequila, lime, triple sec.",
        "price_cents": 1290,
        "currency": "USD",
        "is_available": True,
        "allowed_modifiers_json": [
            _modifier("rim", "Rim", "choice", ["salt", "tajin", "none"]),
            _modifier("frozen", "Frozen", "toggle"),
        ],
    },
    {
        "id": "itm_024",
        "category_id": "cat_non_alcoholic",
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
        "id": "itm_025",
        "category_id": "cat_non_alcoholic",
        "name": "Sparkling Lemonade",
        "description": "Fresh citrus lemonade with bubbles.",
        "price_cents": 520,
        "currency": "USD",
        "is_available": True,
        "allowed_modifiers_json": [
            _modifier("less_sugar", "Less Sugar", "toggle"),
            _modifier("add_mint", "Add Mint", "toggle"),
        ],
    },
    {
        "id": "itm_026",
        "category_id": "cat_non_alcoholic",
        "name": "Greek Iced Coffee",
        "description": "Shaken chilled coffee with foam.",
        "price_cents": 490,
        "currency": "USD",
        "is_available": True,
        "allowed_modifiers_json": [
            _modifier("milk", "Milk", "choice", ["whole", "oat", "almond", "none"]),
            _modifier("sweetness", "Sweetness", "choice", ["unsweet", "half", "sweet"]),
        ],
    },
]


def _table_seed_rows(now: datetime) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for index in range(1, 21):
        table_id = f"tbl_{index:03d}"
        rows.append(
            {
                "id": table_id,
                "restaurant_id": "rst_001",
                "status": "OPEN" if table_id == "tbl_001" else "CLOSED",
                "opened_at": now if table_id == "tbl_001" else None,
                "closed_at": None if table_id == "tbl_001" else now,
            }
        )
    return rows


def _location_seed_rows(now: datetime) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    table_zones = ["Entrance Lane", "Main Dining", "Window Line", "Patio"]
    for index in range(1, 21):
        rows.append(
            {
                "id": f"loc_tbl_{index:03d}",
                "restaurant_id": "rst_001",
                "type": "TABLE",
                "name": f"table_{index:03d}",
                "display_label": f"Table {index}",
                "capacity": 4 if index % 5 else 6,
                "zone": table_zones[(index - 1) % len(table_zones)],
                "is_active": True,
                "created_at": now,
            }
        )
    for index in range(1, 21):
        rows.append(
            {
                "id": f"loc_bar_{index:03d}",
                "restaurant_id": "rst_001",
                "type": "BAR_SEAT",
                "name": f"bar_seat_{index:03d}",
                "display_label": f"Bar {index}",
                "capacity": 1,
                "zone": "Bar Counter",
                "is_active": True,
                "created_at": now,
            }
        )
    rows.append(
        {
            "id": "loc_online_pickup",
            "restaurant_id": "rst_001",
            "type": "ONLINE_PICKUP",
            "name": "online_pickup",
            "display_label": "Online Pickup",
            "capacity": None,
            "zone": "Off Premise",
            "is_active": True,
            "created_at": now,
        }
    )
    rows.append(
        {
            "id": "loc_online_delivery",
            "restaurant_id": "rst_001",
            "type": "ONLINE_DELIVERY",
            "name": "online_delivery",
            "display_label": "Online Delivery",
            "capacity": None,
            "zone": "Off Premise",
            "is_active": True,
            "created_at": now,
        }
    )
    return rows


def main() -> None:
    engine = get_engine(timeout_seconds=2.0)
    inspector = inspect(engine)
    required_tables = {
        "restaurants",
        "menus",
        "menu_items",
        "menu_categories",
        "locations",
        "roles",
        "sessions",
        "tables",
    }
    if not required_tables.issubset(set(inspector.get_table_names(schema="public"))):
        print("no schema yet")
        return

    now = datetime.now(timezone.utc)
    target_item_ids = [str(item["id"]) for item in MENU_ITEMS]
    target_category_ids = [row["id"] for row in CATEGORY_ROWS]

    with Session(engine) as session:
        session.execute(
            insert(RestaurantModel)
            .values(
                id="rst_001",
                name="FoodBiz Grand Kitchen",
                timezone="America/Chicago",
                currency="USD",
                created_at=now,
            )
            .on_conflict_do_update(
                index_elements=[RestaurantModel.id],
                set_={
                    "name": "FoodBiz Grand Kitchen",
                    "timezone": "America/Chicago",
                    "currency": "USD",
                },
            )
        )

        for role_row in ROLE_ROWS:
            session.execute(
                insert(RoleModel)
                .values(**role_row, created_at=now)
                .on_conflict_do_update(
                    index_elements=[RoleModel.id],
                    set_={
                        "code": role_row["code"],
                        "display_name": role_row["display_name"],
                        "role_group": role_row["role_group"],
                    },
                )
            )

        for location_row in _location_seed_rows(now):
            session.execute(
                insert(LocationModel)
                .values(**location_row)
                .on_conflict_do_update(
                    index_elements=[LocationModel.id],
                    set_={
                        "restaurant_id": location_row["restaurant_id"],
                        "type": location_row["type"],
                        "name": location_row["name"],
                        "display_label": location_row["display_label"],
                        "capacity": location_row["capacity"],
                        "zone": location_row["zone"],
                        "is_active": location_row["is_active"],
                    },
                )
            )

        for table_row in _table_seed_rows(now):
            session.execute(
                insert(TableModel)
                .values(**table_row)
                .on_conflict_do_update(
                    index_elements=[TableModel.id],
                    set_={
                        "restaurant_id": table_row["restaurant_id"],
                        "status": table_row["status"],
                        "opened_at": table_row["opened_at"],
                        "closed_at": table_row["closed_at"],
                    },
                )
            )

        session.execute(
            update(SessionModel)
            .where(
                SessionModel.restaurant_id == "rst_001",
                SessionModel.location_id.like("loc_tbl_%"),
                SessionModel.location_id != "loc_tbl_001",
                SessionModel.status == "OPEN",
            )
            .values(
                status="CLOSED",
                closed_at=now,
                notes="Closed during deterministic seed reset",
            )
        )
        session.execute(
            update(SessionModel)
            .where(
                SessionModel.restaurant_id == "rst_001",
                SessionModel.location_id == "loc_tbl_001",
                SessionModel.id != "ses_seed_tbl_001",
                SessionModel.status == "OPEN",
            )
            .values(
                status="CLOSED",
                closed_at=now,
                notes="Closed during deterministic seed reset",
            )
        )
        session.execute(
            insert(SessionModel)
            .values(
                id="ses_seed_tbl_001",
                restaurant_id="rst_001",
                location_id="loc_tbl_001",
                status="OPEN",
                opened_at=now,
                closed_at=None,
                opened_by_role_id="rol_host",
                opened_by_source="STAFF_CONSOLE",
                notes="Seeded open dining session",
            )
            .on_conflict_do_update(
                index_elements=[SessionModel.id],
                set_={
                    "restaurant_id": "rst_001",
                    "location_id": "loc_tbl_001",
                    "status": "OPEN",
                    "opened_at": now,
                    "closed_at": None,
                    "opened_by_role_id": "rol_host",
                    "opened_by_source": "STAFF_CONSOLE",
                    "notes": "Seeded open dining session",
                },
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
            delete(MenuCategoryModel).where(
                MenuCategoryModel.restaurant_id == "rst_001",
                MenuCategoryModel.id.not_in(target_category_ids),
            )
        )

        for category_row in CATEGORY_ROWS:
            session.execute(
                insert(MenuCategoryModel)
                .values(**category_row, restaurant_id="rst_001", created_at=now)
                .on_conflict_do_update(
                    index_elements=[MenuCategoryModel.id],
                    set_={
                        "restaurant_id": "rst_001",
                        "name": category_row["name"],
                        "category_kind": category_row["category_kind"],
                        "cuisine_or_family": category_row["cuisine_or_family"],
                    },
                )
            )

        session.execute(
            delete(MenuItemModel).where(
                MenuItemModel.menu_id == "men_001",
                MenuItemModel.id.not_in(target_item_ids),
            )
        )

        for item in MENU_ITEMS:
            session.execute(
                insert(MenuItemModel)
                .values(
                    id=item["id"],
                    menu_id="men_001",
                    restaurant_id="rst_001",
                    category_id=item["category_id"],
                    name=item["name"],
                    description=item["description"],
                    price_cents=item["price_cents"],
                    currency=item["currency"],
                    is_available=item["is_available"],
                    created_at=now,
                    allowed_modifiers_json=item["allowed_modifiers_json"],
                )
                .on_conflict_do_update(
                    index_elements=[MenuItemModel.id],
                    set_={
                        "menu_id": "men_001",
                        "restaurant_id": "rst_001",
                        "category_id": item["category_id"],
                        "name": item["name"],
                        "description": item["description"],
                        "price_cents": item["price_cents"],
                        "currency": item["currency"],
                        "is_available": item["is_available"],
                        "allowed_modifiers_json": item["allowed_modifiers_json"],
                    },
                )
            )

        session.commit()
        print("seed complete")


if __name__ == "__main__":
    main()
