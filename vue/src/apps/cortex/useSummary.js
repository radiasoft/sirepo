import { util } from '@/services/util.js';

export const SUMMARY_COLUMNS = [
    {
        name: 'dpa_fpy',
        heading: 'DPA',
        subheading: 'per fpy',
        std: true,
    },
    {
        name: 'h_appm_fpy',
        heading: 'H',
        subheading: 'appm / fpy',
        std: true,
    },
    {
        name: 'he_appm_fpy',
        heading: 'HE',
        subheading: 'appm / fpy',
        std: true,
    },
    {
        name: 'activity_bq_per_kg_at_100y',
        heading: 'Activity',
        subheading: 'Bq/kg @ 100y',
        format: (v) => util.formatExponential(v),
        numeric: true,
    },
    {
        name: 'decayheat_w_per_cm3_at_100y',
        heading: 'Decay Heat',
        subheading: 'W/cm³ @ 100y',
        format: (v) => util.formatExponential(v),
        numeric: true,
    },
];

// maxDecimals caps the precision std-paired columns are shown at (undefined = uncapped)
export function useSummary(maxDecimals) {

    const stdDecimals = (value) => {
        if (! value) {
            return 3;
        }
        const d = Math.max(0, 3 - Math.floor(Math.log10(Math.abs(value))));
        return maxDecimals === undefined ? d : Math.min(maxDecimals, d);
    };

    const formatValue = (row, col) => {
        const v = row[col.name];
        if (v === undefined || v === null) {
            return '';
        }
        if (col.std) {
            return v.toFixed(stdDecimals(v));
        }
        return col.format ? col.format(v) : v;
    };

    const formatStd = (row, col) => {
        const v = row[`${col.name}_std`];
        if (v === undefined || v === null) {
            return '';
        }
        // match the value's own precision, so "value ± std" lines up
        return v.toFixed(stdDecimals(row[col.name]));
    };

    return { formatValue, formatStd };
}
