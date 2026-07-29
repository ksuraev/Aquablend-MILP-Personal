"""
Building the AquaBlend network model in PuLP as defined in formulation.pdf.

Extended from the toy model in toy.py to include multiple plants, zones, and water quality parameters.
"""

import math

import pulp

# Sources, treatment plants, zones, and water quality parameters
S = ["s1", "s2", "s3"]
T = ["t1", "t2"]
Z = ["z1", "z2"]
P = ["alkalinity", "pH", "turbidity"]

quality_in_source = {
    "alkalinity": {"s1": 50.0, "s2": 60.0, "s3": 70.0},  # mg/L CaCO3
    "pH": {"s1": 10**-7.0, "s2": 10**-6.5, "s3": 10**-6.0},  # mol/L
    "turbidity": {"s1": 0.5, "s2": 1.0, "s3": 2.0},  # NTU
}

# Arcs between sources and treatment plants, and between treatment plants and zones
st_arcs = [
    ("s1", "t1"),
    ("s1", "t2"),
    ("s2", "t1"),
    ("s2", "t2"),
    ("s3", "t1"),
    ("s3", "t2"),
]
tz_arcs = [("t1", "z1"), ("t1", "z2"), ("t2", "z1"), ("t2", "z2")]

max_source_withdrawal = {"s1": 350.0, "s2": 300.0, "s3": 300.0}  # W̅_s : ML/day cap

# Minimum and maximum throughput for each treatment plant (ML/day)
min_plant_throughput = {"t1": 100.0, "t2": 150.0}  # V̲_t: ML/day
max__plant_throughput = {"t1": 400.0, "t2": 500.0}  # V̅_t : ML/day

# Fixed costs for sources and treatment plants
S_activation_costs = {"s1": 100.0, "s2": 50.0, "s3": 10.0}  # F_s : $/day to activate
T_activation_costs = {"t1": 200.0, "t2": 150.0}  # F_t : $/day to activate

# Unit costs for sources and treatment plants
S_unit_costs = {"s1": 50.0, "s2": 80.0, "s3": 120.0}  # C_s : $/ML drawn
T_unit_costs = {"t1": 64.0, "t2": 70.0}  # C_t : $/ML treated

# Link flow capacity between sources and treatment plants (ML/day)
max_flow_st = {
    ("s1", "t1"): 200.0,
    ("s1", "t2"): 150.0,
    ("s2", "t1"): 100.0,
    ("s2", "t2"): 200.0,
    ("s3", "t1"): 150.0,
    ("s3", "t2"): 100.0,
}  # L̅_st : ML/day
min_flow_st = {
    ("s1", "t1"): 0.0,
    ("s1", "t2"): 0.0,
    ("s2", "t1"): 0.0,
    ("s2", "t2"): 0.0,
    ("s3", "t1"): 0.0,
    ("s3", "t2"): 0.0,
}  # L̲_st : ML/day

# Link flow capacity between treatment plants and zones (ML/day)
max_flow_tz = {
    ("t1", "z1"): 250.0,
    ("t1", "z2"): 200.0,
    ("t2", "z1"): 150.0,
    ("t2", "z2"): 300.0,
}  # L̅_tz : ML/day

min_flow_tz = {
    ("t1", "z1"): 0.0,
    ("t1", "z2"): 0.0,
    ("t2", "z1"): 0.0,
    ("t2", "z2"): 0.0,
}  # L̲_tz : ML/day

quality_upper_bounds = {
    "alkalinity": 100.0,  # mg/L CaCO3
    "pH": 10**-6.5,  # mol/L
    "turbidity": 5.0,  # NTU
}

quality_lower_bounds = {
    "alkalinity": 20.0,  # mg/L CaCO3
    "pH": 10**-8.5,  # mol/L
    "turbidity": 0.0,  # NTU
}

demand = {"z1": 300.0, "z2": 400.0}  # D_z : ML/day the zone needs

problem = pulp.LpProblem("AquaBlend", pulp.LpMinimize)

# Decision variables
alpha = {s: pulp.LpVariable(f"alpha_{s}", cat="Binary") for s in S}  # alpha_s: "is source s on?"
a = {s: pulp.LpVariable(f"a_{s}", lowBound=0) for s in S}  # a_s: "how much to draw from source s?"
beta = {t: pulp.LpVariable(f"beta_{t}", cat="Binary") for t in T}  # beta_t: "is treatment plant t on?"
gamma = {
    (s, t): pulp.LpVariable(f"gamma_{s}_{t}", cat="Binary") for (s, t) in st_arcs
}  # gamma_st: "is link from source s to treatment plant t on?"
b = {
    (s, t): pulp.LpVariable(f"b_{s}_{t}", lowBound=0) for (s, t) in st_arcs
}  # b_st: "flow from source s to treatment plant t"
delta = {
    (t, z): pulp.LpVariable(f"delta_{t}_{z}", cat="Binary") for (t, z) in tz_arcs
}  # delta_tz: "is link from treatment plant t to zone z on?"
c = {
    (t, z): pulp.LpVariable(f"c_{t}_{z}", lowBound=0) for (t, z) in tz_arcs
}  # c_tz: "flow from treatment plant t to zone z"

# Objective function
problem += (
    pulp.lpSum(S_activation_costs[s] * alpha[s] for s in S)
    + pulp.lpSum(T_activation_costs[t] * beta[t] for t in T)
    + pulp.lpSum(S_unit_costs[s] * a[s] for s in S)
    + pulp.lpSum(T_unit_costs[t] * pulp.lpSum(b[(s, t)] for s in S if (s, t) in st_arcs) for t in T)
)

# Constraints

# Demand satisfaction: the total flow to each zone must meet its demand
for z in Z:
    problem += (
        pulp.lpSum(c[(t, z)] for t in T if (t, z) in tz_arcs) >= demand[z],
        f"demand_satisfaction_{z}",
    )

# Source capacity and activation
for s in S:
    problem += a[s] <= max_source_withdrawal[s] * alpha[s], f"source_capacity_{s}"

# Plant capacity and activation
for t in T:
    problem += (
        pulp.lpSum(b[(s, t)] for s in S if (s, t) in st_arcs) >= min_plant_throughput[t] * beta[t],
        f"min_plant_throughput_{t}",
    )
    problem += (
        pulp.lpSum(b[(s, t)] for s in S if (s, t) in st_arcs) <= max__plant_throughput[t] * beta[t],
        f"max_plant_throughput_{t}",
    )

# Plant flow conservation
for t in T:
    problem += (
        pulp.lpSum(b[(s, t)] for s in S if (s, t) in st_arcs) == pulp.lpSum(c[(t, z)] for z in Z if (t, z) in tz_arcs),
        f"plant_flow_conservation_{t}",
    )

# Source flow conservation
for s in S:
    problem += (
        a[s] == pulp.lpSum(b[(s, t)] for t in T if (s, t) in st_arcs),
        f"source_flow_conservation_{s}",
    )

# Source to treatment plant link capacity and activation
for s, t in st_arcs:
    problem += b[(s, t)] <= max_flow_st[(s, t)] * gamma[(s, t)], f"max_flow_st_{s}_{t}"
    problem += b[(s, t)] >= min_flow_st[(s, t)] * gamma[(s, t)], f"min_flow_st_{s}_{t}"

# Treatment plant to zone link capacity and activation
for t, z in tz_arcs:
    problem += c[(t, z)] <= max_flow_tz[(t, z)] * delta[(t, z)], f"max_flow_tz_{t}_{z}"
    problem += c[(t, z)] >= min_flow_tz[(t, z)] * delta[(t, z)], f"min_flow_tz_{t}_{z}"

# Links require active node upstream
for s, t in st_arcs:
    problem += gamma[(s, t)] <= alpha[s], f"link_activation_source_{s}_{t}"
for t, z in tz_arcs:
    problem += delta[(t, z)] <= beta[t], f"link_activation_plant_{t}_{z}"

# Water quality
for t in T:
    inflow = pulp.lpSum(b[(s, t)] for s in S if (s, t) in st_arcs)
    for p in P:
        loaded = pulp.lpSum(quality_in_source[p][s] * b[(s, t)] for s in S if (s, t) in st_arcs)
        problem += loaded >= quality_lower_bounds[p] * inflow, f"{p}_quality_lower_{t}"
        problem += loaded <= quality_upper_bounds[p] * inflow, f"{p}_quality_upper_{t}"

# Solve the problem
solver = pulp.HiGHS(msg=False)
problem.solve(solver)
status = pulp.LpStatus[problem.status]
total_cost = pulp.value(problem.objective) if status == "Optimal" else None

# Helper indexes: for each plant, which sources feed it / which zones it
# feeds. Built once from the arc lists.
sources_into = {t: [s for s, tt in st_arcs if tt == t] for t in T}
zones_from = {t: [z for tt, z in tz_arcs if tt == t] for t in T}
plants_into = {z: [t for t, zz in tz_arcs if zz == z] for z in Z}

print(f"Status: {status}")
if total_cost is not None:
    print(f"Total cost: ${total_cost:,.2f}/day\n")

for s in S:
    print(f"{s}: alpha={round(alpha[s].value())}  a={a[s].value():.1f} ML/day")
for t in T:
    inflow_value = sum(b[(s, t)].value() for s in sources_into[t])
    print(f"{t}: beta={round(beta[t].value())}  inflow={inflow_value:.1f} ML/day")

if status == "Optimal":
    print("\nFlows:")
    for (s, t), var in b.items():
        if var.value() > 1e-6:
            print(f"  {s} -> {t}: {var.value():.1f} ML/day")
    for (t, z), var in c.items():
        if var.value() > 1e-6:
            print(f"  {t} -> {z}: {var.value():.1f} ML/day")

    print("\nCost breakdown:")
    activation_cost = sum(S_activation_costs[s] * round(alpha[s].value()) for s in S) + sum(
        T_activation_costs[t] * round(beta[t].value()) for t in T
    )
    drawing_cost = sum(S_unit_costs[s] * a[s].value() for s in S)
    treatment_cost = sum(T_unit_costs[t] * sum(b[(s, t)].value() for s in sources_into[t]) for t in T)
    print(f"  Activation: ${activation_cost:,.2f}")
    print(f"  Drawing:    ${drawing_cost:,.2f}")
    print(f"  Treatment:  ${treatment_cost:,.2f}")

    print("\nDemand:")
    for z in Z:
        delivered = sum(c[(t, z)].value() for t in plants_into[z])
        print(f"  {z}: {demand[z]:.1f} required, {delivered:.1f} delivered " f"({delivered - demand[z]:+.1f} slack)")

    print("\nBlended quality at each active plant:")
    for t in T:
        inflow_value = sum(b[(s, t)].value() for s in sources_into[t])
        if inflow_value > 1e-9:
            values = []
            for p in P:
                blended = sum(quality_in_source[p][s] * b[(s, t)].value() for s in sources_into[t]) / inflow_value
                if p == "pH":
                    # stored as [H+]; convert back to the human-readable pH scale
                    blended = -math.log10(blended)
                values.append(f"{p}={blended:.2f}")
            print(f"  {t}: {', '.join(values)}")

    print("\nCapacity utilisation (active sources only):")
    for s in S:
        if round(alpha[s].value()) == 1:
            utilisation = 100 * a[s].value() / max_source_withdrawal[s]
            print(f"  {s}: {a[s].value():.1f} / {max_source_withdrawal[s]:.1f} ML/day ({utilisation:.0f}%)")
