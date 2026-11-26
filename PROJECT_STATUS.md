## Status and known limitations

This project is a working Linux bridge that sends live sim racing telemetry
to UDP wheel displays and to the built-in web dashboard. It was written by a
hobbyist with the help of AI, so the code may not be elegant, but it works.

### What works today
- Speed, gear, RPM and shift LEDs
- Fuel level
- Tyre wear
- Current lap time
- Tested with: Le Mans Ultimate (LMU) [add other tested games]
- Tested hardware: Thrustmaster T-GT II, SF1000 (firmware v9.15), T-LCM
- Operating system: CachyOS Linux

### What is missing
- **Lap delta**: not implemented yet.
- **Battery / ERS / KERS on the SF1000 display**: the values are present
  in the telemetry stream and I verified this, but I could not get them to
  appear on the wheel's display. The cause may be a limitation of the wheel's
  firmware rather than of this bridge, but I could not confirm it.
- ERS / battery on the web dashboard: [not done yet / to be added].

### Help wanted
I am not a professional programmer and I do not plan to develop this much
further. If you have the skills and the interest, contributions are very
welcome, especially for:
- implementing the lap delta;
- finding out whether the SF1000 can display the ERS bar at all;
- adding ERS / battery to the web dashboard;
- supporting other wheels and displays.

Feel free to open an issue or a pull request, or to fork the project.
