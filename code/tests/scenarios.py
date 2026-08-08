"""Constructing ``ModelParameters`` directly rather than relying on the pipeline
that produces it.

The toy network is three sources feeding one plant, which serves one zone:

    A (cheap, low alkalinity)      --|
    B (mid)                          ---> T1 ---> Z1   demand 100 ML/day
    C (expensive, high alkalinity) --|

Alkalinity limits are set so that the cheapest source alone cannot satisfy
them. Blending is therefore required.
"""

from __future__ import annotations

from src.contracts import ModelParameters

PH = "hydrogen_ion_concentration_mol_l"
ALK = "alkalinity"
TURB = "turbidity"


def ph_to_mol_l(ph: float) -> float:
    """Match the transform preprocessing currently applies."""
    return 10.0**-ph


def toy() -> ModelParameters:
    """Three sources, one plant, one zone. Alkalinity forces a blend."""
    sources = ("S1", "S2", "S3")
    arcs_st = (("S1", "T1"), ("S2", "T1"), ("S3", "T1"))
    arcs_tz = (("T1", "Z1"),)

    quality = {}
    for source_id, ph, alk, turb in (
        ("S1", 7.0, 30.0, 1.0),
        ("S2", 7.5, 50.0, 2.0),
        ("S3", 8.0, 70.0, 3.0),
    ):
        quality[(source_id, PH)] = ph_to_mol_l(ph)
        quality[(source_id, ALK)] = alk
        quality[(source_id, TURB)] = turb

    return ModelParameters(
        source_ids=sources,
        plant_ids=("T1",),
        zone_ids=("Z1",),
        quality_parameter_ids=(PH, ALK, TURB),
        source_plant_arcs=arcs_st,
        plant_zone_arcs=arcs_tz,
        demand_by_zone={"Z1": 100.0},
        source_fixed_cost={"S1": 10.0, "S2": 10.0, "S3": 40.0},
        plant_fixed_cost={"T1": 0.0},
        source_unit_cost={"S1": 1.0, "S2": 2.0, "S3": 3.0},
        plant_unit_treatment_cost={"T1": 0.1},
        source_min_withdrawal={"S1": 0.0, "S2": 0.0, "S3": 0.0},
        source_max_withdrawal={"S1": 100.0, "S2": 100.0, "S3": 100.0},
        plant_min_throughput={"T1": 0.0},
        plant_max_throughput={"T1": 1000.0},
        source_plant_link_capacity={k: 100.0 for k in arcs_st},
        plant_zone_link_capacity={k: 1000.0 for k in arcs_tz},
        source_plant_transfer_cost={k: 0.0 for k in arcs_st},
        plant_zone_transfer_cost={k: 0.0 for k in arcs_tz},
        source_quality=quality,
        # pH 6.5 to 8.5 expressed as hydrogen ion concentration, so the bounds invert
        quality_lower_bound={
            PH: ph_to_mol_l(8.5),
            ALK: 40.0,
            TURB: 0.0,
        },
        quality_upper_bound={
            PH: ph_to_mol_l(6.5),
            ALK: 200.0,
            TURB: 5.0,
        },
        quality_units={PH: "mol/L", ALK: "mg/L CaCO3", TURB: "NTU"},
        warnings=(),
    )


def two_plants() -> ModelParameters:
    """Two sources, two plants, one zone: the smallest network with a routing choice."""
    sources = ("S1", "S2")
    plants = ("T1", "T2")
    arcs_st = (("S1", "T1"), ("S1", "T2"), ("S2", "T1"), ("S2", "T2"))
    arcs_tz = (("T1", "Z1"), ("T2", "Z1"))

    quality = {}
    for sid in sources:
        quality[(sid, PH)] = ph_to_mol_l(7.2)
        quality[(sid, ALK)] = 50.0
        quality[(sid, TURB)] = 1.0

    return ModelParameters(
        source_ids=sources,
        plant_ids=plants,
        zone_ids=("Z1",),
        quality_parameter_ids=(PH, ALK, TURB),
        source_plant_arcs=arcs_st,
        plant_zone_arcs=arcs_tz,
        demand_by_zone={"Z1": 100.0},
        source_fixed_cost={s: 0.0 for s in sources},
        plant_fixed_cost={t: 0.0 for t in plants},
        source_unit_cost={"S1": 1.0, "S2": 1.0},
        plant_unit_treatment_cost={t: 0.1 for t in plants},
        source_min_withdrawal={s: 0.0 for s in sources},
        source_max_withdrawal={s: 100.0 for s in sources},
        plant_min_throughput={t: 0.0 for t in plants},
        plant_max_throughput={t: 1000.0 for t in plants},
        source_plant_link_capacity={k: 100.0 for k in arcs_st},
        plant_zone_link_capacity={k: 1000.0 for k in arcs_tz},
        source_plant_transfer_cost={k: 0.0 for k in arcs_st},
        plant_zone_transfer_cost={k: 0.0 for k in arcs_tz},
        source_quality=quality,
        quality_lower_bound={PH: ph_to_mol_l(8.5), ALK: 20.0, TURB: 0.0},
        quality_upper_bound={PH: ph_to_mol_l(6.5), ALK: 200.0, TURB: 5.0},
        quality_units={PH: "mol/L", ALK: "mg/L CaCO3", TURB: "NTU"},
        warnings=(),
    )
