"""The configuration flow for the robot."""

import asyncio

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .CloudApi import iRobotCloudApi
from .const import DOMAIN

SCHEMA = vol.Schema(
    {
        vol.Required("base_url"): str,
        vol.Required("cloud_api", default=True): bool,
        vol.Optional("irobot_username"): str,
        vol.Optional("irobot_password"): str,
    }
)


class RoombaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow."""

    async def async_step_user(self, user_input=None):
        """Show the user the input for the base url."""
        if user_input is not None:
            session = async_get_clientsession(self.hass)
            data = {}
            async with asyncio.timeout(10):
                try:
                    async with session.get(
                        f"{user_input['base_url']}/api/local/info/state"
                    ) as resp:
                        data = await resp.json() or {}
                        if data == {}:
                            return self.async_show_form(
                                step_id="user",
                                data_schema=SCHEMA,
                                errors=["cannot_connect"],
                            )
                    if user_input["cloud_api"]:
                        async with iRobotCloudApi(
                            user_input["irobot_username"], user_input["irobot_password"]
                        ) as api:
                            await api.authenticate()
                except Exception:
                    return self.async_show_form(
                        step_id="user",
                        data_schema=SCHEMA,
                        errors=["cannot_connect"],
                    )

            return self.async_create_entry(
                title=data.get("name", "Roomba"),
                data=user_input,
            )

        return self.async_show_form(step_id="user", data_schema=SCHEMA)

    async def async_step_options(self, user_input=None):
        """I dont know."""
        return self.async_create_entry(
            title="Room Switches Configured via UI",
            data=self.options,
            options=self.options,
        )
