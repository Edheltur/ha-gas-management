"""Constants for Gas Management."""

DOMAIN = "gas_management"
GAS_CO2 = "CO₂"

TARE_MASS = "tare_mass"
EQUIPMENT_MASS = "equipment_mass"
ASSEMBLY_MASS = "assembly_mass"
NOMINAL_FILL_MASS = "nominal_fill_mass"
MASS_KEYS = (TARE_MASS, EQUIPMENT_MASS, ASSEMBLY_MASS, NOMINAL_FILL_MASS)

MAX_MASS_KG = 1000
MASS_STEP_KG = 0.001
