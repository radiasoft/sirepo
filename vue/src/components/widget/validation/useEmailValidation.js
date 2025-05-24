/**
 * Email field validation.
 */
import { watch } from 'vue'
import { useValidation } from '@/components/widget/validation/useValidation.js'

export function useEmailValidation(field) {
    const { isInvalid, parsedValue, rawValue } = useValidation(field);

    watch(rawValue, () => {
        if (isInvalid.value) {
            return;
        }
        if (field.optional && rawValue.value === '') {
            return;
        }
        if (! ( rawValue.value && rawValue.value.match(/^.+@.+\..+$/) )) {
            isInvalid.value = true;
            return;
        }
    });

    return { isInvalid, parsedValue, rawValue };
}
