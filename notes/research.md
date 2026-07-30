# Notes/research

[Nonlinear Model Predictive Control of a
coagulation chemical dosing unit for water
treatment plants ](https://www.sciencedirect.com/science/article/pii/S1474667016416423)

- coagulation in water treatment plants
- chemistry is very complex and nonlinear

[Nonlinear Model Feedback Linearization Control Strategy of a pH Neutralization Process](https://www.researchgate.net/publication/271471644_Nonlinear_model_feedback_linearization_control_strategy_of_a_pH_neutralization_process)

- pH neutralisation process - "difficult control problem"
- Probably a rather ambitious choice as an initial parameter
- Not sure if this applies to the problem but some good insights here

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

[A Mixed-Integer Programming Approach to Optimal Operations of
Drinking Water Treatment Plant with Verification on an Industrial
Site](https://pubs.acs.org/iecred/article-pdf/64/26/13221/41899072/ie4c04633.pdf)

- Good visualisation of treatment plant structure and process
- Identifies filtration as first step (limestone filter as opposed to lime dosing)
- Gave me the idea: can we do filtration before chemical dosing? If so, how does this affect the model and the assumptions we make about the water chemistry? Could we model this as a fixed percent reduction in turbidity, for example?
