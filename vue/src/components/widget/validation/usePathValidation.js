/**
 * File path field validation.
 */
import { watch } from 'vue'
import { useValidation } from '@/components/widget/validation/useValidation.js'

export function usePathValidation(field) {
    const unsafePathChars = '\\/|&:+?\'*"<>'.split('');
    const unsafePathRegexp = new RegExp('[\\' + unsafePathChars.join('\\') + ']');

    return useValidation(field, (parsedValue, rawValue) => {
        if (unsafePathRegexp.test(rawValue.value)) {
            field.error = 'Value must not include: ' +  unsafePathChars.join(' ');
            return true;
        }
        if (/^\.|\.$/.test(rawValue.value)) {
            field.error = 'Value must not start or end with a "."';
            return true;
        }
    });
}
