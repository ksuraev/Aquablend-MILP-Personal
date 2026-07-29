"""
Building the AquaBlend toy model in PuLP and solving it with HiGHS before generalising to the network model.

Toy model: 3 sources, 1 plant, 3 water quality parameters
"""

import pulp

sources = ["s1", "s2", "s3"]

source_activation_cost = {
    "s1": 100.0,
    "s2": 50.0,
    "s3": 10.0,
}  # F_s : $/day to activate
source_unit_cost = {"s1": 50.0, "s2": 80.0, "s3": 120.0}  # C_s : $/ML drawn
max_withdrawal = {"s1": 350.0, "s2": 300.0, "s3": 300.0}  # W_s : ML/day cap

treatment_cost_per_ml = 64.0  # C_t : the one plant's $/ML treatment cost
demand = 500.0  # D_z : ML/day the one zone needs

# Alkalinity (mg/L CaCO3) for each source and the lower/upper bounds
alkalinity = {"s1": 50.0, "s2": 60.0, "s3": 70.0}
alkalinity_lower = 20.0
alkalinity_upper = 100.0

# pH (hydrogen ion concentration in mol/L) for each source and the lower/upper bounds
pH_hydrogen_conc = {"s1": 10**-7.0, "s2": 10**-6.5, "s3": 10**-6.0}
pH_hydrogen_conc_lower = 10**-8.5
pH_hydrogen_conc_upper = 10**-6.5

# Turbidity (NTU) for each source and the lower/upper bounds
turbidity = {"s1": 0.5, "s2": 1.0, "s3": 2.0}
turbidity_lower = 0.0
turbidity_upper = 5.0

# Create a new LP problem instance
prob = pulp.LpProblem("toy", pulp.LpMinimize)


# Decision variables: alpha_s (binary) and a_s (continuous)
# Dict {s: pulp.LpVariable(...) for s in sources} gives you one variable per source, then reference by name (alpha["s1"])
alpha = {
    s: pulp.LpVariable(f"alpha_{s}", cat="Binary") for s in sources
}  # alpha_s: "is source s turned on?"
a = {
    s: pulp.LpVariable(f"a_{s}", lowBound=0) for s in sources
}  # a_s: "how much do we draw from source s?"


# Objective
# `prob += expression` is how you attach something to the problem
prob += (
    pulp.lpSum(source_activation_cost[s] * alpha[s] for s in sources)
    + pulp.lpSum(source_unit_cost[s] * a[s] for s in sources)
    + treatment_cost_per_ml * pulp.lpSum(a[s] for s in sources)
), "total_cost"


# Constraints
# Demand satisfaction: everything drawn goes to the one zone, so the total draw must meet demand
prob += pulp.lpSum(a[s] for s in sources) >= demand, "demand_satisfaction"

# Source capacity and activation
for s in sources:
    prob += a[s] <= max_withdrawal[s] * alpha[s], f"capacity_{s}"

# Water quality: in "load form"
total_draw = pulp.lpSum(a[s] for s in sources)

blended_alkalinity = pulp.lpSum(alkalinity[s] * a[s] for s in sources)
prob += blended_alkalinity >= alkalinity_lower * total_draw, "alk_quality_lower"
prob += blended_alkalinity <= alkalinity_upper * total_draw, "alk_quality_upper"

blended_hydrogen_conc = pulp.lpSum(pH_hydrogen_conc[s] * a[s] for s in sources)
prob += (
    blended_hydrogen_conc >= pH_hydrogen_conc_lower * total_draw,
    "hyd_quality_lower",
)
prob += (
    blended_hydrogen_conc <= pH_hydrogen_conc_upper * total_draw,
    "hyd_quality_upper",
)

blended_turbidity = pulp.lpSum(turbidity[s] * a[s] for s in sources)
prob += blended_turbidity >= turbidity_lower * total_draw, "turb_quality_lower"
prob += blended_turbidity <= turbidity_upper * total_draw, "turb_quality_upper"


# Solve
prob.solve(pulp.HiGHS(msg=False))


# Results
print(f"Status: {pulp.LpStatus[prob.status]}")
print(f"Total cost: ${pulp.value(prob.objective):,.2f}/day\n")

for s in sources:
    print(f"{s}: alpha={alpha[s].value():.0f}  a={a[s].value():.1f} ML/day")

if pulp.LpStatus[prob.status] == "Optimal":

    # Cost breakdown: same three terms as the objective, computed separately to see which one is driving the cost
    activation_cost = sum(
        source_activation_cost[s] * round(alpha[s].value()) for s in sources
    )
    drawing_cost = sum(source_unit_cost[s] * a[s].value() for s in sources)
    treatment_cost = treatment_cost_per_ml * sum(a[s].value() for s in sources)

    print("\nCost breakdown:")
    print(f"  Source activation: ${activation_cost:,.2f}")
    print(f"  Drawing water:     ${drawing_cost:,.2f}")
    print(f"  Treatment:         ${treatment_cost:,.2f}")

    # Check if demand was met and how much slack there was (if any)
    total_drawn = sum(a[s].value() for s in sources)
    print(
        f"\nDemand: {demand:.1f} ML/day required, {total_drawn:.1f} ML/day drawn "
        f"({total_drawn - demand:+.1f} slack)"
    )

    # Blended water quality actually achieved
    if total_drawn > 1e-9:
        blended_alkalinity_value = (
            sum(alkalinity[s] * a[s].value() for s in sources) / total_drawn
        )
        print(
            f"\nBlended alkalinity: {blended_alkalinity_value:.1f} mg/L CaCO3 "
            f"(bounds: {alkalinity_lower:.1f}-{alkalinity_upper:.1f})"
        )
        blended_hydrogen_conc_value = (
            sum(pH_hydrogen_conc[s] * a[s].value() for s in sources) / total_drawn
        )
        print(
            f"Blended hydrogen ion concentration: {blended_hydrogen_conc_value:.2e} mol/L "
            f"(bounds: {pH_hydrogen_conc_lower:.2e}-{pH_hydrogen_conc_upper:.2e})"
        )
        blended_turbidity_value = (
            sum(turbidity[s] * a[s].value() for s in sources) / total_drawn
        )
        print(
            f"Blended turbidity: {blended_turbidity_value:.1f} NTU "
            f"(bounds: {turbidity_lower:.1f}-{turbidity_upper:.1f})"
        )

    # Capacity utilisation: how much of each source's capacity was used, expressed as a percentage
    print("\nCapacity utilisation (active sources only):")
    for s in sources:
        if round(alpha[s].value()) == 1:
            utilisation = 100 * a[s].value() / max_withdrawal[s]
            print(
                f"  {s}: {a[s].value():.1f} / {max_withdrawal[s]:.1f} ML/day ({utilisation:.0f}%)"
            )
