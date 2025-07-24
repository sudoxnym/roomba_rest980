"""Buttons needed."""

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
import logging
from .const import DOMAIN, regionTypeMappings

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    """Create the switches to identify cleanable rooms."""
    cloudCoordinator = hass.data[DOMAIN][entry.entry_id + "_cloud"]
    entities = []
    if cloudCoordinator and cloudCoordinator.data:
        blid = hass.data[DOMAIN][entry.entry_id + "_blid"]
        # Get cloud data for the specific robot
        if blid in cloudCoordinator.data:
            cloud_data = cloudCoordinator.data
            # Create button entities from cloud data
            if "favorites" in cloud_data:
                entities.extend(
                    [FavoriteButton(entry, fav) for fav in cloud_data["favorites"]]
                )
    async_add_entities(entities)


class FavoriteButton(ButtonEntity):
    """A button entity to initiate iRobot favorite routines."""

    def __init__(self, entry, data) -> None:
        """Creates a button entity for entries."""
        self._attr_name = f"{data['name']}"
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{data['favorite_id']}"
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_extra_state_attributes = data
        self._data = data
        self._attr_icon = "mdi:star"
        self._attr_entity_registry_enabled_default = not data["hidden"]
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.unique_id)},
            "name": entry.title,
            "manufacturer": "iRobot",
        }

    async def async_press(self):
        """Send command out to clean with the ID."""
        await self.hass.services.async_call(
            DOMAIN,
            "rest980_clean",
            service_data={
                "base_url": self._entry.data["base_url"],
                "payload": {"cmd": f"favorite_id: {self._data['favorite_id']}"},
            },
        )
