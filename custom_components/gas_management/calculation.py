"""Gas inventory calculations in kilograms."""

from collections.abc import Mapping
from decimal import Decimal
from math import isfinite

from .const import ASSEMBLY_MASS, EQUIPMENT_MASS, MAX_MASS_KG, NOMINAL_FILL_MASS, TARE_MASS


def normalize_mass_kg(value: object) -> float | None:
    """Return a valid mass rounded to the nearest gram, or None."""
    if type(value) not in (int, float):
        return None
    if not 0 <= value <= MAX_MASS_KG or not isfinite(value):
        return None
    return round(float(value), 3)


def gas_remaining_kg(masses: Mapping[str, float]) -> Decimal | None:
    """Calculate remaining gas, treating an inconsistent measurement as unknown."""
    gross = masses.get(ASSEMBLY_MASS)
    tare = masses.get(TARE_MASS)
    equipment = masses.get(EQUIPMENT_MASS)
    if gross is None or tare is None or equipment is None:
        return None
    # Decimal subtraction keeps an exactly empty cylinder at zero.
    remaining = Decimal(str(gross)) - Decimal(str(tare)) - Decimal(str(equipment))
    return remaining if remaining >= 0 else None


def gas_remaining_g(masses: Mapping[str, float]) -> float | None:
    """Calculate the remaining gas in grams."""
    remaining = gas_remaining_kg(masses)
    return None if remaining is None else float(remaining * 1000)


def fill_pct(masses: Mapping[str, float]) -> float | None:
    """Calculate fill percentage relative to the nominal fill mass."""
    remaining = gas_remaining_kg(masses)
    nominal_fill = masses.get(NOMINAL_FILL_MASS)
    if remaining is None or nominal_fill is None or nominal_fill <= 0:
        return None
    return float(remaining * 100 / Decimal(str(nominal_fill)))
