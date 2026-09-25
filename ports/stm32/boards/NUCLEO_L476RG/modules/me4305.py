# ME 4305 firmware identification and build provenance.
#
# The firmware build generates _build_info.py from the exact checked-out
# sources. This module remains importable from a source checkout, but it does
# not substitute provisional values when build provenance is unavailable.
#
# Copyright (c) 2026 Charlie Refvem
# SPDX-License-Identifier: GPL-3.0-only

FIRMWARE_NAME = "ME 4305 Firmware"

try:
    from _build_info import (
        CUSTOM_REPOSITORY_SHA,
        FROZEN_MODULES,
        MICROPYTHON_SHA,
        ULAB_SHA,
    )
except ImportError:
    CUSTOM_REPOSITORY_SHA = None
    MICROPYTHON_SHA = None
    ULAB_SHA = None
    FROZEN_MODULES = ()


def info():
    """Print firmware identity and exact provenance when it is embedded."""
    import sys

    print(FIRMWARE_NAME)
    if CUSTOM_REPOSITORY_SHA is None:
        print("Build provenance: unavailable outside a firmware build")
    else:
        print("Source commit:", CUSTOM_REPOSITORY_SHA)
        print("MicroPython commit:", MICROPYTHON_SHA)
        print("ulab commit:", ULAB_SHA)
        print("Frozen modules:", ", ".join(FROZEN_MODULES))
    print(sys.implementation)
