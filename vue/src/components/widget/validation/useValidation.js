/**
 * Base field validation: required/optional.
 */
import { ref, watch } from 'vue'

export function useValidation(field) {
    const isInvalid = ref(false);
    const parsedValue = ref('');
    const rawValue = ref('');

    watch(rawValue, () => {
        if (! field.optional && rawValue.value === '') {
            isInvalid.value = true;
            return;
        }
        parsedValue.value = rawValue.value;
        isInvalid.value = false;
    });
    return { isInvalid, parsedValue, rawValue };
}
