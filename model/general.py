"""
Building the AquaBlend network model in PuLP as defined in formulation.pdf.

Extended from the toy model in toy.py to include multiple plants, zones, and water quality parameters.
"""

import math
from dataclasses import dataclass, field

import pulp


@dataclass
class NetworkData:
    """Data class to hold the network model data."""

    S: list
    T: list
    Z: list
    P: list
    st_arcs: list
    tz_arcs: list
    quality_in_source: dict
    max_source_withdrawal: dict
    min_plant_throughput: dict
    max_plant_throughput: dict
    S_activation_costs: dict
    T_activation_costs: dict
    S_unit_costs: dict
    T_unit_costs: dict
    max_flow_st: dict
    min_flow_st: dict
    max_flow_tz: dict
    min_flow_tz: dict
    quality_lower_bounds: dict
    quality_upper_bounds: dict
    demand: dict

    # Helper indexes, built once from the arcs
    sources_into: dict = field(init=False)
    zones_from: dict = field(init=False)
    plants_into: dict = field(init=False)

    def __post_init__(self):
        self.sources_into = {t: [s for s, tt in self.st_arcs if tt == t] for t in self.T}
        self.zones_from = {t: [z for tt, z in self.tz_arcs if tt == t] for t in self.T}
        self.plants_into = {z: [t for t, zz in self.tz_arcs if zz == z] for z in self.Z}


def build_model(data: NetworkData) -> tuple[pulp.LpProblem, dict]:
    """Create decision variables, objective, and constraints. Returns the
    problem plus a dict of the variable dicts."""
    problem = pulp.LpProblem("AquaBlend", pulp.LpMinimize)

    alpha = {s: pulp.LpVariable(f"alpha_{s}", cat="Binary") for s in data.S}
    a = {s: pulp.LpVariable(f"a_{s}", lowBound=0) for s in data.S}
    beta = {t: pulp.LpVariable(f"beta_{t}", cat="Binary") for t in data.T}
    gamma = {(s, t): pulp.LpVariable(f"gamma_{s}_{t}", cat="Binary") for s, t in data.st_arcs}
    b = {(s, t): pulp.LpVariable(f"b_{s}_{t}", lowBound=0) for s, t in data.st_arcs}
    delta = {(t, z): pulp.LpVariable(f"delta_{t}_{z}", cat="Binary") for t, z in data.tz_arcs}
    c = {(t, z): pulp.LpVariable(f"c_{t}_{z}", lowBound=0) for t, z in data.tz_arcs}

    # Objective
    problem += (
        pulp.lpSum(data.S_activation_costs[s] * alpha[s] for s in data.S)
        + pulp.lpSum(data.T_activation_costs[t] * beta[t] for t in data.T)
        + pulp.lpSum(data.S_unit_costs[s] * a[s] for s in data.S)
        + pulp.lpSum(data.T_unit_costs[t] * pulp.lpSum(b[(s, t)] for s in data.sources_into[t]) for t in data.T)
    )

    # Demand satisfaction
    for z in data.Z:
        problem += (
            pulp.lpSum(c[(t, z)] for t in data.plants_into[z]) >= data.demand[z],
            f"demand_satisfaction_{z}",
        )

    # Source capacity and activation
    for s in data.S:
        problem += a[s] <= data.max_source_withdrawal[s] * alpha[s], f"source_capacity_{s}"

    # Plant capacity and activation
    for t in data.T:
        inflow = pulp.lpSum(b[(s, t)] for s in data.sources_into[t])
        problem += inflow >= data.min_plant_throughput[t] * beta[t], f"min_plant_throughput_{t}"
        problem += inflow <= data.max_plant_throughput[t] * beta[t], f"max_plant_throughput_{t}"

    # Flow conservation
    for t in data.T:
        problem += (
            pulp.lpSum(b[(s, t)] for s in data.sources_into[t]) == pulp.lpSum(c[(t, z)] for z in data.zones_from[t]),
            f"plant_flow_conservation_{t}",
        )
    for s in data.S:
        st_targets = [t for ss, t in data.st_arcs if ss == s]
        problem += a[s] == pulp.lpSum(b[(s, t)] for t in st_targets), f"source_flow_conservation_{s}"

    # Link capacity and activation
    for s, t in data.st_arcs:
        problem += b[(s, t)] <= data.max_flow_st[(s, t)] * gamma[(s, t)], f"max_flow_st_{s}_{t}"
        problem += b[(s, t)] >= data.min_flow_st[(s, t)] * gamma[(s, t)], f"min_flow_st_{s}_{t}"
    for t, z in data.tz_arcs:
        problem += c[(t, z)] <= data.max_flow_tz[(t, z)] * delta[(t, z)], f"max_flow_tz_{t}_{z}"
        problem += c[(t, z)] >= data.min_flow_tz[(t, z)] * delta[(t, z)], f"min_flow_tz_{t}_{z}"

    # Links require an active upstream node
    for s, t in data.st_arcs:
        problem += gamma[(s, t)] <= alpha[s], f"link_activation_source_{s}_{t}"
    for t, z in data.tz_arcs:
        problem += delta[(t, z)] <= beta[t], f"link_activation_plant_{t}_{z}"

    # Water quality, per plant
    for t in data.T:
        inflow = pulp.lpSum(b[(s, t)] for s in data.sources_into[t])
        for p in data.P:
            loaded = pulp.lpSum(data.quality_in_source[p][s] * b[(s, t)] for s in data.sources_into[t])
            problem += loaded >= data.quality_lower_bounds[p] * inflow, f"{p}_quality_lower_{t}"
            problem += loaded <= data.quality_upper_bounds[p] * inflow, f"{p}_quality_upper_{t}"

    variables = {"alpha": alpha, "a": a, "beta": beta, "gamma": gamma, "b": b, "delta": delta, "c": c}
    return problem, variables


def solve(problem: pulp.LpProblem) -> tuple[str, float | None]:
    """Solve the problem and return the status and total cost (if optimal)."""
    problem.solve(pulp.HiGHS(msg=False))
    status = pulp.LpStatus[problem.status]
    total_cost = pulp.value(problem.objective) if status == "Optimal" else None
    return status, total_cost


def print_results(data: NetworkData, variables: dict, status: str, total_cost: float | None) -> None:
    """Print the results of the optimisation."""
    alpha, a, beta, b, c = (
        variables["alpha"],
        variables["a"],
        variables["beta"],
        variables["b"],
        variables["c"],
    )

    print(f"Status: {status}")
    if total_cost is not None:
        print(f"Total cost: ${total_cost:,.2f}/day\n")

    for s in data.S:
        print(f"{s}: alpha={round(alpha[s].value())}  a={a[s].value():.1f} ML/day")
    for t in data.T:
        inflow_value = sum(b[(s, t)].value() for s in data.sources_into[t])
        print(f"{t}: beta={round(beta[t].value())}  inflow={inflow_value:.1f} ML/day")

    if status != "Optimal":
        return

    print("\nFlows:")
    for (s, t), var in b.items():
        if var.value() > 1e-6:
            print(f"  {s} -> {t}: {var.value():.1f} ML/day")
    for (t, z), var in c.items():
        if var.value() > 1e-6:
            print(f"  {t} -> {z}: {var.value():.1f} ML/day")

    print("\nCost breakdown:")
    activation_cost = sum(data.S_activation_costs[s] * round(alpha[s].value()) for s in data.S) + sum(
        data.T_activation_costs[t] * round(beta[t].value()) for t in data.T
    )
    drawing_cost = sum(data.S_unit_costs[s] * a[s].value() for s in data.S)
    treatment_cost = sum(data.T_unit_costs[t] * sum(b[(s, t)].value() for s in data.sources_into[t]) for t in data.T)
    print(f"  Activation: ${activation_cost:,.2f}")
    print(f"  Drawing:    ${drawing_cost:,.2f}")
    print(f"  Treatment:  ${treatment_cost:,.2f}")

    print("\nDemand:")
    for z in data.Z:
        delivered = sum(c[(t, z)].value() for t in data.plants_into[z])
        print(
            f"  {z}: {data.demand[z]:.1f} required, {delivered:.1f} delivered "
            f"({delivered - data.demand[z]:+.1f} slack)"
        )

    print("\nBlended quality at each active plant:")
    for t in data.T:
        inflow_value = sum(b[(s, t)].value() for s in data.sources_into[t])
        if inflow_value > 1e-9:
            values = []
            for p in data.P:
                blended = (
                    sum(data.quality_in_source[p][s] * b[(s, t)].value() for s in data.sources_into[t]) / inflow_value
                )
                if p == "pH":
                    blended = -math.log10(blended)
                values.append(f"{p}={blended:.2f}")
            print(f"  {t}: {', '.join(values)}")

    print("\nCapacity utilisation (active sources only):")
    for s in data.S:
        if round(alpha[s].value()) == 1:
            utilisation = 100 * a[s].value() / data.max_source_withdrawal[s]
            print(f"  {s}: {a[s].value():.1f} / {data.max_source_withdrawal[s]:.1f} " f"ML/day ({utilisation:.0f}%)")


def main() -> None:
    # Populate network data with example values
    data = NetworkData(
        S=["s1", "s2", "s3"],
        T=["t1", "t2"],
        Z=["z1", "z2"],
        P=["alkalinity", "pH", "turbidity"],
        st_arcs=[("s1", "t1"), ("s1", "t2"), ("s2", "t1"), ("s2", "t2"), ("s3", "t1"), ("s3", "t2")],
        tz_arcs=[("t1", "z1"), ("t1", "z2"), ("t2", "z1"), ("t2", "z2")],
        quality_in_source={
            "alkalinity": {"s1": 50.0, "s2": 60.0, "s3": 70.0},
            "pH": {"s1": 10**-7.0, "s2": 10**-6.5, "s3": 10**-6.0},
            "turbidity": {"s1": 0.5, "s2": 1.0, "s3": 2.0},
        },
        max_source_withdrawal={"s1": 350.0, "s2": 300.0, "s3": 300.0},
        min_plant_throughput={"t1": 100.0, "t2": 150.0},
        max_plant_throughput={"t1": 400.0, "t2": 500.0},
        S_activation_costs={"s1": 100.0, "s2": 50.0, "s3": 10.0},
        T_activation_costs={"t1": 200.0, "t2": 150.0},
        S_unit_costs={"s1": 50.0, "s2": 80.0, "s3": 120.0},
        T_unit_costs={"t1": 64.0, "t2": 70.0},
        max_flow_st={
            ("s1", "t1"): 200.0,
            ("s1", "t2"): 150.0,
            ("s2", "t1"): 100.0,
            ("s2", "t2"): 200.0,
            ("s3", "t1"): 150.0,
            ("s3", "t2"): 100.0,
        },
        min_flow_st={
            key: 0.0
            for key in [
                ("s1", "t1"),
                ("s1", "t2"),
                ("s2", "t1"),
                ("s2", "t2"),
                ("s3", "t1"),
                ("s3", "t2"),
            ]
        },
        max_flow_tz={("t1", "z1"): 250.0, ("t1", "z2"): 200.0, ("t2", "z1"): 150.0, ("t2", "z2"): 300.0},
        min_flow_tz={key: 0.0 for key in [("t1", "z1"), ("t1", "z2"), ("t2", "z1"), ("t2", "z2")]},
        quality_lower_bounds={"alkalinity": 20.0, "pH": 10**-8.5, "turbidity": 0.0},
        quality_upper_bounds={"alkalinity": 100.0, "pH": 10**-6.5, "turbidity": 5.0},
        demand={"z1": 300.0, "z2": 400.0},
    )

    problem, variables = build_model(data)
    status, total_cost = solve(problem)
    print_results(data, variables, status, total_cost)


if __name__ == "__main__":
    main()
