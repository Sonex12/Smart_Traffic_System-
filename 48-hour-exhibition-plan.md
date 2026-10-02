# 48-hour exhibition readiness plan

**Today: Monday 21 Sept · Tomorrow: Tuesday 22 Sept · Exhibition: Wednesday 23 Sept**

---

## Where you actually stand

**Done and working:**

- The physical board — roads, junction, trees, and it looks good
- **The camera counting works.** Cars detected in all four zones, trees correctly ignored. This was the hardest and riskiest part of the whole project, and it is behind you.
- Poster and block diagram

**Not yet done:**

- LEDs and the full system have never been run together
- Camera-failure fallback never tested
- No comparison demo, no dress rehearsal
- Power at the venue unknown, and the Pi is showing an undervoltage warning
- No logbook, explanation not rehearsed

**The important thing:** everything left is *integration and rehearsal*, not invention. You are not building anything new. You are connecting parts that already work and proving they survive being moved. That is a very different position from having a broken detector two days out.

---

## The one rule for the next 48 hours

> **Fix the power before you test anything else.**

An undervolted Pi produces failures that look exactly like software bugs — random freezes, a camera that stops responding, LEDs that flicker. If you debug code while that warning is on screen, you will chase problems that do not exist and waste a day you do not have.

---

## TODAY — Monday

### Step 1 · Make the power solid (30 min, before anything else)

```bash
vcgencmd get_throttled
```

- `throttled=0x0` → clean, no undervoltage since boot. Good, move on.
- Anything else (`0x50005`, `0x50000`, etc.) → voltage problems have occurred.

Fix: the **official Raspberry Pi 5V supply** (Pi 4 needs 3A USB-C, Pi 5 needs 5A). If you are on a power bank, use a short, thick, good-quality USB-C cable — thin or long cables drop voltage and cause exactly this.

Then run the system for ten minutes with camera and LEDs active and check `get_throttled` again.

**Do not move to Step 2 until it reads `0x0` after a full run.** Every test below is untrustworthy otherwise.

### Step 2 · Prove the LEDs (30 min — or 2 hours if not yet wired)

```bash
cd smart_traffic
python3 traffic_lights.py
```

**Pass =** all 12 LEDs cycle North → East → South → West, with red, yellow and green correct on each direction.

If nothing lights at all: check the GND rail connection first, then LED polarity (long leg is the anode, goes to the resistor side).
If one direction is dead: check those three GPIO pins against the table in the build guide §3.
If the LEDs are not wired yet at all: this is tonight's main job. Do it before anything else — budget two hours and do not start the camera work until they cycle.

### Step 3 · The moment of truth (45 min)

```bash
python3 smart_traffic.py
```

This is the actual project — counting, timing and lights together for the first time.

**Pass =** put five cars on North. North's green is visibly longer than the other three. Remove them while it is still green, and it cuts to yellow early.

If it fails, isolate rather than guess. Run `python3 counter.py` alone (vision still good?) and `python3 traffic_lights.py` alone (lights still good?). Whichever passes on its own tells you the fault is in the joining, not in the part — and that is a much smaller problem to solve.

### Step 4 · Phone the organisers (10 min)

Ask one question: **"Is there a mains socket at our table?"**

- **Yes** → official PSU plus laptop charger. Skip tomorrow's battery rehearsal entirely and use that time for rehearsal instead.
- **No, or unsure** → treat it as no, and do the battery rehearsal tomorrow.

Make this call today. It decides how tomorrow is spent.

### Step 5 · Logbook (1 hour, evening)

You have done real experimental work and none of it is written down. Do it tonight while you still remember the details. Dated entries, and **include the failures** — judges score process far more than polish.

Things that genuinely happened and belong in there: tuning `SAT_MIN` and `MIN_AREA` until counting was reliable; the concern that coloured paper trees would be counted as cars, the reasoning that zone rectangles gate the count, and the test that confirmed it (trees visible in the mask, all four counts still zero); adjusting the camera field of view so background clutter stayed out of frame; finding the undervoltage warning and fixing the supply.

That last one is especially good. "I found a hardware fault that was masquerading as a software problem" is exactly the kind of entry that impresses.

---

## TOMORROW — Tuesday

### Morning · Insurance (1 hour)

**1. The camera-failure test.** Start `smart_traffic.py`, let it run, then physically unplug the webcam. The lights must keep cycling on a fixed timer with a warning printed on screen.

Five minutes of work that converts your single most likely disaster into a talking point. If it happens on the day you get to say *"it detected the failure and fell back automatically — let me show you"* instead of standing in front of a dead table.

**2. The comparison demo.**

```bash
python3 smart_traffic.py --fixed
```

Run the same arrangement of cars both ways — fixed and adaptive — and **write both waiting-time numbers on paper**. A judge who sees two numbers side by side remembers your project. Description does not compete with comparison.

### Midday · Battery rehearsal (2 hours — only if mains was not confirmed)

Charge everything fully. **Switch off your home router** — that is the whole point of the test. Phone hotspot on, Pi on the power bank, laptop on its own battery, VNC connected. Run the real thing for an hour.

- Connect by hostname `raspberrypi.local`, since the IP will be different on the hotspot.
- Add the hotspot to the Pi's known networks *at home*, before the day.
- If VNC shows a blank or tiny desktop with no HDMI attached: `sudo raspi-config` → Display Options → VNC Resolution.
- Do not plug a charger into the power bank while it is running the Pi — many banks cut output briefly and reboot it.

### Afternoon · Dinuth rehearses, then dress rehearsal (2 hours)

He needs to deliver the 60-second explanation **without reading it**, and handle the four judge questions in build guide §10. Have him explain it to someone who knows nothing about the project — their confused questions are the ones judges will ask.

Then the test that actually matters: **tear the whole thing down, pack it into the box, and set it up again from scratch, timed.** Target under 10 minutes. Then leave it running 30 minutes without touching it.

This is where you discover the clamp you forgot, the cable that is too short, and the fact that the zones need redrawing after the camera mast moves. Far better to find that tomorrow afternoon than on Wednesday morning.

Practise `python3 counter.py --setup` until redrawing the four zones takes you 30 seconds calmly with someone watching. You will almost certainly need it on the day.

### Evening · Pack the box

- Pi, official power supply, webcam, the assembled board
- Laptop + charger, VNC already tested and working
- Power banks charged (bring a spare), short USB-C cables
- **Your own clip-on lamp** — this is not optional, hall lighting will not match your house
- Toy cars in a bowl, plus a sign: *"Add cars and watch the timing change"*
- Poster, logbook, spare LEDs, spare resistors, tape, small screwdriver
- A printed copy of the `timing.py` results table

---

## Exhibition day — Wednesday

Arrive early. Set up in your practised order. Then, before visitors arrive:

1. Clip the lamp on and aim it at the board — do this *before* tuning anything.
2. Run `counter.py` with zero cars on the board. Every count should read 0. If not, raise `SAT_MIN` in `config.py` until it does.
3. Place five cars in one zone and confirm it reads 5.
4. Tape the camera mast down. Then tape it again.
5. Start `smart_traffic.py` and leave it running.

Then let visitors play with the cars. Dinuth talks, and stops talking, and lets them try it.

---

## If it goes wrong on the day

You have layered fallbacks. Know them in this order so you are never standing there with nothing.

1. **Camera dies** → already automatic. Lights continue on a fixed timer. Explain it as fault-tolerant design.
2. **Vision misbehaves under hall lighting and re-tuning does not fix it** → `python3 smart_traffic.py --nocam`, type the counts in by hand. The adaptive timing still demonstrates completely; you simply say you are feeding the counts manually because the lighting is fighting you. **Practise this at least once tomorrow.**
3. **The Pi will not boot at all** → poster, plus `timing.py` running on the laptop showing the evidence table. The algorithm is still explainable and the results table is still real.

---

## If you run out of time, cut in this order

Drop first: the 30-minute unattended run, then the `--fixed` comparison, then logbook depth.

**Never cut:** solid power, `smart_traffic.py` working end to end, and Dinuth being able to explain it. A working project nobody can explain scores badly. A modest project explained clearly scores well.
