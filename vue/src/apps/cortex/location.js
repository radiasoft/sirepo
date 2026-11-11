// POSIT: sirepo.sim_api.cortex.material_xlsx location values, slab.py.jinja
// puts a plasma-facing material in the armor layer and any other in the first wall
export const LOCATION_HEADING = 'Location';

export const locationName = (isPlasmaFacing) => isPlasmaFacing ? 'Armor' : 'First Wall';
