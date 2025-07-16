
import { pubSub } from '@/services/pubsub.js';
import { onMounted, onUnmounted } from 'vue';

export function useSubscription(event, callback) {
    onMounted(() => {
        pubSub.subscribe(event, callback);
    });

    onUnmounted(() => {
        pubSub.unsubscribe(event, callback);
    });
}
