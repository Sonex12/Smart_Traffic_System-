# Smart Adaptive Traffic Light System
### Raspberry Pi build guide — Grade 9 exhibition project

**The idea:** an ordinary traffic light gives every road the same green time, even when one road is jammed and the others are empty. This one uses a camera to count waiting vehicles and gives the busy road a longer green.

**Your deadline is 2–4 weeks and you don't have a camera yet.** Every recommendation below is chosen for that reality. Read section 1 before you buy anything.

---

## 1. The one decision that will save this project

You said "four cameras." Please don't. Here's why, and what to do instead.

**The problem with four cameras:**

- A Raspberry Pi 4 has **one** camera ribbon port. A Pi 5 has two. Neither has four. ([Raspberry Pi Forums](https://forums.raspberrypi.com/viewtopic.php?t=358242))
- Connecting four ribbon cameras needs an Arducam multiplexer board — imported, expensive, and it will not arrive in three weeks. ([Arducam](https://blog.arducam.com/multi-camera-adapter-module-raspberry-pi/))
- Four USB webcams *technically* work, but they fight over USB bandwidth, and you'd have to calibrate four separate views under four different lighting angles. That is four times the ways for it to fail on exhibition day.

**Do this instead: one camera, mounted overhead, looking straight down at the junction. Divide the picture into four rectangles — one per approach road.**

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

One photo. Four rectangles. Four counts. Same result, **one quarter of the cost and one quarter of the ways to break.**

And this is not a compromise you should hide — it's the engineering insight you lead with:

> "A four-camera system costs four times as much and needs four calibrations. I realised one overhead camera sees all four approaches in a single frame, so I count four regions of interest instead. Same data, quarter the cost, and one calibration instead of four."

Judges reward that kind of reasoning far more than four cameras would have impressed them.

---

## 2. What to buy — today, not tomorrow

You already have the Pi, LEDs, breadboard and wires. Here's the rest.

### The camera — buy the fastest option, not the best one

| Option | Get it from | Why |
|---|---|---|
| **Any USB webcam** ← *recommended* | Any computer shop in Colombo, Unity Plaza, or a supermarket | **Available today.** Works with the code as-is. A 720p webcam is more than enough. |
| Pi Camera Module V2 / V1.3 | [tronic.lk](https://tronic.lk/category/light-sensor-modules/cameras-barcodes-ccd), [duino.lk](https://www.duino.lk/product-category/modules/camera-module/), [microchip.lk](https://microchip.lk/product-category/embedded-solution/raspberi-pi/pi-cameras/), [alphatronic.lk](https://alphatronic.lk/product/raspberry-pi-camera-module-v1-3-5mp-ov5647/) | Better picture, but check delivery time before ordering |

**With a 2–4 week deadline, a webcam you can hold in your hand today beats a better camera arriving in ten days.** Buy the webcam. If a Pi camera also arrives in time, switch by setting one line in `config.py`. Confirm prices with the shops directly — don't rely on old listings.

### Everything else

- **12 LEDs** — 4 red, 4 yellow, 4 green (you may already have these)
- **12 resistors**, 220Ω. If the greens look dim, swap those for 150Ω
- **Foam board or plywood**, about 60 × 60 cm, for the junction model
- **Toy cars** — 15–20 of them, in **bright, strongly coloured** shades. Red, blue, yellow, green. **Avoid grey, silver, white and black** — the detection works on colour, and a grey car on a grey road is invisible to it. This one shopping choice decides whether your project works.
- **Black paint or black paper** for the road surface, white tape for lane markings
- **A camera mast** — PVC pipe, a broom handle clamped to the board, or a desk lamp arm with the bulb removed
- **A small USB LED light or clip-on lamp** to fix to the mast. **Do not skip this.** See section 9.
- **Official 5V power supply** for the Pi. A weak phone charger causes random crashes that look like software bugs and will waste days of your life.

---

## 3. Wiring the twelve LEDs

Every LED: **Pi GPIO pin → 220Ω resistor → LED long leg (anode) → LED short leg (cathode) → GND rail.**

Use BCM pin numbers (the GPIO numbers, not the physical positions).

| Direction | Red | Yellow | Green |
|---|---|---|---|
| North | GPIO 4 | GPIO 17 | GPIO 27 |
| East | GPIO 22 | GPIO 5 | GPIO 6 |
| South | GPIO 13 | GPIO 19 | GPIO 26 |
| West | GPIO 12 | GPIO 16 | GPIO 20 |

GPIO 2 and 3 are deliberately left free in case you add a small OLED display later.

> ### ⚠️ One electrical rule you must respect
>
> Each GPIO pin can safely supply about 16 mA, and **all the pins together should stay under about 50 mA.** At 220Ω each LED draws roughly 6 mA, so:
>
> - Normal operation lights 4–5 LEDs at once ≈ 30 mA. **Safe.**
> - Lighting all 12 at once ≈ 72 mA. **Over the limit.**
>
> The code never lights all twelve simultaneously, and neither should your testing. If you want an "all lights flash" startup animation, flash them in groups, not all together.
>
> This is a genuinely good thing to mention on your poster — it shows you thought about the electronics, not just the code.

---

## 4. How it actually works — the three ideas

### Idea 1: finding cars by colour, not by shape

Real AI object detection (YOLO, TensorFlow) is trained on photographs of real cars. It often fails on toy cars, it runs slowly on a Pi, and it would eat your entire three weeks.

There's a much better trick for a model junction. Convert the image from RGB to **HSV** colour space. In HSV, the **S** channel means "how colourful is this pixel":

- Grey road, black tarmac, white lines → **low saturation**
- Red, blue, yellow, green toy car → **high saturation**

So: keep only the pixels with saturation above a threshold, clean up the specks, and count the blobs that are big enough to be a car. That's about fifteen lines of OpenCV and it runs instantly on any Pi.

**Why this beats brightness-based methods:** saturation barely changes when the lighting gets brighter or dimmer. A method based on brightness or on background subtraction breaks the moment you move from your bedroom to the exhibition hall. This one mostly survives it.

### Idea 2: the timing rule

> Every road gets **5 seconds of green for free**,
> **plus 2 more seconds for every vehicle waiting**,
> but **never more than 25 seconds**,
> and the **whole cycle never exceeds 76 seconds.**

Each part exists for a reason, and you should be able to say what it is:

| Rule | Why it exists |
|---|---|
| Minimum 5s green | A road with one car is never ignored. Fairness. |
| 2s per vehicle | The adaptive part — demand becomes time. |
| Maximum 25s green | Stops one busy road hogging the junction forever. |
| Cycle capped at 76s | 76s is exactly what the old fixed timer takes, so **the smart system can never make anyone wait longer than the system it replaces.** |
| Fixed N→E→S→W order | Every direction gets a turn in **every** cycle. Only the *duration* adapts, never the *order*. This is what makes "starvation" impossible. |
| 3s yellow + 1s all-red | Safety. The all-red gap lets the junction clear before the next road moves. Real junctions do this. |

### Idea 3: early cut-off

If a green road empties out before its time is up, the system cuts to yellow early (but never before the 5-second minimum).

This is your best live demo. **Remove the toy cars while the light is green and the light changes in front of the visitor's eyes.** Cause and effect they can see in three seconds. Nothing else on your table will land as well.

---

## 5. Software setup

On Raspberry Pi OS, install OpenCV through `apt` rather than `pip`. The `pip` version tries to compile from source and can take hours on a Pi, or fail outright.

```bash
sudo apt update
sudo apt install -y python3-opencv python3-gpiozero python3-numpy
```

`picamera2` is already installed on current Raspberry Pi OS — you only need it if you use a ribbon-cable camera rather than a USB webcam.

Check it worked:

```bash
python3 -c "import cv2, gpiozero; print('OpenCV', cv2.__version__, '- ready')"
```

If you prefer a virtual environment, create it with `python3 -m venv --system-site-packages env` — without that flag the venv can't see the apt-installed OpenCV.

---

## 6. The programs, and the order to run them

Copy the five files into a folder called `smart_traffic` on your Pi.

| File | What it is |
|---|---|
| `config.py` | Every number you might want to change. Pin numbers, timings, detection sensitivity. Change things **here**. |
| `traffic_lights.py` | Controls the 12 LEDs. Runs a fixed-time cycle. **No camera needed.** |
| `counter.py` | Camera + counting the cars in four zones. |
| `timing.py` | The brain. Turns counts into green times. **No camera and no LEDs needed** — runs on any computer. |
| `smart_traffic.py` | Everything together. This is what runs on exhibition day. |

**Run them in this order as you build:**

```bash
# Day 1 - LEDs only, no camera required
python3 traffic_lights.py

# Any day - prove the algorithm is correct, on any computer
python3 timing.py

# No camera yet? Type counts in by hand and watch the lights respond
python3 smart_traffic.py --nocam

# Once the camera arrives - draw the four zones (do this ONCE)
python3 counter.py --setup

# Check the counting is accurate
python3 counter.py

# The real thing
python3 smart_traffic.py

# The comparison, for your demo
python3 smart_traffic.py --fixed
```

### What `timing.py` prints

This is your evidence table. Run it in front of a judge:

```
Scenario                 North    East   South    West   cycle    saved
----------------------------------------------------------------------
Empty junction            5.0s    5.0s    5.0s    5.0s   36.0s     0.0%
Light, even              11.0s   11.0s   11.0s   11.0s   60.0s    19.0%
Balanced, moderate       15.0s   15.0s   15.0s   15.0s   76.0s     0.0%
Rush hour, one road      25.0s    7.0s    7.0s    7.0s   62.0s    33.7%
Everything on North      25.0s    5.0s    5.0s    5.0s   56.0s    63.8%
Two busy, two quiet      23.0s   21.0s    7.0s    5.0s   72.0s     9.1%
Gridlock everywhere      15.0s   15.0s   15.0s   15.0s   76.0s     0.0%
```

Read that table carefully, because it's an **honest** result and honesty is what separates a good project from a flashy one:

- When traffic is **uneven**, the system saves 10–60% of waiting time. This is the win.
- When traffic is **perfectly balanced**, it behaves exactly like a fixed timer — 0%. Of course it does. There's nothing to optimise.
- When traffic is **light**, it saves time by running *shorter* cycles — nobody waits at an empty junction.
- When **everything** is jammed, it ties the fixed timer. No timing plan can fix a junction that's over capacity; you'd need another lane.
- **It is never worse.** That's guaranteed by the 76-second cap, and the test file checks it automatically.

Say all of that out loud to the judges. "My system helps when traffic is uneven and does no harm when it isn't" is a much stronger claim than "my system is 60% better," because the second one falls apart the moment someone tests it with equal traffic.

---

## 7. Building the model junction

- Cut foam board to about 60 × 60 cm. Paint the roads black or glue on black paper — **high contrast with your coloured cars is the whole game.**
- White insulation tape or paper strips for lane markings.
- Mount the camera **directly above the centre**, roughly 50–60 cm up, pointing straight down. Straight down matters — a tilted camera makes far-away cars look small and they fall below the size threshold.
- **Tape the camera mast down so it cannot be nudged.** If the camera moves, your four zones no longer line up with the roads and everything breaks. Tape, then tape again.
- Mount the traffic light LEDs at the four corners of the junction, where a real signal head would be. Cardboard tubes painted black make convincing signal housings.
- **Clip your own small lamp to the mast, aimed at the board.** Section 9 explains why this single piece of tape is the difference between a working demo and a broken one.

---

## 8. Day-by-day plan (3 weeks)

**Order the camera on day 1 — or better, buy a USB webcam off the shelf today. Everything else can be done while waiting, but nothing can be finished without it.**

### Week 1 — electronics and logic

| Day | Do this |
|---|---|
| 1 | Buy the webcam. Wire 3 LEDs (one direction) and get them blinking. |
| 2 | Wire all 12. Run `traffic_lights.py`. **You now have working traffic lights.** |
| 3 | Run `timing.py`. Read the code until you understand the formula. Change `SEC_PER_VEHICLE` and watch the table change. |
| 4 | Run `smart_traffic.py --nocam`. Type counts, watch the lights respond. **The whole project now works except the camera.** |
| 5–7 | Build the physical model: board, roads, LED mounting, camera mast. |

### Week 2 — vision

| Day | Do this |
|---|---|
| 8 | Camera working, `counter.py --setup`, four zones drawn. |
| 9 | Tune `SAT_MIN` and `MIN_AREA` until counting is reliable. Expect this to take a full day. It is normal. |
| 10 | Test with 0, 1, 5, 15 cars in each zone. Write the results in your logbook. |
| 11 | Full system: `python3 smart_traffic.py`. |
| 12–13 | Tune `SEC_PER_VEHICLE`. Measure your real `FLOW_RATE` (see section 11). |
| 14 | **Test under three different lighting conditions.** Daylight, room light at night, torch shining on it. Fix what breaks. |

### Week 3 — making it survive contact with the public

| Day | Do this |
|---|---|
| 15 | Fallback mode: unplug the camera mid-run and confirm the lights keep working. |
| 16 | Poster and labelled diagram. |
| 17 | Write and rehearse your 60-second explanation. |
| 18 | Full dress rehearsal — set up from scratch in under 10 minutes, run for 30 minutes without touching it. |
| 19 | Explain it to someone who knows nothing about it. Their confused questions are the ones judges will ask. |
| 20–21 | **Buffer.** Something will break. Something always breaks. If nothing does, rehearse again. |

---

## 9. Things that will go wrong — and the fixes

### The lighting problem — read this one twice

**This is the number one killer of camera projects at exhibitions.** You tune everything perfectly at home. You arrive at the hall. The lights are fluorescent, or there's a window behind you, or you're under a different-coloured bulb — and your carefully tuned thresholds detect nothing, or detect the road as forty cars.

**Three defences, use all three:**

1. **Bring your own light.** Clip a small USB lamp to the camera mast, aimed down at the board. Now your lighting is the same everywhere in the world. This is the single most valuable piece of advice in this document.
2. **Use saturation, not brightness** — already built into the code, and this is exactly why.
3. **Be able to re-tune in 30 seconds.** Know that `SAT_MIN` in `config.py` is the dial. Higher = fewer detections. Practise changing it and restarting until you can do it without thinking.

### The camera got bumped
Your four zones no longer line up with the roads. Fix: `python3 counter.py --setup`, redraw, 30 seconds. Practise it beforehand so you can do it calmly with someone watching.

### Everything is detected as a car
`SAT_MIN` too low, or your road is too colourful. Raise `SAT_MIN`. Make the road properly black.

### Nothing is detected
`MIN_AREA` too high (camera too far away, cars too small in frame) or `SAT_MIN` too high. Lower them. Move the camera closer.

### The Pi randomly reboots or freezes
Almost always the power supply. Use the official one. A weak charger produces symptoms that look exactly like software bugs and will cost you days.

### The camera dies completely on the day
Already handled — `smart_traffic.py` detects it and falls back to a fixed timer automatically, printing why on screen. **The lights keep running.** You can then explain the failure to the judge and turn a disaster into a talking point about fault-tolerant design. Test this before the day so you know it works.

---

## 10. Exhibition day

### Your table

- Model junction with the lights running
- **A monitor showing the live output** — the counts, the bars, the green times, the running "% less waiting" figure. Visitors watching numbers change is what makes them stop walking.
- A bowl of toy cars, with a sign: **"Add cars and watch the timing change."** Let them do it themselves. Interactivity is what gets remembered.
- Poster with the block diagram
- Your logbook, open

### The 60-second explanation

> "Normal traffic lights give every road the same green time, whether it's jammed or empty. Mine uses one overhead camera to count the vehicles waiting on each of the four roads, then gives more green time to the busiest one — five seconds guaranteed for everyone, plus two extra seconds per vehicle, capped at twenty-five so no road hogs the junction.
>
> Here — put some cars on this road. See the green time go up? Now take them away while it's green. It cuts short instead of wasting everyone's time.
>
> In my tests it cuts waiting time by up to 60% when traffic is uneven, and it's never worse than a fixed timer, because I capped the cycle length at exactly what the old system uses."

Then stop talking and let them play with the cars.

### The demo that wins

Run the same set of cars twice — once with `--fixed` and once adaptive — and point at the waiting-time number. **Comparison beats description.** A judge who sees 456 vs 351 on screen remembers your project.

### Questions judges ask, and good answers

**"Why not four cameras?"**
> "I worked out that a Pi 4 only has one camera port, and a four-camera multiplexer costs four times as much. One overhead camera sees all four approaches in the same frame, so I count four regions instead. Same data, quarter the cost, one calibration instead of four."

**"Would this work on a real road?"**
> "Not as it is. Real vehicles aren't bright uniform colours, so I'd need proper object detection — something like YOLO — and a much more powerful computer than a Pi. Real junctions also use inductive loops buried in the road rather than cameras. What I'm demonstrating is the *timing algorithm*, and that part is real."

That honest answer scores higher than overclaiming. Judges have heard a hundred students say "this could be deployed in Colombo tomorrow" and they know it isn't true.

**"What happens if the camera fails?"**
> "It falls back to a fixed timer automatically and shows a warning. Let me unplug it and show you." *(Then actually do it.)*

**"How do you know a road doesn't wait forever?"**
> "The order is fixed — North, East, South, West, always. Only the duration changes. So every road gets a turn in every single cycle, and there's a guaranteed five-second minimum. Starvation is impossible by design."

**"Where did your improvement number come from?"**
> "I model waiting time in vehicle-seconds, accounting for the fact that a short green can't clear a long queue, so leftover vehicles wait another whole cycle. It's a simplification and I'd rather say so — but it's the same comparison applied to both systems, so the *relative* result is fair."

---

## 11. If you have spare time — how to score higher

Roughly in order of value-per-hour:

1. **Measure your real flow rate.** Time how long it takes 10 cars to clear the junction on your model, divide 10 by the seconds. Put that number in `config.py` as `FLOW_RATE`. Now your improvement figures come from measurement rather than assumption — that's the difference between a demonstration and an experiment.
2. **Keep a proper logbook.** Date, what you tried, what happened, what you changed. Include the failures. Judges score *process*, and a page reading "Day 9: detected 40 cars on an empty road, realised the wooden table edge was in the zone, redrew it" is worth more than a page of perfect results.
3. **A graph.** Waiting time vs traffic imbalance, from the `timing.py` numbers. One well-labelled graph beats three paragraphs.
4. **Emergency vehicle priority.** Put one distinctly-coloured car in a zone; if detected, that road goes green next. About 15 lines of code and it always gets a reaction.
5. **Pedestrian button.** A push button on a spare GPIO that inserts an all-red walk phase.
6. **A countdown display.** An OLED on GPIO 2/3 showing seconds remaining. Very visible, very satisfying.
7. **Log to CSV** and show a graph of a full hour of operation.

**Don't** attempt real AI object detection in three weeks. It's a great "future work" line on your poster and a terrible use of your remaining time.

---

## 12. Safety

Everything here runs at 3.3V and 5V. Nothing touches mains electricity. Keep it that way — there is no reason for a mains connection anywhere in this project, and an exhibition table is exactly the wrong place for one.

Respect the GPIO current limit in section 3. Always shut the Pi down properly with `sudo shutdown -h now` before unplugging it, or you risk corrupting the SD card — which, the night before an exhibition, is a genuinely miserable experience.

---

## Quick reference — the dials in `config.py`

| Setting | Default | Turn it up when... |
|---|---|---|
| `SAT_MIN` | 90 | The road is being detected as cars |
| `MIN_AREA` | 300 | Small specks are being counted |
| `SEC_PER_VEHICLE` | 2.0 | You want the system to react more aggressively |
| `G_MIN` | 5 | Quiet roads feel too rushed |
| `G_MAX` | 25 | One road should be allowed to dominate more |
| `CAMERA_INDEX` | 0 | The webcam isn't found — try 1, then 2 |
| `USE_PICAMERA` | False | You're using a ribbon-cable Pi camera |

---

**Sources**

- [Raspberry Pi Forums — 4 cameras on Raspberry Pi 5](https://forums.raspberrypi.com/viewtopic.php?t=358242)
- [Arducam — Raspberry Pi multiple camera solutions](https://blog.arducam.com/multi-camera-adapter-module-raspberry-pi/)
- [Tom's Hardware — How to use dual cameras on the Raspberry Pi 5](https://www.tomshardware.com/raspberry-pi/how-to-use-dual-cameras-on-the-raspberry-pi-5)
- [Picamera2 Library Manual (Raspberry Pi)](https://datasheets.raspberrypi.com/camera/picamera2-manual.pdf)
- Sri Lankan suppliers: [tronic.lk](https://tronic.lk/category/light-sensor-modules/cameras-barcodes-ccd) · [duino.lk](https://www.duino.lk/product-category/modules/camera-module/) · [microchip.lk](https://microchip.lk/product-category/embedded-solution/raspberi-pi/pi-cameras/) · [alphatronic.lk](https://alphatronic.lk/product/raspberry-pi-camera-module-v1-3-5mp-ov5647/) · [iotstore.lk](https://iotstore.lk/)
