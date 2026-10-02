# Final test and exhibition day

**The code is finished. Freeze it.** No more changes after the final test. This doc replaces the older 48-hour plan for everything on the day.

---

## 1. Freeze a copy tonight

```bash
cp -r ~/smart_traffic ~/smart_traffic_FINAL
```

If anything gets broken tomorrow, this puts everything back exactly as it is now:

```bash
cp ~/smart_traffic_FINAL/* ~/smart_traffic/
```

---

## 2. Final test run (about 30 minutes)

Run each test once. If one fails, stop and fix that one before going on.

| # | Test | Do this | Pass looks like |
|---|---|---|---|
| 1 | Power | `vcgencmd get_throttled` | `throttled=0x0`. Anything else means the supply or cable is too weak. |
| 2 | Empty board | `python3 smart_traffic.py`, no cars on the board | All four get 5s, order North → East → South → West, and the lights keep cycling |
| 3 | One road only | 3 cars on South only | North, East, West show `SKIPPED (empty)`, `order this cycle: South`, only South's light goes green |
| 4 | Busiest first | 1 car North, 3 cars West | `order this cycle: West -> North`, West 11s, North 7s |
| 5 | Early cut-off | 5 cars on one road. When it turns green, take them all off | About 2 seconds after the 5-second minimum it goes yellow, and the terminal prints `road cleared, cut short` |
| 6 | Camera unplug | While it runs, pull out the webcam USB | Prints `Camera error mid-run -> fixed timer from now on`, and the lights keep going at 15s each. To get the camera back: plug it in, `Ctrl+C`, start again |
| 7 | Panic button | Set `PRIORITY_ORDER` and `SKIP_EMPTY` to `False`, run, then set them back to `True` | With both off, all four roads always run in N → E → S → W order |
| 8 | Redraw zones | `python3 counter.py --setup` | You can redraw all four boxes in under a minute. The camera will get knocked during transport. |
| 9 | Hotspot + VNC | Phone hotspot on. Connect the Pi to it (Wi-Fi icon, top right), then the laptop. VNC to `raspberry.local` | The Pi desktop appears. The home Wi-Fi will not be at the venue. |
| 10 | Shutdown | `sudo shutdown -h now` | Wait until the Pi's green activity LED stops blinking before unplugging |

**About test 9:** the Pi's name is `raspberry` (from the `dinuth@raspberry` prompt), so the address is `raspberry.local`, not `raspberrypi.local` as the battery plan says. If `.local` does not connect, find the Pi's IP address in the phone hotspot's list of connected devices and type that into VNC instead.

---

## 3. What the system does now (say it this way)

The old explanation said "five seconds guaranteed for everyone." **That is no longer true.** Empty roads now get nothing. Use this version:

> "Normal traffic lights give every road the same green time, whether it's jammed or empty. Mine uses one overhead camera to count the cars waiting on each road. A road with no cars is skipped completely. The busiest road goes first. Every road with cars gets at least five seconds, plus two more seconds per car, but never more than twenty-five.
>
> Here, put cars on just this one road. See? It's the only light that turns green. Now take them away while it's green. It cuts short instead of wasting everyone's time.
>
> No road with cars waiting ever waits more than one cycle, and the whole cycle is never longer than the old fixed timer's 76 seconds. So it can never be worse than the system it replaces."

Then stop talking and let them play with the cars.

---

## 4. Judge questions, updated answers

**"How do you know a road doesn't wait forever?"**
> "Every road with cars gets exactly one turn in every cycle, and the cycle is capped at 76 seconds. A road is only skipped when nobody is on it. My test file checks that automatically." *Then run `python3 timing.py` and point at "a road is only ever skipped when it has NO vehicles waiting."*

**"Why does the busiest road go first?"**
> "Serving the longest queue first cuts total waiting time. In my gridlock test the fixed-order version tied the fixed timer at 0%, and busiest-first gets 4%. Real traffic lights usually keep a fixed order so drivers can predict it, so I made it a switch and I can show both."

**"What happens when there are no cars at all?"**
> "It falls back to a normal cycle, five seconds each, so the lights never freeze."

**"What if the camera fails?"**
> "It detects that and falls back to a fixed timer automatically. Let me unplug it and show you." *(Then actually do it.)*

**"Would this work on a real road?"**
> "Not as it is. Real cars aren't bright colours, so I'd need proper AI object detection and a stronger computer. Real junctions mostly use sensors buried in the road. What I'm showing is the timing algorithm, and that part is real."

---

## 5. The evidence table

This is what `python3 timing.py` prints now. Print it and put it on the table next to the poster.

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

The honest reading: when traffic is uneven it saves a lot. When traffic is perfectly balanced it matches the fixed timer, because there's nothing to optimise. And it is never worse.

---

## 6. Exhibition morning, before visitors arrive

1. Turn on the lamp and aim it at the board **before** tuning anything.
2. `python3 counter.py` with no cars on the board. All four counts must be 0. If not, raise `SAT_MIN` in `config.py`.
3. Put 5 cars in one zone and check it reads 5. If the boxes don't line up with the roads, run `python3 counter.py --setup`.
4. Tape the camera mast down, then tape it again.
5. `python3 smart_traffic.py`, then make the terminal window full-screen on the laptop. That is your visitor display.

---

## 7. If something goes wrong

| Problem | Fix |
|---|---|
| Camera glitches mid-run | `Ctrl+C`, start `smart_traffic.py` again |
| Counting goes wrong under the hall lights | Raise `SAT_MIN` in `config.py` and restart |
| Skipping or ordering behaves strangely | Set both flags to `False`. That's the version that has been working all along. |
| Camera will not work at all | `python3 smart_traffic.py --nocam` and type the counts in by hand. The timing still shows fully. |
| Files got broken | `cp ~/smart_traffic_FINAL/* ~/smart_traffic/` |
| Pi will not boot | Poster, logbook and the printed evidence table. Explain the algorithm from the table. |

---

## 8. Pack

- Pi, official power supply, **and** a charged power bank with a short, thick USB-C cable (venue power is still unconfirmed)
- Webcam, the board, the camera mast, the lamp
- Laptop and charger, phone for the hotspot
- Toy cars in a bowl, plus a sign: *"Add cars and watch the lights change"*
- Poster, logbook, printed evidence table
- Tape, spare LEDs, spare resistors
