# Generated register interface API contract

`registerinterface.py` is a build product for the ME 4305 firmware. It gives
MicroPython code a typed, shared byte buffer for the register map used by the
left- and right-motor systems. The generated file is frozen into firmware, but
is intentionally ignored by Git and is not a durable documentation source.

The source of truth for a particular interface is the pinned combination of:

- `register_definitions.json`, which defines the register hierarchy, types,
  ranges, units, aliases, scaling, display metadata, plots, and memory-layout
  policy;
- `register_map_generator.py`, which defines layout and Python-name generation;
  and
- this API contract, which defines which generated names and behaviors are
  public and stable.

The generator also emits one `register_metadata_<schema-hash>.json` file. That
file is the machine-readable API manifest for the generated module. It includes
the full definition and generator hashes, generated-module hash, public module
objects and array views, Python paths, byte offsets and sizes, access modes,
declared ranges, units, scaling, and display metadata. Downstream documentation
should consume that manifest and pin the three tracked sources above. It should
not scrape an untracked `registerinterface.py` file.

## Stable public API

The generated module currently defines no public Python classes. The public API
consists of these attributes, function, and module objects:

| Name | Kind | Contract |
| --- | --- | --- |
| `schema_hash` | `int` | First 64 bits of the SHA-256 hash of `register_definitions.json`. |
| `REG_MAP_ALLOC_SIZE` | `micropython.const` integer | Allocated byte count for the complete register map. |
| `buf` | `bytearray` | Shared backing storage for every struct and array view. |
| `hexdump()` | function | Prints `buf` in byte order, with four bytes per line. |
| `lm`, `rm` | `uctypes.struct` objects | Read/write views for `LeftMotor.Registers` and `RightMotor.Registers`. |
| `lm_K`, `rm_K` | `ulab.numpy.ndarray` views | Read/write views of each motor's gain registers. |
| `lm_z`, `rm_z` | `ulab.numpy.ndarray` views | Read/write controller-signal views. |
| `lm_w`, `rm_w` | `ulab.numpy.ndarray` views | Read/write observer-signal views. |
| `lm_y_h`, `rm_y_h` | `ulab.numpy.ndarray` views | Read/write output-estimate views. |
| `lm_x_h`, `rm_x_h` | `ulab.numpy.ndarray` views | Read/write state-estimate views. |

All these objects share `buf`; writing through one view is immediately visible
through every overlapping view. The generated module imports `micropython`,
`uctypes`, and `ulab`, so it is intended to be imported by the target firmware,
not ordinary CPython.

### Names from JSON

A system object's name is the lowercase sequence of uppercase letters in its
PascalCase JSON name: `LeftMotor` becomes `lm` and `RightMotor` becomes `rm`.
Names below `Registers` retain their spelling and nesting, so the JSON path
`LeftMotor.Registers.Parameters.Gains.Kp` is exposed as
`lm.Parameters.Gains.Kp`.

A group with an `alias` also produces a one-dimensional array view named
`<system>_<alias>`. For example, the `K` alias on
`LeftMotor.Registers.Parameters.Gains` produces `lm_K`. Array order follows the
definition order in the JSON. The generated API manifest records every exact
object name, path, data type, and shape so documentation generators do not need
to duplicate this naming algorithm.

Names beginning with `_`, including generated `uctypes` descriptor dictionaries
and `_array_view()`, are implementation details. Their names and structure may
change without an API-compatibility guarantee. Byte padding and descriptor
construction are also implementation details; the offsets and sizes recorded
in the generated API manifest are authoritative for a pinned build.

## Access, types, ranges, and exceptions

Every generated register field and alias array is a read/write view of the
shared buffer. The interface does not implement read-only fields, locking, or
range checking. A definition's `range` is a semantic/documentation constraint;
it is not enforced by the generated module.

The supported storage types are `INT8`, `INT16`, `INT32`, `INT64`, `UINT8`,
`UINT16`, `UINT32`, `UINT64`, `FLOAT32`, and `FLOAT64`, with their conventional
signed, unsigned, and IEEE-754 storage ranges. `size` and `offset` in the API
manifest describe the actual byte layout. `scale` and `scaledunits` describe a
presentation conversion and do not alter the value stored in `buf`.

The module defines no custom exception classes. A missing field raises the
normal `AttributeError`. Invalid assignments and invalid array operations are
reported by the target's `uctypes` or `ulab` implementation, and importing the
module without its MicroPython dependencies raises `ImportError`. Callers must
not rely on host-CPython coercion or exception details for invalid values.

Generator failures are intentionally explicit: malformed JSON raises a JSON
decode error, unsupported type names raise `KeyError`, invalid memory-layout
settings raise `ValueError`, and invalid or incomplete definitions may raise
the corresponding key/type error. A successful run writes both outputs.

## Generation and build provenance

From the repository root, generate the interface with:

```sh
cd tools
python3 register_map_generator.py
```

Inputs are `tools/register_definitions.json` and
`tools/register_map_generator.py`. Outputs are `tools/registerinterface.py` and
one `tools/register_metadata_<schema-hash>.json`. Run the command from `tools`
because those are the generator's default relative paths.

The firmware workflow copies `registerinterface.py` into the board's frozen
module directory temporarily. It then runs `tools/build_manifest.py`, which
creates `build_manifest.json` and the temporary frozen `_build_info.py`. The
uploaded firmware artifact contains the register API manifest and build
manifest. The build manifest ties the firmware to the exact custom-repository,
MicroPython, and ulab commits; hashes all three durable register API sources and
the generated module; lists the frozen custom modules; and records relevant
generation/build options. It deliberately contains no guessed version or build
date.

To verify that documentation and firmware came from the same build, compare the
API-manifest filename and SHA-256 plus the register input and generated-module
hashes in `build_manifest.json`.

## Attribution and license

The register definitions, generator, generated Python module, generated API
manifest, and this contract are Copyright (c) 2026 Charlie Refvem and are
licensed under the GNU General Public License, version 3.0 only. See the root
`LICENSE` file. MicroPython, ulab, and other third-party components retain their
own copyright notices and licenses.
