"""General network MILP, built from ModelParameters.

Implements the network formulation in docs/formulation.tex.

This module builds variables and constraints. Does no validation, no filtering and no
unit transformation, because preprocessing has already done all three.

No result type as there is no agreed results contract yet. ``solve`` returns the solved
problem alongside the variables, and the readers at the bottom are convenience only.
"""

from __future__ import annotations

from typing import Any

import pulp
from src.contracts import ModelParameters


def build_model(p: ModelParameters) -> tuple[pulp.LpProblem, dict[str, Any]]:
    """Build the MILP from the formulation in docs/formulation.tex.

    Return the model and a dict of the decision variables.
    """
    model = pulp.LpProblem("AquaBlend", pulp.LpMinimize)

    # ============== Decision Variables (section 2.3) ==============

    # αₛ ∈ {0,1}, if source s is activated
    alpha = {s: model.add_variable(f"alpha_{s}", cat=pulp.LpBinary) for s in p.source_ids}

    # aₛ ≥ 0, volume drawn from source s
    a = {s: model.add_variable(f"a_{s}", lowBound=0) for s in p.source_ids}

    # βₜ ∈ {0,1}, if plant t is activated
    beta = {t: model.add_variable(f"beta_{t}", cat=pulp.LpBinary) for t in p.plant_ids}

    # γₛₜ ∈ {0,1}, if source s sends water to plant t
    gamma = {
        k: model.add_variable(f"gamma_{k[0]}_{k[1]}", cat=pulp.LpBinary)
        for k in p.source_plant_arcs
    }

    # bₛₜ ≥ 0, volume of water from source s to plant t
    b = {k: model.add_variable(f"b_{k[0]}_{k[1]}", lowBound=0) for k in p.source_plant_arcs}

    # δₜz ∈ {0,1}, if plant t sends water to demand zone z
    delta = {
        k: model.add_variable(f"delta_{k[0]}_{k[1]}", cat=pulp.LpBinary) for k in p.plant_zone_arcs
    }

    # cₜz ≥ 0, volume of water from plant t to demand zone z
    c = {k: model.add_variable(f"c_{k[0]}_{k[1]}", lowBound=0) for k in p.plant_zone_arcs}

    # Adjacency lists for convenience, so we don't have to filter the arcs repeatedly in constraints
    arcs_into_plant = {t: [k for k in p.source_plant_arcs if k[1] == t] for t in p.plant_ids}
    arcs_from_plant = {t: [k for k in p.plant_zone_arcs if k[0] == t] for t in p.plant_ids}
    arcs_into_zone = {z: [k for k in p.plant_zone_arcs if k[1] == z] for z in p.zone_ids}
    arcs_from_source = {s: [k for k in p.source_plant_arcs if k[0] == s] for s in p.source_ids}

    # Volume arriving at each plant
    inflow = {t: pulp.lpSum(b[k] for k in arcs_into_plant[t]) for t in p.plant_ids}

    # ============== Objective (section 4) ==============

    source_activation = pulp.lpSum(p.source_fixed_cost[s] * alpha[s] for s in p.source_ids)
    plant_activation = pulp.lpSum(p.plant_fixed_cost[t] * beta[t] for t in p.plant_ids)
    drawing_water = pulp.lpSum(p.source_unit_cost[s] * a[s] for s in p.source_ids)
    treating_water = pulp.lpSum(p.plant_unit_treatment_cost[t] * inflow[t] for t in p.plant_ids)

    model += (source_activation + plant_activation + drawing_water + treating_water, "Total_Cost")

    # ============= Constraints (section 5) ==============

    # Demand satisfaction
    for z in p.zone_ids:
        model += (pulp.lpSum(c[k] for k in arcs_into_zone[z]) >= p.demand_by_zone[z], f"Demand_{z}")

    # Source capacity and activation
    for s in p.source_ids:
        model += (a[s] >= p.source_min_withdrawal[s] * alpha[s], f"Source_Min_{s}")
        model += (a[s] <= p.source_max_withdrawal[s] * alpha[s], f"Source_Max_{s}")

    # Plant capacity and activation
    for t in p.plant_ids:
        model += (inflow[t] >= p.plant_min_throughput[t] * beta[t], f"Plant_Min_{t}")
        model += (inflow[t] <= p.plant_max_throughput[t] * beta[t], f"Plant_Max_{t}")

    # Plant flow conservation
    for t in p.plant_ids:
        model += (
            pulp.lpSum(c[k] for k in arcs_from_plant[t]) == inflow[t],
            f"Plant_Conservation_{t}",
        )

    # Source flow conservation
    for s in p.source_ids:
        model += (a[s] == pulp.lpSum(b[k] for k in arcs_from_source[s]), f"Source_Conservation_{s}")

    # Link capacity
    for k in p.source_plant_arcs:
        model += (b[k] <= p.source_plant_link_capacity[k] * gamma[k], f"Link_ST_Cap_{k[0]}_{k[1]}")
    for k in p.plant_zone_arcs:
        model += (c[k] <= p.plant_zone_link_capacity[k] * delta[k], f"Link_TZ_Cap_{k[0]}_{k[1]}")

    # Links require active nodes
    for k in p.source_plant_arcs:
        model += (gamma[k] <= alpha[k[0]], f"Link_ST_Src_{k[0]}_{k[1]}")
    for k in p.plant_zone_arcs:
        model += (delta[k] <= beta[k[0]], f"Link_TZ_Plant_{k[0]}_{k[1]}")

    # Water quality
    for t in p.plant_ids:
        for q in p.quality_parameter_ids:
            load = pulp.lpSum(p.source_quality[(k[0], q)] * b[k] for k in arcs_into_plant[t])
            model += (load >= p.quality_lower_bound[q] * inflow[t], f"Q_Min_{t}_{q}")
            model += (load <= p.quality_upper_bound[q] * inflow[t], f"Q_Max_{t}_{q}")

    variables = {
        "alpha": alpha,
        "a": a,
        "beta": beta,
        "gamma": gamma,
        "b": b,
        "delta": delta,
        "c": c,
    }
    return model, variables


def solve(p: ModelParameters, msg: bool = False) -> tuple[pulp.LpProblem, dict[str, Any]]:
    """Invoke the HiGHS solver on the PuLP problem."""
    model, variables = build_model(p)
    model.solve(pulp.HiGHS(msg=msg))
    return model, variables


def is_optimal(model: pulp.LpProblem) -> bool:
    """True when the solver proved optimality."""
    return model.status == pulp.LpStatusOptimal


def status(model: pulp.LpProblem) -> str:
    """Helper function to return the status of a PuLP."""
    return pulp.LpStatus[model.status]


def total_cost(model: pulp.LpProblem) -> float | None:
    """Objective value, or None when the problem was not solved to optimality."""
    if model.status != pulp.LpStatusOptimal:
        return None
    return pulp.value(model.objective)


# =========================================================
# Helper functions for convenience and not an output format.
# =========================================================


def source_draws(p: ModelParameters, v) -> dict[str, float]:
    """Calculate the volume drawn from each source."""
    return {s: pulp.value(v["a"][s]) or 0.0 for s in p.source_ids}


def flows(p: ModelParameters, v) -> tuple[dict, dict]:
    """Calculate the flows along each arc.

    Returns (source->plant, plant->zone).
    """
    st = {k: pulp.value(v["b"][k]) or 0.0 for k in p.source_plant_arcs}
    tz = {k: pulp.value(v["c"][k]) or 0.0 for k in p.plant_zone_arcs}
    return st, tz


def active(p: ModelParameters, v) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Return the activated sources and plants."""
    return (
        tuple(s for s in p.source_ids if (pulp.value(v["alpha"][s]) or 0) > 0.5),
        tuple(t for t in p.plant_ids if (pulp.value(v["beta"][t]) or 0) > 0.5),
    )


def delivered(p: ModelParameters, v) -> dict[str, float]:
    """Return the volume delivered to each zone."""
    _, tz = flows(p, v)
    return {z: sum(f for k, f in tz.items() if k[1] == z) for z in p.zone_ids}


def oversupply(p: ModelParameters, v) -> dict[str, float]:
    """Delivered minus demand per zone.

    Demand is a lower bound, so excess is forced by a plant minimum and never chosen.
    """
    received = delivered(p, v)
    return {z: received[z] - p.demand_by_zone[z] for z in p.zone_ids}


def blended_quality(p: ModelParameters, v) -> dict[str, dict[str, float]]:
    """Volume-weighted blend at each plant.

    Returns plant -> quality parameter -> value. Plants with no inflow are omitted
    rather than reported as zero.
    """
    st, _ = flows(p, v)
    out: dict[str, dict[str, float]] = {}
    for t in p.plant_ids:
        arcs = [k for k in p.source_plant_arcs if k[1] == t]
        volume = sum(st[k] for k in arcs)
        if volume <= 0:
            continue
        out[t] = {
            q: sum(p.source_quality[(k[0], q)] * st[k] for k in arcs) / volume
            for q in p.quality_parameter_ids
        }
    return out
