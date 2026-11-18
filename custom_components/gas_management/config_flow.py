"""Configure a CO₂ cylinder from the Home Assistant UI."""

from random import choice

import probatio
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_NAME
from homeassistant.helpers.selector import NumberSelector, NumberSelectorConfig, NumberSelectorMode

from .calculation import mass_kg
from .const import (
    CONFIGURED_MASS_KEYS,
    DOMAIN,
    MASS_STEP_KG,
    MAX_MASS_KG,
    NOMINAL_FILL_MASS,
    TARE_MASS,
)
from .cylinder_names import DREADNOUGHT_NAMES

MASS_SELECTOR = NumberSelector(
    NumberSelectorConfig(
        min=MASS_STEP_KG,
        max=MAX_MASS_KG,
        step=MASS_STEP_KG,
        unit_of_measurement="kg",
        mode=NumberSelectorMode.BOX,
    )
)
TYPICAL_CO2_CYLINDER_5L = {TARE_MASS: 8.5, NOMINAL_FILL_MASS: 3.0}


class GasManagementConfigFlow(ConfigFlow, domain=DOMAIN):
    """Create one config entry for each physical cylinder."""

    VERSION = 2

    def _suggest_cylinder_name(self) -> str:
        """Suggest an unused name, treating both spellings as the same name."""
        russian = self.hass.config.language == "ru"
        used = {entry.title.strip().casefold() for entry in self._async_current_entries()}
        available = [
            display_name if russian else key.capitalize()
            for key, display_name in DREADNOUGHT_NAMES.items()
            if key not in used and display_name.casefold() not in used
        ]
        if available:
            return choice(available)

        key, display_name = choice(tuple(DREADNOUGHT_NAMES.items()))
        index = 2
        while f"{key} {index}" in used or f"{display_name.casefold()} {index}" in used:
            index += 1
        return f"{display_name if russian else key.capitalize()} {index}"

    async def async_step_user(
        self, user_input: dict[str, str | float] | None = None
    ) -> ConfigFlowResult:
        """Ask for a display name and the two masses stamped on the cylinder."""
        errors: dict[str, str] = {}
        if user_input is not None:
            name = str(user_input[CONF_NAME]).strip()
            if not name:
                errors[CONF_NAME] = "empty_name"
            data: dict[str, str | float] = {CONF_NAME: name}
            for key in CONFIGURED_MASS_KEYS:
                value = mass_kg(user_input[key])
                if value is None or value <= 0:
                    errors[key] = "invalid_mass"
                else:
                    data[key] = value
            if not errors:
                return self.async_create_entry(title=name, data=data)

        name_field = probatio.Required(CONF_NAME)
        if user_input is None:
            name_field = probatio.Required(CONF_NAME, default=self._suggest_cylinder_name())
        schema = probatio.Schema(
            {
                name_field: str,
                probatio.Required(TARE_MASS): MASS_SELECTOR,
                probatio.Required(NOMINAL_FILL_MASS): MASS_SELECTOR,
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                schema, TYPICAL_CO2_CYLINDER_5L if user_input is None else user_input
            ),
            errors=errors,
        )
