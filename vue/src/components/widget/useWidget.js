/**
 * Base widget implementation.
 */
import { ref, watch } from 'vue'

export function useWidget(ui_ctx, field_name) {
    const enabled = ref(true);

    const field = () => ui_ctx[field_name];

    watch(() => field().enabled, () => {
        enabled.value = field().enabled;
    });

    return { enabled, field };
}
