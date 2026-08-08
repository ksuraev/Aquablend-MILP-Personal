"""Solve different scenarios and print a summary.

python -m run_scenarios          (from the code directory)
python -m run_scenarios toy      (just one, by name)
"""

from __future__ import annotations

import math
import shutil
import sys
from dataclasses import replace

from src.contracts import ModelParameters
from src.model import (
    blended_quality,
    cost_breakdown,
    delivered,
    flows,
    is_optimal,
    oversupply,
    solve,
    source_draws,
    status,
    total_cost,
)
from tests.scenarios import ALK, PH, TURB, ph_to_mol_l, toy, two_plants

# Just nice terminal printing things
WIDTH = shutil.get_terminal_size(fallback=(74, 24)).columns

_COLOUR = sys.stdout.isatty()
RED = "\033[1;31m" if _COLOUR else ""
RESET = "\033[0m" if _COLOUR else ""


def describe(p: ModelParameters) -> None:
    """Print the inputs, so the decisions below can be read against them."""
    for s in p.source_ids:
        ph = -math.log10(p.source_quality[(s, PH)])
        print(
            f"  {s:<4} ${p.source_unit_cost[s]:.2f}/ML  fixed ${p.source_fixed_cost[s]:>5.0f}"
            f"  draw [{p.source_min_withdrawal[s]:.0f}, {p.source_max_withdrawal[s]:.0f}]"
            f"  pH {ph:.2f}  alk {p.source_quality[(s, ALK)]:5.1f}"
            f"  turb {p.source_quality[(s, TURB)]:4.1f}"
        )
    for t in p.plant_ids:
        print(
            f"  {t:<4} ${p.plant_unit_treatment_cost[t]:.2f}/ML"
            f"  fixed ${p.plant_fixed_cost[t]:>5.0f}"
            f"  throughput [{p.plant_min_throughput[t]:.0f},"
            f" {p.plant_max_throughput[t]:.0f}]"
        )
    print("  demand " + "  ".join(f"{z} {p.demand_by_zone[z]:.0f}" for z in p.zone_ids))
    print(
        f"  limits pH [{-math.log10(p.quality_upper_bound[PH]):.2f},"
        f" {-math.log10(p.quality_lower_bound[PH]):.2f}]"
        f"  alk [{p.quality_lower_bound[ALK]:.0f}, {p.quality_upper_bound[ALK]:.0f}]"
        f"  turb [{p.quality_lower_bound[TURB]:.0f}, {p.quality_upper_bound[TURB]:.0f}]"
    )
    priced = {
        **{k: x for k, x in p.source_plant_transfer_cost.items() if x},
        **{k: x for k, x in p.plant_zone_transfer_cost.items() if x},
    }
    if priced:
        print("  arcs   " + "  ".join(f"{a}->{b} ${x:.2f}" for (a, b), x in priced.items()))


def show(p: ModelParameters, title: str, note: str = "") -> None:
    """Solve one scenario and print the inputs, then the decisions."""
    print("\n" + "=" * WIDTH)
    print(title)
    if note:
        print(note)
    print("=" * WIDTH)

    print("inputs")
    describe(p)
    print()

    model, v = solve(p)
    print(f"status        {status(model)}")

    if not is_optimal(model):
        print("no feasible blend exists for this scenario")
        return

    print(f"total cost    {total_cost(model):,.2f}")
    for label, amount in cost_breakdown(p, v).items():
        print(f"  {label:<20} {amount:>10,.2f}")

    draws = source_draws(p, v)
    print("\ndraws         " + "  ".join(f"{s} {draws[s]:6.1f}" for s in p.source_ids))

    st, tz = flows(p, v)
    used = [f"{a}->{b} {x:.1f}" for (a, b), x in {**st, **tz}.items() if x > 1e-6]
    print("flows         " + "  ".join(used))

    got, extra = delivered(p, v), oversupply(p, v)
    print(
        "delivered     "
        + "  ".join(
            f"{z} {got[z]:.1f} of {p.demand_by_zone[z]:.1f} ({extra[z]:+.1f})" for z in p.zone_ids
        )
    )

    for plant, blend in blended_quality(p, v).items():
        ph = -math.log10(blend[PH])
        low = -math.log10(p.quality_upper_bound[PH])
        high = -math.log10(p.quality_lower_bound[PH])
        reading = f"pH {ph:5.2f} [{low:.2f}, {high:.2f}]"
        if not low <= ph <= high:
            reading = f"{RED}{reading}{RESET}"
        print(
            f"blend at {plant:<4} {reading}"
            f"   alkalinity {blend[ALK]:6.1f} [{p.quality_lower_bound[ALK]:.0f},"
            f" {p.quality_upper_bound[ALK]:.0f}]"
            f"   turbidity {blend[TURB]:5.2f} [{p.quality_lower_bound[TURB]:.0f},"
            f" {p.quality_upper_bound[TURB]:.0f}]"
        )


# Each entry matches one test in tests/test_model.py.
SCENARIOS = {
    "toy": lambda: (
        toy(),
        "toy: three sources, one plant, one zone",
        "S1 is cheapest but too low in alkalinity to use alone so a blend is forced",
    ),
    "min-withdrawal": lambda: (
        replace(
            toy(),
            source_min_withdrawal={"S1": 80.0, "S2": 0.0, "S3": 0.0},
            plant_max_throughput={"T1": 100.0},
        ),
        "S1 has a minimum withdrawal of 80 ML",
        "alkalinity caps S1 at 75, so 80 is unreachable and S1 is dropped entirely",
    ),
    "plant-minimum": lambda: (
        replace(toy(), plant_min_throughput={"T1": 150.0}),
        "plant minimum of 150 ML against demand of 100 ML",
        "demand is a lower bound, so the extra 50 ML is oversupplied",
    ),
    "all-high-turbidity": lambda: (
        replace(
            toy(),
            source_quality={
                **toy().source_quality,
                **{(s, TURB): 9.0 for s in toy().source_ids},
            },
        ),
        "every source at 9 NTU against a limit of 5",
        "a blend is a weighted average, so no mix of these works and the model is infeasible",
    ),
    "arcs-free": lambda: (
        two_plants(),
        "two plants, every arc transfer is free",
        "nothing distinguishes the plants, so the solver picks either",
    ),
    "arcs-priced": lambda: (
        replace(
            two_plants(),
            source_plant_transfer_cost={
                ("S1", "T1"): 0.20,
                ("S1", "T2"): 5.00,
                ("S2", "T1"): 5.00,
                ("S2", "T2"): 0.20,
            },
            plant_zone_transfer_cost=dict.fromkeys(two_plants().plant_zone_arcs, 0.30),
        ),
        "two plants, each source has one cheap arc and one expensive one",
        "routing follows the cheap arcs; 100 ML x (0.20 + 0.30) = 50.00 transfer",
    ),
    "ph-mol": lambda: (
        replace(
            toy(),
            source_quality={
                **toy().source_quality,
                **{(s, PH): ph_to_mol_l(8.6) for s in toy().source_ids},
            },
            quality_lower_bound={**toy().quality_lower_bound, ALK: 0.0},
        ),
        "every source at pH 8.6 against a limit of 8.5, carried in mol/L",
        "accepted: the bound is 3.16e-9 and HiGHS ignores violations below 1e-7",
    ),
}


def main() -> None:
    wanted = sys.argv[1:] or list(SCENARIOS)
    for name in wanted:
        if name not in SCENARIOS:
            print(f"unknown scenario {name!r}; choose from {', '.join(SCENARIOS)}")
            continue
        show(*SCENARIOS[name]())
    print()


if __name__ == "__main__":
    main()
