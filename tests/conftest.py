"""Run integration tests against the minimum supported Home Assistant Core."""

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from homeassistant import bootstrap, loader
from homeassistant.config_entries import ConfigEntries
from homeassistant.core import HomeAssistant


@pytest.fixture
async def hass(tmp_path: Path) -> AsyncIterator[HomeAssistant]:
    components = Path(__file__).resolve().parents[1] / "custom_components"
    (tmp_path / "custom_components").symlink_to(components, target_is_directory=True)
    hass = HomeAssistant(str(tmp_path))
    loader.async_setup(hass)
    hass.config.skip_pip = True
    try:
        hass.config_entries = ConfigEntries(hass, {})
        await loader.async_get_custom_components(hass)
        assert await bootstrap.async_load_base_functionality(hass)
        yield hass
    finally:
        await hass.async_stop()
