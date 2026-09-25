# ME 4305 MicroPython firmware

This repository contains the custom board configuration, frozen Python modules,
register-map generator, and build workflow for the ME 4305 STM32 firmware.

The generated `registerinterface.py` module is intentionally not tracked. Its
durable API sources and generation instructions are documented in
[`tools/README.md`](tools/README.md).

## License

Original work in this repository is licensed under the GNU General Public
License, version 3.0 only; see [`LICENSE`](LICENSE). Files derived from
MicroPython, ulab, or other third-party projects retain the copyright notices
and licenses stated in those files. In particular, the copied ulab
configuration and STM32 HAL configuration are MIT-licensed third-party files.
