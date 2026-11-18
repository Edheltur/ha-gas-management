"""Editable measurements for a gas cylinder."""

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.const import UnitOfMass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import GasManagementConfigEntry
from .const import (
    ASSEMBLY_MASS,
    EDITABLE_MASS_KEYS,
    EQUIPMENT_MASS,
    MASS_STEP_KG,
    MAX_MASS_KG,
)

MASS_ICONS = {
    EQUIPMENT_MASS: "mdi:gauge",
    ASSEMBLY_MASS: "mdi:weight",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GasManagementConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Expose the two masses that can change after setup."""
    async_add_entities(CylinderNumber(entry, key) for key in EDITABLE_MASS_KEYS)


class CylinderNumber(NumberEntity):
    """An editable mass in kilograms."""

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_device_class = NumberDeviceClass.WEIGHT
    _attr_native_unit_of_measurement = UnitOfMass.KILOGRAMS
    _attr_native_min_value = 0
    _attr_native_max_value = MAX_MASS_KG
    _attr_native_step = MASS_STEP_KG
    _attr_mode = NumberMode.BOX

    def __init__(self, entry: GasManagementConfigEntry, key: str) -> None:
        """Bind this measurement to its cylinder."""
        self._cylinder = entry.runtime_data
        self._key = key
        self._attr_device_info = self._cylinder.device_info
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_translation_key = key
        # Supply the icon on the state for controls that use the weight fallback.
        self._attr_icon = MASS_ICONS[key]

    @property
    def native_value(self) -> float | None:
        """Return the last saved measurement, if supplied."""
        return self._cylinder.masses.get(self._key)

    async def async_set_native_value(self, value: float) -> None:
        """Save the measurement in kilograms."""
        await self._cylinder.async_set_reading(self._key, value)

    async def async_added_to_hass(self) -> None:
        """Listen for edits to this measurement."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(self.hass, self._cylinder.signal, self.async_write_ha_state)
        )
