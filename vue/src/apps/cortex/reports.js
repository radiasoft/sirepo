// POSIT: the names are sirepo.template.cortex NEUTRONICS_REPORTS (the impurity
// reports of SIM_VERSION are only run from the Impurities tab)
// label is for controls, title spells out the breeding blanket concept
export const REPORTS = [
    {
        name: 'hcllSlabAnimation',
        label: 'HCLL Slab',
        title: 'Helium-Cooled Lithium-Lead (HCLL) Slab',
    },
    {
        name: 'hcpbSlabAnimation',
        label: 'HCPB Slab',
        title: 'Helium-Cooled Pebble Bed (HCPB) Slab',
    },
    {
        name: 'wcllSlabAnimation',
        label: 'WCLL Slab',
        title: 'Water-Cooled Lithium-Lead (WCLL) Slab',
    },
];

// run on import, listed with the materials and needed to make a material public
// POSIT: sirepo.sim_api.cortex.material_db DEFAULT_LIST_MODEL
export const DEFAULT_REPORT = 'hcpbSlabAnimation';

// POSIT: sirepo.template.cortex impurity_report
// e.g. hcpbSlabAnimation, 'max' -> hcpbSlabMaxImpurityAnimation
export const impurityReport = (report, impurity) => report.replace(
    'SlabAnimation',
    `Slab${impurity[0].toUpperCase()}${impurity.slice(1)}ImpurityAnimation`,
);
