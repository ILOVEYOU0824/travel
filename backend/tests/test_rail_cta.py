"""철도 CTA — Routes transit 파싱 기준."""

from app.config import Settings
from app.schemas.route import RouteLeg, TransitLineInfo, TravelMode
from app.services.klook_links import klook_search_url, wrap_affiliate_url
from app.services.rail_cta import (
    airport_booking_cta_fallback,
    booking_cta_for_leg,
    booking_cta_from_transit,
    resolve_airport_rule,
)
from app.services.transit_parse import parse_transit_lines_from_leg, transit_mode_label


def test_resolve_airport_osaka() -> None:
    rule = resolve_airport_rule("오사카")
    assert rule is not None
    assert "간사이" in rule.airport_query


def test_parse_haruka_from_fixture_shape() -> None:
    leg = {
        "steps": [
            {"travelMode": "WALK"},
            {
                "travelMode": "TRANSIT",
                "transitDetails": {
                    "transitLine": {
                        "name": "Haruka",
                        "nameShort": "Haruka",
                        "vehicle": {
                            "type": "COMMUTER_TRAIN",
                            "name": {"text": "Train", "languageCode": "en"},
                        },
                    }
                },
            },
            {
                "travelMode": "TRANSIT",
                "transitDetails": {
                    "transitLine": {
                        "name": "Midosuji Line",
                        "vehicle": {"type": "SUBWAY"},
                    }
                },
            },
        ]
    }
    lines = parse_transit_lines_from_leg(leg)
    assert len(lines) == 2
    assert lines[0].name == "Haruka"
    assert lines[0].vehicle_type == "COMMUTER_TRAIN"
    label = transit_mode_label(lines)
    assert label and "Haruka" in label


def test_cta_from_haruka_not_subway() -> None:
    settings = Settings()
    lines = [
        TransitLineInfo(name="Haruka", name_short="Haruka", vehicle_type="COMMUTER_TRAIN"),
        TransitLineInfo(name="Midosuji Line", vehicle_type="SUBWAY"),
    ]
    cta = booking_cta_from_transit(settings, lines)
    assert cta is not None
    assert cta.source_line_name == "Haruka"
    assert cta.product_hint == "airport_rail"
    assert "klook.com" in cta.url


def test_cta_from_shinkansen() -> None:
    settings = Settings()
    cta = booking_cta_from_transit(
        settings,
        [TransitLineInfo(name="Nozomi", vehicle_type="HIGH_SPEED_TRAIN")],
    )
    assert cta is not None
    assert cta.product_hint == "shinkansen"
    assert "Nozomi" in cta.label


def test_subway_only_no_cta() -> None:
    settings = Settings()
    assert (
        booking_cta_from_transit(
            settings,
            [TransitLineInfo(name="Ginza Line", vehicle_type="SUBWAY")],
        )
        is None
    )


def test_leg_prefers_transit_lines() -> None:
    settings = Settings()
    leg = RouteLeg(
        distance_meters=50_000,
        duration_seconds=4000,
        travel_mode=TravelMode.transit,
        transit_lines=[
            TransitLineInfo(name="Haruka", vehicle_type="COMMUTER_TRAIN"),
        ],
    )
    cta = booking_cta_for_leg(settings, leg, from_region="오사카", to_region="교토")
    assert cta is not None
    assert cta.source_line_name == "Haruka"


def test_airport_fallback_without_lines() -> None:
    settings = Settings()
    cta = airport_booking_cta_fallback(settings, "교토", transit_lines=[])
    assert cta is not None
    assert "간사이" in (cta.search_query or "")


def test_wrap_template() -> None:
    settings = Settings(
        travelpayouts_klook_url_template="https://example.test/r?u={url}",
    )
    dest = klook_search_url("Haruka")
    wrapped = wrap_affiliate_url(settings, dest)
    assert wrapped.startswith("https://example.test/r?u=")


def test_wrap_marker_default() -> None:
    settings = Settings(travelpayouts_marker="760147")
    dest = klook_search_url("Haruka")
    wrapped = wrap_affiliate_url(settings, dest)
    assert wrapped.startswith("https://tp.media/r?marker=760147&u=")
    assert "klook.com" in wrapped
