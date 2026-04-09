from __future__ import annotations

import pytest

from rop.domain.commerce.enums import Channel
from rop.domain.commerce.rules import ensure_channel_table_consistency, ensure_third_party_metadata
from rop.domain.errors import ValidationError


def test_dine_in_requires_table() -> None:
    with pytest.raises(ValidationError) as exc:
        ensure_channel_table_consistency(Channel.DINE_IN, None)
    assert exc.value.code == "TABLE_REQUIRED"


def test_non_dine_in_rejects_table_id() -> None:
    with pytest.raises(ValidationError) as exc:
        ensure_channel_table_consistency(Channel.PICKUP, "tbl_001")
    assert exc.value.code == "TABLE_NOT_ALLOWED"


def test_third_party_requires_external_reference() -> None:
    with pytest.raises(ValidationError) as exc:
        ensure_third_party_metadata(Channel.THIRD_PARTY, "uber_eats", None)
    assert exc.value.code == "EXTERNAL_REFERENCE_REQUIRED"
