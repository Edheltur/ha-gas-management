"""Configure a CO₂ cylinder from the Home Assistant UI."""

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

MASS_SELECTOR = NumberSelector(
    NumberSelectorConfig(
        min=MASS_STEP_KG,
        max=MAX_MASS_KG,
        step=MASS_STEP_KG,
        unit_of_measurement="kg",
        mode=NumberSelectorMode.BOX,
    )
)
SETUP_SCHEMA = probatio.Schema(
    {
        probatio.Required(CONF_NAME): str,
        probatio.Required(TARE_MASS): MASS_SELECTOR,
        probatio.Required(NOMINAL_FILL_MASS): MASS_SELECTOR,
    }
)


class GasManagementConfigFlow(ConfigFlow, domain=DOMAIN):
    """Create one config entry for each physical cylinder."""

    VERSION = 2

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

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(SETUP_SCHEMA, user_input),
            errors=errors,
        )
