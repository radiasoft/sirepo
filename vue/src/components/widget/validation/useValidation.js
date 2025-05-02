/**
 * Base field validation: required/optional.
 */
import { ref, watch } from 'vue'

export function useValidation(field) {
    const isInvalid = ref(false);
    const parsedValue = ref('');
    const rawValue = ref('');

    watch(rawValue, () => {
        parsedValue.value = rawValue.value;
        isInvalid.value = ! field.optional && rawValue.value === '';
    });
    return { isInvalid, parsedValue, rawValue };
}
