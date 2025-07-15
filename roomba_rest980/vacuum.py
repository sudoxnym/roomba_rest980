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

from .const import (
    DOMAIN,
    binMappings,
    cleanBaseMappings,
    cycleMappings,
    errorMappings,
    jobInitiatorMappings,
    notReadyMappings,
    phaseMappings,
    yesNoMappings,
)

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
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.unique_id)},
            "name": entry.title,
            "manufacturer": "iRobot",
        }

    def _get_default(self, key: str, default: str):
        return self.coordinator.data.get(key) if self.coordinator.data else default

    @property
    def name(self):
        """Return its name."""
        return self.coordinator.data.get("name") if self.coordinator.data else "Roomba"

    @property
    def available(self):
        """Is vacuum available?"""
        return self.coordinator.data is not None

    @property
    def activity(self):
        """Return the state."""
        data = self.coordinator.data
        if not data:
            return None  # Return None so HA marks entity as unavailable

        status = data.get("cleanMissionStatus", {})
        cycle = status.get("cycle")
        not_ready = status.get("notReady")

        if cycle == "none" and not_ready == 39:
            return VacuumActivity.IDLE
        if not_ready and not_ready > 0:
            return VacuumActivity.ERROR
        if cycle in ["clean", "quick", "spot", "train"]:
            return VacuumActivity.CLEANING
        if cycle in ["evac", "dock"]:
            return VacuumActivity.DOCKED
        return VacuumActivity.IDLE

    @property
    def extra_state_attributes(self):
        """Return all the given attributes from rest980."""
        data = self.coordinator.data or {}
        status = data.get("cleanMissionStatus", {})
        # Mission State
        cycle = status.get("cycle")
        phase = status.get("phase")
        err = status.get("error")
        notReady = status.get("notReady")
        initiator = status.get("initiator")
        missionStartTime = status.get("mssnStrtTm")
        rechargeTime = status.get("rechrgTm")
        expireTime = status.get("expireTm")

        # Generic Data
        softwareVer = data.get("softwareVer")
        vacuumHigh = data.get("vacHigh")
        carpetBoost = data.get("carpetBoost")

        if vacuumHigh is not None:
            if not vacuumHigh and not carpetBoost:
                robotCarpetBoost = "Eco"
            elif vacuumHigh and not carpetBoost:
                robotCarpetBoost = "Performance"
            else:
                robotCarpetBoost = "Auto"
        else:
            robotCarpetBoost = "n-a"

        battery = data.get("batPct")
        if "+" in softwareVer:
            softwareVer = softwareVer.split("+")[1]

        if cycle == "none" and notReady == 39:
            extv = "Pending"
        elif notReady > 0:
            extv = f"Not Ready ({notReady})"
        else:
            extv = self.returnIn(cycleMappings, cycle)

        if phase == "charge" and battery == 100:
            rPhase = "Idle"
        elif cycle == "none" and phase == "stop":
            rPhase = "Stopped"
        else:
            rPhase = self.returnIn(phaseMappings, phase)

        if missionStartTime != 0:
            time = datetime.fromtimestamp(missionStartTime)
            elapsed = round((datetime.now().timestamp() - time.timestamp()) / 60)
            if elapsed > 60:
                jobTime = f"{elapsed // 60}h {f'{elapsed % 60:0>2d}'}m"
            else:
                jobTime = f"{elapsed}m"
        else:
            jobTime = "n-a"

        if rechargeTime != 0:
            time = datetime.fromtimestamp(rechargeTime)
            resume = round((datetime.now().timestamp() - time.timestamp()) / 60)
            if elapsed > 60:
                jobResumeTime = f"{resume // 60}h {f'{resume % 60:0>2d}'}m"
            else:
                jobResumeTime = f"{resume}m"
        else:
            jobResumeTime = "n-a"

        if expireTime != 0:
            time = datetime.fromtimestamp(expireTime)
            expire = round((datetime.now().timestamp() - time.timestamp()) / 60)
            if elapsed > 60:
                jobExpireTime = f"{expire // 60}h {f'{expire % 60:0>2d}'}m"
            else:
                jobExpireTime = f"{expire}m"
        else:
            jobExpireTime = "n-a"
        # Bin
        robotBin = data.get("bin")
        binFull = robotBin.get("full")
        binPresent = robotBin.get("present")

        # Dock
        dock = data.get("dock")
        dockState = dock.get("state")

        # Pose
        ## NOTE: My roomba's firmware does not support this anymore, so I'm blindly guessing based on the previous YAML integration details.
        pose = data.get("pose") or {}
        theta = pose.get("theta")
        point = pose.get("point") or {}
        pointX = point.get("x")
        pointY = point.get("y")
        if theta is not None:
            location = f"{pointX}, {pointY}, {theta}"
        else:
            location = "n-a"

        # Networking
        signal = data.get("signal")
        rssi = signal.get("rssi")

        # Runtime Statistics
        runtimeStats = data.get("runtimeStats")
        sqft = runtimeStats.get("sqft")
        hr = runtimeStats.get("hr")
        timeMin = runtimeStats.get("min")

        # Mission total(s?)
        bbmssn = data.get("bbmssn")
        numMissions = bbmssn.get("nMssn")
        # Run total(s?)
        bbrun = data.get("bbrun")
        numDirt = bbrun.get("nScrubs")
        numEvacs = bbrun.get("nEvacs")
        # numEvacs only for I7+/S9+ Models (Clean Base)

        pmaps = data.get("pmaps", [])
        pmap0id = next(iter(pmaps[0]), None) if pmaps else None

        noAutoPasses = data.get("noAutoPasses")
        twoPass = data.get("twoPass")
        if noAutoPasses is not None and twoPass is not None:
            if noAutoPasses is True and twoPass is False:
                robotCleanMode = "One"
            elif noAutoPasses is True and twoPass is True:
                robotCleanMode = "Two"
            else:
                robotCleanMode = "Auto"
        else:
            robotCleanMode = "n-a"

        return [
            ("extendedStatus", extv),
            ("notready_msg", self.returnIn(notReadyMappings, notReady)),
            ("error_msg", self.returnIn(errorMappings, err)),
            ("battery", battery),
            ("software_ver", softwareVer),
            ("phase", rPhase),
            ("bin", self.returnIn(binMappings, binFull)),
            ("bin_present", self.returnIn(yesNoMappings, binPresent)),
            ("clean_base", self.returnIn(cleanBaseMappings, dockState)),
            ("location", location),
            ("rssi", rssi),
            ("total_area", f"{round(sqft / 10.764 * 100)}m²"),
            ("total_time", f"{hr}h {timeMin}m"),
            ("total_jobs", numMissions),
            ("dirt_events", numDirt),
            ("evac_events", numEvacs),
            ("job_initiator", self.returnIn(jobInitiatorMappings, initiator)),
            ("job_time", jobTime),
            ("job_recharge", jobResumeTime),
            ("job_expire", jobExpireTime),
            ("clean_mode", robotCleanMode),
            ("carpet_boost", robotCarpetBoost),
            ("clean_edges", "true" if not data.get("openOnly", False) else "false"),
            ("maint_due", False),
            ("pmap0_id", pmap0id),
        ]

    def returnIn(self, map: map, index: any):
        """Default or map value."""
        if index in map:
            return map[index]
        return index

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
