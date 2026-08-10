"""KKday eSIM CTA — 제휴 홈 링크만 사용."""

from app.config import Settings
from app.services.kkday_links import kkday_esim_cta


def test_esim_cta_uses_affiliate_home() -> None:
    settings = Settings(kkday_affiliate_home_url="https://kkday.tpk.lu/I3n5UXqs")
    cta = kkday_esim_cta(settings, region="오사카")
    assert cta is not None
    assert cta.provider == "kkday"
    assert cta.url == "https://kkday.tpk.lu/I3n5UXqs"
    assert cta.product_hint == "esim"
    assert "eSIM" in cta.label


def test_esim_cta_none_without_home() -> None:
    settings = Settings(kkday_affiliate_home_url="")
    assert kkday_esim_cta(settings) is None
