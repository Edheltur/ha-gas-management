"""Test cylinder calculations independently of entity updates."""

from copy import copy

import pytest

from custom_components.gas_management.calculation import fill_pct, gas_remaining_g, mass_kg
from custom_components.gas_management.const import (
    ASSEMBLY_MASS,
    EQUIPMENT_MASS,
    NOMINAL_FILL_MASS,
    TARE_MASS,
)

MASSES = {
    TARE_MASS: 4.0,
    EQUIPMENT_MASS: 0.3,
    ASSEMBLY_MASS: 5.8,
    NOMINAL_FILL_MASS: 1.0,
}


@pytest.mark.parametrize("key", [TARE_MASS, EQUIPMENT_MASS, ASSEMBLY_MASS, NOMINAL_FILL_MASS])
def test_missing_inputs(key: str) -> None:
    """Only calculations depending on the missing input become unavailable."""
    masses = copy(MASSES)
    del masses[key]
    assert gas_remaining_g(masses) == (1500 if key == NOMINAL_FILL_MASS else None)
    assert fill_pct(masses) is None


def test_empty_cylinder_with_decimal_masses() -> None:
    """An exact decimal sum does not become a negative floating-point residual."""
    masses = {**MASSES, TARE_MASS: 4.1, EQUIPMENT_MASS: 0.2, ASSEMBLY_MASS: 4.3}
    assert gas_remaining_g(masses) == 0
    assert fill_pct(masses) == 0


def test_over_nominal_fill() -> None:
    """Show fill values above 100 percent."""
    assert gas_remaining_g(MASSES) == 1500
    assert fill_pct(MASSES) == 150


@pytest.mark.parametrize("value", [None, "1", True, float("nan"), float("inf"), -1, 1001])
def test_invalid_mass(value: object) -> None:
    """A missing or invalid stored mass never enters a calculation."""
    assert mass_kg(value) is None


def test_mass_precision() -> None:
    """Measurements are stored to one gram."""
    assert mass_kg(1.2346) == 1.235
