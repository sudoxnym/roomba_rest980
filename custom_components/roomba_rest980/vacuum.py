"""The vacuum."""

from datetime import datetime

import json
import logging

from homeassistant.components.vacuum import (
    StateVacuumEntity,
    VacuumActivity,
    VacuumEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

from .LegacyCompatibility import createExtendedAttributes

_LOGGER = logging.getLogger(__name__)

SUPPORT_ROBOT = (
    VacuumEntityFeature.START
    | VacuumEntityFeature.RETURN_HOME
    | VacuumEntityFeature.CLEAN_SPOT
    | VacuumEntityFeature.MAP
    | VacuumEntityFeature.SEND_COMMAND
    | VacuumEntityFeature.STATE
    | VacuumEntityFeature.STATUS
)


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    """Create the vacuum."""
    coordinator = hass.data[DOMAIN][entry.entry_id + "_coordinator"]
    await coordinator.async_config_entry_first_refresh()
    async_add_entities([RoombaVacuum(hass, coordinator, entry)])


class RoombaVacuum(CoordinatorEntity, StateVacuumEntity):
    """The Rest980 controlled vacuum."""

    def __init__(self, hass: HomeAssistant, coordinator, entry: ConfigEntry) -> None:
        """Setup the robot."""
        super().__init__(coordinator)
        self.hass = hass
        self._entry: ConfigEntry = entry
        self._attr_supported_features = SUPPORT_ROBOT
        self._attr_unique_id = f"{entry.unique_id}_vacuum"
        self._attr_name = entry.title
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.unique_id)},
            "name": entry.title,
            "manufacturer": "iRobot",
        }

    def _handle_coordinator_update(self):
        """Update all attributes."""
        data = self.coordinator.data or {}
        status = data.get("cleanMissionStatus", {})
        cycle = status.get("cycle")
        not_ready = status.get("notReady")

        self._attr_activity = VacuumActivity.IDLE
        if cycle == "none" and not_ready == 39:
            self._attr_activity = VacuumActivity.IDLE
        if not_ready and not_ready > 0:
            self._attr_activity = VacuumActivity.ERROR
        if cycle in ["clean", "quick", "spot", "train"]:
            self._attr_activity = VacuumActivity.CLEANING
        if cycle in ["evac", "dock"]:
            self._attr_activity = VacuumActivity.DOCKED

        self._attr_available = data != {}
        self._attr_battery_level = data.get("batPct", 0)
        self._attr_extra_state_attributes = createExtendedAttributes(self)
        self._attr_device_info = {
            "identifiers": self._attr_device_info.get("identifiers"),
            "name": self._attr_device_info.get("name"),
            "manufacturer": self._attr_device_info.get("manufacturer"),
            "model": f"Roomba {data.get('sku')}",
            "sw_version": data.get("softwareVer"),
        }
        self._async_write_ha_state()

    async def async_clean_spot(self, **kwargs):
        """Spot clean."""

    async def async_start(self):
        """Start cleaning floors, check if any are selected or just clean everything."""
        payload = []

        for entity in self.hass.states.async_all("switch"):
            if entity.entity_id.startswith("switch.clean_") and entity.state == "on":
                switch_obj = self.hass.data[DOMAIN].get(entity.entity_id)
                if switch_obj:
                    payload.append(switch_obj.get_region_json())

        if payload:
            # TODO: FIX THIS FIX THIS IT NEEDS TO BE DYNAMIC NOT THIS GARBAGE
            # TODO: FIX THIS FIX THIS IT NEEDS TO BE DYNAMIC NOT THIS GARBAGE
            # TODO: FIX THIS FIX THIS IT NEEDS TO BE DYNAMIC NOT THIS GARBAGE
            await self.hass.services.async_call(
                DOMAIN,
                "vacuum_clean",
                service_data={
                    "payload": json.dumps(
                        {
                            "ordered": 1,
                            "pmap_id": "BGQxV6zGTmCsalWFHr-S5g",
                            "regions": payload,
                        }
                    )
                },
                blocking=True,
            )
        else:
            _LOGGER.warning("No rooms selected for cleaning")

    async def async_return_to_base(self):
        """Calls the Roomba back to its dock."""
        await self.hass.services.async_call(
            DOMAIN, "vacuum_action", service_data={"command": "dock"}, blocking=True
        )
