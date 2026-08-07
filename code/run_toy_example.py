"""Solve the toy network and print a summary.

python -m run_toy_example (from the code directory)
"""

import math

from src.model import (
    active,
    blended_quality,
    delivered,
    oversupply,
    solve,
    source_draws,
    status,
    total_cost,
)
from tests.scenarios import PH, toy

p = toy()
model, v = solve(p)

print("Status      ", status(model))
print("Total cost  ", total_cost(model))
print("Draws       ", {k: round(x, 2) for k, x in source_draws(p, v).items()})
print("Active      ", active(p, v))
print("Delivered   ", delivered(p, v))
print("Oversupply  ", oversupply(p, v))

blend = blended_quality(p, v)["T1"]
print(blend)
print("Blend at plant      ", {q: f"{x:.4g}" for q, x in blend.items()})
print("Transformed pH      ", round(-math.log10(blend[PH]), 3))
