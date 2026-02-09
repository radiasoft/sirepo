
import { MODEL_SAVED_EVENT } from '@/services/appstate.js';
import { useSubscription } from '@/components/useSubscription.js';

export function useModelSaved(callback) {
    useSubscription(MODEL_SAVED_EVENT, callback);
}
