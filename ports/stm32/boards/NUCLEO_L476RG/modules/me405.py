# me405_firmware.py

FIRMWARE_NAME = "ME405 Firmware"
FIRMWARE_VERSION = "2026.1"

MICROPYTHON_BASE = "1.29-dev"

MODULES = (
    "ulab",
    "cotask",
    "task_share",
)

BUILD_DATE = "2026-06-15"

def info():
    import sys

    print(FIRMWARE_NAME)
    print("Version:", FIRMWARE_VERSION)
    # print(sys.version)
    print(sys.implementation)
    # print(sys.implementation.version)