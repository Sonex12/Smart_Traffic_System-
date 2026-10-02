# Running the Smart Traffic Light on battery power (no venue electricity)

The organisers may not provide mains power. The project does not need it: the Pi runs on 5 V USB power from a power bank, and the display is a laptop (or phone/tablet) on its own battery, connected over VNC.

**What to tell the organisers:** "Our project needs no power from the venue. It runs entirely on USB power banks at 5 volts, like charging a phone. No mains plug, no extension cords."

## The setup

| Part | Power it from | Notes |
|---|---|---|
| Raspberry Pi + webcam + 12 LEDs | 20,000 mAh power bank, **USB-C port** | Roughly 5–7 W. About 8–10 hours from a 20,000 mAh bank; a 10,000 mAh bank gives about half. Estimates only; test at home. |
| Display | Laptop (or phone/tablet) on its own battery, running VNC Viewer | No monitor on the Pi. |
| Lamp over the board | External lamp, which must be battery or rechargeable | A lamp that plugs into the wall needs venue power. Use a rechargeable LED lamp, or a USB lamp on a second power bank. |

## VNC at the venue

- **The home Wi-Fi router won't be there.** VNC needs a network. Use a phone hotspot, or the laptop's own hotspot (Windows: Settings → Network → Mobile hotspot). Add that hotspot to the Pi's Wi-Fi at home, then test the full connection with the home router switched off.
- The Pi will get a different IP address on the hotspot. Connect by hostname (e.g. `raspberrypi.local`) or find the IP in the hotspot's list of connected devices.
- **Test with no HDMI cable plugged into the Pi.** Some setups show a blank or tiny desktop over VNC without a monitor. Fix: `sudo raspi-config` → Display Options → VNC Resolution.
- Laptop battery: charge fully and lower the screen brightness. If the laptop charges over USB-C, a PD power bank can top it up. If the laptop dies, the Pi and the traffic lights keep running; only the on-screen numbers go away.

## Power-bank pitfalls

- Use a short, good-quality USB-C cable. Thin or long cables drop the voltage, and the Pi throttles or crashes. Check with `vcgencmd get_throttled`: `throttled=0x0` means no undervoltage happened.
- **Pi 5 only:** power banks can't supply the 5 A it asks for. It still runs, but it limits its USB ports to 600 mA total. The webcam fits within that.
- Don't charge the bank while it is powering the Pi. Many banks cut output briefly when the charger is plugged in, and the Pi reboots.
- Swapping banks reboots the Pi. Shut down properly first (`sudo shutdown -h now`), then reconnect VNC and start `smart_traffic.py` again after the swap.

## Rehearsal

Charge everything fully, switch off the home router, start at the exhibition's opening time, and run until the battery dies. That tests the hotspot, VNC and the real runtime together. Bring a spare charged bank on the day.

## Poster angle

Measure the real power draw with a cheap USB-C power meter (USB tester). Something like "The whole system uses X watts; one power bank runs it for Y hours" is a measured result, and it connects to a real problem: traffic lights going dark during power cuts.
