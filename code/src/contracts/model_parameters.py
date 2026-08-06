"""Model-facing parameter contract.

Mirrors the ``ModelParameters`` dataclass currently defined inside the team's
``preprocessing.py``.

https://github.com/ksuraev/Aqua-Blend-MILP-Team/blob/main/MILP/src/preprocessing.py

It is duplicated here to verifying the formulation independently,
so it must not depend on the team's loader or preprocessing modules.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ModelParameters:
    # Sets: S, T, Z and P
    source_ids: tuple[str, ...]
    plant_ids: tuple[str, ...]
    zone_ids: tuple[str, ...]
    quality_parameter_ids: tuple[str, ...]

    # Transfer arcs
    source_plant_arcs: tuple[tuple[str, str], ...]
    plant_zone_arcs: tuple[tuple[str, str], ...]

    # Demand and cost parameters
    demand_by_zone: dict[str, float]
    source_fixed_cost: dict[str, float]
    plant_fixed_cost: dict[str, float]
    source_unit_cost: dict[str, float]
    plant_unit_treatment_cost: dict[str, float]

    # Source and plant capacities
    source_min_withdrawal: dict[str, float]
    source_max_withdrawal: dict[str, float]
    plant_min_throughput: dict[str, float]
    plant_max_throughput: dict[str, float]

    # Arc/link capacites
    source_plant_link_capacity: dict[tuple[str, str], float]
    plant_zone_link_capacity: dict[tuple[str, str], float]

    # Transformed water-quality values and bounds
    source_quality: dict[tuple[str, str], float]
    quality_lower_bound: dict[str, float]
    quality_upper_bound: dict[str, float]
    quality_units: dict[str, str]

    warnings: tuple[str, ...] = ()


__all__ = ["ModelParameters"]
