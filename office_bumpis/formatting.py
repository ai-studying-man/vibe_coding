from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any


def official_date(value: Any | None = None) -> str:
    """Return Korean official-document date format: YYYY. M. D."""
    if value in (None, ""):
        d = date.today()
    elif isinstance(value, datetime):
        d = value.date()
    elif isinstance(value, date):
        d = value
    else:
        text = str(value).strip()
        for fmt in ("%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d", "%Y%m%d"):
            try:
                d = datetime.strptime(text, fmt).date()
                break
            except ValueError:
                continue
        else:
            return text
    return f"{d.year}. {d.month}. {d.day}."


_DIGITS = ["", "일", "이", "삼", "사", "오", "육", "칠", "팔", "구"]
_SMALL_UNITS = ["", "십", "백", "천"]
_BIG_UNITS = ["", "만", "억", "조", "경"]


def amount_to_korean_won(value: Any) -> str:
    """Return a public-document style amount string: 12,340원(금일만이천삼백사십원)."""
    amount = int(Decimal(str(value)).quantize(Decimal("1")))
    if amount == 0:
        korean = "영"
    else:
        parts: list[str] = []
        n = amount
        group_index = 0
        while n:
            group = n % 10000
            if group:
                parts.append(_group_to_korean(group) + _BIG_UNITS[group_index])
            n //= 10000
            group_index += 1
        korean = "".join(reversed(parts))
    return f"{amount:,}원(금{korean}원)"


def _group_to_korean(group: int) -> str:
    out: list[str] = []
    digits = list(map(int, f"{group:04d}"))
    for idx, digit in enumerate(digits):
        if digit == 0:
            continue
        unit = _SMALL_UNITS[3 - idx]
        out.append(_DIGITS[digit] + unit)
    return "".join(out)
