
import { defineStore } from 'pinia'

export const useModelStore = defineStore('models', {
    state: () => ({
        dog: {
            first_name: 'Scooby',
            last_name: 'Doo',
            balance: 1.25,
            treats: '2x',
        },
    }),
    actions: {
        saveModels() {
        },
    },
});
