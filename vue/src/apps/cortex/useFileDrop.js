import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

export function useFileDrop(dropPanel, onDrop, acceptMimeType) {
    const dragEnterCount = ref(0);
    const isOverDropZone = ref(false);
    const isInvalidMimeType = ref(false);
    const events = ['dragenter', 'dragover', 'dragleave', 'drop']

    function handleDragEvent(e) {
        e.preventDefault()
        isInvalidMimeType.value = acceptMimeType && e?.dataTransfer?.items[0].type !== acceptMimeType;
        if (e.type === 'dragover') {
            return;
        }
        if (e.type === 'drop') {
            dragEnterCount.value = 0;
            if (! isInvalidMimeType.value) {
                onDrop(e.dataTransfer.files);
            }
        }
        if (e.type === 'dragenter') {
            dragEnterCount.value++;
        }
        else if (e.type === 'dragleave') {
            dragEnterCount.value--;
        }
    }

    onMounted(async () => {
        events.forEach((eventName) => {
            dropPanel.value.addEventListener(eventName, handleDragEvent);
        });
    });

    onBeforeUnmount(() => {
        events.forEach((eventName) => {
            dropPanel.value.removeEventListener(eventName, handleDragEvent);
        });
    });

    watch(dragEnterCount, () => {
        isOverDropZone.value = dragEnterCount.value > 0;
    });

    return { isOverDropZone, isInvalidMimeType };
}
