"""Configure a CO₂ cylinder from the Home Assistant UI."""

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_NAME

from .const import DOMAIN


class GasManagementConfigFlow(ConfigFlow, domain=DOMAIN):
    """Create one config entry for each physical cylinder."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, str] | None = None) -> ConfigFlowResult:
        """Ask for a display name, allowing cylinders with the same name."""
        errors = {}
        if user_input is not None:
            name = user_input[CONF_NAME].strip()
            if name:
                return self.async_create_entry(title=name, data={CONF_NAME: name})
            errors[CONF_NAME] = "empty_name"

        schema = vol.Schema({vol.Required(CONF_NAME): str})
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
