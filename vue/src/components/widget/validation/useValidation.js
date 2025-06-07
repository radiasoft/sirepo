/**
 * Base field validation: required/optional.
 */
import { ref, watch } from 'vue'

export function useValidation(field, validator) {
    const isInvalid = ref(false);
    const parsedValue = ref('');
    const rawValue = ref('');

    watch(rawValue, () => {
        field.error = '';
        parsedValue.value = rawValue.value;
        isInvalid.value = false;
        if (! field.optional && rawValue.value === '') {
            isInvalid.value = true;
            return;
        }
        if (validator && rawValue.value) {
            isInvalid.value = validator(parsedValue, rawValue) || false;
        }
    });

    return { isInvalid, parsedValue, rawValue };
}
