/**
 * Base widget implementation.
 */
import { ref, watch } from 'vue'

export function useWidget(ui_ctx, field_name) {
    const field = () => ui_ctx.fields[field_name];

    const enabled = ref(field().enabled);
    const error = ref(field().error);

    const onInput = () => {
        field().dirty = true;
    };

    watch(() => field().enabled, () => {
        enabled.value = field().enabled;
    });

    watch(() => field().error, () => {
        error.value = field().error;
    });

    return { enabled, error, field, onInput };
}
