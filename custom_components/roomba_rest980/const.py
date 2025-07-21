"""Constants for the Roomba (Rest980) integration."""

from datetime import timedelta

DOMAIN = "roomba_rest980"
DEFAULT_SCAN_INTERVAL = timedelta(seconds=10)  # or whatever interval you want

notReadyMappings = {
    0: "n-a",
    2: "Uneven Ground",
    15: "Low Battery",
    39: "Pending",
    48: "Path Blocked",
    68: "Updating Map",
}

errorMappings = {
    0: "n-a",
    15: "Reboot Required",
    18: "Docking Issue",
    68: "Updating Map",
}

cycleMappings = {
    "clean": "Clean",
    "quick": "Clean (Quick)",
    "spot": "Spot",
    "evac": "Emptying",
    "dock": "Docking",
    "train": "Training",
    "none": "Ready",
}

phaseMappings = {
    "charge": "Charge",
    "run": "Run",
    "evac": "Empty",
    "stop": "Paused",
    "stuck": "Stuck",
    "hmUsrDock": "Sent Home",
    "hmMidMsn": "Mid Dock",
    "hmPostMsn": "Final Dock",
    "idle": "Idle",  # Added for RoombaPhase
    "stopped": "Stopped",  # Added for RoombaPhase
}

binMappings = {True: "Full", False: "Not Full"}

yesNoMappings = {True: "Yes", False: "No"}

cleanBaseMappings = {
    300: "Ready",
    301: "Ready",
    302: "Empty",
    303: "Empty",
    350: "Bag Missing",
    351: "Clogged",
    352: "Sealing Problem",
    353: "Bag Full",
    360: "Comms Problem",
    364: "Bin Full Sensors Not Cleared",
}

jobInitiatorMappings = {
    "schedule": "iRobot Schedule",
    "rmtApp": "iRobot App",
    "manual": "Robot",
    "localApp": "HA",
    "none": "None",  # Added for RoombaJobInitiator
}

regionTypeMappings = {
    "default": "mdi:map-marker",
    "custom": "mdi:face-agent",
    "basement": "mdi:home-floor-b",
    "bathroom": "mdi:shower",
    "bedroom": "mdi:bed-king",
    "breakfast_room": "mdi:silverware-fork-knief",
    "closet": "mdi:hanger",
    "den": "mdi:sofa-single",
    "dining_room": "mdi:silverware-fork-knife",
    "entryway": "mdi:door-open",
    "family_room": "mdi:sofa-single",
    "foyer": "mdi:door-open",
    "garage": "mdi:garage",
    "guest_bathroom": "mdi:shower",
    "guest_bedroom": "mdi:bed-king",
    "hallway": "mdi:shoe-print",
    "kitchen": "mdi:fridge",
    "kids_room": "mdi:teddy-bear",
    "laundry_room": "mdi:washing-machine",
    "living_room": "mdi:sofa",
    "lounge": "mdi:sofa",
    "media_room": "mdi:television",
    "mud_room": "mdi:landslide",
    "office": "mdi:chair-rolling",
    "outside": "mdi:asterisk",
    "pantry": "mdi:archive",
    "playroom": "mdi:teddy-bear",
    "primary_bathroom": "mdi:shower",
    "primary_bedroom": "mdi:bed-king",
    "recreation_room": "mdi:sofa",
    "storage_room": "mdi:archive",
    "study": "mdi:bookshelf",
    "sun_room": "mdi:sun-angle",
    "unfinished_basement": "mdi:home-floor-b",
    "workshop": "mdi:toolbox",
}
