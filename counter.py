"""
counter.py  --  STAGE 2.  Counting toy cars with ONE overhead camera.

The camera looks straight down at your model junction. The picture is
divided into four rectangles ("regions of interest"), one per approach
road. Cars are counted separately inside each rectangle.

FIRST TIME ONLY - draw the four rectangles:

    python3 counter.py --setup

    Drag a box over the NORTH road, press ENTER.
    Repeat for EAST, SOUTH, WEST. Press ESC when all four are done.
    The boxes are saved to rois.json and reused from then on.

To check the counting is working:

    python3 counter.py

    A window shows the live count in each zone. Press Q to quit.
"""

import json
import sys
import time
import cv2
import numpy as np

from config import (CAMERA_INDEX, USE_PICAMERA, FRAME_W, FRAME_H,
                    SAT_MIN, VAL_MIN, MIN_AREA, ROI_FILE, ORDER,
                    FORCE_V4L2, USE_MJPG, FLUSH_FRAMES)


def probe_index(index):
    """
    Can we actually GET A PICTURE from this index?

    isOpened() alone is not enough - the Pi has many /dev/video devices
    that are video codecs, not cameras. They open happily and then give
    you nothing. Only a real frame proves it is a camera.
    """
    backend = cv2.CAP_V4L2 if FORCE_V4L2 else cv2.CAP_ANY
    cap = cv2.VideoCapture(index, backend)
    if not cap.isOpened():
        cap.release()
        return None
    ok, frame = cap.read()
    cap.release()
    if ok and frame is not None:
        return (frame.shape[1], frame.shape[0])
    return None


def find_camera(preferred=CAMERA_INDEX, limit=11):
    """Try the configured index first, then every other one."""
    order = [preferred] + [i for i in range(limit) if i != preferred]
    for i in order:
        size = probe_index(i)
        if size:
            return i, size
    return None, None


def scan_report():
    """python3 counter.py --scan  -> which indexes are real cameras."""
    print("Scanning camera indexes 0-10. This takes a few seconds.\n")
    working = []
    for i in range(11):
        size = probe_index(i)
        if size:
            print(f"  index {i:<3d} WORKS  - gives {size[0]}x{size[1]}")
            working.append(i)
        else:
            print(f"  index {i:<3d} nothing")
    print()
    if not working:
        print("No cameras found at all. Check:")
        print("  - lsusb                 is it still detected?")
        print("  - pkill -f counter.py   is an old run still holding it?")
        print("  - unplug, wait 5s, replug, then try again")
    else:
        print(f"Put this in config.py:   CAMERA_INDEX = {working[0]}")


class Camera:
    """Wraps either a USB webcam or the ribbon-cable Pi Camera."""

    def __init__(self):
        self.picam = None
        self.cap = None
        if USE_PICAMERA:
            from picamera2 import Picamera2
            self.picam = Picamera2()
            cfg = self.picam.create_preview_configuration(
                main={"size": (FRAME_W, FRAME_H), "format": "RGB888"})
            self.picam.configure(cfg)
            self.picam.start()
        else:
            # CAP_V4L2 matters: without it OpenCV on Raspberry Pi OS uses
            # GStreamer and hangs forever instead of opening the webcam.
            backend = cv2.CAP_V4L2 if FORCE_V4L2 else cv2.CAP_ANY
            self.index = CAMERA_INDEX
            self.cap = cv2.VideoCapture(self.index, backend)

            # A replugged webcam often comes back on a DIFFERENT index.
            # Rather than fail, go and look for it.
            if not self.cap.isOpened():
                self.cap.release()
                print(f"Camera index {CAMERA_INDEX} did not open - "
                      "searching other indexes...")
                found, size = find_camera()
                if found is None:
                    raise RuntimeError(
                        "No working camera found on any index 0-10.\n"
                        "  - is anything else still using it? try:\n"
                        "        pkill -f counter.py\n"
                        "        pkill -f smart_traffic.py\n"
                        "  - is it still listed?   lsusb\n"
                        "  - unplug it, wait 5 seconds, plug it back in\n"
                        "  - on an older Pi, try a different USB port")
                self.index = found
                print(f"Found a working camera at index {found} {size}.")
                print(f"Set CAMERA_INDEX = {found} in config.py "
                      "to skip this search next time.")
                self.cap = cv2.VideoCapture(self.index, backend)

            if USE_MJPG:
                self.cap.set(cv2.CAP_PROP_FOURCC,
                             cv2.VideoWriter_fourcc(*"MJPG"))
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_W)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_H)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            if not self.cap.isOpened():
                raise RuntimeError(
                    f"Camera at index {self.index} closed again unexpectedly.")

            # Some webcams hand back a black first frame while the sensor
            # wakes up. Read a few and discard them.
            for _ in range(5):
                self.cap.read()

        # NEVER trust the size you asked for. Many webcams have a fixed
        # aspect ratio and silently give you something else - this one
        # returns 640x360 when asked for 640x480. Measure what actually
        # arrives, because the detection zones depend on it.
        probe = self.frame()
        self.height, self.width = probe.shape[:2]
        if (self.width, self.height) != (FRAME_W, FRAME_H):
            print(f"Note: camera gives {self.width}x{self.height}, "
                  f"not the {FRAME_W}x{FRAME_H} requested. Using actual size.")

    def frame(self):
        """Grab one FRESH picture. Returns a BGR image."""
        if self.picam:
            rgb = self.picam.capture_array()
            return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

        # Dump the stale frames sitting in the driver's queue, so the
        # count reflects the junction NOW and not three seconds ago.
        for _ in range(max(0, FLUSH_FRAMES - 1)):
            self.cap.grab()
        ok, img = self.cap.read()
        if not ok:
            raise RuntimeError("Camera stopped sending pictures.")
        return img

    def close(self):
        if self.picam:
            self.picam.stop()
        if self.cap:
            self.cap.release()


def colour_mask(bgr):
    """
    Turn a colour picture into black and white, where WHITE means
    "this pixel is colourful enough to be a vehicle".

    How it works, in plain words:
      1. Convert to HSV. In HSV, 'S' means how COLOURFUL a pixel is.
         Black road = low S. White paint = low S. Red toy car = high S.
      2. Keep only the colourful pixels.
      3. Clean up specks with a morphological "open" and "close".

    Using saturation instead of brightness is the trick that makes this
    survive the exhibition hall's lighting being different from home.
    It is ALSO why white lane markings and pedestrian crossings are
    completely invisible to the detector - white has no saturation.
    """
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv,
                       np.array([0, SAT_MIN, VAL_MIN]),
                       np.array([179, 255, 255]))
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    return mask


def count_in_roi(frame, roi):
    """Count vehicle-sized coloured blobs inside one rectangle."""
    x, y, w, h = roi
    patch = frame[y:y + h, x:x + w]
    if patch.size == 0:
        return 0, None

    mask = colour_mask(patch)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL,
                                   cv2.CHAIN_APPROX_SIMPLE)
    cars = [c for c in contours if cv2.contourArea(c) > MIN_AREA]
    return len(cars), mask


class VehicleCounter:
    """Counts vehicles on all four approaches from a single frame."""

    def __init__(self, camera=None):
        self.camera = camera or Camera()
        self.rois = load_rois(self.camera.width, self.camera.height)

    def count_all(self):
        """Returns e.g. {'North': 6, 'East': 2, 'South': 0, 'West': 1}"""
        frame = self.camera.frame()
        return {d: count_in_roi(frame, self.rois[d])[0] for d in ORDER}, frame

    def count_one(self, direction):
        frame = self.camera.frame()
        return count_in_roi(frame, self.rois[direction])[0]

    def close(self):
        self.camera.close()


def load_rois(width=FRAME_W, height=FRAME_H):
    try:
        with open(ROI_FILE) as f:
            raw = json.load(f)
        return {d: tuple(raw[d]) for d in ORDER}
    except FileNotFoundError:
        print(f"No {ROI_FILE} found - using four rough zones. "
              "Run 'python3 counter.py --setup' to draw proper ones.")
        hw, hh = width // 2, height // 2
        return {"North": (hw // 2, 0, hw, hh),
                "East":  (hw, hh // 2, hw, hh),
                "South": (hw // 2, hh, hw, hh),
                "West":  (0, hh // 2, hw, hh)}


def setup_rois():
    """Interactive: drag a box for each direction, ENTER after each."""
    cam = Camera()
    print("\nPoint the camera at the junction with NO cars on it.")
    input("Press ENTER when ready...")
    frame = cam.frame()
    cam.close()

    rois = {}
    for d in ORDER:
        print(f"\nDrag a box over the {d.upper()} approach road, "
              "then press ENTER.")
        box = cv2.selectROI(f"Select {d} zone", frame, showCrosshair=True)
        cv2.destroyAllWindows()
        if box[2] == 0 or box[3] == 0:
            print("Empty box - try again.")
            return
        rois[d] = [int(v) for v in box]

    with open(ROI_FILE, "w") as f:
        json.dump(rois, f, indent=2)
    print(f"\nSaved four zones to {ROI_FILE}:")
    for d, r in rois.items():
        print(f"  {d:6s} x={r[0]} y={r[1]} w={r[2]} h={r[3]}")


def live_preview(show_mask=False):
    """
    Show the camera view with live counts drawn on top.

    With show_mask=True you also get the black-and-white view that the
    computer actually sees. This is the single most useful tool for
    building your model: anything WHITE in that view is being treated
    as a vehicle. If your grass, your trees or a reflection shows up
    white inside a zone, you have found your problem before it ruins
    the exhibition.
    """
    counter = VehicleCounter()
    colours = {"North": (255, 120, 0), "East": (0, 200, 255),
               "South": (0, 220, 120), "West": (200, 100, 255)}
    print("Live counting. Press Q in the window to quit.")
    if show_mask:
        print("Mask view ON - WHITE = counted as vehicle, BLACK = ignored.")
    try:
        while True:
            counts, frame = counter.count_all()
            for d in ORDER:
                x, y, w, h = counter.rois[d]
                cv2.rectangle(frame, (x, y), (x + w, y + h), colours[d], 2)
                cv2.putText(frame, f"{d}: {counts[d]}", (x + 5, y + 22),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, colours[d], 2)
            total = sum(counts.values())
            cv2.putText(frame, f"total {total}", (10, frame.shape[0] - 12),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            if show_mask:
                mask = cv2.cvtColor(colour_mask(frame), cv2.COLOR_GRAY2BGR)
                for d in ORDER:
                    x, y, w, h = counter.rois[d]
                    cv2.rectangle(mask, (x, y), (x + w, y + h), colours[d], 2)
                cv2.putText(mask, "WHAT THE COMPUTER SEES", (10, 24),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                view = np.vstack([frame, mask])
            else:
                view = frame

            cv2.imshow("Vehicle counting - press Q to quit", view)
            if cv2.waitKey(30) & 0xFF == ord("q"):
                break
    finally:
        counter.close()
        cv2.destroyAllWindows()


def tune_report():
    """
    python3 counter.py --tune

    Prints how colourful each zone actually is, once a second, so you can
    choose SAT_MIN by MEASURING instead of guessing.

    Method:
      1. Run it with an EMPTY board. Note the p95 numbers - that is your
         background (paper, floor, whatever).
      2. Put one car in one zone. Note that zone's p95 - that is a car.
      3. Set SAT_MIN in config.py roughly HALFWAY between the two.

    Write both numbers in your logbook. "I measured my background at 85
    and my vehicles at 190, so I set the threshold to 135" is a far
    better answer to a judge than "I tried numbers until it worked".
    """
    vc = VehicleCounter()
    print("\nSaturation readout - one line per second. Ctrl+C to stop.")
    print("p95 = how colourful the most colourful part of the zone is.\n")
    print(f"Current SAT_MIN is {SAT_MIN}. Anything above it counts.\n")
    try:
        while True:
            counts, frame = vc.count_all()
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            parts = []
            for d in ORDER:
                x, y, w, h = vc.rois[d]
                s = hsv[y:y + h, x:x + w, 1]
                if s.size == 0:
                    continue
                parts.append(f"{d[0]} p95={np.percentile(s, 95):5.1f} "
                             f"n={counts[d]}")
            print("   ".join(parts), flush=True)
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        vc.close()


if __name__ == "__main__":
    if "--scan" in sys.argv:
        scan_report()
    elif "--setup" in sys.argv:
        setup_rois()
    elif "--tune" in sys.argv:
        tune_report()
    else:
        live_preview(show_mask="--mask" in sys.argv)
