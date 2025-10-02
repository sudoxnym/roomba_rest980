"""The vacuum."""

import logging

from homeassistant.components.vacuum import (
    StateVacuumEntity,
    VacuumActivity,
    VacuumEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
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
    | VacuumEntityFeature.STOP
    | VacuumEntityFeature.PAUSE
)

# Enhanced status mapping for i3 model support
I3_STATUS_MAPPING = {
    # Idle/Ready states
    0: VacuumActivity.IDLE,     # Ready
    1: VacuumActivity.IDLE,     # Idle
    2: VacuumActivity.IDLE,     # Run

    # Cleaning states
    3: VacuumActivity.CLEANING,  # Clean
    4: VacuumActivity.CLEANING,  # Spot cleaning
    5: VacuumActivity.CLEANING,  # Edge cleaning

    # Docking/Charging states
    6: VacuumActivity.RETURNING, # Seeking dock
    7: VacuumActivity.DOCKED,    # Charging
    8: VacuumActivity.DOCKED,    # Docked

    # Error states
    9: VacuumActivity.ERROR,     # Error
    10: VacuumActivity.ERROR,    # Stuck
    11: VacuumActivity.ERROR,    # Picked up

    # Additional i3 specific states
    12: VacuumActivity.IDLE,     # Stopped
    13: VacuumActivity.PAUSED,   # Paused
    14: VacuumActivity.CLEANING, # Training
    15: VacuumActivity.CLEANING, # Mapping
    16: VacuumActivity.IDLE,     # Manual
    17: VacuumActivity.RETURNING,# Recharging
    18: VacuumActivity.DOCKED,   # Evacuating
    19: VacuumActivity.CLEANING, # Smart cleaning
    20: VacuumActivity.CLEANING, # Room cleaning
}

# Phase to activity mapping for better status detection
PHASE_MAPPING = {
    "run": VacuumActivity.CLEANING,
    "stop": VacuumActivity.IDLE,
    "pause": VacuumActivity.PAUSED,
    "charge": VacuumActivity.DOCKED,
    "stuck": VacuumActivity.ERROR,
    "hmUsrDock": VacuumActivity.RETURNING,
    "hmPostMsn": VacuumActivity.RETURNING,
    "hwMidMsn": VacuumActivity.CLEANING,
    "evac": VacuumActivity.DOCKED,
    "dock": VacuumActivity.DOCKED,
    "charging": VacuumActivity.DOCKED,
    "train": VacuumActivity.CLEANING,
    "spot": VacuumActivity.CLEANING,
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
):
    """Create the vacuum."""
    async_add_entities(
        [RoombaVacuum(hass, entry.runtime_data.local_coordinator, entry)]
    )


class RoombaVacuum(CoordinatorEntity, StateVacuumEntity):
    """The Rest980 controlled vacuum with enhanced i3 support."""

    def __init__(self, hass: HomeAssistant, coordinator, entry: ConfigEntry) -> None:
        """Setup the robot."""
        super().__init__(coordinator)
        self.hass = hass
        self._entry: ConfigEntry = entry
        self._attr_supported_features = SUPPORT_ROBOT
        self._attr_unique_id = f"{entry.unique_id}_vacuum"
        self._attr_name = entry.title

    def _handle_coordinator_update(self):
        """Update all attributes with enhanced i3 status handling."""
        data = self.coordinator.data or {}
        status = data.get("cleanMissionStatus", {})

        # Get all relevant status fields
        cycle = status.get("cycle")
        phase = status.get("phase")
        not_ready = status.get("notReady", 0)
        mission_state = status.get("mssnStrtTm")  # Mission start time
        error_code = status.get("error", 0)

        # Get robot model info for model-specific handling
        robot_name = data.get("name", "").lower()
        is_i3_model = "i3" in robot_name or data.get("sku", "").startswith("R3")

        # Default to IDLE
        self._attr_activity = VacuumActivity.IDLE

        # Enhanced status determination logic
        try:
            # Check for error conditions first
            if error_code > 0 or not_ready > 0:
                self._attr_activity = VacuumActivity.ERROR
                _LOGGER.debug(f"Vacuum in error state: error={error_code}, not_ready={not_ready}")

            # Check phase mapping first (most reliable for i3)
            elif phase and phase in PHASE_MAPPING:
                self._attr_activity = PHASE_MAPPING[phase]
                _LOGGER.debug(f"Status from phase mapping: phase={phase}, activity={self._attr_activity}")

            # Check cycle-based status
            elif cycle:
                if cycle == "none":
                    if not_ready == 39:
                        self._attr_activity = VacuumActivity.IDLE
                    else:
                        self._attr_activity = VacuumActivity.IDLE
                elif cycle in ["clean", "quick", "spot", "train"]:
                    self._attr_activity = VacuumActivity.CLEANING
                elif cycle in ["evac", "dock"]:
                    self._attr_activity = VacuumActivity.DOCKED
                else:
                    _LOGGER.debug(f"Unknown cycle: {cycle}")

            # For i3 models, check additional status fields
            if is_i3_model:
                # i3 models might have different status reporting
                battery_percent = data.get("batPct", 100)
                if battery_percent < 20 and phase in ["charge", "charging"]:
                    self._attr_activity = VacuumActivity.DOCKED

                # Check if mission is active
                if mission_state and cycle in ["clean", "spot", "quick"]:
                    self._attr_activity = VacuumActivity.CLEANING

            # Final fallback - if we still don't have a proper state
            if self._attr_activity == VacuumActivity.IDLE and cycle and cycle != "none":
                _LOGGER.warning(f"Unknown status combination: cycle={cycle}, phase={phase}, not_ready={not_ready}")
                # Log for debugging to help identify new status combinations
                _LOGGER.warning(f"Full status data: {status}")

        except Exception as e:
            _LOGGER.error(f"Error determining vacuum activity: {e}")
            self._attr_activity = VacuumActivity.IDLE

        self._attr_available = data != {}
        self._attr_extra_state_attributes = createExtendedAttributes(self)
        self._async_write_ha_state()

    @property
    def device_info(self) -> DeviceInfo:
        """Return the Roomba's device information."""
        data = self.coordinator.data or {}
        model = data.get("sku", "Roomba")

        # Enhanced model detection for i3
        if model.startswith("R3") or "i3" in data.get("name", "").lower():
            model = "Roomba i3"
        elif model.startswith("R7"):
            model = "Roomba i7"
        elif model.startswith("R9"):
            model = "Roomba s9"

        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.unique_id)},
            name=data.get("name", "Roomba"),
            manufacturer="iRobot",
            model=model,
            model_id=data.get("sku"),
            sw_version=data.get("softwareVer"),
        )

    async def async_clean_spot(self, **kwargs):
        """Spot clean."""

    async def async_start(self):
        """Start cleaning floors, check if any are selected or just clean everything."""
        data = self.coordinator.data or {}
        if data.get("phase") == "stop":
            await self.hass.services.async_call(
                DOMAIN,
                "rest980_action",
                service_data={
                    "action": "resume",
                    "base_url": self._entry.data["base_url"],
                },
                blocking=True,
            )
            return

        try:
            # Get selected rooms from switches (if available)
            payload = []
            regions = []

            # Check if we have room selection switches available
            domain_data = self._entry.runtime_data.switched_rooms
            selected_rooms = []

            # Find all room switches that are turned on
            for key, entity in domain_data.items():
                if (
                    key.startswith("switch.")
                    and hasattr(entity, "is_on")
                    and entity.is_on
                ):
                    selected_rooms.append(entity)

            # If we have specific rooms selected, use targeted cleaning
            if selected_rooms:
                # Build regions list from selected rooms
                regions = [
                    room.get_region_json()
                    for room in selected_rooms
                    if hasattr(room, "get_region_json")
                ]

            # If we have specific regions selected, use targeted cleaning
            if regions:
                payload = {
                    "ordered": 1,
                    "pmap_id": self._attr_extra_state_attributes.get("pmap0_id", ""),
                    "regions": regions,
                }

                await self.hass.services.async_call(
                    DOMAIN,
                    "rest980_clean",
                    service_data={
                        "payload": payload,
                        "base_url": self._entry.data["base_url"],
                    },
                    blocking=True,
                )
            else:
                # No specific rooms selected, start general clean
                _LOGGER.info("Starting general cleaning (no specific rooms selected)")
                await self.hass.services.async_call(
                    DOMAIN,
                    "rest980_clean",
                    service_data={
                        "payload": {"action": "start"},
                        "base_url": self._entry.data["base_url"],
                    },
                    blocking=True,
                )
        except (KeyError, AttributeError, ValueError, Exception) as e:
            _LOGGER.error("Failed to start cleaning due to configuration error: %s", e)

    async def async_stop(self) -> None:
        """Stop the action."""
        await self.hass.services.async_call(
            DOMAIN,
            "rest980_action",
            service_data={
                "action": "stop",
                "base_url": self._entry.data["base_url"],
            },
            blocking=True,
        )

    async def async_pause(self):
        """Pause the current action."""
        await self.hass.services.async_call(
            DOMAIN,
            "rest980_action",
            service_data={
                "action": "pause",
                "base_url": self._entry.data["base_url"],
            },
            blocking=True,
        )

    async def async_return_to_base(self):
        """Calls the Roomba back to its dock."""
        await self.hass.services.async_call(
            DOMAIN,
            "rest980_action",
            service_data={
                "action": "dock",
                "base_url": self._entry.data["base_url"],
            },
            blocking=True,
        )