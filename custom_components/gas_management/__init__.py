"""Track gas in individually configured Home Assistant devices."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, Platform
from homeassistant.core import HomeAssistant

from .cylinder import Cylinder, cylinder_store

type GasManagementConfigEntry = ConfigEntry[Cylinder]
PLATFORMS = (Platform.NUMBER, Platform.SENSOR)


async def async_setup_entry(hass: HomeAssistant, entry: GasManagementConfigEntry) -> bool:
    """Load an individual cylinder."""
    cylinder = Cylinder(hass, entry.entry_id, entry.data[CONF_NAME])
    await cylinder.async_load()
    entry.runtime_data = cylinder
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: GasManagementConfigEntry) -> bool:
    """Unload the cylinder and wait for in-flight measurements."""
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    await entry.runtime_data.async_close()
    return True


async def async_remove_entry(hass: HomeAssistant, entry: GasManagementConfigEntry) -> None:
    """Remove only the measurements belonging to the deleted cylinder."""
    await cylinder_store(hass, entry.entry_id).async_remove()
