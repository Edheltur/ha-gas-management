"""Runtime data and persistent measurements for a single cylinder."""

from asyncio import Lock

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.storage import Store

from .calculation import normalize_mass_kg
from .const import ASSEMBLY_MASS, DOMAIN, EDITABLE_MASS_KEYS, EQUIPMENT_MASS, GAS_CO2

STORAGE_VERSION = 1


def cylinder_store(hass: HomeAssistant, entry_id: str) -> Store[dict[str, float]]:
    """Get a store scoped to one config entry."""
    return Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry_id}", atomic_writes=True)


class Cylinder:
    """Track and persist the measurements of one cylinder."""

    def __init__(
        self, hass: HomeAssistant, entry_id: str, name: str, configured_masses: dict[str, float]
    ) -> None:
        """Set up entry-scoped identity and storage."""
        self.hass = hass
        self.signal = f"{DOMAIN}.{entry_id}.mass_changed"
        self.device_info = DeviceInfo(identifiers={(DOMAIN, entry_id)}, name=name, model=GAS_CO2)
        self._configured_masses = configured_masses
        self._readings: dict[str, float] = {}
        self._store = cylinder_store(hass, entry_id)
        self._lock = Lock()
        self._closed = False

    @property
    def masses(self) -> dict[str, float]:
        """Combine configured cylinder masses with the current readings."""
        return self._configured_masses | self._readings

    async def async_load(self) -> None:
        """Restore known valid masses before creating entities."""
        data = await self._store.async_load()
        if isinstance(data, dict):
            self._readings = {
                key: value
                for key in EDITABLE_MASS_KEYS
                if (value := normalize_mass_kg(data.get(key))) is not None
            }

    async def async_set_reading(self, key: str, value: float) -> None:
        """Persist an edit and notify entities after the write."""
        if key not in EDITABLE_MASS_KEYS:
            raise ValueError(f"Unknown reading key: {key}")
        mass = normalize_mass_kg(value)
        if mass is None:
            raise HomeAssistantError("Mass must be a finite value from 0 to 1000 kg")

        async with self._lock:
            if self._closed:
                raise HomeAssistantError("Cylinder is unloading")
            if self._readings.get(key) == mass:
                return
            updated = {**self._readings, key: mass}
            if key == EQUIPMENT_MASS and key in self._readings:
                updated.pop(ASSEMBLY_MASS, None)
            await self._store.async_save(updated)
            # Home Assistant's Store logs certain write errors instead of raising them.
            if await self._store.async_load() != updated:
                raise HomeAssistantError("Could not save the cylinder measurements")
            self._readings = updated
            async_dispatcher_send(self.hass, self.signal)

    async def async_close(self) -> None:
        """Drain pending writes before allowing reload or removal."""
        async with self._lock:
            self._closed = True
