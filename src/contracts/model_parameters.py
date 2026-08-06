"""
Model-facing parameter contract. Mirrors the ``ModelParameters`` dataclass currently defined inside the
team's ``preprocessing.py``. It is duplicated here to verifying the formulation independently, so it must not depend on the
team's loader or preprocessing modules.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


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

    def as_formulation_dict(self) -> dict[str, Any]:
        """Expose parameters using the formulation's mathematical names."""
        return {
            "S": self.source_ids,
            "T": self.plant_ids,
            "Z": self.zone_ids,
            "P": self.quality_parameter_ids,
            "A_ST": self.source_plant_arcs,
            "A_TZ": self.plant_zone_arcs,
            "D_z": self.demand_by_zone,
            "F_s": self.source_fixed_cost,
            "F_t": self.plant_fixed_cost,
            "C_s": self.source_unit_cost,
            "C_t": self.plant_unit_treatment_cost,
            "W_lower_s": self.source_min_withdrawal,
            "W_upper_s": self.source_max_withdrawal,
            "V_lower_t": self.plant_min_throughput,
            "V_upper_t": self.plant_max_throughput,
            "L_upper_st": self.source_plant_link_capacity,
            "L_upper_tz": self.plant_zone_link_capacity,
            "Q_sp": self.source_quality,
            "Q_lower_p": self.quality_lower_bound,
            "Q_upper_p": self.quality_upper_bound,
        }


__all__ = ["ModelParameters"]
