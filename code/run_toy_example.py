"""Solve the toy network and print a summary.

python -m run_toy_example (from the code directory)
"""

import math

from src.model import (
    active,
    blended_quality,
    cost_breakdown,
    delivered,
    flows,
    oversupply,
    solve,
    source_draws,
    status,
    total_cost,
)
from tests.scenarios import PH, toy


def as_ph(hydrogen_ion: float) -> float:
    """Invert the transform preprocessing applies, for reporting only."""
    return -math.log10(hydrogen_ion)


p = toy()
model, v = solve(p, msg=True)

for name, con in model.constraints.items():
    slack = con.value()
    if abs(slack) < 1e-7:
        print(f"binding: {name}")

print(f"\nStatus        {status(model)}")
print(f"Total cost    {total_cost(model):,.2f}")

print("\nCost breakdown")
for label, amount in cost_breakdown(p, v).items():
    print(f"  {label:<20} {amount:>10,.2f}")

print("\nSources")
draws = source_draws(p, v)
activated, _ = active(p, v)
for s in p.source_ids:
    marker = "on " if s in activated else "off"
    share = draws[s] / p.source_max_withdrawal[s] if p.source_max_withdrawal[s] else 0.0
    print(
        f"  {s:<6} {marker}  {draws[s]:>7.1f} ML/day"
        f"  of {p.source_max_withdrawal[s]:>7.1f} capacity ({share:>5.1%})"
        f"  at ${p.source_unit_cost[s]:.2f}/ML"
    )

print("\nZones")
received = delivered(p, v)
excess = oversupply(p, v)
for z in p.zone_ids:
    print(
        f"  {z:<6} {received[z]:>7.1f} delivered"
        f"  {p.demand_by_zone[z]:>7.1f} demanded"
        f"  {excess[z]:>+7.1f} oversupply"
    )

print("\nArc flows")
st, tz = flows(p, v)
for (source, plant), flow in st.items():
    if flow > 1e-6:
        print(f"  {source} -> {plant}  {flow:>7.1f} ML/day")
for (plant, zone), flow in tz.items():
    if flow > 1e-6:
        print(f"  {plant} -> {zone}  {flow:>7.1f} ML/day")

for plant, blend in blended_quality(p, v).items():
    print(f"\nBlend leaving {plant}")
    for q, value in blend.items():
        if q == PH:
            # Bounds are stored as hydrogen ion concentration, so inverting them
            # back to pH also swaps which one is the lower limit
            shown = as_ph(value)
            low, high = as_ph(p.quality_upper_bound[q]), as_ph(p.quality_lower_bound[q])
            label, unit = "pH", ""
        else:
            shown = value
            low, high = p.quality_lower_bound[q], p.quality_upper_bound[q]
            label, unit = q, p.quality_units[q]
        room = "" if low <= shown <= high else "  OUTSIDE LIMITS"
        print(
            f"  {label:<12} {shown:>8.2f}  limits {low:.2f} to {high:.2f} {unit}{room}"
        )
