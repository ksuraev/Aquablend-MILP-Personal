"""
Experimenting and building the AquaBlend network model in PuLP as defined in formulation.pdf.

Extended from the toy model in toy.py to include multiple plants, zones, and water quality parameters.

Imports a scenario JSON file (see toy_scenario.json) as input data, builds the MILP, solves it with HiGHS, and prints the results.
"""

import argparse
import json
import math
from dataclasses import dataclass, field
from typing import Any

import pulp


@dataclass
class Data:
    """Data class to hold the model data."""

    S: list
    T: list
    Z: list
    P: list
    st_arcs: list
    tz_arcs: list
    quality_in_source: dict
    max_source_withdrawal: dict
    min_source_withdrawal: dict
    min_plant_throughput: dict
    max_plant_throughput: dict
    source_activation_cost: dict
    plant_activation_cost: dict
    source_unit_cost: dict
    plant_unit_cost: dict
    max_flow_st: dict
    min_flow_st: dict
    max_flow_tz: dict
    min_flow_tz: dict
    quality_lower_bounds: dict
    quality_upper_bounds: dict
    quality_transform: dict
    demand: dict

    # Helper indexes: built once from the arcs
    sources_into: dict = field(init=False)
    zones_from: dict = field(init=False)
    plants_into: dict = field(init=False)

    def __post_init__(self):
        self.sources_into = {t: [s for s, tt in self.st_arcs if tt == t] for t in self.T}
        self.zones_from = {t: [z for tt, z in self.tz_arcs if tt == t] for t in self.T}
        self.plants_into = {z: [t for t, zz in self.tz_arcs if zz == z] for z in self.Z}


def load_data(path: str) -> Data:
    """Build a Data instance from a scenario JSON file (see toy_scenario.json)."""
    with open(path, "r", encoding="utf-8") as handle:
        scenario: dict[str, Any] = json.load(handle)

    sources = scenario["sources"]
    plants = scenario["plants"]
    zones = scenario["zones"]
    st_links = scenario["source_plant_links"]
    tz_links = scenario["plant_zone_links"]
    quality_limits = scenario["quality_limits"]

    # Sets
    S = [s["id"] for s in sources]
    T = [t["id"] for t in plants]
    Z = [z["id"] for z in zones]
    P = list(quality_limits.keys())

    # Source-to-plant and plant-to-zone arcs
    st_arcs = [(link["source"], link["plant"]) for link in st_links]
    tz_arcs = [(link["plant"], link["zone"]) for link in tz_links]

    # Source parameters
    max_source_withdrawal = {s["id"]: s["max_flow"] for s in sources}
    min_source_withdrawal = {s["id"]: s.get("min_flow", 0.0) for s in sources}
    source_activation_cost = {s["id"]: s.get("fixed_cost", 0.0) for s in sources}
    source_unit_cost = {s["id"]: s["unit_cost"] for s in sources}

    # Plant parameters
    min_plant_throughput = {t["id"]: t.get("min_flow", 0.0) for t in plants}
    max_plant_throughput = {t["id"]: t["max_flow"] for t in plants}
    plant_activation_cost = {t["id"]: t.get("fixed_cost", 0.0) for t in plants}
    plant_unit_cost = {t["id"]: t["unit_cost"] for t in plants}

    # Arc/link parameters
    max_flow_st = {(link["source"], link["plant"]): link["max_flow"] for link in st_links}
    min_flow_st = {(link["source"], link["plant"]): link.get("min_flow", 0.0) for link in st_links}
    max_flow_tz = {(link["plant"], link["zone"]): link["max_flow"] for link in tz_links}
    min_flow_tz = {(link["plant"], link["zone"]): link.get("min_flow", 0.0) for link in tz_links}

    # Source quality values and their bounds: keyed by the parameter names in quality_limits
    quality_in_source = {}
    quality_lower_bounds = {}
    quality_upper_bounds = {}
    quality_transform = {}

    for p, bounds in quality_limits.items():
        transform = bounds.get("transform", "identity")
        quality_transform[p] = transform
        lower, upper = bounds["min"], bounds["max"]

        if transform == "identity":
            quality_in_source[p] = {s["id"]: s["quality"][p] for s in sources}
            quality_lower_bounds[p], quality_upper_bounds[p] = lower, upper
        elif transform == "hydrogen_ion":
            # pH is logarithmic and doesn't blend linearly by volume, so stored as hydrogen-ion concentration - the bounds swap: higher pH means lower [H+].
            quality_in_source[p] = {s["id"]: 10 ** -s["quality"][p] for s in sources}
            quality_lower_bounds[p], quality_upper_bounds[p] = 10**-upper, 10**-lower
        else:
            raise ValueError(f"Unknown transform {transform!r} for quality parameter {p!r}.")

    # Demand per zone
    demand = {z["id"]: z["demand"] for z in zones}

    return Data(
        S=S,
        T=T,
        Z=Z,
        P=P,
        st_arcs=st_arcs,
        tz_arcs=tz_arcs,
        quality_in_source=quality_in_source,
        max_source_withdrawal=max_source_withdrawal,
        min_source_withdrawal=min_source_withdrawal,
        min_plant_throughput=min_plant_throughput,
        max_plant_throughput=max_plant_throughput,
        source_activation_cost=source_activation_cost,
        plant_activation_cost=plant_activation_cost,
        source_unit_cost=source_unit_cost,
        plant_unit_cost=plant_unit_cost,
        max_flow_st=max_flow_st,
        min_flow_st=min_flow_st,
        max_flow_tz=max_flow_tz,
        min_flow_tz=min_flow_tz,
        quality_lower_bounds=quality_lower_bounds,
        quality_upper_bounds=quality_upper_bounds,
        quality_transform=quality_transform,
        demand=demand,
    )


def build_model(data: Data) -> tuple[pulp.LpProblem, dict]:
    """Create decision variables, objective, and constraints. Returns the problem plus a dictionary of decision variables"""
    problem = pulp.LpProblem("AquaBlend_Toy", pulp.LpMinimize)

    # Maps directly to '2.3 Decision Variables' in formulation.pdf
    alpha = {s: pulp.LpVariable(f"alpha_{s}", cat="Binary") for s in data.S}
    a = {s: pulp.LpVariable(f"a_{s}", lowBound=0) for s in data.S}
    beta = {t: pulp.LpVariable(f"beta_{t}", cat="Binary") for t in data.T}
    gamma = {(s, t): pulp.LpVariable(f"gamma_{s}_{t}", cat="Binary") for s, t in data.st_arcs}
    b = {(s, t): pulp.LpVariable(f"b_{s}_{t}", lowBound=0) for s, t in data.st_arcs}
    delta = {(t, z): pulp.LpVariable(f"delta_{t}_{z}", cat="Binary") for t, z in data.tz_arcs}
    c = {(t, z): pulp.LpVariable(f"c_{t}_{z}", lowBound=0) for t, z in data.tz_arcs}

    # Objective: '4 Objective' in formulation.pdf
    problem += (
        pulp.lpSum(data.source_activation_cost[s] * alpha[s] for s in data.S)
        + pulp.lpSum(data.plant_activation_cost[t] * beta[t] for t in data.T)
        + pulp.lpSum(data.source_unit_cost[s] * a[s] for s in data.S)
        + pulp.lpSum(
            data.plant_unit_cost[t] * pulp.lpSum(b[(s, t)] for s in data.sources_into[t])
            for t in data.T
        )
    )

    # Demand satisfaction: eq (3)
    for z in data.Z:
        problem += (
            pulp.lpSum(c[(t, z)] for t in data.plants_into[z]) >= data.demand[z],
            f"demand_satisfaction_{z}",
        )

    # Source capacity and activation: eq (4)
    for s in data.S:
        problem += (
            a[s] <= data.max_source_withdrawal[s] * alpha[s],
            f"source_capacity_upper_{s}",
        )
        problem += (
            a[s] >= data.min_source_withdrawal[s] * alpha[s],
            f"source_capacity_lower_{s}",
        )

    # Plant capacity and activation: eq (5)
    for t in data.T:
        inflow = pulp.lpSum(b[(s, t)] for s in data.sources_into[t])
        problem += (
            inflow >= data.min_plant_throughput[t] * beta[t],
            f"min_plant_throughput_{t}",
        )
        problem += (
            inflow <= data.max_plant_throughput[t] * beta[t],
            f"max_plant_throughput_{t}",
        )

    # Plant flow conservation: eq (6)
    for t in data.T:
        problem += (
            pulp.lpSum(b[(s, t)] for s in data.sources_into[t])
            == pulp.lpSum(c[(t, z)] for z in data.zones_from[t]),
            f"plant_flow_conservation_{t}",
        )
    # Source flow conservation: eq (7)
    for s in data.S:
        st_targets = [t for ss, t in data.st_arcs if ss == s]
        problem += (
            a[s] == pulp.lpSum(b[(s, t)] for t in st_targets),
            f"source_flow_conservation_{s}",
        )

    # Source-to-plant and plant-to-zone flow bounds: eqs (8) and (9)
    for s, t in data.st_arcs:
        problem += (
            b[(s, t)] <= data.max_flow_st[(s, t)] * gamma[(s, t)],
            f"max_flow_st_{s}_{t}",
        )
        problem += (
            b[(s, t)] >= data.min_flow_st[(s, t)] * gamma[(s, t)],
            f"min_flow_st_{s}_{t}",
        )
    for t, z in data.tz_arcs:
        problem += (
            c[(t, z)] <= data.max_flow_tz[(t, z)] * delta[(t, z)],
            f"max_flow_tz_{t}_{z}",
        )
        problem += (
            c[(t, z)] >= data.min_flow_tz[(t, z)] * delta[(t, z)],
            f"min_flow_tz_{t}_{z}",
        )

    # Links require an active upstream node: eqs (10) and (11)
    for s, t in data.st_arcs:
        problem += gamma[(s, t)] <= alpha[s], f"link_activation_source_{s}_{t}"
    for t, z in data.tz_arcs:
        problem += delta[(t, z)] <= beta[t], f"link_activation_plant_{t}_{z}"

    # Water quality arriving at plant: eq (13)
    for t in data.T:
        inflow = pulp.lpSum(b[(s, t)] for s in data.sources_into[t])
        for p in data.P:
            loaded = pulp.lpSum(
                data.quality_in_source[p][s] * b[(s, t)] for s in data.sources_into[t]
            )
            problem += (
                loaded >= data.quality_lower_bounds[p] * inflow,
                f"{p}_quality_lower_{t}",
            )
            problem += (
                loaded <= data.quality_upper_bounds[p] * inflow,
                f"{p}_quality_upper_{t}",
            )

    variables = {
        "alpha": alpha,
        "a": a,
        "beta": beta,
        "gamma": gamma,
        "b": b,
        "delta": delta,
        "c": c,
    }
    return problem, variables


def solve(problem: pulp.LpProblem) -> tuple[str, float | None]:
    """Solve the problem and return the status and total cost (if optimal)."""
    problem.solve(pulp.HiGHS(msg=False))
    optimal = problem.status == pulp.LpStatusOptimal
    return pulp.LpStatus[problem.status], pulp.value(problem.objective) if optimal else None


def print_results(data: Data, variables: dict, status: str, total_cost: float | None) -> None:
    """Print the results of the optimisation purely for interpretation. Future: return output JSON instead (or in addition to)."""
    alpha, a, beta, b, c = (
        variables["alpha"],
        variables["a"],
        variables["beta"],
        variables["b"],
        variables["c"],
    )

    # Status and total cost
    print(f"Status: {status}")
    if total_cost is not None:
        print(f"Total cost: ${total_cost:.2f}/day\n")

    if status != "Optimal":
        return

    # Compute inflow (arriving at plant)
    inflow = {t: sum(b[(s, t)].value() for s in data.sources_into[t]) for t in data.T}

    # Print source and plant activation and flow
    for s in data.S:
        print(f"{s}: alpha={round(alpha[s].value())}  a={a[s].value():.1f} ML/day")
    for t in data.T:
        print(f"{t}: beta={round(beta[t].value())}  inflow={inflow[t]:.1f} ML/day")

    # Compute delivered volume (leaving plant to zone)
    delivered = {z: sum(c[(t, z)].value() for t in data.plants_into[z]) for z in data.Z}

    # Print flow volumes along arcs
    print("\nFlows:")
    for node_from, node_to in b:
        if b[(node_from, node_to)].value() > 1e-6:
            print(f"  {node_from} -> {node_to}: {b[(node_from, node_to)].value():.1f} ML/day")
    for node_from, node_to in c:
        if c[(node_from, node_to)].value() > 1e-6:
            print(f"  {node_from} -> {node_to}: {c[(node_from, node_to)].value():.1f} ML/day")

    # Cost breakdown: same three terms as the objective, computed separately to see which one is driving the cost
    print("\nCost breakdown:")
    activation_cost = sum(
        data.source_activation_cost[s] * round(alpha[s].value()) for s in data.S
    ) + sum(data.plant_activation_cost[t] * round(beta[t].value()) for t in data.T)
    drawing_cost = sum(data.source_unit_cost[s] * a[s].value() for s in data.S)
    treatment_cost = sum(data.plant_unit_cost[t] * inflow[t] for t in data.T)

    print(f"  Activation: ${activation_cost:,.2f}")
    print(f"  Drawing:    ${drawing_cost:,.2f}")
    print(f"  Treatment:  ${treatment_cost:,.2f}")

    # Print demand satisfaction and slack
    print("\nDemand:")
    for z in data.Z:
        print(
            f"  {z}: {data.demand[z]:.1f} required, {delivered[z]:.1f} delivered "
            f"({delivered[z] - data.demand[z]:+.1f} slack)"
        )

    # Compute and print blended water quality arriving at each active plant (1 in toy scenario)
    print("\nBlended quality arriving at each active plant:")
    for t in data.T:
        if inflow[t] < 1e-9:
            continue
        values = []
        for p in data.P:
            blended = (
                sum(data.quality_in_source[p][s] * b[(s, t)].value() for s in data.sources_into[t])
                / inflow[t]
            )
            lower, upper = data.quality_lower_bounds[p], data.quality_upper_bounds[p]
            if p == "pH":
                # Bounds are stored inverted (as hydrogen-ion concentration), so invert them back to pH for printing
                blended = -math.log10(blended)
                lower, upper = -math.log10(upper), -math.log10(lower)
            values.append(
                f"{p}={blended:.2f} (safe: {lower:.2f}-{upper:.2f})"
            )  # Append the safe range of each parameter
        print(f"  {t}: {', '.join(values)}")

    # Compute and print capacity utilisation of each active source
    print("\nCapacity utilisation (active sources only):")
    for s in data.S:
        utilisation = 100 * a[s].value() / data.max_source_withdrawal[s]
        drawn, capacity = a[s].value(), data.max_source_withdrawal[s]
        print(f"  {s}: {drawn:.1f} / {capacity:.1f} ML/day ({utilisation:.0f}%)")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build and solve from scenario JSON file",
    )
    parser.add_argument(
        "scenario",
        default="model/scenarios/toy_scenario.json",
        nargs="?",
        help="Path to a scenario JSON file.",
    )
    args = parser.parse_args()

    data = load_data(args.scenario)
    problem, variables = build_model(data)
    status, total_cost = solve(problem)
    print_results(data, variables, status, total_cost)


if __name__ == "__main__":
    main()
