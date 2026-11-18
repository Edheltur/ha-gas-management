"""Test the config flow and entity lifecycle through Home Assistant."""

import asyncio

import probatio
import pytest
from homeassistant.config_entries import SOURCE_USER, ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID, CONF_NAME, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.translation import async_get_translations

from custom_components.gas_management import config_flow
from custom_components.gas_management.const import (
    ASSEMBLY_MASS,
    DOMAIN,
    EQUIPMENT_MASS,
    GAS_CO2,
    NOMINAL_FILL_MASS,
    TARE_MASS,
)
from custom_components.gas_management.cylinder import cylinder_store


async def add_cylinder(hass: HomeAssistant, name: str) -> ConfigEntry:
    """Create a real config entry using the user flow."""
    form = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert form["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(
        form["flow_id"], {CONF_NAME: name, TARE_MASS: 4.0, NOMINAL_FILL_MASS: 1.0}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    return result["result"]


def entity_id(hass: HomeAssistant, entry: ConfigEntry, platform: str, key: str) -> str:
    """Find an entity by its entry-scoped unique ID."""
    result = er.async_get(hass).async_get_entity_id(platform, DOMAIN, f"{entry.entry_id}_{key}")
    assert result is not None
    return result


async def set_mass(hass: HomeAssistant, entry: ConfigEntry, key: str, value: float) -> None:
    """Edit a mass using the standard Home Assistant action."""
    await hass.services.async_call(
        "number",
        "set_value",
        {ATTR_ENTITY_ID: entity_id(hass, entry, "number", key), "value": value},
        blocking=True,
    )


async def test_blank_name(hass: HomeAssistant) -> None:
    """Keep the form open if the name contains only whitespace."""
    form = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        form["flow_id"], {CONF_NAME: " ", TARE_MASS: 4.0, NOMINAL_FILL_MASS: 1.0}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_NAME: "empty_name"}
    fields = probatio.to_field_list(result["data_schema"], custom_serializer=cv.custom_serializer)
    suggestions = {field["name"]: field["description"]["suggested_value"] for field in fields}
    assert suggestions == {CONF_NAME: " ", TARE_MASS: 4.0, NOMINAL_FILL_MASS: 1.0}


async def test_localized_setup_form_with_suggested_masses(hass: HomeAssistant) -> None:
    """Serve the translated setup fields and initial values on the first form."""
    form = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    fields = probatio.to_field_list(form["data_schema"], custom_serializer=cv.custom_serializer)
    fields_by_name = {field["name"]: field for field in fields}
    assert set(fields_by_name) == {CONF_NAME, TARE_MASS, NOMINAL_FILL_MASS}
    assert fields_by_name[CONF_NAME]["default"] in {
        name.capitalize() for name in config_flow.DREADNOUGHT_NAMES
    }
    assert fields_by_name[TARE_MASS]["description"]["suggested_value"] == 8.5
    assert fields_by_name[NOMINAL_FILL_MASS]["description"]["suggested_value"] == 3.0

    for language in ("ru", "en"):
        translations = await async_get_translations(hass, language, "config", {DOMAIN})
        prefix = f"component.{DOMAIN}.config.step.user."
        for name in fields_by_name:
            assert translations[f"{prefix}data.{name}"] != name
            assert translations[f"{prefix}data_description.{name}"]

    result = await hass.config_entries.flow.async_configure(
        form["flow_id"], {CONF_NAME: "Ромашка", TARE_MASS: 8.5, NOMINAL_FILL_MASS: 3.0}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].title == "Ромашка"


@pytest.mark.parametrize(
    ("existing", "expected"),
    [(["Bjorn"], "Танкред"), (["Бьорн", "Tankred", "Бьорн 2", "Tankred 2"], None)],
)
async def test_russian_name_suggestion(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch, existing: list[str], expected: str | None
) -> None:
    """Avoid either spelling of an existing name and number names when needed."""
    monkeypatch.setattr(config_flow, "DREADNOUGHT_NAMES", {"bjorn": "Бьорн", "tankred": "Танкред"})
    hass.config.language = "ru"
    for name in existing:
        await add_cylinder(hass, name)
    form = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    fields = probatio.to_field_list(form["data_schema"], custom_serializer=cv.custom_serializer)
    name = next(field["default"] for field in fields if field["name"] == CONF_NAME)
    if expected is None:
        assert name in ("Бьорн 3", "Танкред 3")
    else:
        assert name == expected


@pytest.mark.parametrize("key", [TARE_MASS, NOMINAL_FILL_MASS])
async def test_configuration_requires_positive_masses(hass: HomeAssistant, key: str) -> None:
    """Require both masses and reject zero for either field."""
    form = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    data = {CONF_NAME: "CO2", TARE_MASS: 4.0, NOMINAL_FILL_MASS: 1.0}
    with pytest.raises(probatio.Invalid):
        form["data_schema"]({field: value for field, value in data.items() if field != key})
    with pytest.raises(probatio.Invalid):
        form["data_schema"]({**data, key: 0})


async def test_weighing_controls_and_icons(hass: HomeAssistant) -> None:
    """Expose only the readings, with explicit icons before the first weighing."""
    entry = await add_cylinder(hass, "CO2")
    assert entry.data[TARE_MASS] == 4.0
    assert entry.data[NOMINAL_FILL_MASS] == 1.0
    registry = er.async_get(hass)
    assert registry.async_get_entity_id("number", DOMAIN, f"{entry.entry_id}_{TARE_MASS}") is None
    assert (
        registry.async_get_entity_id("number", DOMAIN, f"{entry.entry_id}_{NOMINAL_FILL_MASS}")
        is None
    )

    russian = await async_get_translations(hass, "ru", "entity", {DOMAIN})
    labels = {
        EQUIPMENT_MASS: "Вес оснастки",
        ASSEMBLY_MASS: "Общий вес",
    }
    for key, label in labels.items():
        assert russian[f"component.{DOMAIN}.entity.number.{key}.name"] == label

    icons = {
        EQUIPMENT_MASS: "mdi:gauge",
        ASSEMBLY_MASS: "mdi:weight",
    }
    for key, icon in icons.items():
        state = hass.states.get(entity_id(hass, entry, "number", key))
        assert state is not None
        assert state.state == STATE_UNKNOWN
        assert state.attributes["icon"] == icon
        assert state.attributes["device_class"] == "weight"


async def test_reload_uses_entry_title(hass: HomeAssistant) -> None:
    entry = await add_cylinder(hass, "Бьорн")
    assert CONF_NAME not in entry.data
    hass.config_entries.async_update_entry(entry, title="Ромашка")
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, entry.entry_id), entry.entry_id
    )
    assert device.name == "Ромашка"


@pytest.mark.parametrize("key", [TARE_MASS, NOMINAL_FILL_MASS, "other"])
async def test_reject_non_reading_keys(hass: HomeAssistant, key: str) -> None:
    entry = await add_cylinder(hass, "Бьорн")
    cylinder = entry.runtime_data
    before = cylinder.masses.copy()
    with pytest.raises(ValueError, match="Unknown reading key"):
        await cylinder.async_set_reading(key, 9)
    assert cylinder.masses == before
    assert await cylinder_store(hass, entry.entry_id).async_load() is None


async def test_calculate_from_manual_edits(hass: HomeAssistant) -> None:
    """Edit masses independently and recalculate only from valid input."""
    entry = await add_cylinder(hass, "Keg CO2")
    remaining = entity_id(hass, entry, "sensor", "gas_remaining")
    fill = entity_id(hass, entry, "sensor", "fill_level")
    assert hass.states.get(remaining).state == STATE_UNAVAILABLE
    assert hass.states.get(fill).state == STATE_UNAVAILABLE
    assert hass.states.get(entity_id(hass, entry, "number", EQUIPMENT_MASS)).state == STATE_UNKNOWN

    await asyncio.gather(
        set_mass(hass, entry, EQUIPMENT_MASS, 0.3),
        set_mass(hass, entry, ASSEMBLY_MASS, 5.8),
    )
    assert float(hass.states.get(remaining).state) == 1500
    assert hass.states.get(remaining).attributes["unit_of_measurement"] == "g"
    assert hass.states.get(remaining).attributes["state_class"] == "measurement"
    assert float(hass.states.get(fill).state) == 150
    assert hass.states.get(fill).attributes["unit_of_measurement"] == "%"

    await set_mass(hass, entry, ASSEMBLY_MASS, 4.2)
    assert hass.states.get(remaining).state == STATE_UNAVAILABLE
    assert hass.states.get(fill).state == STATE_UNAVAILABLE

    await set_mass(hass, entry, EQUIPMENT_MASS, 0)
    await set_mass(hass, entry, ASSEMBLY_MASS, 4.2)
    assert float(hass.states.get(remaining).state) == 200
    assert float(hass.states.get(fill).state) == 20


async def test_equipment_change_requires_new_weighing(hass: HomeAssistant) -> None:
    entry = await add_cylinder(hass, "CO2")
    gross = entity_id(hass, entry, "number", ASSEMBLY_MASS)
    remaining = entity_id(hass, entry, "sensor", "gas_remaining")
    fill = entity_id(hass, entry, "sensor", "fill_level")

    await set_mass(hass, entry, ASSEMBLY_MASS, 5.8)
    await set_mass(hass, entry, EQUIPMENT_MASS, 0.3)
    await set_mass(hass, entry, EQUIPMENT_MASS, 0.3)
    assert float(hass.states.get(remaining).state) == 1500

    await set_mass(hass, entry, EQUIPMENT_MASS, 0.5)
    assert hass.states.get(gross).state == STATE_UNKNOWN
    assert hass.states.get(remaining).state == STATE_UNAVAILABLE
    assert hass.states.get(fill).state == STATE_UNAVAILABLE
    assert await cylinder_store(hass, entry.entry_id).async_load() == {EQUIPMENT_MASS: 0.5}

    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(gross).state == STATE_UNKNOWN
    assert hass.states.get(remaining).state == STATE_UNAVAILABLE
    await set_mass(hass, entry, ASSEMBLY_MASS, 5.8)
    assert float(hass.states.get(remaining).state) == 1300
    assert float(hass.states.get(fill).state) == 130


async def test_storage_reload_and_removal(hass: HomeAssistant) -> None:
    """Reload and remove one of two identically named cylinders."""
    first = await add_cylinder(hass, "CO2")
    second = await add_cylinder(hass, "CO2")
    devices = dr.async_get(hass)
    first_device = devices.async_get_device_by_identifier((DOMAIN, first.entry_id), first.entry_id)
    second_device = devices.async_get_device_by_identifier(
        (DOMAIN, second.entry_id), second.entry_id
    )
    assert first_device is not None and second_device is not None
    assert first_device.id != second_device.id
    assert first_device.model == second_device.model == GAS_CO2

    registry = er.async_get(hass)
    first_entities = er.async_entries_for_device(registry, first_device.id)
    assert len(first_entities) == 4
    assert all(entity.config_entry_id == first.entry_id for entity in first_entities)

    readings = {EQUIPMENT_MASS: 0.3, ASSEMBLY_MASS: 5.8}
    for key, value in readings.items():
        await set_mass(hass, first, key, value)
    await set_mass(hass, second, ASSEMBLY_MASS, 9)

    assert await cylinder_store(hass, first.entry_id).async_load() == readings
    assert await hass.config_entries.async_reload(first.entry_id)
    await hass.async_block_till_done()
    for key, value in readings.items():
        assert float(hass.states.get(entity_id(hass, first, "number", key)).state) == value
    assert float(hass.states.get(entity_id(hass, first, "sensor", "fill_level")).state) == 150
    assert (
        hass.states.get(entity_id(hass, second, "sensor", "fill_level")).state == STATE_UNAVAILABLE
    )

    await hass.config_entries.async_remove(first.entry_id)
    await hass.async_block_till_done()
    assert devices.async_get(first_device.id) is None
    assert not er.async_entries_for_config_entry(registry, first.entry_id)
    assert await cylinder_store(hass, first.entry_id).async_load() is None
    assert devices.async_get(second_device.id) is not None
    assert float(hass.states.get(entity_id(hass, second, "number", ASSEMBLY_MASS)).state) == 9
