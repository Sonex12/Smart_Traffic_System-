"""
smart_traffic.py  --  STAGE 4.  The whole thing, running together.

    python3 smart_traffic.py             normal adaptive mode
    python3 smart_traffic.py --fixed     plain fixed timer (for comparison)
    python3 smart_traffic.py --nocam     adaptive logic, typed-in counts

WHAT IT DOES, ONE CYCLE AT A TIME:
    1. Take one photo from the overhead camera.
    2. Count the toy cars waiting in each of the four zones.
    3. Work out how long each green should be, and which roads get a
       turn at all - a road with no cars is skipped (SKIP_EMPTY).
    4. Run those roads, busiest first if PRIORITY_ORDER is on.
    5. While a light is green, keep watching that road - if it empties
       out early, cut to yellow instead of wasting everyone's time.

IF THE CAMERA FAILS it drops to a fixed timer automatically and says so
on screen. The junction keeps working. That is the single most
important feature on exhibition day.

A FIXED TIMER NEVER SKIPS AND NEVER REORDERS. That is the whole point
of the comparison, so --fixed always runs all four in N-E-S-W order.
"""

import sys
import time

from config import ORDER, YELLOW, ALL_RED, G_MIN, FIXED_GREEN
from traffic_lights import Lights
from timing import (compute_green_times, fixed_green_times, cycle_length,
                    total_waiting_time, improvement, phase_order)

CHECK_EVERY = 0.5      # how often to re-look at the green road, seconds
EMPTY_CHECKS_TO_CUT = 3  # consecutive empty looks before cutting short


class Controller:
    def __init__(self, use_camera=True, adaptive=True):
        self.lights = Lights()
        self.adaptive = adaptive
        self.counter = None
        self.camera_ok = False
        self.cycle_no = 0
        self.saved_total = 0.0
        self.fixed_total = 0.0

        if use_camera:
            try:
                from counter import VehicleCounter
                self.counter = VehicleCounter()
                self.camera_ok = True
            except Exception as e:
                print(f"\n!! Camera unavailable: {e}")
                print("!! Falling back to FIXED TIMER mode.\n")

    # -----------------------------------------------------------
    def read_counts(self):
        """Ask the camera how many cars are waiting on each road."""
        if not self.camera_ok:
            return {d: 0 for d in ORDER}
        try:
            counts, _frame = self.counter.count_all()
            return counts
        except Exception as e:
            print(f"!! Camera error mid-run: {e}  -> fixed timer from now on")
            self.camera_ok = False
            return {d: 0 for d in ORDER}

    def read_one(self, direction):
        if not self.camera_ok:
            return 999          # pretend it is busy: never cut short
        try:
            return self.counter.count_one(direction)
        except Exception:
            self.camera_ok = False
            return 999

    # -----------------------------------------------------------
    def run_cycle(self):
        self.cycle_no += 1
        counts = self.read_counts()

        if self.adaptive and self.camera_ok:
            greens = compute_green_times(counts)
            order = phase_order(counts)     # skips empties, busiest first
            mode = "ADAPTIVE"
        else:
            greens = fixed_green_times()
            order = list(ORDER)             # a fixed timer does neither
            mode = "FIXED TIMER" + ("" if self.camera_ok else "  (no camera)")

        self.print_header(mode, counts, greens, order)

        for direction in order:
            if greens[direction] <= 0:
                continue                    # empty road - no turn at all
            self.run_phase(direction, greens[direction])

        if self.camera_ok and self.adaptive:
            self.track_saving(counts, greens)

    def run_phase(self, direction, green_seconds):
        """Green, then yellow, then the all-red safety gap."""
        self.lights.go(direction)
        started = time.time()
        empty_looks = 0
        cut_short = False

        while True:
            elapsed = time.time() - started
            if elapsed >= green_seconds:
                break

            time.sleep(CHECK_EVERY)

            # Early cut-off: only allowed once the minimum green is done.
            if self.adaptive and self.camera_ok and elapsed >= G_MIN:
                if self.read_one(direction) == 0:
                    empty_looks += 1
                    if empty_looks >= EMPTY_CHECKS_TO_CUT:
                        cut_short = True
                        break
                else:
                    empty_looks = 0

        actual = time.time() - started
        note = "  <- road cleared, cut short" if cut_short else ""
        print(f"   GREEN  {direction:6s} {actual:5.1f}s "
              f"(planned {green_seconds:4.1f}s){note}")

        self.lights.caution(direction)
        time.sleep(YELLOW)
        self.lights.all_red()
        time.sleep(ALL_RED)

    # -----------------------------------------------------------
    def print_header(self, mode, counts, greens, order):
        print("\n" + "=" * 62)
        print(f" CYCLE {self.cycle_no}   mode: {mode}")
        print("=" * 62)
        bar = lambda n: "#" * min(n, 30)
        for d in ORDER:
            if greens[d] <= 0:
                print(f"   {d:6s} {counts[d]:3d} cars {'':<20s}"
                      f" ->   SKIPPED (empty)")
            else:
                print(f"   {d:6s} {counts[d]:3d} cars {bar(counts[d]):<20s}"
                      f" -> {greens[d]:5.1f}s green")
        print(f"   order this cycle: {' -> '.join(order)}")
        print(f"   full cycle: {cycle_length(greens):.0f}s")

    def track_saving(self, counts, greens):
        """Running total of waiting time saved - your headline number."""
        smart = total_waiting_time(counts, greens, phase_order(counts))
        dumb = total_waiting_time(counts, fixed_green_times(), list(ORDER))
        self.saved_total += smart
        self.fixed_total += dumb
        pct, _, _ = improvement(counts)
        print(f"   waiting time this cycle: {smart:6.0f} vehicle-seconds "
              f"vs {dumb:6.0f} fixed  ({pct:+.0f}%)")
        if self.fixed_total > 0:
            overall = (self.fixed_total - self.saved_total) / self.fixed_total * 100
            print(f"   SINCE START: {overall:+.1f}% less waiting than a "
                  f"fixed timer")

    def shutdown(self):
        self.lights.off()
        if self.counter:
            self.counter.close()


def manual_mode():
    """No camera yet? Type the counts in by hand and watch it work."""
    lights = Lights()
    print("Manual mode - type four numbers, e.g.  8 2 0 3   (Ctrl+C to stop)\n")
    try:
        while True:
            raw = input(f"cars on {', '.join(ORDER)}: ").split()
            if len(raw) != 4:
                print("  need exactly four numbers")
                continue
            counts = {d: int(v) for d, v in zip(ORDER, raw)}
            greens = compute_green_times(counts)
            order = phase_order(counts)
            pct, smart, dumb = improvement(counts)

            for d in ORDER:
                if greens[d] <= 0:
                    print(f"   {d:6s} {counts[d]:3d} cars ->   SKIPPED (empty)")
                else:
                    print(f"   {d:6s} {counts[d]:3d} cars -> {greens[d]:5.1f}s")
            print(f"   order: {' -> '.join(order)}")
            print(f"   cycle {cycle_length(greens):.0f}s, "
                  f"{pct:.0f}% less waiting than a fixed timer\n")

            for d in order:
                if greens[d] <= 0:
                    continue
                lights.go(d)
                time.sleep(greens[d])
                lights.caution(d)
                time.sleep(YELLOW)
                lights.all_red()
                time.sleep(ALL_RED)
    except KeyboardInterrupt:
        lights.off()
        print("\nStopped.")


if __name__ == "__main__":
    if "--nocam" in sys.argv:
        manual_mode()
        sys.exit()

    ctrl = Controller(use_camera=True, adaptive="--fixed" not in sys.argv)
    try:
        while True:
            ctrl.run_cycle()
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        ctrl.shutdown()
        print("All LEDs off. Goodbye.")
