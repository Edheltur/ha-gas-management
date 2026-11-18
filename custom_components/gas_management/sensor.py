"""Calculated gas inventory sensors."""

from collections.abc import Callable, Mapping

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import PERCENTAGE, UnitOfMass
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import GasManagementConfigEntry
from .calculation import fill_pct, gas_remaining_g
from .const import NOMINAL_FILL_MASS


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GasManagementConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Expose remaining gas mass and fill level."""
    async_add_entities((RemainingGasSensor(entry), FillLevelSensor(entry)))


class CylinderSensor(SensorEntity):
    """A calculated sensor tied to one cylinder."""

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        entry: GasManagementConfigEntry,
        calculate: Callable[[Mapping[str, float]], float | None],
    ) -> None:
        """Bind this calculation to a cylinder."""
        self._cylinder = entry.runtime_data
        self._calculate = calculate
        self._attr_device_info = self._cylinder.device_info
        self._attr_unique_id = f"{entry.entry_id}_{self.translation_key}"
        self._update_value()

    def _update_value(self) -> None:
        self._attr_native_value = self._calculate(self._cylinder.masses)
        self._attr_available = self._attr_native_value is not None

    async def async_added_to_hass(self) -> None:
        """Subscribe to changes and read the latest measurements."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(self.hass, self._cylinder.signal, self._async_mass_changed)
        )
        self._update_value()

    @callback
    def _async_mass_changed(self, key: str) -> None:
        self._update_value()
        self.async_write_ha_state()


class RemainingGasSensor(CylinderSensor):
    """Remaining gas mass in grams."""

    _attr_translation_key = "gas_remaining"
    _attr_device_class = SensorDeviceClass.WEIGHT
    _attr_native_unit_of_measurement = UnitOfMass.GRAMS
    _attr_suggested_unit_of_measurement = UnitOfMass.GRAMS
    _attr_suggested_display_precision = 0

    def __init__(self, entry: GasManagementConfigEntry) -> None:
        """Set up a remaining mass sensor."""
        super().__init__(entry, gas_remaining_g)

    @callback
    def _async_mass_changed(self, key: str) -> None:
        if key != NOMINAL_FILL_MASS:
            super()._async_mass_changed(key)


class FillLevelSensor(CylinderSensor):
    """Percentage of the nominal fill mass."""

    _attr_translation_key = "fill_level"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_suggested_display_precision = 1

    def __init__(self, entry: GasManagementConfigEntry) -> None:
        """Set up a fill level sensor."""
        super().__init__(entry, fill_pct)
