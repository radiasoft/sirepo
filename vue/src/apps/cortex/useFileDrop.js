import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

export function useFileDrop(dropPanel, onDrop) {
    const dragEnterCount = ref(0);
    const isOverDropZone = ref(false);
    const events = ['dragenter', 'dragover', 'dragleave', 'drop']

    function handleDragEvent(e) {
        e.preventDefault()
        if (e.type === 'dragover') {
            return;
        }
        if (e.type === 'drop') {
            dragEnterCount.value = 0;
            onDrop(e.dataTransfer.files);
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

    return { isOverDropZone };
}
