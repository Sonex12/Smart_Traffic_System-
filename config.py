"""
config.py  --  All the numbers you might want to change live here.
Change values here instead of hunting through the other files.
"""

# ---------------------------------------------------------------
# 1. WHICH GPIO PIN GOES TO WHICH LED   (BCM numbering)
# ---------------------------------------------------------------
# GPIO 2 and 3 are deliberately left free in case you add an
# I2C OLED display later.
PINS = {
    "North": {"red": 4,  "yellow": 17, "green": 27},
    "East":  {"red": 22, "yellow": 5,  "green": 6},
    "South": {"red": 13, "yellow": 19, "green": 26},
    "West":  {"red": 12, "yellow": 16, "green": 20},
}

# The order the lights take turns in. NEVER changes.
# This is what guarantees no direction is ignored forever.
ORDER = ["North", "East", "South", "West"]

# ---------------------------------------------------------------
# 2. TIMING RULES  (all in seconds)
# ---------------------------------------------------------------
G_MIN     = 5    # shortest green any direction can EVER get
G_MAX     = 25   # longest green any direction can EVER get
YELLOW    = 3    # fixed by law in real life, so fixed here too
ALL_RED   = 1    # safety gap: everyone red while the junction clears
# A full cycle may never take longer than this. It is set equal to the
# fixed-timer cycle it replaces (4 x FIXED_GREEN + lost time = 76s), so
# the smart system can never make anybody wait longer than the old one.
CYCLE_MAX = 76

# Seconds of extra green earned by each waiting vehicle.
# This is the single most important number in the project - tune it
# by testing, and be ready to explain why you chose the value you did.
SEC_PER_VEHICLE = 2.0

# How many vehicles can clear the junction per second of green.
# Used only by the waiting-time comparison, not by the lights.
# Measure this on your own model and put the real number here.
FLOW_RATE = 0.5

# Fixed-timer value, used for the "old system" comparison and as
# the emergency fallback if the camera fails.
FIXED_GREEN = 15

# ---------------------------------------------------------------
# 3. CAMERA + VEHICLE DETECTION
# ---------------------------------------------------------------
CAMERA_INDEX = 0        # 0 = first USB webcam. Ignored if USE_PICAMERA.
USE_PICAMERA = False    # True if using the ribbon-cable Pi Camera
FRAME_W = 640
FRAME_H = 360   # this webcam is 16:9. The code measures the real size
                # anyway, so a wrong guess here is harmless.

# On Raspberry Pi OS, OpenCV picks the GStreamer backend by default and
# then HANGS FOREVER on a USB webcam. Forcing V4L2 is the fix.
FORCE_V4L2 = True

# Most cheap USB webcams stream MJPG far more happily than raw video,
# especially on the older Pi's shared USB bus. Set False if yours fails.
USE_MJPG = True

# The webcam keeps a few old frames in a queue. Without throwing those
# away you count cars that were moved several seconds ago - which ruins
# the "remove the cars and watch the light change" demo.
FLUSH_FRAMES = 3

# A toy car is COLOURFUL, the road is GREY. Grey has low "saturation".
# So: anything with saturation above SAT_MIN is probably a car.
SAT_MIN = 80      # raise if the road is being detected as cars
VAL_MIN = 50      # ignore very dark shadows
MIN_AREA = 150    # a blob smaller than this many pixels is noise

ROI_FILE = "rois.json"   # where the 4 detection zones are saved
# ---------------------------------------------------------------
# 4. DEMO SWITCHES
# Set all three False to go back to the 21 September behaviour.
# ---------------------------------------------------------------
SHOW_CAMERA    = True
PRIORITY_ORDER = True
SKIP_EMPTY     = True
