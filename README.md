# Smart Adaptive Traffic Light 🚦

A Raspberry Pi traffic light that watches the road before deciding who goes.

One overhead webcam counts the toy cars waiting on each of the four roads at a model junction. The controller then skips roads with nobody waiting, lets the busiest road go first, and gives longer green to longer queues, while never making anyone wait longer than an ordinary fixed-time traffic light would.

Built as a Grade 9 school science exhibition project (September 2026).

<!-- Add a photo of the model junction here, for example:
![The model junction](docs/images/junction.jpg) -->

---

## The problem

A normal traffic light gives every road the same green time, whether that road is jammed or completely empty. Cars sit at red lights while the green goes to a road with no one on it.

This system measures the demand on each road first, then shares out the green time to match it.

---

## How it works

### 1. One camera, four zones

Instead of four cameras (a Raspberry Pi 4 has only one camera port), a single webcam looks straight down at the junction. The picture is divided into four rectangles, one per approach road, and cars are counted in each rectangle.

```
        camera looking down from ~50 cm
                    |
        +-----------|-----------+
        |     +-----------+     |
        |     |   NORTH   |     |
        |  +--+-----------+--+  |
        |  |  |///////////|  |  |
        |  |W |// JUNCTION|  |E |
        |  |  |///////////|  |  |
        |  +--+-----------+--+  |
        |     |   SOUTH   |     |
        |     +-----------+     |
        +-----------------------+
```

Same data as four cameras, a quarter of the cost, and one calibration instead of four.

### 2. Finding cars by colour

Each frame is converted from RGB to HSV colour space. The **S** (saturation) channel measures how colourful a pixel is:

- black road, white lane markings, grey board → low saturation
- red, blue, yellow and green toy cars → high saturation

Pixels above a saturation threshold are kept, small specks are cleaned up, and every blob large enough to be a car is counted. This runs instantly on a Pi, and because saturation changes much less than brightness when the lighting changes, it holds up better when the project moves from home to an exhibition hall.

### 3. The timing rules

| Rule | Why it exists |
|---|---|
| A road with no cars is skipped | Nobody waits for a green that no one is using |
| The busiest road goes first | Serving the longest queue first cuts total waiting time |
| At least 5 s green for any road with cars | A road with one car is never ignored |
| Plus 2 s for every waiting car | The adaptive part: demand becomes green time |
| Never more than 25 s green | One busy road can't hog the junction |
| Whole cycle never longer than 76 s | 76 s is exactly what the old fixed timer takes (4 roads × 15 s green + 3 s yellow + 1 s all-red), so the system can never be worse than the one it replaces |
| 3 s yellow + 1 s all-red between roads | Safety: the junction clears before the next road moves |
| No cars anywhere → normal 5 s cycle | The lights never freeze |

**Early cut-off:** if a road empties while its light is green, it changes to yellow early (never before the 5-second minimum). Take the cars away during a green and the light changes in front of you.

**No road waits forever:** every road with cars gets exactly one turn in every cycle, and the cycle is capped at 76 seconds. A road is only skipped when nobody is on it. `timing.py` checks this automatically.

Busiest-first ordering and empty-road skipping can both be switched off in `config.py`, which gives the classic fixed North → East → South → West order.

### 4. Fault tolerance

If the camera fails or is unplugged while the system is running, `smart_traffic.py` detects it, prints a warning, and carries on as a fixed-time traffic light (15 s each road). The lights never go dark.

---

## Results

Output of `python3 timing.py`:

```
Scenario                 North    East   South    West   cycle    saved
------------------------------------------------------------------------
Empty junction            5.0s    5.0s    5.0s    5.0s   36.0s     0.0%
Light, even              11.0s   11.0s   11.0s   11.0s   60.0s    19.0%
Balanced, moderate       15.0s   15.0s   15.0s   15.0s   76.0s     0.0%
Rush hour, one road      25.0s    7.0s    7.0s    7.0s   62.0s    33.7%
Everything on North      25.0s    0.0s    0.0s    0.0s   29.0s    63.8%
Two busy, two quiet      23.0s   21.0s    7.0s    0.0s   63.0s     9.1%
Gridlock everywhere      15.0s   15.0s   15.0s   15.0s   76.0s     4.0%
One car, one road         0.0s    0.0s    7.0s    0.0s   11.0s    97.4%
```

"saved" is the reduction in total waiting time (in vehicle-seconds) compared with a fixed 15-second timer, using the same model for both.

How to read it honestly:

- **Uneven traffic:** large savings. This is where the system helps.
- **Perfectly balanced traffic:** it matches the fixed timer, because there is nothing to rebalance.
- **Light traffic:** it saves time by running shorter cycles.
- **Gridlock:** only a small gain. No timing plan can fix a junction that is over capacity.
- **It is never worse than the fixed timer**, guaranteed by the 76-second cycle cap.

The waiting-time model is a simplification. If a green is too short to clear a queue, the leftover cars wait another full cycle. Because the same model is applied to both systems, the comparison between them is fair.

---

## Hardware

- Raspberry Pi 4 with Raspberry Pi OS
- USB webcam (720p is plenty)
- 12 LEDs (4 red, 4 yellow, 4 green) and 12 × 220 Ω resistors
- Breadboard and jumper wires
- About 60 × 60 cm of foam board or plywood, with black roads and white lane markings
- 15–20 brightly coloured toy cars (red, blue, yellow, green; avoid grey, silver, white and black, which the detector can't see)
- A camera mast holding the webcam about 50–60 cm above the centre, pointing straight down
- A small lamp clipped to the mast, so the lighting is the same wherever the project is set up
- Official Raspberry Pi power supply, or a 20,000 mAh USB-C power bank with a short, thick cable

## Wiring

Every LED: **GPIO pin → 220 Ω resistor → LED long leg (anode) → LED short leg (cathode) → GND**

BCM pin numbers:

| Direction | Red | Yellow | Green |
|---|---|---|---|
| North | GPIO 4 | GPIO 17 | GPIO 27 |
| East | GPIO 22 | GPIO 5 | GPIO 6 |
| South | GPIO 13 | GPIO 19 | GPIO 26 |
| West | GPIO 12 | GPIO 16 | GPIO 20 |

GPIO 2 and 3 are left free for an optional OLED display.

> **Current limit:** each LED draws about 6 mA at 220 Ω. The Pi's GPIO pins should stay under about 50 mA in total. Normal operation lights 4–5 LEDs (about 30 mA), which is safe. Lighting all 12 at once (about 72 mA) is not, so the code never does it.

---

## Software setup

On Raspberry Pi OS, install OpenCV with `apt`, not `pip` (the `pip` version can take hours to build on a Pi):

```bash
sudo apt update
sudo apt install -y python3-opencv python3-gpiozero python3-numpy git
git clone https://github.com/<your-username>/smart-traffic-light.git
cd smart-traffic-light
```

Check it worked:

```bash
python3 -c "import cv2, gpiozero; print('OpenCV', cv2.__version__, '- ready')"
```

If you use a virtual environment, create it with `python3 -m venv --system-site-packages env`, otherwise it can't see the apt-installed OpenCV.

## Files

| File | What it does |
|---|---|
| `config.py` | Every setting: pin numbers, timings, detection sensitivity. Change things here. |
| `traffic_lights.py` | Drives the 12 LEDs on a fixed-time cycle. No camera needed. |
| `counter.py` | Camera capture and car counting in the four zones. `--setup` draws the zones. |
| `timing.py` | Turns counts into green times and prints the results table. Runs on any computer, no camera or LEDs needed. |
| `smart_traffic.py` | The complete system: counting, timing and lights together. |
| `tools/checksat.py` | Diagnostic: saves test masks at several saturation thresholds to help choose `SAT_MIN`. |
| `tools/checkarea.py` | Diagnostic: prints the pixel size of each detected blob to help choose `MIN_AREA`. |

## Running it

```bash
# LEDs only, no camera
python3 traffic_lights.py

# Check the timing algorithm (any computer)
python3 timing.py

# Full system with counts typed in by hand (no camera)
python3 smart_traffic.py --nocam

# Draw the four zones (once, and again whenever the camera moves)
python3 counter.py --setup

# Check that counting is accurate
python3 counter.py

# The complete system
python3 smart_traffic.py

# Fixed-timer mode, for side-by-side comparison
python3 smart_traffic.py --fixed
```

Shut the Pi down properly before unplugging it, or the SD card can get corrupted:

```bash
sudo shutdown -h now
```

## Settings in `config.py`

| Setting | Starting value | Raise it when… |
|---|---|---|
| `SAT_MIN` | 90 | The road or background is being counted as cars |
| `MIN_AREA` | 300 | Small specks are being counted |
| `SEC_PER_VEHICLE` | 2.0 | You want the system to react more strongly to queues |
| `G_MIN` | 5 | Roads feel too rushed |
| `G_MAX` | 25 | One road should be allowed to dominate more |
| `CAMERA_INDEX` | 0 | The webcam isn't found (try 1, then 2) |
| `USE_PICAMERA` | False | Set to True for a ribbon-cable Pi camera |
| `PRIORITY_ORDER` | True | Set to False for a fixed N → E → S → W order |
| `SKIP_EMPTY` | True | Set to False to give empty roads their 5 s anyway |
| `FLOW_RATE` | — | Set to your measured value: cars cleared ÷ seconds on your model |

`SAT_MIN` and `MIN_AREA` need tuning for your own board and lighting. `tools/checksat.py` and `tools/checkarea.py` help with that. `config.py` is only read at startup, so restart the program after changing it.

---

## Running without mains power

The whole system runs on 5 V USB power, with no mains connection needed:

- Pi, webcam and LEDs on a 20,000 mAh power bank (roughly 8–10 hours, depending on the bank)
- A laptop on its own battery as the display, connected to the Pi over VNC
- A phone hotspot as the network, since there's no home Wi-Fi at the venue. Add the hotspot to the Pi's Wi-Fi at home first, then connect by hostname (`<hostname>.local`) or by the IP shown in the hotspot's device list.

Check for undervoltage with `vcgencmd get_throttled`. `throttled=0x0` means the power has been clean since boot. Anything else means the supply or cable is too weak, which causes freezes that look like software bugs.

More detail in [docs/battery-power-plan.md](docs/battery-power-plan.md).

## Troubleshooting

| Problem | Fix |
|---|---|
| Everything is counted as a car | Raise `SAT_MIN`. Make sure the road is properly dark. |
| Nothing is counted | Lower `SAT_MIN` or `MIN_AREA`, or move the camera closer |
| A count flickers on and off | The value is right on the edge. Lower `MIN_AREA` and redraw the zones with more margin. |
| Counts are wrong after moving the board | The camera shifted. Run `python3 counter.py --setup` and redraw the zones. |
| Counting changes as the room light changes | Webcam auto-exposure is drifting. Use your own lamp on the mast. |
| The Pi freezes or reboots randomly | Almost always the power supply. Check `vcgencmd get_throttled`. |
| The camera stops mid-run | The system falls back to a fixed timer automatically. To get the camera back: plug it in, `Ctrl+C`, start again. |

---

## Limitations

- Detection depends on brightly coloured cars on a dark road. Grey, silver, white and black cars aren't detected.
- Two cars parked bumper to bumper merge into one blob and are counted as one.
- The waiting-time figures come from a model, not from measuring real traffic.
- It would not work on a real road as it is. Real vehicles aren't bright uniform colours, so a real version would need trained object detection (such as YOLO) and a more powerful computer, and real junctions mostly use sensors buried in the road. What this project demonstrates is the timing algorithm, and that part carries over.

## Planned next

- Pedestrian crossing: an all-red "scramble" walk phase requested by push buttons, with a buzzer for accessibility
- A web page for live viewing and control, with a safety checker that blocks conflicting greens
- Emergency vehicle priority
- Night mode with flashing yellows when the junction is empty
- Data logging and graphs
- Comparing colour detection with an AI object detector trained on the toy cars

---

## Repository layout

```
smart-traffic-light/
├── README.md
├── config.py
├── traffic_lights.py
├── counter.py
├── timing.py
├── smart_traffic.py
├── tools/
│   ├── checksat.py
│   └── checkarea.py
└── docs/
    ├── build-guide.md
    ├── battery-power-plan.md
    ├── 48-hour-exhibition-plan.md
    └── final-test-and-exhibition-day.md
```

## Project documents

The `docs/` folder holds the planning documents used while building the project, in the order they were written:

1. [build-guide.md](docs/build-guide.md): the original design, shopping list, wiring and three-week plan
2. [battery-power-plan.md](docs/battery-power-plan.md): running everything from power banks with no venue electricity
3. [48-hour-exhibition-plan.md](docs/48-hour-exhibition-plan.md): integration and rehearsal plan for the last two days
4. [final-test-and-exhibition-day.md](docs/final-test-and-exhibition-day.md): the final test checklist and exhibition-day plan. This is the most up-to-date description of how the system behaves; where the earlier documents differ, this one is correct.

## Acknowledgements

Planning, code drafting and debugging were done with help from Claude, an AI assistant made by Anthropic. Building the model junction, wiring, tuning the camera, testing and presenting the project were done by hand.
