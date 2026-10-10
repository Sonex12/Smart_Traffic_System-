"""
timing.py  --  STAGE 3.  The brain: turning car counts into green times.

This file has no camera and no LEDs in it, which means you can test it
on any computer. That is deliberate - if a judge asks "how do you know
your algorithm is right?", you run:

    python3 timing.py

and show the test results.

THE RULE, IN ONE LINE:
    every road WITH VEHICLES gets 5 seconds of green for free,
    plus 2 more seconds for every vehicle waiting,
    but never more than 25 seconds,
    and the whole cycle never exceeds 76 seconds.

A road with NO vehicles is skipped entirely (SKIP_EMPTY), which is what
real vehicle-actuated junctions do. If EVERY road is empty the system
falls back to a normal rotation so the lights keep moving.
"""

from config import (ORDER, G_MIN, G_MAX, YELLOW, ALL_RED, CYCLE_MAX,
                    SEC_PER_VEHICLE, FLOW_RATE, FIXED_GREEN,
                    PRIORITY_ORDER, SKIP_EMPTY)

PHASE_OVERHEAD = YELLOW + ALL_RED     # lost time for ONE phase that runs


def active_directions(counts):
    """
    Which directions actually get a turn this cycle.

    With SKIP_EMPTY on, a road with no vehicles is skipped - nobody is
    waiting there, so giving it green wastes everyone else's time.
    If the junction is COMPLETELY empty we fall back to all four, so the
    lights keep cycling instead of freezing on all-red.
    """
    if not SKIP_EMPTY:
        return list(ORDER)
    active = [d for d in ORDER if counts.get(d, 0) > 0]
    return active if active else list(ORDER)


def phase_order(counts):
    """
    The order the directions take their turn in, for ONE cycle.

    PRIORITY_ORDER False -> fixed North, East, South, West.
    PRIORITY_ORDER True  -> busiest road goes first.

    Either way every direction that has vehicles gets exactly one turn
    per cycle, so no road with cars waiting can ever be starved.
    """
    active = active_directions(counts)
    if PRIORITY_ORDER:
        return sorted(active, key=lambda d: counts.get(d, 0), reverse=True)
    return [d for d in ORDER if d in active]


def compute_green_times(counts):
    """
    Step 1  Each ACTIVE direction earns  G_MIN + 2s per waiting vehicle.
            Skipped directions get 0.
    Step 2  Nothing may exceed G_MAX (stops one road hogging the junction).
    Step 3  If the whole cycle would run past CYCLE_MAX, shrink only the
            EARNED part of each green, never the guaranteed G_MIN.

    Because step 3 shrinks the bonus rather than the whole green, the
    5-second guarantee survives no matter how heavy the traffic is.
    """
    active = active_directions(counts)

    raw = {d: 0.0 for d in ORDER}
    for d in active:
        earned = SEC_PER_VEHICLE * counts.get(d, 0)
        raw[d] = min(float(G_MAX), G_MIN + earned)

    lost = len(active) * PHASE_OVERHEAD
    if sum(raw.values()) + lost <= CYCLE_MAX:
        return raw

    # Too long - scale the bonuses down so everything just fits.
    bonus = {d: raw[d] - G_MIN for d in active}
    allowed_bonus = CYCLE_MAX - lost - len(active) * G_MIN
    total_bonus = sum(bonus.values())
    scale = allowed_bonus / total_bonus if total_bonus > 0 else 0.0

    out = {d: 0.0 for d in ORDER}
    for d in active:
        out[d] = G_MIN + bonus[d] * scale
    return out


def fixed_green_times():
    """What an ordinary, non-smart traffic light would do."""
    return {d: float(FIXED_GREEN) for d in ORDER}


def cycle_length(greens):
    """Only the phases that actually run cost yellow + all-red time."""
    running = sum(1 for d in ORDER if greens.get(d, 0) > 0)
    return sum(greens.values()) + running * PHASE_OVERHEAD


def total_waiting_time(counts, greens, order=None):
    """
    A simple model of total waiting time, in vehicle-seconds.

    The important idea is CAPACITY. A green light of g seconds can only
    let  g x FLOW_RATE  vehicles through. Any vehicle that does not fit
    is still sitting there when the cycle ends, and has to wait for the
    whole junction to come around again. That is the real cost of
    giving a busy road too little green, and it is what a fixed timer
    gets wrong.

    It IS a simplification - say so when you present it - but it lets
    you put a number on the improvement instead of just claiming one.
    """
    cyc = cycle_length(greens)
    delay = 0.0
    elapsed = 0.0

    # Vehicles are served in the order the lights actually run. The
    # caller passes that order in, because the SMART system may skip and
    # reorder phases while the FIXED timer always runs all four in turn.
    if order is None:
        order = [d for d in ORDER if greens.get(d, 0) > 0]

    for d in order:
        if greens.get(d, 0) <= 0:
            continue                    # skipped road - nobody waiting

        n = counts.get(d, 0)
        capacity = greens[d] * FLOW_RATE
        served = min(n, capacity)
        stuck = max(0.0, n - capacity)

        # Vehicles that get through: they queue up and leave one by one.
        if served > 0:
            discharge = served / FLOW_RATE
            delay += served * (elapsed + discharge / 2.0)

        # Vehicles left behind: they wait for the next full cycle.
        delay += stuck * (elapsed + cyc)

        elapsed += greens[d] + PHASE_OVERHEAD

    return delay


def improvement(counts):
    """
    Percentage of waiting time saved versus a fixed timer.

    The fixed timer is compared honestly: it always runs ALL FOUR
    directions in the plain North-East-South-West order, because a
    fixed timer cannot skip an empty road or reorder its phases.
    """
    smart = total_waiting_time(counts, compute_green_times(counts),
                               phase_order(counts))
    dumb = total_waiting_time(counts, fixed_green_times(), list(ORDER))
    if dumb == 0:
        return 0.0, smart, dumb
    return (dumb - smart) / dumb * 100.0, smart, dumb


# -------------------------------------------------------------------
# Tests - proof that the rules hold and the idea actually works
# -------------------------------------------------------------------
def _test():
    scenarios = {
        "Empty junction":      {"North": 0,  "East": 0,  "South": 0, "West": 0},
        "Light, even":         {"North": 3,  "East": 3,  "South": 3, "West": 3},
        "Balanced, moderate":  {"North": 5,  "East": 5,  "South": 5, "West": 5},
        "Rush hour, one road": {"North": 20, "East": 1,  "South": 1, "West": 1},
        "Everything on North": {"North": 12, "East": 0,  "South": 0, "West": 0},
        "Two busy, two quiet": {"North": 9,  "East": 8,  "South": 1, "West": 0},
        "Gridlock everywhere": {"North": 18, "East": 16, "South": 15, "West": 20},
        "One car, one road":   {"North": 0,  "East": 0,  "South": 1, "West": 0},
    }

    head = " ".join(f"{d:>7}" for d in ORDER)
    print(f"{'Scenario':<22} {head}   cycle    saved")
    print("-" * 76)

    for name, counts in scenarios.items():
        g = compute_green_times(counts)
        pct, smart, dumb = improvement(counts)

        # Safety rules - these must NEVER fail
        for d in ORDER:
            if g[d] > 0:
                assert g[d] >= G_MIN - 1e-9, f"{name}: {d} below minimum green"
                assert g[d] <= G_MAX + 1e-9, f"{name}: {d} above maximum green"
            else:
                # A road may only be skipped if nobody is waiting on it.
                assert counts.get(d, 0) == 0, f"{name}: {d} SKIPPED WITH CARS"
        assert cycle_length(g) <= CYCLE_MAX + 1e-6, f"{name}: cycle too long"
        assert pct >= -1e-6, f"{name}: WORSE than a fixed timer ({pct:.1f}%)"
        assert any(g[d] > 0 for d in ORDER), f"{name}: no direction runs at all"

        times = " ".join(f"{g[d]:6.1f}s" for d in ORDER)
        print(f"{name:<22} {times}  {cycle_length(g):5.1f}s  {pct:6.1f}%")

    print("-" * 76)
    print(f"Switches:  PRIORITY_ORDER={PRIORITY_ORDER}   SKIP_EMPTY={SKIP_EMPTY}")
    print()
    print("All safety rules passed:")
    print(f"  - a running green is never below {G_MIN}s or above {G_MAX}s")
    print(f"  - a full cycle never exceeds {CYCLE_MAX}s")
    print("  - a road is only ever skipped when it has NO vehicles waiting")
    print("  - at least one direction always runs, so the lights never freeze")
    print("  - the adaptive system is never slower than the fixed timer")

    print()
    print("Phase order for 'Two busy, two quiet':",
          " -> ".join(phase_order(scenarios["Two busy, two quiet"])))


if __name__ == "__main__":
    _test()
