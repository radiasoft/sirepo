
import { appState } from '@/services/appstate.js';
import { ref } from 'vue';
import { useModelChanged } from '@/components/useModelChanged.js';

export function useSimModal(modelName, initialValuesCallback, createdCallback) {
    const modalRef = ref(null);

    useModelChanged((names) => {
        if (names[0] === modelName) {
            createdCallback(appState.models[modelName]);
        }
    });

    const showModal = async (...args) => {
        await appState.clearModels({
            [modelName]: appState.setModelDefaults(initialValuesCallback(...args), modelName),
        });
        modalRef.value.showModal();
    };

    return { modalRef, showModal };
}
