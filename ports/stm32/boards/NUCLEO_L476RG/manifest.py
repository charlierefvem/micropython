import os

include("$(PORT_DIR)/boards/manifest.py")

_frozen_opt_level = int(os.environ.get("MICROPY_FROZEN_OPT_LEVEL", "0"))
if _frozen_opt_level < 0 or _frozen_opt_level > 3:
    raise ValueError("MICROPY_FROZEN_OPT_LEVEL must be 0, 1, 2, or 3")

freeze("$(BOARD_DIR)/modules", opt=_frozen_opt_level)
