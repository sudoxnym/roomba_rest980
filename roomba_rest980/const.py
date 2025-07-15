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
}
errorMappings = {0: "n-a", 15: "Reboot Required", 18: "Docking Issue"}

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
}

jobInitiatorMappings = {
    "schedule": "iRobot Schedule",
    "rmtApp": "iRobot App",
    "manual": "Robot",
    "localApp": "HA",
    "none": "None",  # Added for RoombaJobInitiator
}
