"""
currency.py — Multi-currency support for Sentinel Sync.

Applications can be ingested in any supported currency (USD, INR, EUR, GBP,
etc.), and the dashboard normalizes everything to a USD-equivalent value
internally for ranking purposes (Dynamic Priority Score, average package),
while letting the user choose how amounts are *displayed* — in the
application's native currency, in USD, in INR, or in INR/LPA (Lakhs Per
Annum), independent of how each entry was originally entered.

FX rates below are fixed, illustrative reference points so the prototype is
stable and reproducible — not a live feed. Swap FX_PER_USD for a live rates
API call in production.
"""

from __future__ import annotations

CURRENCY_SYMBOLS = {
    "USD": "$",
    "INR": "₹",
    "EUR": "€",
    "GBP": "£",
    "AED": "د.إ",
    "SGD": "S$",
    "AUD": "A$",
    "CAD": "C$",
}

SUPPORTED_CURRENCIES = list(CURRENCY_SYMBOLS.keys())

# Indicative reference rates: units of currency per 1 USD.
FX_PER_USD = {
    "USD": 1.0,
    "INR": 83.0,
    "EUR": 0.92,
    "GBP": 0.79,
    "AED": 3.67,
    "SGD": 1.34,
    "AUD": 1.52,
    "CAD": 1.36,
}

LAKH = 100_000  # 1 LPA unit = 100,000 INR

DISPLAY_UNIT_LABELS = {
    "native": "Native Currency",
    "USD": "USD ($)",
    "INR": "INR (₹)",
    "INR_LPA": "INR (LPA)",
    "EUR": "EUR (€)",
    "GBP": "GBP (£)",
}
DISPLAY_UNIT_OPTIONS = list(DISPLAY_UNIT_LABELS.values())
LABEL_TO_UNIT = {v: k for k, v in DISPLAY_UNIT_LABELS.items()}


def to_usd(amount: float, currency: str) -> float:
    rate = FX_PER_USD.get(currency, 1.0)
    return amount / rate


def from_usd(amount_usd: float, currency: str) -> float:
    rate = FX_PER_USD.get(currency, 1.0)
    return amount_usd * rate


def indian_grouping(n: float) -> str:
    """Format using Indian digit grouping, e.g. 8500000 -> '85,00,000'."""
    s = str(int(round(n)))
    sign = ""
    if s.startswith("-"):
        sign, s = "-", s[1:]
    if len(s) <= 3:
        return sign + s
    last3 = s[-3:]
    rest = s[:-3]
    groups = []
    while len(rest) > 2:
        groups.insert(0, rest[-2:])
        rest = rest[:-2]
    if rest:
        groups.insert(0, rest)
    return sign + ",".join(groups) + "," + last3


def format_amount(amount: float, currency: str, display_unit_label: str) -> str:
    """
    Convert `amount` (stored in `currency`) into the unit selected via the
    sidebar dropdown, and return a ready-to-render display string.
    """
    unit = LABEL_TO_UNIT.get(display_unit_label, "native")

    if unit == "native":
        symbol = CURRENCY_SYMBOLS.get(currency, currency + " ")
        if currency == "INR":
            return f"{symbol}{indian_grouping(amount)}"
        return f"{symbol}{amount:,.0f}"

    amount_usd = to_usd(amount, currency)

    if unit == "USD":
        return f"${amount_usd:,.0f}"
    if unit == "INR":
        return f"₹{indian_grouping(from_usd(amount_usd, 'INR'))}"
    if unit == "INR_LPA":
        return f"{from_usd(amount_usd, 'INR') / LAKH:,.2f} LPA"
    if unit == "EUR":
        return f"€{from_usd(amount_usd, 'EUR'):,.0f}"
    if unit == "GBP":
        return f"£{from_usd(amount_usd, 'GBP'):,.0f}"

    return f"${amount_usd:,.0f}"
