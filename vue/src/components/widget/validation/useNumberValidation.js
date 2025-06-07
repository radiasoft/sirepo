/**
 * Numeric (integer or float) field validation.
 */
import { watch } from 'vue'
import { useValidation } from '@/components/widget/validation/useValidation.js'

export function useNumberValidation(field) {
    const NUMBER_REGEXP = /^\s*(\-|\+)?(\d+|(\d*(\.\d*)))([eE][+-]?\d+)?\s*$/;

    return useValidation(field, (parsedValue, rawValue) => {
        if (! NUMBER_REGEXP.test(rawValue.value)) {
            return true;
        }
        parsedValue.value = parseFloat(rawValue.value);
        if (field.widget === 'integer') {
            parsedValue.value = parseInt(parsedValue.value);
        }
        if ('min' in field) {
            if (parsedValue.value < field.min) {
                return true;
            }
        }
        if ('max' in field) {
            if (parsedValue.value > field.max) {
                return true;
            }
        }
    });
}
