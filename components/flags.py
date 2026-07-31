"""Country flag emojis, derived from ISO codes (visual delight, no downloads).

flag(iso3) returns the emoji flag for a country. Flags are computed from the ISO
3166-1 alpha-2 code using Unicode regional indicator symbols, so any country with a
known alpha-2 mapping renders a real flag.
"""
from __future__ import annotations

# alpha-3 -> alpha-2 for the countries the app surfaces (story countries + festivals).
ISO3_TO_ISO2 = {
    "IND": "IN", "JPN": "JP", "ITA": "IT", "MEX": "MX", "THA": "TH", "FRA": "FR",
    "CHN": "CN", "USA": "US", "ETH": "ET", "MAR": "MA", "BRA": "BR", "GRC": "GR",
    "VNM": "VN", "DEU": "DE", "ESP": "ES", "GBR": "GB", "KOR": "KR", "NGA": "NG",
    "TUR": "TR", "IRN": "IR", "EGY": "EG", "PER": "PE", "IDN": "ID", "RUS": "RU",
    "KEN": "KE", "AUS": "AU", "CAN": "CA", "ARG": "AR", "ZAF": "ZA", "PRT": "PT",
}


def _iso2_to_emoji(iso2: str) -> str:
    iso2 = iso2.upper()
    if len(iso2) != 2 or not iso2.isalpha():
        return ""
    return "".join(chr(0x1F1E6 + (ord(c) - ord("A"))) for c in iso2)


def flag(iso3: str | None) -> str:
    """Return the flag emoji for an iso3 code, or a plate emoji if unknown."""
    if not iso3:
        return "🍽️"
    iso2 = ISO3_TO_ISO2.get(iso3.upper())
    return _iso2_to_emoji(iso2) if iso2 else "🍽️"
