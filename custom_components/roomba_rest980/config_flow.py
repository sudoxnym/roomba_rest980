"""The configuration flow for the robot."""

import voluptuous as vol

from homeassistant import config_entries

from .const import DOMAIN


class RoombaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow."""

    async def async_step_user(self, user_input=None):
        """Show the user the input for the base url."""
        if user_input is not None:
            return self.async_create_entry(title="Roomba", data=user_input, options={})

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required("base_url"): str}),
        )

    async def async_step_options(self, user_input=None):
        """I dont know."""
        return self.async_create_entry(
            title="Room Switches Configured via UI",
            data=self.options,
            options=self.options,
        )
