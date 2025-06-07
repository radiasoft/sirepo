/**
 * Email field validation.
 */
import { watch } from 'vue'
import { useValidation } from '@/components/widget/validation/useValidation.js'

export function useEmailValidation(field) {
    return useValidation(field, (parsedValue, rawValue) => {
        if (! ( rawValue.value && rawValue.value.match(/^.+@.+\..+$/) )) {
            return true;
        }
    });
}
