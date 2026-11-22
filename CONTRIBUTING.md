# Contributing & Maintaining OpenSimWheel Linux Bridge

Thank you for your interest in **OpenSimWheel Linux Bridge**!

This project was created to solve a real gap in the Linux simracing ecosystem: bridging Windows Shared Memory and native process telemetry from Steam Proton games directly to **F1-UDP compatible steering wheels and displays** (such as Thrustmaster SF1000, custom ESP32/VoCore DDUs, and mobile/tablet dashboard apps) as well as the built-in **Web Live Dash**, without SimHub or Wine overhead.

## Looking for Co-Maintainers
The creator is actively looking for experienced Python / Linux developers who would like to adopt, co-maintain, or expand this repository. If you want to take ownership of new features or long-term maintenance, feel free to open an Issue or Pull Request!

## Priority Areas for Improvement
1. **Protocol Refactoring (`f1_udp_protocol.py`):** Centralize the F1 2020/2023 binary UDP packet builders (currently distributed across `OpenSimWheel_Linux_Bridge.py`, `lmu_bridge.py`, `rf2_bridge.py`, `acc_bridge.py`, `ac_ace_bridge.py`, and `rrre_bridge.py`) into a single shared output module.
2. **Native Memory Scanner Refinements (`rf2_bridge.py` / `lmu_bridge.py`):** Further optimize the DLL-free Linux `process_vm_readv` memory scanner + REST API (`5397`/`6397`) for faster lock-on across game updates and track/car switches.
3. **Extended Telemetry & New Simulators:** Add Brake Temperatures, live sector deltas, ERS/battery deployment, and support for additional titles (such as Automobilista 2, EA SPORTS WRC, or iRacing).
4. **Additional Hardware & Protocol Adapters:** Add native output adapters for Nextion serial/USB displays, LED strips, or Moza/Simagic/Fanatec USB HID telemetry protocols.

## Coding Guidelines
- Keep simulator modules isolated so changes to one game do not affect others.
- Minimize external dependencies (rely on Python 3 standard library `mmap`, `struct`, `socket`, `http.server`, `configparser`, and optional `numpy`) for zero-friction installation across all Linux distributions.
- Test bash scripts with `bash -n` and Python files with `python3 -m py_compile` before submitting.


