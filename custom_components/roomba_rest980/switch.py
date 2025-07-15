"""Switches needed."""

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN

ROOMS = {
    "Kitchen": {"region_id": "11", "type": "rid"},
    "Living Room": {"region_id": "9", "type": "rid"},
    "Dining Room": {"region_id": "1", "type": "rid"},
    "Hallway": {"region_id": "10", "type": "rid"},
    "Office": {"region_id": "12", "type": "rid"},
}


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    """Create the switches to identify cleanable rooms."""
    entities = [RoomSwitch(entry, name, data) for name, data in ROOMS.items()]
    for ent in entities:
        hass.data[DOMAIN][f"switch.{ent.unique_id}"] = ent
    async_add_entities(entities)


class RoomSwitch(SwitchEntity):
    """A switch entity to determine whether or not a room should be cleaned by the vacuum."""

    def __init__(self, entry, name, data) -> None:
        """Creates a switch entity for rooms."""
        self._attr_name = f"Clean {name}"
        self._attr_unique_id = f"{entry.entry_id}_{name.lower().replace(' ', '_')}"
        self._is_on = False
        self._room_json = data
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.unique_id)},
            "name": entry.title,
            "manufacturer": "iRobot",
        }

    @property
    def is_on(self):
        """Does the user want the room to be cleaned?"""
        return self._is_on

    async def async_turn_on(self, **kwargs):
        """Yes."""
        self._is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        """No."""
        self._is_on = False
        self.async_write_ha_state()

    def get_region_json(self):
        """I'm not sure what this does to be honest."""
        return self._room_json
