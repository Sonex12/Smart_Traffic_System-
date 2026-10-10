"""
traffic_lights.py  --  STAGE 1.  No camera needed.

Run this on day one, the moment your 12 LEDs are wired up.
It runs a normal fixed-time traffic light cycle.

    python3 traffic_lights.py

This same file also gives the rest of the project its Lights class,
so getting this working is real progress, not a throwaway test.
"""

import time
from config import PINS, ORDER, YELLOW, ALL_RED, FIXED_GREEN

try:
    from gpiozero import LED
    ON_PI = True
except ImportError:
    ON_PI = False
    print("gpiozero not found - running in PRINT-ONLY simulation mode.")


class FakeLED:
    """Stand-in for an LED so you can test the logic on a laptop."""
    def __init__(self, pin):
        self.pin = pin
        self.is_lit = False

    def on(self):
        self.is_lit = True

    def off(self):
        self.is_lit = False


class Lights:
    """Controls all 12 LEDs of the four-way junction."""

    def __init__(self):
        maker = LED if ON_PI else FakeLED
        self.leds = {}
        for direction, colours in PINS.items():
            self.leds[direction] = {
                colour: maker(pin) for colour, pin in colours.items()
            }
        self.all_red()

    def _set(self, direction, colour):
        """Light exactly one colour for one direction."""
        for c, led in self.leds[direction].items():
            led.on() if c == colour else led.off()

    def all_red(self):
        for direction in ORDER:
            self._set(direction, "red")

    def go(self, direction):
        """Green for one direction, red for the other three."""
        for d in ORDER:
            self._set(d, "green" if d == direction else "red")

    def caution(self, direction):
        for d in ORDER:
            self._set(d, "yellow" if d == direction else "red")

    def status(self):
        """Readable line like 'North=GREEN East=red ...' for the screen."""
        parts = []
        for d in ORDER:
            lit = [c for c, led in self.leds[d].items() if led.is_lit]
            parts.append(f"{d}={lit[0].upper() if lit else 'off'}")
        return "  ".join(parts)

    def off(self):
        for d in ORDER:
            for led in self.leds[d].values():
                led.off()


def fixed_cycle(lights, green_seconds=FIXED_GREEN):
    """One full round of the junction on a plain fixed timer."""
    for direction in ORDER:
        lights.go(direction)
        print(f"GREEN  {direction:6s} for {green_seconds}s   |  {lights.status()}")
        time.sleep(green_seconds)

        lights.caution(direction)
        print(f"YELLOW {direction:6s} for {YELLOW}s")
        time.sleep(YELLOW)

        lights.all_red()
        time.sleep(ALL_RED)


if __name__ == "__main__":
    lights = Lights()
    print("Fixed-timer traffic lights running. Press Ctrl+C to stop.\n")
    try:
        while True:
            fixed_cycle(lights)
    except KeyboardInterrupt:
        lights.off()
        print("\nStopped. All LEDs off.")
