"""Roomba integration using an external Rest980 server."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from .const import DOMAIN
from .coordinator import RoombaDataCoordinator, RoombaCloudCoordinator

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Setup Roombas with the Rest980 base url."""
    coordinator = RoombaDataCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id + "_coordinator"] = coordinator
    hass.data[DOMAIN][entry.entry_id + "_blid"] = "unknown"
    if entry.data["cloud_api"]:
        cc = RoombaCloudCoordinator(hass, entry)
        await cc.async_config_entry_first_refresh()
        hass.data[DOMAIN][entry.entry_id + "_cloud"] = cc
        if "blid" not in entry.data:
            for blid, robo in cc.data.items():
                try:
                    ifo = robo["robot_info"] or {}
                    ifosku = ifo.get("sku")
                    ifoswv = ifo.get("softwareVer")
                    ifoname = ifo.get("name")
                    thisname = coordinator.data.get("name", "Roomba")
                    thisswv = coordinator.data.get("softwareVer")
                    thissku = coordinator.data.get("sku")
                    if ifosku == thissku and ifoswv == thisswv and ifoname == thisname:
                        hass.data[DOMAIN][entry.entry_id + "_blid"] = blid
                except Exception as e:
                    _LOGGER.debug(e)
    else:
        hass.data[DOMAIN][entry.entry_id + "_cloud"] = {}
    # Forward platforms; create tasks but await to ensure no failure?
    await hass.config_entries.async_forward_entry_setups(
        entry, ["vacuum", "sensor", "switch"]
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Safely remove Roombas."""
    await hass.config_entries.async_unload_platforms(
        entry, ["vacuum", "sensor", "switch"]
    )
    hass.data[DOMAIN].pop(entry.entry_id + "_coordinator")
    return True
