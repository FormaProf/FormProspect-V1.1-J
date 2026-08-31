from datetime import datetime

from services.cloud_crm_mapping import parse_datetime


def test_parse_datetime_adds_local_timezone_in_summer():
    result = parse_datetime("2026-09-22 20:00")

    expected = datetime(
        2026, 9, 22, 20, 0
    ).astimezone().isoformat()

    assert result == expected


def test_parse_datetime_adds_local_timezone_in_winter():
    result = parse_datetime("2026-01-22 20:00")

    expected = datetime(
        2026, 1, 22, 20, 0
    ).astimezone().isoformat()

    assert result == expected


def test_parse_datetime_preserves_existing_timezone():
    value = "2026-09-22T20:00:00+02:00"

    assert parse_datetime(value) == value
