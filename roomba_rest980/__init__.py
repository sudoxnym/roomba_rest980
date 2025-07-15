"""Roomba integration using an external Rest980 server."""

import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Setup Roombas with the Rest980 base url."""
    hass.data.setdefault(DOMAIN, {})
    url = entry.data["base_url"]
    session = async_get_clientsession(hass)  # Use HA’s shared session

    async def async_update_data():
        async with asyncio.timeout(10):
            async with session.get(f"{url}/api/local/info/state") as resp:
                return await resp.json()

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="Roomba REST Data",
        update_method=async_update_data,
        update_interval=DEFAULT_SCAN_INTERVAL,
    )
    hass.data[DOMAIN][entry.entry_id + "_coordinator"] = coordinator
    await coordinator.update_method()

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
