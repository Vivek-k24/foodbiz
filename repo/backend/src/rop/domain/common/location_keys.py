from __future__ import annotations

from rop.domain.common.ids import LocationId, TableId


def table_location_id(table_id: TableId) -> LocationId:
    raw_table_id = str(table_id)
    if raw_table_id.startswith("tbl_"):
        return LocationId(f"loc_{raw_table_id}")
    return LocationId(f"loc_tbl_{raw_table_id}")


def table_id_from_location(location_id: LocationId | str) -> TableId | None:
    raw_location_id = str(location_id)
    if not raw_location_id.startswith("loc_tbl_"):
        return None
    return TableId(raw_location_id.removeprefix("loc_"))
