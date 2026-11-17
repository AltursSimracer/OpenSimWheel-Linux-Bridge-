# Contributing & Maintaining OpenSimWheel Linux Bridge

Thank you for your interest in **OpenSimWheel Linux Bridge**!

This project was created to solve a real gap in the Linux simracing ecosystem: bridging Windows Shared Memory from Steam Proton games directly to native UDP steering wheels (**Thrustmaster SF1000**) and web dashboards without SimHub or Wine overhead.

## Looking for Co-Maintainers
The creator is actively looking for experienced Python / Linux developers who would like to adopt, co-maintain, or expand this repository. If you want to take ownership of new features or long-term maintenance, feel free to open an Issue or Pull Request!

## Priority Areas for Improvement
1. **Protocol Refactoring (`sf1000_protocol.py`):** Centralize the Thrustmaster SF1000 binary packet builders (currently distributed across `lmu_bridge.py`, `acc_bridge.py`, `ac_ace_bridge.py`, and `rrre_bridge.py`) into a single shared module.
2. **rFactor 2 (`rF2`) Support:** Add full `rFactor2SharedMemoryMapPlugin64.dll` support (AppID `365960`) reusing the existing LMU native memory architecture.
3. **Extended Telemetry:** Add Brake Bias, TC/ABS levels, Brake Temperatures, and Race Flags to `DASH_STATE` and `livedash.html`.
4. **Additional Hardware Support:** Add output adapters for SimHub-compatible UDP displays, Nextion screens, or Moza/Simagic telemetry protocols.

## Coding Guidelines
- Keep simulator modules isolated so changes to one game do not affect others.
- Avoid external pip dependencies where possible; rely on Python 3 standard library (`mmap`, `struct`, `socket`, `http.server`, `configparser`) for zero-friction installation across all Linux distributions.
- Test bash scripts with `bash -n` and Python files with `python3 -m py_compile` before submitting.
