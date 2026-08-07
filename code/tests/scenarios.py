"""Parameters built by hand, with no loader or preprocessing.

Building ModelParameters directly keeps these tests about the MILP rather than
what the pipeline produces.

The toy network is three sources into one plant, serving one zone:

    S1 (cheap, low alkalinity)      ‾|
    S2 (mid)                          ---> T1 ---> Z1   demand 100 ML/day
    S3 (expensive, high alkalinity) _|

The alkalinity limits are set so the cheapest source can't meet them on its
own. That forces a real blend, which most of the tests below rely on.
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
        source_fixed_cost={"S1": 0.0, "S2": 0.0, "S3": 0.0},
        plant_fixed_cost={"T1": 0.0},
        source_unit_cost={"S1": 1.0, "S2": 2.0, "S3": 3.0},
        plant_unit_treatment_cost={"T1": 0.1},
        source_min_withdrawal={"S1": 0.0, "S2": 0.0, "S3": 0.0},
        source_max_withdrawal={"S1": 100.0, "S2": 100.0, "S3": 100.0},
        plant_min_throughput={"T1": 0.0},
        plant_max_throughput={"T1": 1000.0},
        source_plant_link_capacity={k: 100.0 for k in arcs_st},
        plant_zone_link_capacity={k: 1000.0 for k in arcs_tz},
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
