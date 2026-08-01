# Notes/research

## Australian Water Drinking Guidelines

[Australian Water Drinking Guidelines - Calcium Hydroxide (Ca(OH)2)](https://guidelines.nhmrc.gov.au/australian-drinking-water-guidelines/part-5/treatment-chemicals/calcium-hydroxide)

- Lime/hydrated lime
- Adds hydroxide ions to water, increasing pH and alkalinity
- Softens hard water
- 5 - 500mg/L range
- Essentially, treating with lime has multiple effects on water chemistry

[Australian Water Drinking Guidelines - Sodium carbonate](https://guidelines.nhmrc.gov.au/australian-drinking-water-guidelines/part-5/treatment-chemicals/sodium-carbonate#general-description)

- More expensive than lime, easier to handle
- Mainly used to increase pH and alkalinity
- "should be used in such a way that any contaminant or by-product formed by the use of the chemical does not exceed guideline values"

[Australian Water Drinking Guidelines - Turbidity](https://guidelines.nhmrc.gov.au/australian-drinking-water-guidelines/part-5/physical-chemical-characteristics/turbidity#general-description)

- Chlorine-based disinfection - does not address all pathogens - "efficiency is impaired above pH 8.0"
- Reduction (particle removal) through filtration
- "consequently the target for the turbidity of water leaving individual filters should be less than 0.2 NTU, and should not exceed 0.5 NTU at any time."

---

## Melbourne Water

[Desalination plant](https://www.melbournewater.com.au/water-and-environment/water-management/water-quality/water-treatment/desalination)

- Highlighting process of desalination and water treatment, including filtration, transport and dosing with minerals

[Transfer arcs](https://www.melbournewater.com.au/media/23211)

- Transfer arcs between Melbourne water reservoirs
- Important note "Tarago, on the other hand, is not connected to another reservoir. Water is treated at its onsite treatment plant and then supplied to the Mornington Peninsula. Water from the Desalination Plant enters our supply system at Cardinia Reservoir, where it mixes with water from our catchments supplied from Silvan."

[Water supply system](https://www.melbournewater.com.au/water-and-environment/water-management/water-quality/our-water-supply-system)

- 10 water storage reservoirs
- 40 service reservoirs (what is this?)
- 13 water treatment plants (want to know how these operate)
- "approximately 1,100 km of aqueducts and underground water mains, delivering water to the retail water companies"
- "water storage reservoirs help improve water quality"

[Water treatment](https://www.melbournewater.com.au/water-and-environment/water-management/water-quality/water-treatment)

- Winneke and Tarago (open catchments) - full treatment process listed (which can we model? filtration?)
- Protected catchments - "three smaller membrane filtration plants", "six UV disinfection plants", "chlorination plants located at all major water treatment plants".

---

[A Mixed-Integer Programming Approach to Optimal Operations of
Drinking Water Treatment Plant with Verification on an Industrial
Site](https://pubs.acs.org/iecred/article-pdf/64/26/13221/41899072/ie4c04633.pdf)

- Good visualisation of treatment plant structure and process
- Identifies filtration as first step (limestone filter as opposed to lime dosing)
- Gave me the idea: can we do filtration before chemical dosing? If so, how does this affect the model and the assumptions we make about the water chemistry? Could we model this as a fixed percent reduction in turbidity, for example?

**Rough idea:**
Introduce a new parameter $R_{tp} \in (0,1)$ that represents the fraction of parameter $p$ removed by filtration at plant $t$. Introduce a binary variable $\epsilon_t$ that indicates if filtration is active at a plant $t$. Then, the quality constraint is modified:

$$
\underline{Q}_{p}b_{st} \le (1 - R_{tp})Q_{p}b_{st} \le \overline{Q}_{p}b_{st}, \quad \forall t \in T, \forall p \in P
$$

Assumptions/issues:

- Assume no backwashing losses or cleaning required, assume uniform diameter size of filter media (only one type of filter at a plant), assume no clogging of filter media [Effectiveness of sand media filters for removing turbidity](https://www.sciencedirect.com/science/article/pii/S0378377412001187)
- Assume filter removes a fixed percentage of turbidity (or other applicable parameters).
- Assume no cost associated with using filter (fixed activation cost?, variable cost per unit of water filtered?).

---

## Nonlinearities in water treatment

[Linearizing feedforward–feedback control of pH processes based on the Wiener model](https://www.sciencedirect.com/science/article/pii/S0959152404000484)

- Raises point about the hydrogen ion concentration being defined at 25 degrees Celsius (is this an assumption we missed? Or irrelevant?)
- "typically 'S' shaped static curve relating the input (control reagent flow rate) to the output (pH) that characterizes the nonlinearity associated with pH systems"

[Nonlinear Model Predictive Control of a
coagulation chemical dosing unit for water
treatment plants](https://www.sciencedirect.com/science/article/pii/S1474667016416423)

- coagulation in water treatment plants - coagulation frequently comes up
- chemistry is very complex and nonlinear

[Nonlinear Model Feedback Linearization Control Strategy of a pH Neutralization Process](https://www.researchgate.net/publication/271471644_Nonlinear_model_feedback_linearization_control_strategy_of_a_pH_neutralization_process)

- pH neutralisation process - "difficult control problem"
- Probably a rather ambitious choice as an initial parameter
- Not sure if this applies to the problem but some good insights here

---
