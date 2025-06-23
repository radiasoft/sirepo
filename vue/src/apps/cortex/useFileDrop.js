import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

export function useFileDrop(dropAreaElement, onDrop, acceptMimeType) {
    let dragEnterCount = 0;
    const events = {
        dragenter: () => dragEnterCount++,
        dragleave: () => dragEnterCount--,
        dragover: () => {},
        drop: (e) => {
            dragEnterCount = 0;
            if (! isInvalidMimeType.value) {
                onDrop(e.dataTransfer.files);
            }
        },
    };
    const isInvalidMimeType = ref(false);
    const isOverDropZone = ref(false);

    const handleDragEvent = (e) => {
        e.preventDefault()
        isInvalidMimeType.value = acceptMimeType && e?.dataTransfer?.items[0].type !== acceptMimeType;
        events[e.type](e);
        isOverDropZone.value = dragEnterCount > 0;
    };

    const updateListeners = (method) => {
        Object.keys(events).forEach((eventName) => {
            dropAreaElement.value[method](eventName, handleDragEvent);
        });
    };

    onBeforeUnmount(() => updateListeners('removeEventListener'));
    onMounted(() => updateListeners('addEventListener'));

    return { isOverDropZone, isInvalidMimeType };
}
