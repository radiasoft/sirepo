
import { MODEL_CHANGED_EVENT } from '@/services/appstate.js';
import { useSubscription } from '@/components/useSubscription.js';

export function useModelChanged(callback) {
    useSubscription(MODEL_CHANGED_EVENT, callback);
}
